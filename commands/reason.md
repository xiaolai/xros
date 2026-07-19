---
description: The Tier-C path — structured, adversarial reasoning for a claim that has NO mechanical check. Decomposes the claim into premises and verifies the checkable ones, runs a pre-mortem, and emits dated tripwires. Never runs the CDC engine, never claims a verified result; all output is labeled UNVERIFIED. xros:run redirects here automatically when verifier.soundness is "none".
argument-hint: "<path/to/spec.json>"
---

# xros:reason — Tier-C structured reasoning (no oracle)

You are reasoning about the spec at **$ARGUMENTS**, whose check is `soundness: none`
— there is no mechanical way to settle its claim. So you will **not** run the CDC
engine (that would produce confident text with nothing anchoring it — exactly the
failure XROS exists to prevent). Instead you do the adversarial thinking that does
*not* require an oracle, and you label the result honestly.

> **Everything this command produces is UNVERIFIED — human judgment required.**
> It reduces obvious errors and surfaces risks; it cannot confirm the claim is right.

## Step 1 — Load & confirm the tier

Validate the spec with the bundled validator (same invocation as `xros:run` Step 1):

```bash
SPEC="$ARGUMENTS"
python3 "${CLAUDE_PLUGIN_ROOT}/schema/tools/xros_validate.py" \
        "${CLAUDE_PLUGIN_ROOT}/schema/xros-spec.schema.json" "$SPEC"
```

Refuse on non-zero exit. Then confirm `verification.verifier.soundness === "none"`.
If it is `sound` or `statistical`, **stop and redirect to `xros:run`** — this
command is only for the no-check case. Read `objective.claim`, `success.nonGoals`,
`verification.adversarialChecklist`, any `deferredVerification`, and
**`toolPolicy`**.

**Honor `toolPolicy`.** The spec was validated with a lookup policy; your premise
agents must respect it — obey `toolPolicy.webSearch`, never run a
`toolPolicy.forbiddenLookups` query, and run agents under `execution.agentType` if
set. A Tier-C run does not get to bypass the spec's own escape-hatch limits.

This is a *modest* run — a handful of agents, not the 64-agent engine. Use
**sonnet** for the legwork (premise checks, extraction) and a **stronger** tier for
the pre-mortem and the synthesis, where judgment concentrates.

## Step 2 — Premise extraction (the decompose rung, made concrete)

Propose the claim's candidate premises — the things that would have to be true for
it to hold — and classify each:

- **checkable-now** — a fact, computation, or data lookup you can verify today.
- **checkable-later** — becomes checkable after an event (→ a tripwire in Step 4).
- **judgment** — rests irreducibly on opinion or values.

These premises are *your* decomposition, and an AI-guessed "load-bearing" premise
may be wrong, or merely one of several possible rationales. So mark each premise
`necessary` **only** when the user ratifies it as load-bearing, or when you can show
a genuine logical entailment (claim is false if the premise is false). Un-ratified
premises are `contributing`, not `necessary`. An unverifiable conclusion often rests
on *some* verifiable premises — find them, but don't overclaim which ones the whole
thing hangs on.

## Step 3 — Check the checkable premises (with citations resolved)

For every `checkable-now` premise, actually check it — compute it, look it up, or
research it. Apply the **same citation-entailment rule as `xros:sharpen`**: a source
must be fetched *and* its cited passage must actually support the specific premise —
an unfetchable, irrelevant, or non-entailing source is treated as fabricated and the
premise reverts to unverified. Report each premise as **supported / refuted /
unresolved**, and label the *strength* of each check as **sound / statistical /
judgment**, each with its **ceiling** (what the check does not establish).

If a **`necessary`** premise is **refuted**, that is the headline finding — surface
it first; that is the one place Tier-C can deliver something close to a hard result.
If a merely **`contributing`** premise is refuted, report exactly that — *"this
proposed rationale is undermined"* — and do **not** claim the whole conclusion is
sunk on the strength of an un-ratified decomposition.

## Step 4 — Pre-mortem and tripwires

**Pre-mortem** — assume the claim turned out wrong; enumerate the most likely
reasons, most-plausible first. This is adversarial thinking that needs no oracle.
Seed it with the spec's `adversarialChecklist` (the domain failure modes) and
extend it. Run this on the stronger model.

**Tripwires** — convert the claim's unverifiable-*now* content into verifiable-
*later* checks. Use `deferredVerification.tripwires` if the spec has them, else
generate them. Each needs:

- `observation` — the concrete thing to watch,
- `byWhen` — a **calendar date (ISO YYYY-MM-DD)**; if the trigger is an event rather
  than a date, put the date you'll *review* in `byWhen` and describe the event
  separately — "eventually" is not a `byWhen`,
- `whatWouldFalsify` — the outcome that would show the claim was wrong,
- `owner` — who is responsible for checking.

**Every generated tripwire must be ratified by the user** — confirm the owner is a
real, willing person and the date/observable/falsification-threshold are ones they
accept. Do not assign an unwilling or nonexistent owner. State plainly: **a tripwire
without a real date and a consenting owner is theater, and XROS can emit tripwires
but cannot enforce them** — someone has to actually watch.

## Step 5 — Decision memo

Synthesize (stronger model), in this order, prefixed **UNVERIFIED — HUMAN JUDGMENT
REQUIRED**:

1. The claim, restated precisely.
2. **Premise ledger** — each premise, whether it is `necessary` (ratified) or
   `contributing`, its status (supported / refuted / unresolved / judgment), the
   check strength (sound / statistical / judgment) and ceiling, with evidence for
   the checked ones.
3. **Pre-mortem** — the top ways this is wrong.
4. **Tripwires** — the dated, owned, user-ratified checks that would catch it later.
5. **Evidence coverage** — separately from any confidence statement: how many
   necessary premises are supported vs unresolved vs judgment. This is the factual
   part; report it plainly.
6. **Judgment-only decision confidence** — a defended level (e.g. "low: two of five
   necessary premises unresolved, core mechanism is judgment"). Name it exactly that
   — "judgment-only decision confidence" — and **never use verified/proven/certain
   language**; it must not read as a verdict that could overpower the UNVERIFIED
   banner. Even "high" here means only "well-argued", not "confirmed".
7. **What would upgrade this out of Tier C** — the check that, if it existed, would
   let this be verified (and thus `xros:sharpen`'s target).

Do not present judgment as fact. The value here is a well-structured decision under
acknowledged uncertainty — not a verdict.
