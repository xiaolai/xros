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

## The four capabilities — two surfaces

| Capability | Claude Code (slash command) | Codex / Antigravity / Grok (skill) |
|------------|-----------------------------|------------------------------------|
| Oracle-first interview → a validated spec | `commands/compile.md` | `skills/xros-compile/` |
| Orient (map a field's nouns/verbs) → falsifiable claim → best-available check | `commands/sharpen.md` | `skills/xros-sharpen/` |
| Tier-A/B engine, gated on the check's exit code | `commands/run.md` | `skills/xros-run/` |
| Tier-C path: premises, pre-mortem, dated tripwires; UNVERIFIED | `commands/reason.md` | `skills/xros-reason/` |

## Layout — one repo, four hosts

| Host | Manifest | Reads |
|------|----------|-------|
| Claude Code | `.claude-plugin/plugin.json` | `commands/` (slash commands) |
| OpenAI Codex | `.codex-plugin/plugin.json` (`"skills": "./skills/"`) | `skills/` |
| Google Antigravity | `plugin.json` **at the repo root** (required by `agy plugin install`) | `skills/`, `rules/` |
| xAI Grok | `.grok-plugin/plugin.json` | `skills/` |

`skills/` is a **single shared tree**: the same `SKILL.md` files serve Codex,
Antigravity, and Grok, because all three implement the same
`skills/<name>/SKILL.md` contract (`name` + `description` frontmatter). Keep the
skill bodies **tool-neutral** — no `$ARGUMENTS`, no Claude Workflow scripts, no
model names, no `CLAUDE_PLUGIN_ROOT` except as a documented fallback. Anything
host-specific belongs in a manifest, not in a skill body.

`commands/` (Claude) and `skills/` (everyone else) express the same four
capabilities and **must be kept in behavioural sync**. The Claude commands may use
the Workflow engine directly; the skills describe the same algorithm as a protocol
the host executes with its own sub-agents — or sequentially, which is weaker
independence and must be reported as such.

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
- On release, keep **one version across all five manifests**:
  `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`,
  `.codex-plugin/plugin.json`, `.grok-plugin/plugin.json`, and the root
  `plugin.json` (Antigravity).
- Antigravity's `plugin.json` schema is `additionalProperties: false` — only
  `name`, `description`, and (by de-facto convention) `version`. Do **not** add
  `license` / `author` / `keywords` there; those belong in the Codex and Grok
  manifests, and the root `LICENSE` file is the source of truth either way.
- Every command and skill interpolates untrusted spec text into agent prompts and
  can run a spec-declared shell command; treat specs as untrusted input and never
  claim a result verified unless the check's exit code passed.

## Standing limitation

No spec has yet been driven end-to-end through a live `run`. Treat the orchestration
as validated-by-review, not battle-tested.
