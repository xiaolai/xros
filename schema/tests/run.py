#!/usr/bin/env python3
"""XROS spec-schema conformance suite.

Guards the bundled validator (schema/tools/xros_validate.py), which is the ONLY
required validator for both commands — if it wrongly accepts an invalid spec the
safety rules fail open.

Sections:
  1. schema preflight — every keyword in the schema is one the validator enforces
  2. valid specs (example + tests/valid/*) validate
  3. forbidden STRUCTURAL pairings are rejected — each ISOLATED so it proves the
     specific rule under test (a mutation must not be rejected only by some other
     rule that happens to fire first)
  4. SEMANTIC gates the JSON Schema cannot express
  5. validator unit vectors (keyword-level behaviour, boolean schemas, JSON equality)
  6. robustness — malformed input must yield a clean INVALID, never a traceback
  7. CLI contract — documented exit codes 0/1/2

`jsonschema` is optional and used only as a parity oracle. Set XROS_STRICT=1 to
require it (use that in CI to catch validator/schema drift).

Run:  python3 schema/tests/run.py
Exit: 0 = all pass, 1 = a conformance failure, 2 = missing bundled validator / strict-mode gap.
"""
import sys
sys.dont_write_bytecode = True   # never leave __pycache__ next to the shipped source

import copy
import glob
import importlib.util
import json
import os
import re
import shutil
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(HERE, "..", "xros-spec.schema.json")
EXAMPLE_PATH = os.path.join(HERE, "..", "examples", "lock-free-queue.spec.json")
XV_PATH = os.path.join(HERE, "..", "tools", "xros_validate.py")
TIERB_PATH = os.path.join(HERE, "valid", "tierB-backtest-partial.json")

loader = importlib.util.spec_from_file_location("xros_validate", XV_PATH)
if loader is None:
    print("MISSING: schema/tools/xros_validate.py")
    sys.exit(2)
xv = importlib.util.module_from_spec(loader)
loader.loader.exec_module(xv)

STRICT = os.environ.get("XROS_STRICT") == "1"
try:
    from jsonschema import Draft202012Validator
    HAVE_JS = True
except ImportError:
    HAVE_JS = False

if not HAVE_JS and STRICT:
    print("STRICT MODE: `jsonschema` is required for the parity lane but is not installed.")
    sys.exit(2)

schema = json.load(open(SCHEMA_PATH, encoding="utf-8"))
example = json.load(open(EXAMPLE_PATH, encoding="utf-8"))
tierB = json.load(open(TIERB_PATH, encoding="utf-8"))
# A Tier-B partial spec whose oracle kind is NOT `backtest`, so rule 3c cannot fire.
# Needed to test rule 3b in isolation (see the structural table below).
tierB_nonbacktest = copy.deepcopy(tierB)
tierB_nonbacktest["verification"]["verifier"]["kind"] = "test-suite"

if HAVE_JS:
    Draft202012Validator.check_schema(schema)
    JS = Draft202012Validator(schema)

    def js_errors(spec):
        return len(list(JS.iter_errors(spec)))
    print("schema: well-formed Draft 2020-12 (jsonschema parity oracle active)")
else:
    print("WARNING: `jsonschema` NOT installed — parity lane SKIPPED (set XROS_STRICT=1 in CI to require it)")

fails = 0


def check(name, ok, detail=""):
    global fails
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}{('  — ' + detail) if detail and not ok else ''}")
    if not ok:
        fails += 1


def safe(fn):
    """A raised exception is itself a failure — the validator must never crash."""
    try:
        return fn()
    except Exception as e:  # noqa: BLE001 - crashing is the thing under test
        print(f"        crashed: {type(e).__name__}: {e}")
        return False


def xv_errors(spec):
    return len(xv.validate_spec(spec, schema))


# ---------------------------------------------------------------- 1. preflight
print("\nschema preflight (no keyword may be silently ignored):")
pre = xv.preflight_schema(schema)
check("every keyword in xros-spec.schema.json is enforced by the validator", not pre,
      "; ".join(pre))

# ------------------------------------------------------------------- 2. valid
print("\nvalid specs:")
valid_files = [EXAMPLE_PATH] + sorted(glob.glob(os.path.join(HERE, "valid", "*.json")))
for path in valid_files:
    spec = json.load(open(path, encoding="utf-8"))
    ok = xv_errors(spec) == 0 and (js_errors(spec) == 0 if HAVE_JS else True)
    check(os.path.relpath(path, HERE), ok, "; ".join(xv.validate_spec(spec, schema)))


def mutate(base, fn):
    d = copy.deepcopy(base)
    fn(d)
    return d


