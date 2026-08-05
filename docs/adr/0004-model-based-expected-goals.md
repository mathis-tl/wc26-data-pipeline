# 4. Model-based expected goals, never called xG

Date: 2026-08-04 · Status: accepted

## Context

The flagship analysis asks whether Spain deserved the title. Answering it well
needs opponent-adjusted team strength and expected-goals-style numbers. The
primary source (football-data.org) provides **only final scores** — no shots,
no possession, no event data. Real tracking-based xG is therefore impossible to
compute from this source.

The tempting shortcut is to compute something goals-based, label it "xG"
because that is the term readers recognise, and move on.

## Decision

Fit a **Poisson attack/defense/home-advantage model** by penalised maximum
likelihood on the 104 results (`analytics/model.py`), and derive
_opponent-adjusted_ expected goals and expected points from it. Call these
outputs **"model-based expected goals"** everywhere — prose, figure labels,
JSON, model metadata — and **never "xG"**. Where real xG exists (Spain's
matches, via the SofaScore second source, ADR context), label it "real xG
(SofaScore)" and keep the two visibly distinct, including a column that puts
model xG next to real xG so the reader can see the model validated against
observation.

## Consequences

**Why the naming is load-bearing.** xG has a specific meaning in football
analytics — probability of a shot becoming a goal, from shot-level tracking.
Applying that term to a scores-only Poisson output would be, precisely, lying
to a knowledgeable reader; and the target audience for this project (data
people who love football) is exactly the audience that would catch it. The
credibility of the entire analysis rests on not overclaiming what the data can
support. Being honest about the limitation _is_ the sophistication.

**Statistical guards (ADR-0005 family).** The fit refuses to return ratings
from a non-converged optimiser (`res.success` checked, `FitError` raised) — the
worst failure mode here is plausible-looking garbage. Ridge penalisation keeps
the model stable given ~7 matches per team; the model metadata carries the
match count and final NLL so runs are comparable. The limits are stated
explicitly in the method section: ~7 matches is an estimate, not an oracle.

**Rejected — call it xG.** Recognisable, and everyone else's marketing does it,
but dishonest given the inputs and fatal to credibility with the one audience
that matters. Rejected outright.

**Rejected — no expected-goals analysis at all.** Safe, but forfeits the entire
"show data-science value, not commodity data display" thesis. The model, framed
honestly, is the deliverable.
