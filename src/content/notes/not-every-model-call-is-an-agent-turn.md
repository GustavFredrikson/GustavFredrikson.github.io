---
title: Not every model call needs to be an agent turn
summary: Using a small typed decision model as a gate in front of an expensive agent, what it is not allowed to own, and how I let it earn authority.
date: 2026-10-06
tags: [Agents, Jev, Python, Evaluation]
---

Several automations in my setup wake an expensive reasoning agent when something changes. A new activity syncs, a plan is edited, a candidate shows up. Most of those events don't need reasoning about my whole situation. The question is smaller: does this bounded change matter enough to wake the agent at all?

I use Jev, a small model from TypeSafe that returns typed judgments, for that question. This note is about where I put it in the stack, what I keep out of its reach, and how I decide how much authority it gets. It isn't a review of the model.

## A different role for a model

An agent turn is open-ended: it reads context, plans, calls tools and produces prose. A typed decision is the opposite. My wrapper only exposes three kinds of answer:

- a boolean
- a choice from a fixed list
- a bounded score

There's no free-form generation, so there's nothing to parse and nothing to talk its way around the schema. The calling code gets a value it can branch on.

## The boundary

The model never sees raw world state. Every call goes through the same shape:

```text
raw world state
      ↓
explicit projection (deterministic, bounded)
      ↓
validation: schema-valid, secret-free, ≤ 8,192 bytes
      ↓
Jev: small typed judgment
      ↓
deterministic policy: confidence, allowed routes, rollout gate
      ↓
cheap action  OR  full reasoning agent
```

The projection is the part I spend the most care on. The caller chooses which fields the model may see, and an input that is invalid, contains something that looks like a secret, or is over the size limit never reaches it.

Some things stay outside the model entirely. The module that wraps Jev says so in its header: it must never become a security, authorization, idempotency, approval, source-freshness or mutation boundary. Every call also requires an existing deterministic fallback, so "the model is unavailable" is a normal state the caller has already handled. Hard constraints and anything that writes belong to ordinary code (and, for writes, to something like the [preview/apply/undo workflow](/notes/guarded-mcp-writes/) in the previous note).

## An example: training watch

The concrete case is a watcher that decides what to do when my training data changes. Calling the training agent for every change is wasteful, so Jev answers two independent questions:

1. Is this change materially relevant?
2. Which route should handle it?

The routes are ordered from least to most effort:

```text
ignore
  < persist_only
  < ask_for_subjective_input
  < next_training_brief
  < invoke_training_agent
```

Deterministic code can force an escalation before Jev is asked at all. When Jev does answer, its answer still has to survive several gates before it changes what happens: a confidence threshold, an allowed-route check, a rollout gate, and a floor that escalates when several independent signals agree something is off. The model suggests a route. Policy decides whether to take it.

## Failure is expected

The most useful failure so far came from deployment, not model quality. For a while most training-watch calls were silently taking the deterministic fallback, around 98% of them. My cron helpers didn't inherit the `TYPESAFE_API_KEY` environment variable, so the client couldn't authenticate.

Behaviour stayed correct, because the fallback exists for exactly this. What exposed the problem was the fallback-rate telemetry. It changed how I think about observability for this kind of component: "the feature works" and "the model is actually participating" are different questions, and only one of them shows up as an error.

The fix was to centralize credential resolution in one place, without exporting the key into `os.environ` for every child process to inherit.

## Shadow first, authority later

I didn't plug the model in and trust it. Authority is staged:

```text
A. shadow: Jev answers, nothing acts on it, I measure
      ↓
collect labels
      ↓
measure false negatives and fallback rate
      ↓
B. allow only the safest suppression routes
      ↓
more evidence
      ↓
C. consider widening what it may decide
```

Moving between stages is gated on evidence rather than on a good-looking benchmark: a minimum amount of labelled data, a minimum number of examples that were genuinely suppressible, a bound on false negatives, a bound on a weighted miss score, a ceiling on provider fallback rate, and calibration that is specific to the model version. A new model version starts over.

The asymmetry is deliberate. The costly mistake for a gate like this is suppressing something that mattered, so the measurements centre on misses, and the first routes it's allowed to act on are the ones where a miss is cheapest.

The principle I took from this is that model authority should be earned from observed behaviour on my data, not granted because it looked capable.

## Batching over shared state

A smaller point from a personal-search feature. Several independent judgments often share one expensive piece of context. Calling the model once per candidate pays for that context every time. `evaluate_many()` instead packs multiple typed questions against one bounded shared state, as long as the whole thing stays within the input size limit. The shared part is paid for once.

## Where I think this class of model fits

For now I use it for things that are bounded, semantic and cheap to get slightly wrong:

- routing
- materiality
- relevance filtering
- bounded classification
- candidate triage
- semantic novelty

And I keep it away from things where a wrong answer is costly or the model would become the source of truth:

- permissions and destructive authorization
- hard safety decisions
- open-ended planning
- being the record of what is true

## Limits of this note

This isn't a comparison between Jev and a larger model, and I haven't built a reproducible eval that would support one. I use the two for different jobs: the small model decides whether to reason, and the agent does the reasoning. Cost savings are a consequence of that split, not the reason for it.

## Current takeaway

Not every model call needs to be an agent turn. Between "ordinary code" and "full agent" there's a useful middle: a constrained semantic judgment inside an otherwise deterministic system, fed a projected input, wrapped in policy, backed by a fallback, and given authority in stages that are tied to measurements.