# The isolation bases must themselves be VALID, or an "isolated" negative would be
# proving nothing (it would be rejected for the wrong reason).
print("\nisolation bases are valid (so negatives prove the rule under test):")
check("tierB base valid", xv_errors(tierB) == 0, "; ".join(xv.validate_spec(tierB, schema)))
check("tierB non-backtest base valid", xv_errors(tierB_nonbacktest) == 0,
      "; ".join(xv.validate_spec(tierB_nonbacktest, schema)))

# ------------------------------------------------- 3. structural (ISOLATED)
# Each mutation is applied to a base for which the rule under test is the ONLY
# conditional that can reject it. Rules 3b/4 are based on the Tier-B partial spec
# because starting from complete-only would let Safety Rule 1 reject them first,
# making the test pass even if the rule under test were removed entirely.
structural = [
    ("rule1: complete-only + statistical soundness", example,
     lambda d: d["verification"]["verifier"].__setitem__("soundness", "statistical")),
    ("rule1/3: complete-only + no oracle", example,
     lambda d: d["verification"].__setitem__("verifier", {"kind": "none", "soundness": "none"})),
    ("rule2: open-question + complete-only", example,
     lambda d: d["success"].__setitem__("existenceAssumption", "open-question")),
    ("rule3a: manual kind with soundness=sound", example,
     lambda d: d["verification"]["verifier"].__setitem__("kind", "manual")),
    # ISOLATED on a Tier-B partial whose kind is NOT backtest: rule 1 cannot fire (not
    # complete-only) and rule 3c cannot fire (not a backtest), so ONLY rule 3b rejects.
    ("rule3b [isolated]: soundness=none with mechanical kind", tierB_nonbacktest,
     lambda d: d["verification"]["verifier"].__setitem__("soundness", "none")),
    ("rule3c [isolated]: backtest marked sound", tierB,
     lambda d: d["verification"]["verifier"].__setitem__("soundness", "sound")),
    ("rule4 [isolated]: mechanical oracle without command", tierB,
     lambda d: d["verification"]["verifier"].pop("command")),
    ("rule4 [isolated]: mechanical oracle without artifactToVerify", tierB,
     lambda d: d["verification"]["verifier"].pop("artifactToVerify")),
    ("count: nonGoals < 2", example,
     lambda d: d["success"].__setitem__("nonGoals", d["success"]["nonGoals"][:1])),
    ("count: approaches < 3", example,
     lambda d: d["search"].__setitem__("approaches", d["search"]["approaches"][:2])),
    ("count: adversarialChecklist < 2", example,
     lambda d: d["verification"].__setitem__("adversarialChecklist", d["verification"]["adversarialChecklist"][:1])),
    ("required: verifier.soundness missing", example,
     lambda d: d["verification"]["verifier"].pop("soundness")),
    ("bound: verificationVotes above maximum", example,
     lambda d: d["verification"].__setitem__("verificationVotes", 999)),
    # Rule 5 ISOLATED on the Tier-B partial (already statistical): dropping the ceiling
    # is the ONLY defect, so only rule 5 can reject it.
    ("rule5 [isolated]: statistical check without ceiling", tierB,
     lambda d: d["verification"]["verifier"].pop("ceiling")),
    ("rule5 [isolated]: none-soundness check without ceiling",
     json.load(open(os.path.join(HERE, "valid", "tierC-manual-partial.json"), encoding="utf-8")),
     lambda d: d["verification"]["verifier"].pop("ceiling")),
    ("enum: bad provenance value", example,
     lambda d: d["search"]["approaches"][0].__setitem__("provenance", "made-up")),
    ("enum: bad ontology standing value", example,
     lambda d: d["objective"]["ontology"][0].__setitem__("standing", "made-up")),
    ("bad asOf date format", example,
     lambda d: d["verification"]["verifier"].__setitem__("asOf", "July 20")),
    ("deferredVerification tripwire missing owner",
     json.load(open(os.path.join(HERE, "valid", "tierC-manual-partial.json"), encoding="utf-8")),
     lambda d: d["deferredVerification"]["tripwires"][0].pop("owner")),
    ("deferredVerification tripwire missing byWhen",
     json.load(open(os.path.join(HERE, "valid", "tierC-manual-partial.json"), encoding="utf-8")),
     lambda d: d["deferredVerification"]["tripwires"][0].pop("byWhen")),
    ("path: absolute artifactToVerify", example,
     lambda d: d["verification"]["verifier"].__setitem__("artifactToVerify", ["/etc/passwd"])),
    ("path: '..' traversal", example,
     lambda d: d["verification"]["verifier"].__setitem__("artifactToVerify", ["../escape.tla"])),
    ("path: embedded traversal a/../b", example,
     lambda d: d["verification"]["verifier"].__setitem__("artifactToVerify", ["a/../b.tla"])),
    ("path: windows drive form", example,
     lambda d: d["verification"]["verifier"].__setitem__("artifactToVerify", ["C:\\evil.tla"])),
    ("path: leading ~ (home expansion)", example,
     lambda d: d["verification"]["verifier"].__setitem__("artifactToVerify", ["~/x.tla"])),
    ("required: provenance missing on an approach", example,
     lambda d: d["search"]["approaches"][0].pop("provenance")),
    ("required: provenance missing on a checklist item", example,
     lambda d: d["verification"]["adversarialChecklist"][0].pop("provenance")),
    ("whitespace-only ceiling (statistical)", tierB,
     lambda d: d["verification"]["verifier"].__setitem__("ceiling", "   ")),
    ("whitespace-only ceiling (none)",
     json.load(open(os.path.join(HERE, "valid", "tierC-manual-partial.json"), encoding="utf-8")),
     lambda d: d["verification"]["verifier"].__setitem__("ceiling", " \t\n ")),
    ("byWhen 'eventually' fails ISO shape",
     json.load(open(os.path.join(HERE, "valid", "tierC-manual-partial.json"), encoding="utf-8")),
     lambda d: d["deferredVerification"]["tripwires"][0].__setitem__("byWhen", "eventually")),
]
print("\nforbidden STRUCTURAL pairings (both validators must REJECT):")
for name, base, fn in structural:
    d = mutate(base, fn)
    ok = safe(lambda: xv_errors(d) > 0 and ((js_errors(d) > 0) if HAVE_JS else True))
    check(name, ok)

