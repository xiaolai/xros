---
name: xros-compile
description: Compile an XROS methodology spec through an oracle-first interview. Classifies the problem into verification tier A/B/C before anything else, then fills and validates a schema-valid JSON spec.
---

# xros-compile — methodology spec compiler

You are compiling one **XROS methodology spec**: a JSON file, conforming to
`schema/xros-spec.schema.json` (bundled in this plugin), that another skill
(`$xros-run`) executes as a multi-agent search and checks against a real
verifier. Your job is the *interview*, not the run.

The user's one-line problem, if they gave one.

Run the steps in order. Do not skip Gate 0. Keep questions tight; batch discrete
choices with AskUserQuestion, use open prompts for the rich natural-language
fields. Write nothing to disk until Step 9.

---

## Gate 0 — "How would you know?" (the front door, before problem details)

Everything downstream turns on one question. Ask it in **plain language** — never
say *oracle*, *soundness*, or *tier* to the user; those are your internal fields,
not their vocabulary. Get a one-line problem statement if they did not give one,
then ask, in order:

> **"If I handed you an answer right now, what would you do to check whether it's
> right?"**
> and, if that stalls, **"What would convince you that you were wrong?"**

Almost everyone can answer the second question, including non-experts. A blank
answer usually means the *question* isn't yet checkable — not that the user has
failed. Classify what they give you:

| What they can offer | Internally | Route |
|---------------------|-----------|-------|
| A command/procedure whose pass/fail **establishes the exact claim** (proof checker, model check over a full bounded space) | `soundness: sound` (Tier A) | **Proceed** to Steps 1–8, `complete-only` allowed |
| A command/procedure that gives **evidence, not proof** (held-out backtest, benchmark, sampled experiment, fuzzing) | `soundness: statistical` (Tier B) | **Proceed**, but `returnPolicy` is `strongest-partial-allowed` and a `ceiling` is required |
| Nothing runnable — but the question *is* well-posed | `soundness: none` (Tier C) | Offer the **`$xros-sharpen` handoff** (below); if declined, **`$xros-reason <spec>`** (the Tier-C path) |
| Nothing — and the question isn't even well-posed ("will my startup succeed?") | — | **`$xros-sharpen`** — do not force a spec |

> **`sound` is narrower than "it runs deterministically."** A type-check, a
> compile, or an ordinary test suite is `sound` **only when the claim is exactly the
> property it decides** — "it type-checks" proves type-safety, not functional
> correctness; "the tests pass" proves those cases pass, not that the code is
> correct. Unless the check is *exhaustive over the claim's full scope* (like a
> bounded model check), classify it `statistical` and record the `ceiling`. A
> non-expert must never be allowed to read "it compiles" as "it's correct."

### The discovery ladder (before you ever accept "there's no way to check")

"I don't have a check" is not a terminal answer — it's the start of a short ladder.
For a non-expert, **propose, don't interrogate**: offer concrete options and let
them pick, rather than demanding they produce a check cold.

1. **Run it** — "Is there anything we could run, compute, or measure that would settle this?" Often a check exists the user just didn't think of. *(This is exactly what `$xros-sharpen` researches.)*
2. **Decompose** — "What has to be true for this to be right?" Unverifiable conclusions usually rest on verifiable premises; verify those.
3. **Reformulate** — "As asked, this has no true/false answer. Here's a sharper version that does." Often drops you back to rung 1.
4. **Defer** — "What would you expect to see in three months if this were right? What if it were wrong?" Converts an unverifiable *now*-claim into a `deferredVerification` tripwire (needs a date and an owner).
5. **Values** — if the question is about a preference, not a fact ("family vs career"), say so and stop: verification is *inappropriate* here, not missing.

### Handoff and honesty rules

- **Never invent a check to unlock Tier A.** A fabricated oracle aimed at someone
  who can't detect it is the worst thing this tool can do. "No sound check exists"
  is a legitimate, respected outcome.
- **`complete-only` requires a genuinely sound check.** The schema (safety rule 1)
  rejects any attempt to pair it with a statistical/absent one; do not fight it.
