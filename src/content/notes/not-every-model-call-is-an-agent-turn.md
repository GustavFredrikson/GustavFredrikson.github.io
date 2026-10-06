---
title: Not every model call needs to be an agent turn
summary: How a small typed decision model gates my five-minute coach poll, what it is not allowed to decide, and how it earns the right to suppress a wake.
date: 2026-10-06
tags: [Agents, Jev, Python, Evaluation]
---

I run a training coach as an agent. A cron job polls my Intervals.icu data every five minutes, and when something looks interesting it wakes the `training` agent, which does a full reasoning turn. Most wakes don't need one. The question is rarely "reason about my whole situation and devise a plan". It's "does this bounded change matter enough to wake the coach at all?"

I use Jev, TypeSafe's typed decision model, to answer that smaller question. This note is about where it sits in my stack, what I keep out of its reach, and how I decide how much authority it gets. It isn't a review of the model.

## A different kind of model call

An agent turn is open-ended: it reads context, plans, calls tools and writes prose. A Jev call is the opposite. The API takes one `state` object and a named map of typed questions, and returns structured answers. My wrapper, `jev_eval.py`, exposes three question types:

- **boolean**: a probability of yes, which I turn into a decision and a confidence. For booleans, confidence is distance from 50/50, so a 0.02 is a confident "no", not a weak answer.
- **choice**: one option from a list I supply, with a probability per option.
- **score**: an ordinal on a fixed five-level scale, normalized to [0, 1].

There's no generated text anywhere. Even when a route means "ask me something", Jev can only pick one of a few fixed question templates by signal category. It never writes the question.

## The boundary

Callers don't send raw world state. `normalize_request()` runs before any provider, and so before the network, sees the request, and it rejects the call outright if the input isn't acceptable:

```text
world state
   ↓
explicit feature projection        (the calling feature's job)
   ↓
secret-free check                  (secret_guard)
   ↓
size check                         (context ≤ 8,192 bytes)
   ↓
Jev
   ↓
deterministic policy               (confidence, allowed routes, rollout gate)
   ↓
cheap action  OR  full coach
```

A malformed request raises, because that's an integration bug I want to see. Everything the provider can do wrong is different: a timeout, an HTTP error, a missing credential, an out-of-schema answer, or a confidence below the caller's minimum all resolve to a fallback with a status saying why. `fallback` is a required field on every request, and it is whatever the feature did before Jev existed. The module header says Jev must never become a security, authorization, idempotency, approval, source-freshness or mutation boundary, and nothing in it can write anything.

## The training-watch gate

The poll's existing deterministic logic decides first. Its adapter, `jev_coach_gate.py`, only lets Jev judge two trigger types, `open_loop_due` and `week_shape_drift`. Everything else (a new activity, a missed session, a wellness shift, the morning check-in, stale data, and anything it doesn't recognize) goes to the coach unconditionally.

For the two gateable triggers, the order inside the gate is:

1. **Deterministic escalation.** A fixed regex over declared symptoms (chest pain, fainting, sharp pain, fever, injury language and so on) or a hard-constraint breach sends the wake to the coach. Jev isn't consulted and the feature flag doesn't matter.
2. **Fingerprint reuse.** A SHA-256 over the semantic state (magnitudes bucketed to 0.1, normalized summary text, symptoms), excluding timestamps. An identical fingerprint within 24 hours reuses the previous Jev answer for zero tokens, then re-resolves it under the current config. Escalation is re-checked on every poll and never reused.
3. **Bounded Jev evaluation.** Two questions over one state, in one request: *could this change plausibly alter the next coaching decision?* (boolean) and *which route best matches the required response?* (choice).
4. **Confidence, allowlist and rollout gates.** Cheap routes only count if suppression is enabled, the route is on the allowlist, confidence is at least 0.90, and the rollout gate (below) is open. Otherwise the route is raised to at least `ask_for_subjective_input`. A "not material" answer can only lead to `ignore` at the same 0.90 bar.
5. **Multi-signal floor.** Per-category magnitudes are combined with a noisy-OR, `1 − ∏(1 − weight × magnitude)`. Several individually weak signals can cross 0.6 together even if none would alone, and the route is then raised to a floor.