# --------------------------------------------------------------- 4. semantic
semantic = [
    ("maxRounds < minRounds", example,
     lambda d: d["stopping"].update({"minRounds": 5, "maxRounds": 3})),
    ("fewer than 3 distinct families", example,
     lambda d: [a.__setitem__("family", "same") for a in d["search"]["approaches"]]),
    ("duplicate approach names (they key route state)", example,
     lambda d: [a.__setitem__("name", "dup") for a in d["search"]["approaches"]]),
    ("asOf impossible calendar date (2026-99-99)", tierB,
     lambda d: d["verification"]["verifier"].__setitem__("asOf", "2026-99-99")),
    ("asOf non-leap-year Feb 29", tierB,
     lambda d: d["verification"]["verifier"].__setitem__("asOf", "2025-02-29")),
    ("tripwire byWhen impossible date (2026-13-40)",
     json.load(open(os.path.join(HERE, "valid", "tierC-manual-partial.json"), encoding="utf-8")),
     lambda d: d["deferredVerification"]["tripwires"][0].__setitem__("byWhen", "2026-13-40")),
]
print("\nSEMANTIC gates (bundled validator REJECTS; jsonschema alone would accept):")
for name, base, fn in semantic:
    d = mutate(base, fn)
    ok = safe(lambda: xv_errors(d) > 0 and ((js_errors(d) == 0) if HAVE_JS else True))
    check(name, ok)

# -------------------------------------------------- 4b. mutation testing
# The only real proof that a negative targets its rule: delete the rule from the
# schema and confirm the case is then ACCEPTED. Without this, a test can pass
# because some *other* conditional rejected the mutation first.
print("\nmutation testing (delete a rule → its negative must stop failing):")


def schema_without(rule_key):
    s = copy.deepcopy(schema)
    s["allOf"] = [r for r in s["allOf"] if rule_key not in r.get("description", "")]
    return s, len(s["allOf"]) == len(schema["allOf"]) - 1


mutation_cases = [
    ("rule 1", "Safety rule 1", example,
     lambda d: d["verification"]["verifier"].__setitem__("soundness", "statistical")),
    ("rule 2", "Safety rule 2", example,
     lambda d: d["success"].__setitem__("existenceAssumption", "open-question")),
    ("rule 3b", "Consistency 3b", tierB_nonbacktest,
     lambda d: d["verification"]["verifier"].__setitem__("soundness", "none")),
    ("rule 3c", "Consistency 3c", tierB,
     lambda d: d["verification"]["verifier"].__setitem__("soundness", "sound")),
    ("rule 4", "Rule 4", tierB,
     lambda d: d["verification"]["verifier"].pop("command")),
    ("rule 5", "Rule 5", tierB,
     lambda d: d["verification"]["verifier"].pop("ceiling")),
    ("rule 3a", "Consistency 3a", example,
     lambda d: d["verification"]["verifier"].__setitem__("kind", "manual")),
]
for name, key, base, fn in mutation_cases:
    d = mutate(base, fn)
    reduced, matched = schema_without(key)
    rejected_now = len(xv.validate_spec(d, schema)) > 0
    accepted_without = len(xv.validate_spec(d, reduced)) == 0
    check(f"{name} negative is isolated (targets only that rule)",
          matched and rejected_now and accepted_without,
          f"matched={matched} rejected_now={rejected_now} accepted_without={accepted_without}")