- A `backtest` is `statistical`, never `sound` — soundness is about whether passing
  *proves* the claim, not whether it runs.
- If the user can't name a check, offer: *"I can research how people in this field
  actually check claims like yours, and find the strongest option you can run today
  — want me to?"* → that is `$xros-sharpen`. Bring its result back here.

Record: `verifier.kind`, `verifier.soundness`, and the provisional
`success.returnPolicy`. For a mechanical check also capture the intended
`verifier.command`, `verifier.artifactToVerify`, and `verifier.passCondition`, and
(for statistical) the `ceiling` — what passing will NOT establish — now, while it's
fresh.

---

## Steps 1–8 — Fill the rest of the spec

Walk the schema top-down. For each field, the schema `description` is your
prompt text; enforce the **semantic gates** below (the schema can only count,
not judge).

0. **identity (required — do not skip, or validation fails)** — set
   `schemaVersion: "1.0.0"`, a kebab-case `id` (also the filename), a human `title`,
   and the `domain` (used to key the learning report and to sanity-check whether a
   real check is even plausible). These four are `required` top-level fields; the
   rest of this walkthrough won't remind you again.
1. **objective** — `ontology` (force a precise definition of every load-bearing
   term), one fully-quantified `claim`, optional `claimFormalization` (for Tier
   A, tie it to what the oracle checks). If a term came from an `$xros-sharpen`
   domain map, carry its `standing` / `sources` / `provenance` onto the ontology
   item (the honesty group is all-or-nothing, and `canonical` needs ≥2 sources —
   the validator enforces both).
2. **success** — `successCriterion`; `nonGoals` (gate ↓); confirm
   `existenceAssumption` (if the user genuinely does not know the answer exists,
   it is `open-question`/`unknown` → schema forces `strongest-partial-allowed`);
   confirm `returnPolicy` from Gate 0.
3. **search** — `approaches` (gate ↓); `independenceRounds` (default 2);
   `maxConcurrentAgents` (a ceiling on simultaneous routes; runtimes cap real
   concurrency well below large values, so higher settings widen breadth, not
   simultaneity); `crossPollinationRule`;
   `blockedRouteReopenRule`; `antiProgressRules`; `requiredArtifacts`.
4. **verification** — `adversarialChecklist` (gate ↓); `verificationVotes`
   (default 3); finalize the `verifier` object from Gate 0.
5. **stopping** — `minRounds`, `maxRounds` (≥ minRounds), `budgetTokens`
   (surface the cost, never set it silently), `convergenceRule`,
   `giveUpCondition` (only for `strongest-partial-allowed`).
6. **toolPolicy** — `webSearch` (default `background-only`), `forbiddenLookups`
   (always add "whether this exact problem is already solved/open"),
   `allowedTools`.
7. **execution** — `preview` (keep `true`; it gates only the *cost* preview — the
   oracle command always needs approval); `isolation` (`worktree` when the oracle
   needs repo context, e.g. a `test-suite` command, so the runner verifies in a
   clean checkout; `none` for self-contained artifacts — it is collision isolation,
   **not** a security sandbox); optional `agentModel`/`agentEffort`/`agentType`
   (set `agentType` to a restricted-tool type to actually enforce `allowedTools`).
8. **provenance** — set `derivedFrom: "openai-cdc-v2"`.

### Semantic gates: propose, then have the user ratify

The schema can only *count* items; you judge whether they're real. For an expert,
elicit; for a non-expert, **propose candidates and let them ratify** — an amateur
often cannot name a domain's failure modes cold, but you frequently can, and a
ratified proposal beats a blank field. **Record `provenance` on every checklist
item and approach:**

- `user` — the user supplied it.
- `assistant-proposed` — you suggested it, the user *explicitly* kept it.
- `assistant-assumed` — you filled it and the user did not weigh in.

Then enforce the gates:

- **non-goals (≥2, and *meaningful*):** each names a *specific outcome that looks
  like success but isn't* (a special case, a reduction to another unsolved problem,
  a spot-check, a statistical pass mistaken for a proof). Reject generic filler.
