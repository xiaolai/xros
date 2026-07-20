# XROS — agent guide

XROS turns a long-horizon investigation into a verifiable methodology spec, then
runs it against a real check and gates the verdict on that check's exit code. Its
one rule: **no verification, no claim.**

## The tier model (decided by `verifier.soundness`)

| Tier | `soundness` | What run does |
|------|-------------|---------------|
| A | `sound` | Full engine; may return a verified complete result (`complete-only`) |
| B | `statistical` | Engine runs, but the verdict is evidence only — never "complete" |
| C | `none` | Engine never runs; `xros:run` redirects to `xros:reason` |

The tiers are structurally binding in the schema: a `backtest` can never be `sound`;
a `statistical`/`none` check can never request `complete-only` and must state a
`ceiling`. You cannot pick a weak check to unlock the strong mode.

## The four commands

| Command | Role |
|---------|------|
| `commands/compile.md` | Oracle-first interview → a validated spec |
| `commands/sharpen.md` | Orient (map a field's nouns/verbs) → falsifiable claim → best-available check |
| `commands/run.md` | Tier-A/B multi-agent engine, gated on the check's exit code |
| `commands/reason.md` | Tier-C path: premises, pre-mortem, dated tripwires; UNVERIFIED |

## Architecture

- `schema/xros-spec.schema.json` — the JSON Schema contract. Its `allOf` block holds
  the binding safety rules (rule 1: `complete-only` needs a sound oracle; rules 3a-3c:
  soundness/kind consistency; rule 4: a mechanical oracle needs a command + artifact;
  rule 5: a statistical/none check needs a `ceiling`).
- `schema/tools/xros_validate.py` — the ONLY required validator. Stdlib-only, offline,
  no `jsonschema`/`npx` dependency. Runs a keyword preflight that fails loud on any
  schema keyword it does not implement, so validation can never fail open. Enforces
  three gates JSON Schema cannot express: `maxRounds >= minRounds`, ≥3 distinct
  approach families, unique approach names — plus real-calendar-date checks.
- `schema/tests/run.py` — the conformance suite: valid specs, structural negatives,
  semantic gates, mutation testing (delete a rule → its negative must stop failing),
  robustness, and the CLI contract.

## Prerequisites

- **Python 3** — runs the bundled validator and the conformance suite. Stdlib only;
  `jsonschema` and `npx` are not required (`jsonschema` is an optional CI parity lane,
  enabled with `XROS_STRICT=1`).
- **git** — required only for `execution.isolation: "worktree"`, which verifies a
  candidate in a clean checkout.
- **Node.js** — used only during development, to syntax-check the embedded Workflow
  scripts inside `commands/run.md` and `commands/sharpen.md`.

## Working here

Validate a spec:
```bash
python3 schema/tools/xros_validate.py schema/xros-spec.schema.json <spec>.json
```

Run the suite (`XROS_STRICT=1` requires the optional `jsonschema` parity lane in CI):
```bash
python3 schema/tests/run.py
```

Conventions:
- The suite sets `sys.dont_write_bytecode`; `__pycache__` and `*.pyc` are gitignored.
  Never commit bytecode.
- On release, keep one version in both `.claude-plugin/plugin.json` and
  `.claude-plugin/marketplace.json`.
- Every command interpolates untrusted spec text into agent prompts and can run a
  spec-declared shell command; treat specs as untrusted input and never claim a
  result verified unless the check's exit code passed.

## Standing limitation

No spec has yet been driven end-to-end through a live `run`. Treat the orchestration
as validated-by-review, not battle-tested.