# ------------------------------------------------------- 5. validator units
print("\nvalidator unit vectors:")
check("boolean schema `false` rejects", xv.validate(1, False) != [])
check("boolean schema `true` accepts", xv.validate(1, True) == [])
check("non-dict/non-bool schema node is an error", xv.validate(1, "nonsense") != [])
check("True is NOT integer 1 (type)", xv.validate(True, {"type": "integer"}) != [])
check("True is NOT const 1 (JSON equality)", xv.validate(True, {"const": 1}) != [])
check("1 is NOT const true (JSON equality)", xv.validate(1, {"const": True}) != [])
check("True is NOT in enum [1]", xv.validate(True, {"enum": [1]}) != [])
check("3.0 IS an integer (Draft 2020-12)", xv.validate(3.0, {"type": "integer"}) == [])
check("3.5 is NOT an integer", xv.validate(3.5, {"type": "integer"}) != [])
check("maxItems enforced", xv.validate([1, 2, 3], {"maxItems": 2}) != [])
check("preflight flags unsupported keyword (oneOf)",
      xv.preflight_schema({"oneOf": [{"type": "string"}]}) != [])
check("preflight flags list-form items",
      xv.preflight_schema({"items": [{"type": "string"}]}) != [])
check("preflight accepts the supported subset",
      xv.preflight_schema({"type": "object", "properties": {"a": {"type": "string"}},
                           "allOf": [{"if": {"const": 1}, "then": {"type": "integer"}}]}) == [])
# keyword-value shape guard (a malformed value must not be silently mis-interpreted)
check("preflight flags string-valued enum", xv.preflight_schema({"enum": "nope"}) != [])
check("preflight flags non-list required", xv.preflight_schema({"required": "a"}) != [])
check("preflight flags string minLength", xv.preflight_schema({"minLength": "5"}) != [])
check("preflight flags dict-form additionalProperties (unimplemented)",
      xv.preflight_schema({"additionalProperties": {"type": "string"}}) != [])
# ECMA/Python regex parity guard
check("preflight flags scoped-flag pattern (?i:...)", xv.preflight_schema({"pattern": "(?i:x)"}) != [])
check("preflight flags atomic group (?>...)", xv.preflight_schema({"pattern": "(?>x)"}) != [])
check("preflight flags \\d (unicode divergence)", xv.preflight_schema({"pattern": "^\\d+$"}) != [])
check("preflight ACCEPTS lookaheads (ECMA-valid)", xv.preflight_schema({"pattern": "^(?!/)[a-z]+$"}) == [])
# real-calendar-date helper
check("_real_date accepts a real date", xv._real_date("2026-07-20"))
check("_real_date rejects 2026-99-99", not xv._real_date("2026-99-99"))
check("_real_date rejects non-leap Feb 29", not xv._real_date("2025-02-29"))
check("_real_date accepts leap Feb 29", xv._real_date("2024-02-29"))

# run.md's agent-produced CANDIDATE path must carry an anti-traversal pattern
# (defense-in-depth so a hostile route agent's path is rejected at the output layer).
print("\nrun.md CANDIDATE.artifactFiles path guard:")
_runmd = open(os.path.join(HERE, "..", "..", "commands", "run.md"), encoding="utf-8").read()
check("CANDIDATE path carries a pattern in run.md",
      re.search(r"path:\s*\{\s*type:\s*'string',\s*pattern:", _runmd) is not None)
# the intended anti-traversal semantics (Python-re equivalent of the shipped ECMA regex)
_intended = re.compile(r"^(?![/\\~])(?![A-Za-z]:)(?!.*(^|/)\.\.?(/|$))[^\\]+$")
check("  intended pattern accepts safe relative paths",
      all(_intended.match(g) for g in ["a.tla", "src/b.lean", "LockFreeQueue.cfg"]))
check("  intended pattern rejects absolute/~/traversal/drive/backslash/dot",
      not any(_intended.match(b) for b in ["/etc/passwd", "~/x", "../escape", "a/../b", "C:\\x", "a\\b", "."]))

