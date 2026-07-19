#!/usr/bin/env python3
"""Bundled, dependency-free XROS spec validator.

Uses only the Python standard library (no `jsonschema`, no `npx`) so validation
works offline anywhere python3 exists.

It implements the JSON Schema 2020-12 SUBSET the XROS schema uses:
    type, const, enum, minLength, pattern, minimum, maximum, minItems, maxItems,
    items, required, properties, additionalProperties, allOf, if/then/else,
    plus boolean schemas (true accepts, false rejects).

Because a silently-ignored keyword would make this validator FAIL OPEN (an
invalid spec passing, defeating the safety rules), it first runs a **schema
preflight** that rejects any keyword it does not implement. A future schema
edit that adds `oneOf`/`$ref`/`uniqueItems`/etc. therefore fails LOUDLY here
instead of quietly disabling enforcement.

It also enforces the XROS semantic gates JSON Schema cannot express:
    * stopping.maxRounds >= stopping.minRounds
    * search.approaches has >= 3 DISTINCT family values
    * search.approaches[].name values are UNIQUE (they key runtime route state)

Usage:
    python3 xros_validate.py <schema.json> <spec.json>
Exit: 0 = VALID, 1 = INVALID (errors printed), 2 = usage/IO/schema-preflight error.
"""
import json
import datetime
import re
import sys

# Keywords this validator actually enforces.
SUPPORTED = {
    "type", "const", "enum", "minLength", "pattern", "minimum", "maximum",
    "minItems", "maxItems", "items", "required", "properties",
    "additionalProperties", "allOf", "if", "then", "else",
}
# Pure annotations: safe to ignore, they impose no constraint.
ANNOTATIONS = {
    "$schema", "$id", "$comment", "title", "description", "default",
    "examples", "deprecated", "readOnly", "writeOnly",
}
# Python-only regex constructs. `pattern` is evaluated with Python `re`, but the
# spec mandates ECMA-262; rejecting these keeps the two dialects from diverging.
PY_ONLY_REGEX = ("(?P<", "(?P=", "(?#", "\\A", "\\Z")
# Scoped/inline flag groups (?i:...)/(?i), atomic groups (?>...), and conditionals
# (?(...)...) are all Python-only.
SCOPED_FLAG = re.compile(r"\(\?[aiLmsux]+[:)]|\(\?>|\(\?\(")
# \d and \w match Unicode in Python but ASCII in ECMA-262 (absent /u) — a real
# divergence for date/id patterns; force an explicit [0-9]/[A-Za-z0-9_] class.
UNICODE_DIVERGENT = ("\\d", "\\w")
# Positions whose values are themselves schemas / collections of schemas.
SUBSCHEMA = {"items", "if", "then", "else"}
SUBSCHEMA_LIST = {"allOf"}
SUBSCHEMA_MAP = {"properties"}
NUMERIC_KEYWORDS = {"minLength", "minItems", "maxItems", "minimum", "maximum"}


def _shape_ok(k, v):
    """Does keyword k's VALUE have a shape this validator can interpret? A malformed
    value (e.g. a string-valued `enum`) must be rejected in preflight, not silently
    mis-interpreted at validation time."""
    if k == "type":
        return isinstance(v, str) or (isinstance(v, list) and all(isinstance(x, str) for x in v))
    if k == "enum":
        return isinstance(v, list) and len(v) > 0
    if k == "required":
        return isinstance(v, list) and all(isinstance(x, str) for x in v)
    if k in NUMERIC_KEYWORDS:
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    if k == "additionalProperties":
        return isinstance(v, bool)          # only the boolean form is implemented
    if k == "properties":
        return isinstance(v, dict)
    if k == "allOf":
        return isinstance(v, list)
    if k in ("if", "then", "else"):
        return isinstance(v, (dict, bool))
    if k == "items":
        return isinstance(v, (dict, bool, list))   # list form is rejected below
    if k == "pattern":
        return isinstance(v, str)
    return True                              # const: any value


