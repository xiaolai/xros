# Why this plugin exists

XROS did not begin as a plugin. It began as a question about a result that made the
rounds in late 2026, and about what — if anything — was actually reusable in it.

## The origin

Three inputs seeded it:

1. A **Reddit r/math thread** framing a claimed GPT-5.6 proof not as "the model got
   smarter" but as "a new *workflow* for research."
2. The two **OpenAI documents** it pointed at — the exact **prompt** used, and the
   resulting **proof** of the Cycle Double Cover Conjecture (CDC).
3. An **initial ChatGPT inquiry** where packaging that workflow was first floated.

This note records how we read those sources and what we took from them. The Sources
section links all three; archived copies of the two OpenAI PDFs sit in `sources/`.

## What the Reddit post claimed

A UC Berkeley applied mathematician had worked on a lower-bound problem for a year.
GPT-5.4 and GPT-5.5 had failed on it. After OpenAI published the methodology behind
its CDC proof, he rewrote his prompt to match that methodology, gave GPT-5.6 148
minutes of uninterrupted reasoning, obtained a proof, and then **formally verified it
in Lean**. The result was awaiting peer review.

The post's thesis, which we share: the transferable asset is **not the model**. It is
the **research protocol** — and OpenAI had, in effect, published a reusable one
alongside the proof.

### Our reading, with the framing removed

We separated the durable signal from the hype:

- The "10-page prompt" is **two pages** (about 1.5 of instructions). The asset is
  *density and structure*, not length.
- The proof is a **three-page, elementary** argument (it reduces CDC to a fact of
  F₂ linear algebra via nowhere-zero flows). A 45-year-old conjecture falling to
  three pages should be read skeptically until peer review clears it.
- Therefore **XROS's value does not depend on that proof being correct.** What we
  extracted is the *shape of the protocol*, which stands on its own.

## What the OpenAI prompt actually contains

The prompt is a fill-in-able skeleton. We distilled it into a reusable anatomy:

| Block | The reusable move |
|-------|-------------------|
| Precise definition of every term | kill ambiguity before the search starts |
| One fully-quantified claim | a single unambiguous target |
| **Exhaustive non-goals** | the anti-victory clause — name what *looks* like success but is not (special cases, reductions to another open conjecture, spot-checks, counterexamples without a nonexistence certificate) |
| "Assume a solution exists; search, do not debate" | prevents premature give-up |
| Diverse portfolio, developed independently first | diversity as explicit policy, not vibes |
| Route economics | a route that reduces to a same-strength lemma is not progress; a blocked route reopens only on a new mechanism |
| **Domain-specific adversarial checklist** | verification built from earned domain knowledge |
| Concrete-artifact requirement | reject vague optimism and status reports |
| A stopping rule decoupled from budget | return only on a result that survives audit ("spend at least 8 hours") |
| Tool limits | search for background only, never for the answer |

## The one element that made it trustworthy

Read past the orchestration and one thing is load-bearing: the **external, formal
check** — Lean. The prompt tells the model to *assume a solution exists* and to
*return only a complete proof*. That instruction is safe **only** because an
independent verifier caught the output. Combine "assume a solution exists" with
"no external check," and the identical protocol manufactures confident, wrong
artifacts.

This inverts the popular reading. The methodology does **not** "generalize to
everything." It is most dangerous exactly where it is most tempting — fields with no
verifier (strategy, investing, forecasting), where a plausible-looking answer cannot
be caught.

So XROS's founding rule is: **no verification, no claim.**

## How we structured the plugin

That rule produced the whole design.

- A **spec** (`../schema/xros-spec.schema.json`) encodes the anatomy above and makes
  the verification decision **structurally binding**: a problem's tier is set by
  `verifier.soundness` (`sound` / `statistical` / `none`), and the schema rejects any
  attempt to claim a complete result without a sound, mechanical check.
- Four commands built around that spec:

  | Command | Role |
  |---------|------|
  | `compile` | the interview that fills the spec — asks "how would you check an answer?" before anything else |
  | `run` | the multi-agent engine for problems that *have* a check (Tier A/B), gated on the check's real exit code |
  | `sharpen` | for a not-yet-checkable question: turn it into a falsifiable claim and find the best available check, or say honestly that none clears the bar |
  | `reason` | the Tier-C path for a claim with no mechanical check — premises, pre-mortem, dated tripwires, all labeled UNVERIFIED. The engine never runs without a check |

- A **bundled, dependency-free validator** and a **conformance suite**, because the
  verification claim has to hold for the tool itself.

We deliberately did **not** rebuild the multi-agent orchestration that Claude Code's
Workflow tool and the deep-research skill already provide. XROS's contribution is the
*methodology-and-verification* layer on top of them.

## On the proof's status

The CDC proof is a preprint awaiting review. Treat it as promising, not settled. None
of XROS depends on it.

## Sources

- Reddit r/math thread — <https://www.reddit.com/r/math/comments/1uxj3cy/after_openais_cdc_proof_announcement_gpt56_used_a/>
- OpenAI, CDC prompt (PDF) — <https://cdn.openai.com/pdf/04d1d1e4-bc75-476a-97cf-49055cd98d31/cdc_prompt.pdf>
- OpenAI, CDC proof (PDF) — <https://cdn.openai.com/pdf/04d1d1e4-bc75-476a-97cf-49055cd98d31/cdc_proof.pdf>
- Initial ChatGPT inquiry that seeded the idea — <https://chatgpt.com/share/6a5cc23e-d6b4-83ea-8fc7-259f2ae94445>

`sources/cdc_prompt.pdf` and `sources/cdc_proof.pdf` are archived copies for
provenance. They are OpenAI's published documents (© OpenAI), kept here for reference
only; the canonical versions are the CDN links above. Remove them before any
public/commercial redistribution if that raises a licensing concern.