# ------------------------------------------------------------ 6. robustness
print("\nrobustness (malformed input → clean INVALID, never a traceback):")
cases = [
    ("integral floats accepted, parity holds",
     mutate(example, lambda d: d["stopping"].update({"minRounds": 3.0, "maxRounds": 12.0})),
     lambda d: xv_errors(d) == 0 and ((js_errors(d) == 0) if HAVE_JS else True)),
    ("float rounds still caught by maxRounds<minRounds",
     mutate(example, lambda d: d["stopping"].update({"minRounds": 5.0, "maxRounds": 3.0})),
     lambda d: xv_errors(d) > 0),
    ("non-object `stopping`", mutate(example, lambda d: d.__setitem__("stopping", "oops")),
     lambda d: xv_errors(d) > 0),
    ("non-object `search`", mutate(example, lambda d: d.__setitem__("search", 42)),
     lambda d: xv_errors(d) > 0),
    ("unhashable family value []",
     mutate(example, lambda d: d["search"]["approaches"][0].__setitem__("family", [])),
     lambda d: xv_errors(d) > 0),
    ("unhashable family value {}",
     mutate(example, lambda d: d["search"]["approaches"][0].__setitem__("family", {})),
     lambda d: xv_errors(d) > 0),
    ("approaches not a list", mutate(example, lambda d: d["search"].__setitem__("approaches", "x")),
     lambda d: xv_errors(d) > 0),
    ("empty verifier command", mutate(example, lambda d: d["verification"]["verifier"].__setitem__("command", "")),
     lambda d: xv_errors(d) > 0),
    ("empty artifactToVerify list", mutate(example, lambda d: d["verification"]["verifier"].__setitem__("artifactToVerify", [])),
     lambda d: xv_errors(d) > 0),
    ("spec is not an object at all", "not-a-dict", lambda d: xv_errors(d) > 0),
    # ceiling is REQUIRED only for statistical/none — a sound check may omit it
    ("sound check may omit ceiling",
     mutate(example, lambda d: d["verification"]["verifier"].pop("ceiling")),
     lambda d: xv_errors(d) == 0 and ((js_errors(d) == 0) if HAVE_JS else True)),
    # ontology terms may carry the optional domain-map honesty fields
    ("ontology term may carry standing/source/provenance",
     mutate(example, lambda d: d["objective"]["ontology"][0].update(
         {"standing": "canonical", "source": "https://example.org/x", "provenance": "assistant-proposed"})),
     lambda d: xv_errors(d) == 0 and ((js_errors(d) == 0) if HAVE_JS else True)),
]
for name, d, pred in cases:
    check(name, safe(lambda: pred(d)))

# ------------------------------------------------------------------- 7. CLI
print("\nCLI contract (documented exit codes):")
# A private temp dir — never a fixed path inside the repo, so a concurrent run can't
# race us and cleanup can never delete unrelated files.
tmp = tempfile.mkdtemp(prefix="xros-cli-test-")
try:
    bad_spec = os.path.join(tmp, "bad.json")
    json.dump(mutate(example, lambda d: d["success"].__setitem__("returnPolicy", "complete-only")
                     or d["verification"]["verifier"].__setitem__("soundness", "statistical")),
              open(bad_spec, "w", encoding="utf-8"))
    malformed = os.path.join(tmp, "malformed.json")
    open(malformed, "w", encoding="utf-8").write("{ not json")

    def run_cli(*args):
        return subprocess.run([sys.executable, XV_PATH, *args],
                              capture_output=True, text=True)

    r = run_cli(SCHEMA_PATH, EXAMPLE_PATH)
    check("exit 0 + 'VALID' on a valid spec", r.returncode == 0 and "VALID" in r.stdout)
    r = run_cli(SCHEMA_PATH, bad_spec)
    check("exit 1 + 'INVALID' on an invalid spec", r.returncode == 1 and "INVALID" in r.stdout)
    r = run_cli(SCHEMA_PATH, malformed)
    check("exit 2 on malformed JSON", r.returncode == 2)
    r = run_cli(SCHEMA_PATH, os.path.join(tmp, "missing.json"))
    check("exit 2 on missing file", r.returncode == 2)
    r = run_cli(SCHEMA_PATH)
    check("exit 2 on wrong argument count", r.returncode == 2)
finally:
    shutil.rmtree(tmp, ignore_errors=True)   # removes only our own private temp dir

print()
if fails:
    print(f"RESULT: {fails} FAILURE(S)")
    sys.exit(1)
print("RESULT: all pass"
      f" ({len(valid_files)} valid, {len(structural)} structural, {len(semantic)} semantic,"
      f" {len(mutation_cases)} mutation, units + parity, {len(cases)} robustness, 5 CLI)")
