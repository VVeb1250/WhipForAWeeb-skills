#!/usr/bin/env py
"""Skill Router — UserPromptSubmit hook.

Local (no-AI) skill suggester. On each user prompt it scores every installed
skill/command by TF-IDF cosine similarity against the prompt, then a curated
hybrid layer (intent-phrase boost + prerequisite fan-out + conflict pruning,
see skill-graph.json) refines the ranking, and it injects only the top matches
that clear a confidence threshold. Silent when nothing is a strong match, so
token cost is ~0 on unrelated prompts. With no skill-graph.json the hybrid
layer is inert and behaviour is identical to the pure TF-IDF baseline.

Unlocks the dormant ~/.claude/skills/ecc/* skills (192) that are installed but
not surfaced in the harness skill list, by emitting a Read path for them.

Safe by construction: any error -> exit 0 with no output (never blocks prompt).
"""
import sys, os, json, re, math, glob, unicodedata

HOME = os.path.expanduser("~")
CLAUDE = os.path.join(HOME, ".claude")
AGENTS = os.path.join(HOME, ".agents")
INDEX = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".skill-index.json")
GRAPH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "skill-graph.json")

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


def load_graph():
    """Curated intent_map + skill graph (requires/conflicts). Optional.

    Hand-maintained, separate from the auto-built .skill-index.json so it
    survives index rebuilds. Missing/invalid -> {} -> router behaves exactly
    like the pure TF-IDF v1 (graph layer is purely additive)."""
    try:
        with open(GRAPH, "r", encoding="utf-8") as f:
            g = json.load(f)
        return g if isinstance(g, dict) else {}
    except (OSError, ValueError):
        return {}


def _tfidf(prompt, skills):
    """TF-IDF cosine of prompt vs each skill doc (name*NAME_WEIGHT + desc).

    Returns {name: [cos, skill]} for every skill clearing COSINE_MIN — unpruned
    and unranked. route() applies intent boost, conflict pruning and ranking."""
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
    scored = {}
    if not qv:
        return scored
    for s, d in zip(skills, docs):
        dv, dn = vec(d)
        dot = sum(qv[t] * dv.get(t, 0) for t in qv)
        cos = dot / (qn * dn)
        if cos >= COSINE_MIN:
            # keep best score on a name collision (cmd vs skill sharing a name)
            if s["name"] not in scored or cos > scored[s["name"]][0]:
                scored[s["name"]] = [cos, s]
    return scored


def _apply_intent(prompt, scored, skills, graph):
    """Boost (or inject) skills whose curated intent phrase is in the prompt.

    Catches the synonym gap TF-IDF can't: a prompt that shares no lexical token
    with a skill's description but expresses its intent ('blast radius' ->
    codegraph-affected). Substring match, no NLP dependency."""
    imap = graph.get("intent_map") or {}
    if not imap:
        return
    bonus = graph.get("intent_bonus", 0.34)
    pl = prompt.lower()
    by_name = {}
    for s in skills:
        by_name.setdefault(s["name"], s)
    for phrase, names in imap.items():
        if phrase in pl:
            for nm in names:
                if nm in scored:
                    scored[nm][0] += bonus           # boost an existing match
                elif nm in by_name:
                    scored[nm] = [bonus, by_name[nm]]  # inject a new candidate


def _prune_conflicts(ranked, graph):
    """Drop a skill if a higher-ranked one declares it as conflicting."""
    g = graph.get("graph") or {}
    if not g:
        return ranked
    out, blocked = [], set()
    for cos, s in ranked:
        if s["name"] in blocked:
            continue
        out.append((cos, s))
        blocked.update(g.get(s["name"], {}).get("conflicts_with", []))
    return out


def _fanout_fill(primary, skills, graph):
    """Fill *spare* result slots with prerequisites of the primary matches.

    Surfaces 'to use codegraph-affected you also need codegraph-link'. Only ever
    fills slots left empty under MAX_RESULTS, so a setup skill never displaces a
    real match and never spams when results are already full."""
    g = graph.get("graph") or {}
    if not g or len(primary) >= MAX_RESULTS:
        return primary
    by_name = {}
    for s in skills:
        by_name.setdefault(s["name"], s)
    have = {s["name"] for _, s in primary}
    factor = graph.get("neighbor_factor", 0.3)
    extra = []
    for cos, s in primary:
        for req in g.get(s["name"], {}).get("requires", []):
            if req in have or any(req == e[1]["name"] for e in extra):
                continue
            if req in by_name:
                extra.append((cos * factor, by_name[req]))
    room = MAX_RESULTS - len(primary)
    return primary + extra[:room]


def route(prompt, skills, graph):
    """Hybrid router: TF-IDF (tier-1) + curated intent boost + conflict prune +
    prerequisite fan-out. With an empty graph this is identical to v1."""
    scored = _tfidf(prompt, skills)
    _apply_intent(prompt, scored, skills, graph)
    if not scored:
        return []
    ranked = sorted(scored.values(), key=lambda x: -x[0])
    ranked = _prune_conflicts(ranked, graph)
    top = ranked[0][0]
    primary = [(c, s) for c, s in ranked if c >= top * REL_MIN][:MAX_RESULTS]
    return _fanout_fill(primary, skills, graph)


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
    tag = "semantic" if semantic else "hybrid"
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
    results = route(prompt, idx.get("skills", []), load_graph())
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