def preflight_schema(sch, path="$"):
    """Reject anything this validator cannot enforce. Fail loud, never fail open."""
    errs = []
    if isinstance(sch, bool):
        return errs
    if not isinstance(sch, dict):
        return [f"{path}: schema node must be an object or boolean, got {type(sch).__name__}"]
    for k, v in sch.items():
        if k in ANNOTATIONS:
            continue
        if k not in SUPPORTED:
            errs.append(f"{path}: unsupported schema keyword '{k}' — this validator would ignore it (fail-open)")
            continue
        if not _shape_ok(k, v):
            errs.append(f"{path}.{k}: unsupported value shape ({type(v).__name__}) — would be mis-interpreted")
            continue
        if k in SUBSCHEMA_MAP:
            for pk, pv in v.items():
                errs += preflight_schema(pv, f"{path}.{k}.{pk}")
        elif k in SUBSCHEMA_LIST:
            for i, sub in enumerate(v):
                errs += preflight_schema(sub, f"{path}.{k}[{i}]")
        elif k in SUBSCHEMA:
            if k == "items" and isinstance(v, list):
                errs.append(f"{path}.items: list/tuple form is not supported (use prefixItems — unimplemented)")
            else:
                errs += preflight_schema(v, f"{path}.{k}")
        elif k == "pattern":
            for marker in PY_ONLY_REGEX:
                if marker in v:
                    errs.append(f"{path}.pattern: Python-only construct {marker!r} — Draft 2020-12 is ECMA-262")
            if SCOPED_FLAG.search(v):
                errs.append(f"{path}.pattern: scoped/inline flag, atomic, or conditional group is Python-only")
            for marker in UNICODE_DIVERGENT:
                if marker in v:
                    errs.append(f"{path}.pattern: {marker!r} matches Unicode in Python but ASCII in ECMA-262 — use an explicit class")
            try:
                re.compile(v)
            except re.error as e:
                errs.append(f"{path}.pattern: invalid regex ({e})")
    return errs


def _jeq(a, b):
    """JSON equality: booleans are NOT numbers (Python's True == 1 must not leak)."""
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a is b
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_jeq(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_jeq(x, y) for x, y in zip(a, b))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a == b
    return a == b


def _is_int(x):
    """Integer per Draft 2020-12: an int, or a float with no fractional part."""
    if isinstance(x, bool):
        return False
    return isinstance(x, int) or (isinstance(x, float) and x.is_integer())


def _type_ok(inst, t):
    for tt in (t if isinstance(t, list) else [t]):
        if tt == "object" and isinstance(inst, dict):
            return True
        if tt == "array" and isinstance(inst, list):
            return True
        if tt == "string" and isinstance(inst, str):
            return True
        if tt == "integer" and _is_int(inst):
            return True
        if tt == "number" and not isinstance(inst, bool) and isinstance(inst, (int, float)):
            return True
        if tt == "boolean" and isinstance(inst, bool):
            return True
        if tt == "null" and inst is None:
            return True
    return False


def validate(inst, sch, path="$"):
    """Return a list of human-readable error strings (empty = valid)."""
    # Boolean schemas: true accepts everything, false rejects everything.
    if sch is True:
        return []
    if sch is False:
        return [f"{path}: schema is `false` — nothing is valid here"]
    if not isinstance(sch, dict):
        return [f"{path}: invalid schema node ({type(sch).__name__})"]

    errs = []
    if "type" in sch and not _type_ok(inst, sch["type"]):
        errs.append(f"{path}: expected type {sch['type']}, got {type(inst).__name__}")
    if "const" in sch and not _jeq(inst, sch["const"]):
        errs.append(f"{path}: must equal {sch['const']!r}")
    if "enum" in sch and not any(_jeq(inst, e) for e in sch["enum"]):
        errs.append(f"{path}: {inst!r} not in enum {sch['enum']}")

    if isinstance(inst, str):
        if "minLength" in sch and len(inst) < sch["minLength"]:
            errs.append(f"{path}: shorter than minLength {sch['minLength']}")
        if "pattern" in sch and re.search(sch["pattern"], inst) is None:
            errs.append(f"{path}: does not match pattern {sch['pattern']}")

    if not isinstance(inst, bool) and isinstance(inst, (int, float)):
        if "minimum" in sch and inst < sch["minimum"]:
            errs.append(f"{path}: below minimum {sch['minimum']}")
        if "maximum" in sch and inst > sch["maximum"]:
            errs.append(f"{path}: above maximum {sch['maximum']}")

    if isinstance(inst, list):
        if "minItems" in sch and len(inst) < sch["minItems"]:
            errs.append(f"{path}: fewer than minItems {sch['minItems']}")
        if "maxItems" in sch and len(inst) > sch["maxItems"]:
            errs.append(f"{path}: more than maxItems {sch['maxItems']}")
        if "items" in sch and not isinstance(sch["items"], list):
            for i, it in enumerate(inst):
                errs += validate(it, sch["items"], f"{path}[{i}]")

    if isinstance(inst, dict):
        for r in sch.get("required", []):
            if r not in inst:
                errs.append(f"{path}: missing required property '{r}'")
        props = sch.get("properties", {})
        if isinstance(props, dict):
            for k, v in inst.items():
                if k in props:
                    errs += validate(v, props[k], f"{path}.{k}")
        if sch.get("additionalProperties") is False:
            for k in inst:
                if k not in props:
                    errs.append(f"{path}: additional property '{k}' not allowed")

    for sub in sch.get("allOf", []):
        errs += validate(inst, sub, path)

    if "if" in sch:
        if not validate(inst, sch["if"], path):          # if-schema matches
            if "then" in sch:
                errs += validate(inst, sch["then"], path)
        elif "else" in sch:
            errs += validate(inst, sch["else"], path)

    return errs