- **approach families (≥3, and *distinct*):** cluster by underlying idea; two
  rewordings are one family. If short, offer the menu — invariants, reductions,
  algebraic, structural induction, decomposition, flow/formulation, transition
  systems, embeddings, extremal, computational sanity checks.
- **adversarial checklist (≥2, and *domain-specific*):** each ties to a concrete
  failure mechanism in *this* domain (CDC's "repeated-edge closed trails
  masquerading as cycles"), not generic QA. If the user can't produce two, **you
  propose them** (marked `assistant-proposed`/`assistant-assumed`) and ask them to
  confirm — do not leave the field weak, and do not silently pass off your guesses
  as theirs.

### Confidence downgrade (state it in the output)

Count provenance across checklist + approaches. If a **majority** of load-bearing
items are `assistant-proposed`/`assistant-assumed`, tell the user plainly: *"Most
of this spec's failure modes and approaches came from me, not from your own domain
knowledge. The run will be only as good as those guesses — treat its verdict as
lower-confidence until you've reviewed them."* This is not optional; a spec built
mostly from AI suggestions must carry that flag into `$xros-run`.

---

## Step 9 — Emit and validate

1. Choose a path: `xros/specs/<id>.spec.json` in the user's project (create the
   dir). Confirm before writing.
2. Write the JSON.
3. **Validate with the bundled validator** — portable, stdlib-only, offline (no
   `jsonschema`/`npx` dependency). Paths are passed as arguments, never
   interpolated into source, so an apostrophe in a path can neither break nor
   inject:
   ```bash
   ROOT="${PLUGIN_ROOT:-${GROK_PLUGIN_ROOT:-$CLAUDE_PLUGIN_ROOT}}"   # plugin install root; if unset,
                                                # locate xros_validate.py in this plugin
   SCHEMA="$ROOT/schema/xros-spec.schema.json"
   SPEC="xros/specs/<id>.spec.json"   # substitute the real id
   python3 "$ROOT/schema/tools/xros_validate.py" "$SCHEMA" "$SPEC"
   ```
   It enforces the full schema **and** the three gates JSON Schema cannot express —
   `stopping.maxRounds >= stopping.minRounds`, `search.approaches` holding **at
   least 3 distinct `family` values**, and **unique `approaches[].name`s** (names key
   the runner's per-route state). On any `INVALID` line (non-zero exit), fix
   and re-run; do not advance to `$xros-run` with an uncertified spec. (`jsonschema`
   or `npx ajv-cli@5 --spec=draft2020` may be used as an optional second opinion,
   but neither is required.)
4. Beyond the validator, sanity-check that if `verifier.soundness` is `sound` or
   `statistical`, `verifier.command` and `verifier.artifactToVerify` are present
   and non-empty (the schema requires this, but re-check after any hand edit).
5. Fix and re-validate until clean.

## Output contract

Report, in this order, in plain language (translate the internal terms):
1. **How the answer will be checked**, and what that check can and cannot establish
   (`soundness` and, for statistical/none, the `ceiling`).
2. The spec path and validation result.
3. **Provenance summary** — how much of the spec came from the user vs. from you,
   and the confidence downgrade if you dominated it.
4. Any gate the user only barely cleared (a thin, mostly-assistant checklist is the
   loudest signal).
5. Next step:
   - mechanical check present → `$xros-run <path>` (with the cost/approval reminder);
   - no check but a well-posed question → `$xros-sharpen` to find one;
   - no check and it's judgment-only → **`$xros-reason <path>`**, output labeled UNVERIFIED.

Because `provenance` is recorded on every approach and checklist item, the downgrade
is not just spoken here — `$xros-run` recomputes the assistant-authored proportion
from the spec and repeats the warning in its own report, so it survives the handoff.

Never fabricate a check to unlock `complete-only`. "No sound check exists" is a
correct, useful outcome — it tells the user the trustworthy engine does not fit
their problem yet, and points them at `$xros-sharpen` rather than a dead end.