The routes, cheapest first:

```text
ignore < persist_only < ask_for_subjective_input
       < next_training_brief < invoke_training_agent
```

Only `ignore` and `persist_only` can skip the coach, and only on a live, recorded, effective decision. A skipped wake doesn't update the last-wake record, so the daily dead-man's-switch trigger still reaches the coach.

Every failure path in the gate resolves the same way: run the full coach, as before. The caller only acts on a cheap route when the command exits 0 and reports success. A non-zero exit, unparsable output or a timeout all mean "invoke the agent".

## A failure that wasn't about the model

For a while most Jev calls took the fallback. The poll runs from cron, and cron helper subprocesses don't inherit the gateway environment, so most callers hit "`TYPESAFE_API_KEY` is not set". Nothing broke, because the fallback is the pre-Jev behaviour. I noticed through the provider-status and fallback-rate telemetry rather than through an error.

The fix, in `_resolve_env_api_key()`, looks in the environment first and then falls back to the gateway credential file. It resolves into a private dict instead of `os.environ`, so the key isn't exported to every later subprocess.

It also changed what I check. "The feature works" and "the model is actually participating" are different questions, and the second one needs its own metric. The rollout gate now includes a fallback rate and a recent-window "provider degraded" check for this reason.

## Authority is earned in stages

Suppression is off by default, and getting it on goes through stages:

- **A, measurement.** Jev is enabled and answers live traffic, but `suppression_enabled` is false. Every evaluation is recorded (route, probabilities, model version, tokens) in a hash-chained event log, and I attach what the coach actually did with `record-actual`. Quiet wakes that nothing escalated can be labelled in bulk with `label-quiet`, as an explicit opt-in. A deterministic escalation within 24 hours auto-labels earlier suppressions as false negatives.
- **B, guarded suppression.** Only `ignore` and `persist_only` may end a wake, and only while the gate holds.
- **C, widen the allowlist.** `next_training_brief`, then `ask_for_subjective_input`, which additionally needs a fixed template to exist. Only when the labels justify it.

The gate itself fails closed. Within a 30-day window and for the *current Jev model version only*, it requires at least 30 labelled evaluations, at least 15 of them cases Jev would have suppressed at the current threshold, zero false negatives, a weighted miss score of at most 0.15, a fallback rate of at most 0.2, and a non-degraded provider. False negatives are weighted 3× in the miss score, since under-escalation is the failure this gate must never quietly optimize for. Labels are scored against the route Jev *would* have taken with suppression on, which is what lets stage A traffic count as calibration data. Nothing loosens a threshold automatically, and a new model version starts the evidence count over.

## One request, several questions

The two training-watch questions don't cost two HTTP calls. `evaluate_many()` takes several typed requests over one shared state and sends them as one request with a named question map. It insists the contexts are identical and the question ids unique, and each question keeps its own fallback, confidence threshold, shadow mode and telemetry row. The same path is used for the semantic watches and admin triage. The state is the expensive part of the prompt, so it's paid for once.

## What I think this is good for

Jev decides things that are bounded, semantic and cheap to get slightly wrong: materiality, routing, relevance, triage, novelty. It doesn't decide permissions, safety, writes, idempotency or whether data is fresh, and it's never the record of what's true. Those stay in ordinary code (for writes, the [preview/apply/undo workflow](/notes/guarded-mcp-writes/) from the previous note).

## Limits of this note

I'm describing the design, not publishing results. The thresholds above are defaults in the config, and the live setup, as my docs describe it, enables evaluation while keeping suppression off, so the coach path is unchanged. I haven't built a reproducible comparison between Jev and a larger model, so I'm not claiming one is better. Token savings are a consequence of the split, not the reason for it.

## Current takeaway

Between "ordinary code" and "full agent" there's a useful middle: a constrained semantic judgment inside an otherwise deterministic system. It gets a projected input, sits behind policy, has a fallback that is the old behaviour, and only gains authority when its own track record on my data says it should.
