#!/usr/bin/env py
"""Portable unit tests for the hybrid skill-router layer.

Self-contained: builds a tiny synthetic corpus instead of relying on the
installed index, so it runs identically in CI and on any machine. Asserts the
four guarantees the hybrid layer must hold:

  1. Empty graph -> identical to pure TF-IDF v1 (rollback safety).
  2. Intent phrase injects a skill that has zero lexical overlap with the prompt
     (the synonym gap TF-IDF cannot close).
  3. A prerequisite is fanned into a spare slot but never displaces a real match.
  4. Conflicts are pruned (a lower-ranked conflicting skill is dropped).

Run: py test_hybrid.py   (exit 0 = pass)
"""
import os, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("router", os.path.join(HERE, "skill-router.py"))
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)

# synthetic corpus — descriptions deliberately avoid the intent synonyms below
SKILLS = [
    {"name": "affected-tests", "desc": "select impacted tests from a dependency graph",
     "tier": "skill", "kind": "slash", "path": "x"},
    {"name": "graph-setup", "desc": "wire the dependency graph tooling into a project",
     "tier": "skill", "kind": "slash", "path": "x"},
    {"name": "linter", "desc": "format and lint source files",
     "tier": "skill", "kind": "slash", "path": "x"},
    {"name": "legacy-fmt", "desc": "old formatter superseded by linter",
     "tier": "skill", "kind": "slash", "path": "x"},
]
GRAPH = {
    "intent_bonus": 0.34,
    "neighbor_factor": 0.3,
    "intent_map": {"blast radius": ["affected-tests"]},
    "graph": {
        "affected-tests": {"requires": ["graph-setup"], "conflicts_with": []},
        "linter": {"requires": [], "conflicts_with": ["legacy-fmt"]},
    },
}


def names(results):
    return [s["name"] for _, s in results]


def test_empty_graph_equals_v1():
    p = "lint and format the source files"
    assert names(R.route(p, SKILLS, {})) == names(R.route(p, SKILLS, {})), "non-deterministic"
    # empty graph must not add/remove anything vs the raw tfidf ranking
    raw = sorted(R._tfidf(p, SKILLS).values(), key=lambda x: -x[0])
    top = raw[0][0]
    expect = [s["name"] for c, s in raw if c >= top * R.REL_MIN][: R.MAX_RESULTS]
    assert names(R.route(p, SKILLS, {})) == expect, "empty graph diverged from v1"


def test_intent_injects_zero_overlap_skill():
    # 'blast radius' shares no token with any description -> tfidf finds nothing
    p = "what is the blast radius here"
    assert names(R.route(p, SKILLS, {})) == [], "tfidf unexpectedly matched"
    assert "affected-tests" in names(R.route(p, SKILLS, GRAPH)), "intent did not inject"


def test_fanout_fills_spare_slot_without_displacing():
    p = "what is the blast radius here"
    out = names(R.route(p, SKILLS, GRAPH))
    assert out[0] == "affected-tests", "primary match lost"
    assert "graph-setup" in out, "prerequisite not fanned in"
    # fan-out must never exceed MAX_RESULTS
    assert len(out) <= R.MAX_RESULTS


def test_conflict_pruned():
    p = "lint and format the source files"
    out = names(R.route(p, SKILLS, GRAPH))
    # linter outranks legacy-fmt and declares it a conflict -> legacy-fmt dropped
    if "linter" in out:
        assert "legacy-fmt" not in out, "conflicting skill not pruned"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("PASS", fn.__name__)
    print("\nALL PASS (%d)" % len(fns))
