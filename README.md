# XROS — executable research operating system

[![Validated by NLPM](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/xiaolai/xros-for-claude/main/nlpm-badge.json)](https://github.com/xiaolai/xros-for-claude/blob/main/nlpm-badge.json)

XROS turns a long-horizon investigation into a **verifiable methodology spec**, then runs
it against a **real check** and gates the verdict on that check's exit code.

Its one non-negotiable rule:

> **No verification, no claim.** XROS will not report a solution as verified unless a
> mechanical check actually passed. Where no such check exists, it says so and refuses
> the strong mode — rather than producing confident text with nothing anchoring it.

## Why this exists

It is easy to get an AI to spend hours on a hard problem and return something that
*reads* like a result. The hard part is knowing whether it is one. XROS makes the
answer to "how would we know if this were wrong?" a required, structural input — not
an afterthought.

## The tier model

Everything is decided by one property: **does passing your check actually establish
your claim?** That is recorded as `verifier.soundness`, and it is enforced by the
schema, not by convention.

| Tier | `soundness` | Example checks | What XROS will do |
|------|-------------|----------------|-------------------|
| **A** | `sound` | proof checker (Lean/Coq), model check over a full bounded space, type check, compile, exhaustive test | Full engine. May return a **verified complete** result |
| **B** | `statistical` | held-out backtest, benchmark, sampled experiment, fuzzing | Engine runs, but the verdict is **evidence only** — never "complete" |
| **C** | `none` | human judgment only | **Engine does not run.** Output is labeled UNVERIFIED |

The tiers are structurally binding. A `backtest` can never be marked `sound`; a
statistical or absent check can never request `complete-only`. You cannot shop for a
weak check to unlock the strong mode — the schema rejects it.

## Commands

| Command | What it does |
|---------|--------------|
| `/xros:compile` | Interview → a validated methodology spec. Asks, in plain language, how you would check an answer *before* anything else; routes to `sharpen` when you can't |
| `/xros:sharpen` | For a vague or un-checkable question: sharpen it into a falsifiable claim, then research and dry-run the **currently best available** check — with an explicit statement of what that check *cannot* establish, or an honest "no check clears the soundness bar" |
| `/xros:run` | Tier A/B spec → a multi-agent Workflow (diverse independent routes, adversarial refutation, counterexample-fed loop) → runs your check and gates on its exit code. A Tier-C (`soundness: none`) spec is redirected to `xros:reason` — the engine never runs without a check |
| `/xros:reason` | The Tier-C path for a claim with no mechanical check: decompose into premises and verify the checkable ones, pre-mortem, and emit dated tripwires. All output labeled UNVERIFIED |

## The spec

A spec is a single JSON file conforming to `schema/xros-spec.schema.json`. It encodes
the anatomy of a serious investigation: precise definitions, one fully-quantified
claim, an explicit **non-goals** list (things that look like success but aren't), a
diverse portfolio of approaches, a domain-specific adversarial checklist, stopping and
budget rules, and the check itself.

Worked examples live in `schema/examples/` and `schema/tests/valid/` — one per tier.

## Validation

Specs are validated by a **bundled, dependency-free validator**:

```bash
python3 schema/tools/xros_validate.py schema/xros-spec.schema.json <your-spec>.json
# exit 0 = VALID · 1 = INVALID · 2 = usage/IO/schema fault
```

It uses only the Python standard library — no `jsonschema`, no `npx`, no network. It
enforces the full schema plus three gates JSON Schema cannot express (`maxRounds >=
minRounds`, at least 3 distinct approach families, unique approach names), and it runs
a **schema preflight** that refuses to run if the schema uses a keyword it does not
implement — so validation can never silently fail open.

## Tests

```bash
python3 schema/tests/run.py          # add XROS_STRICT=1 in CI to require the jsonschema parity lane
```

Covers valid specs, isolated structural negatives, semantic gates, validator unit
vectors, robustness (malformed input must yield a clean INVALID, never a traceback),
and the CLI contract. It also includes **mutation testing**: each safety rule is
deleted from the schema in turn, and its negative test must stop failing — the only
real proof that a test targets the rule it claims to.

## Status

v0.1.0 — all four commands (`compile`, `sharpen`, `run`, `reason`) ship. The schema,
the bundled validator, and the conformance suite are the load-bearing, tested parts;
the command bodies are natural-language programs whose rigor rests on their own
instructions (and on the reviews that hardened them). No spec has yet been driven
end-to-end through a live `run`, so treat the orchestration as validated-by-review,
not battle-tested.

## Credit

The methodology is modeled on the prompt OpenAI published alongside its Cycle Double
Cover work: precise definitions, exhaustive non-goals, a diverse portfolio developed
independently before cross-pollination, adversarial audit with domain-specific failure
modes, and a stopping rule gated on surviving that audit.

XROS's addition is the part that made that work trustworthy rather than merely
productive: **the external check is mandatory, and the system refuses to pretend when
it is missing.**

MIT licensed.
