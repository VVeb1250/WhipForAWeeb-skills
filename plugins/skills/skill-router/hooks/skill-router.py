#!/usr/bin/env py
"""Skill Router — UserPromptSubmit hook.

Local (no-AI) skill suggester. On each user prompt it scores every installed
skill/command by TF-IDF cosine similarity against the prompt and injects only
the top matches that clear a confidence threshold. Silent when nothing is a
strong match, so token cost is ~0 on unrelated prompts.

Unlocks the dormant ~/.claude/skills/ecc/* skills (192) that are installed but
not surfaced in the harness skill list, by emitting a Read path for them.

Safe by construction: any error -> exit 0 with no output (never blocks prompt).
"""
import sys, os, json, re, math, glob, unicodedata

HOME = os.path.expanduser("~")
CLAUDE = os.path.join(HOME, ".claude")
AGENTS = os.path.join(HOME, ".agents")
INDEX = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".skill-index.json")

# ---- tuning ----
COSINE_MIN = 0.16      # absolute confidence floor
REL_MIN = 0.5          # keep results within this fraction of the top score
MAX_RESULTS = 3
MIN_PROMPT_LEN = 8
NAME_WEIGHT = 3        # repeat name tokens N times -> name matches rank higher

STOP = set("""the a an and or but if then else for to of in on at by with from into
as is are was were be been being this that these those it its do does did have has
had not no can will would should could may might must your you i we they he she them
how what why when where which who whom use used using make made get got need want via
please help fix add new code file files project run create update check""".split())

TOKEN_RE = re.compile(r"[a-z0-9]{3,}")


def tok(text):
    return [t for t in TOKEN_RE.findall(text.lower()) if t not in STOP]


def read_frontmatter(path):
    """Return (name, description) from a SKILL.md / command .md frontmatter."""
    name = desc = None
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            head = f.read(4000)
    except OSError:
        return None, None
    if head.startswith("---"):
        end = head.find("\n---", 3)
        block = head[3:end] if end != -1 else head[3:]
        for line in block.splitlines():
            m = re.match(r"\s*name\s*:\s*(.+)", line)
            if m and not name:
                name = m.group(1).strip().strip("'\"")
            m = re.match(r"\s*description\s*:\s*(.+)", line)
            if m and not desc:
                desc = m.group(1).strip().strip("'\"")
    if not desc:
        # fallback: first markdown heading or first non-empty line after frontmatter
        for line in head.splitlines():
            s = line.strip()
            if s and not s.startswith("---") and not s.startswith("#") and ":" not in s[:12]:
                desc = s
                break
    return name, desc


def sources():
    """Yield (glob_pattern, tier, invoke_kind)."""
    yield os.path.join(CLAUDE, "commands", "*.md"), "cmd", "slash"
    yield os.path.join(CLAUDE, "skills", "ecc", "*", "SKILL.md"), "ecc", "read"
    yield os.path.join(CLAUDE, "skills", "*", "SKILL.md"), "skill", "slash"
    yield os.path.join(AGENTS, "skills", "*", "SKILL.md"), "agent", "slash"


def collect_files():
    files = []
    for pat, tier, kind in sources():
        for p in glob.glob(pat):
            # skip the ecc aggregate dir when matched by the top-level skills glob
            if tier == "skill" and os.sep + "ecc" + os.sep in p:
                continue
            files.append((p, tier, kind))
    return files


def signature(files):
    # sum of mtimes catches add/remove/edit (removal drops a term, add adds one,
    # edit raises one) — strictly more sensitive than max() for the same cost.
    mt = 0.0
    for p, _, _ in files:
        try:
            mt += os.path.getmtime(p)
        except OSError:
            pass
    return {"count": len(files), "mtime": round(mt, 3)}


def build_index():
    files = collect_files()
    skills = []
    for path, tier, kind in files:
        name, desc = read_frontmatter(path)
        if not name:
            name = os.path.splitext(os.path.basename(path))[0]
            if name == "SKILL":
                name = os.path.basename(os.path.dirname(path))
        if not desc:
            desc = name
        skills.append({
            "name": name,
            "desc": desc,
            "tier": tier,
            "kind": kind,
            "path": path,
        })
    idx = {"sig": signature(files), "skills": skills}
    try:
        with open(INDEX, "w", encoding="utf-8") as f:
            json.dump(idx, f, ensure_ascii=False)
    except OSError:
        pass
    return idx


def load_index():
    try:
        with open(INDEX, "r", encoding="utf-8") as f:
            idx = json.load(f)
    except (OSError, ValueError):
        return build_index()
    if idx.get("sig") != signature(collect_files()):
        return build_index()
    return idx


def score(prompt, skills):
    """TF-IDF cosine of prompt vs each skill doc (name*NAME_WEIGHT + desc)."""
    docs = []
    for s in skills:
        docs.append(tok(s["name"]) * NAME_WEIGHT + tok(s["desc"]))
    n = len(docs)
    df = {}
    for d in docs:
        for t in set(d):
            df[t] = df.get(t, 0) + 1
    idf = {t: math.log((n + 1) / (c + 1)) + 1 for t, c in df.items()}

    def vec(tokens):
        tf = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1
        v = {t: (c / len(tokens)) * idf.get(t, 0) for t, c in tf.items() if t in idf}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return v, norm

    qv, qn = vec(tok(prompt))
    if not qv:
        return []
    out = []
    for s, d in zip(skills, docs):
        dv, dn = vec(d)
        dot = sum(qv[t] * dv.get(t, 0) for t in qv)
        cos = dot / (qn * dn)
        if cos >= COSINE_MIN:
            out.append((cos, s))
    out.sort(key=lambda x: x[0], reverse=True)
    if not out:
        return []
    top = out[0][0]
    return [(c, s) for c, s in out if c >= top * REL_MIN][:MAX_RESULTS]


def has_foreign_letters(text):
    """True if prompt has non-ASCII *letters* (Thai/CJK/Cyrillic/…), not just
    emoji or punctuation. Gate for the heavy semantic tier."""
    for ch in text:
        if ord(ch) > 127 and unicodedata.category(ch).startswith("L"):
            return True
    return False


def semantic_fallback(prompt):
    """Tier-2: multilingual embedding match. Silent if model/deps missing."""
    try:
        import embed
        return embed.search(prompt)
    except Exception:
        return []


def fmt(results, semantic=False):
    tag = "semantic" if semantic else "cosine≥%.2f" % COSINE_MIN
    lines = ["\U0001f3af Skill router (local, %s):" % tag]
    for cos, s in results:
        if s["kind"] == "read":
            how = "Read " + s["path"]
        else:
            how = "/" + s["name"]
        lines.append("• %s — %s · %s" % (s["name"], s["desc"][:90], how))
    return "\n".join(lines)


def main():
    raw = sys.stdin.buffer.read().decode("utf-8", "ignore") if not sys.stdin.isatty() else ""
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except ValueError:
        payload = {}
    prompt = (payload.get("prompt") or "").strip()
    if len(prompt) < MIN_PROMPT_LEN or prompt.startswith("/"):
        return
    idx = load_index()
    results = score(prompt, idx.get("skills", []))
    semantic = False
    if not results and has_foreign_letters(prompt):
        # tier-2: cross-lingual semantic match (lazy, only on foreign prompts)
        if os.path.dirname(os.path.abspath(__file__)) not in sys.path:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        results = semantic_fallback(prompt)
        semantic = bool(results)
    if not results:
        return
    ctx = fmt(results, semantic=semantic)
    out = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": ctx,
        }
    }
    sys.stdout.buffer.write(json.dumps(out, ensure_ascii=False).encode("utf-8"))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