def semantic_gates(spec):
    """XROS gates JSON Schema cannot express.

    Defensive by design: never raise on a structurally invalid spec. validate()
    already reports those defects; these gates must not crash on the way past,
    or the caller would get a traceback instead of a clean INVALID.
    """
    errs = []
    if not isinstance(spec, dict):
        return errs

    st = spec.get("stopping")
    if isinstance(st, dict):
        lo, hi = st.get("minRounds"), st.get("maxRounds")
        if _is_int(lo) and _is_int(hi) and hi < lo:
            errs.append("$.stopping: maxRounds < minRounds")

    search = spec.get("search")
    approaches = search.get("approaches") if isinstance(search, dict) else None
    if isinstance(approaches, list):
        # only count hashable string families; malformed ones are structural errors
        fams = {a["family"] for a in approaches
                if isinstance(a, dict) and isinstance(a.get("family"), str)}
        if len(fams) < 3:
            errs.append(f"$.search.approaches: needs >= 3 distinct families, found {len(fams)}")
        names = [a["name"] for a in approaches
                 if isinstance(a, dict) and isinstance(a.get("name"), str)]
        dupes = sorted({n for n in names if names.count(n) > 1})
        if dupes:
            errs.append(f"$.search.approaches: duplicate approach name(s) {dupes} — names key runtime route state and must be unique")

    # Date fields pass a YYYY-MM-DD *shape* pattern in the schema; here we reject
    # shape-valid but impossible calendar dates (e.g. 2026-99-99, 2025-02-29).
    verifier = spec.get("verification", {}).get("verifier") if isinstance(spec.get("verification"), dict) else None
    if isinstance(verifier, dict):
        a = verifier.get("asOf")
        if _date_shape(a) and not _real_date(a):
            errs.append(f"$.verification.verifier.asOf: '{a}' is not a real calendar date")
    dv = spec.get("deferredVerification")
    tws = dv.get("tripwires") if isinstance(dv, dict) else None
    if isinstance(tws, list):
        for i, t in enumerate(tws):
            bw = t.get("byWhen") if isinstance(t, dict) else None
            if _date_shape(bw) and not _real_date(bw):
                errs.append(f"$.deferredVerification.tripwires[{i}].byWhen: '{bw}' is not a real calendar date")
    return errs


def _date_shape(s):
    return isinstance(s, str) and re.match(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$", s) is not None


def _real_date(s):
    try:
        datetime.date(int(s[0:4]), int(s[5:7]), int(s[8:10]))
        return True
    except (ValueError, TypeError):
        return False


def validate_spec(spec, schema):
    """Full check: schema preflight, then structural validation, then semantic gates."""
    pre = preflight_schema(schema)
    if pre:
        return [f"SCHEMA PREFLIGHT: {e}" for e in pre]
    return validate(spec, schema) + semantic_gates(spec)


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main(argv):
    if len(argv) != 3:
        print("usage: xros_validate.py <schema.json> <spec.json>", file=sys.stderr)
        return 2
    try:
        schema = _load(argv[1])
        spec = _load(argv[2])
    except (OSError, ValueError) as e:
        print(f"IO/parse error: {e}", file=sys.stderr)
        return 2

    pre = preflight_schema(schema)
    if pre:
        for e in pre:
            print(f"SCHEMA PREFLIGHT: {e}", file=sys.stderr)
        return 2                      # a broken schema is an environment fault, not a bad spec

    errs = validate(spec, schema) + semantic_gates(spec)
    if errs:
        for e in errs:
            print(f"INVALID: {e}")
        return 1
    print("VALID")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
