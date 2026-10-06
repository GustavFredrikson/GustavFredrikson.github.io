---
title: Not every model call needs to be an agent turn
summary: How a small typed decision model gates my five-minute coach poll, what it is not allowed to decide, and how it earns the right to suppress a wake.
date: 2026-10-06
tags: [Agents, Jev, Python, Evaluation]
---

I run a training coach as an agent. A cron job polls my Intervals.icu data every five minutes, and when something looks interesting it wakes the training agent, which does a full reasoning turn. Most wakes don't need one. The question is rarely "reason about my whole situation and devise a plan". It's "does this bounded change matter enough to wake the coach at all?"

I use Jev, TypeSafe's typed decision model, to answer that smaller question. This note is about where it sits in my stack, what I keep out of its reach, and how I decide how much authority it gets. It isn't a review of the model.

## A different kind of model call

An agent turn is open-ended: it reads context, plans, calls tools and writes prose. A Jev call is the opposite. The API takes one state object and a named map of typed questions, and returns structured answers. My wrapper exposes three question types:

- **boolean**: a probability of yes, which I turn into a decision and a confidence. For booleans, confidence is distance from 50/50, so a 0.02 is a confident "no", not a weak answer.
- **choice**: one option from a list I supply, with a probability per option.
- **score**: an ordinal on a fixed five-level scale, normalized to [0, 1].

There's no generated text anywhere. Even when a route means "ask me something", Jev can only pick one of a few fixed question templates. It never writes the question.

## Three layers, not two

That gives the system three layers, and each one answers a different kind of question:

| Layer | Good at |
|---|---|
| Deterministic code | invariants, permissions, safety, freshness, writes |
| Jev | bounded semantic classification and routing |
| Agent | open-ended synthesis, planning, tool use |

Most of the design work is deciding which layer owns what. The cheap layer in the middle exists so the expensive one runs less often. It must not take over what the deterministic layer is responsible for.

## The boundary

Callers don't send raw world state. Validation runs before the request goes anywhere near the network, and it rejects the call outright if the input isn't acceptable:

```text
world state
   ↓
explicit feature projection        (the calling feature's job)
   ↓
secret-free check
   ↓
size check                         (context ≤ 8,192 bytes)
   ↓
Jev
   ↓
deterministic policy               (confidence, allowed routes, rollout gate)
   ↓
cheap action  OR  full coach
```

A malformed request raises, because that's an integration bug I want to see. Everything the provider can do wrong is different: a timeout, an HTTP error, a missing credential, an out-of-schema answer, or a confidence below the caller's minimum all resolve to a fallback with a status saying why. Every request must carry a fallback, and it is whatever the feature did before Jev existed. The wrapper states that Jev must never become a security, authorization, idempotency, approval, source-freshness or mutation boundary, and nothing in it can write anything.

## The training-watch gate

The poll's existing deterministic logic decides first. Only two trigger types are allowed to reach Jev at all. Everything else (a new activity, a missed session, a wellness shift, anything unrecognized) goes to the coach unconditionally.

For those two, the gate runs in this order:

1. **Deterministic escalation.** Hard-coded high-risk symptom categories and explicit constraint breaches bypass Jev entirely.
2. **Reuse.** If the semantic state is identical to a recent one (a hash that ignores timestamps), the earlier answer is reused at zero token cost and re-resolved under the current config.
3. **Jev.** Two questions over one state: *could this change plausibly alter the next coaching decision?* (boolean) and *which route best matches the required response?* (choice).
4. **Policy.** A cheap route only counts if suppression is on, the route is on an allowlist, confidence is at least 0.90, and the rollout gate (below) is open. Otherwise the route is raised to at least "ask me a fixed question".
5. **Multi-signal floor.** Several individually weak signals are combined, and if together they cross a threshold the route is raised no matter what Jev said.

The routes, cheapest first:

```text
ignore < persist only < ask a fixed question
       < defer to next brief < invoke the agent
```

Only the two cheapest routes (ignore, and persist the observation without reasoning) can skip the coach. Every failure path resolves the same way: run the full coach, as before. The caller acts on a cheap route only when the gate exits 0 and reports success, so a crash, a timeout or unparsable output all mean "invoke the agent". Skipped wakes also don't update the poll's last-wake record, so the daily dead-man's-switch trigger still reaches the coach.

## A failure that wasn't about the model

For a while most Jev calls took the fallback. The poll runs from cron, and cron helper subprocesses don't inherit the gateway environment, so most callers failed with "API key is not set". Nothing broke, because the fallback is the pre-Jev behaviour. I noticed through the provider-status and fallback-rate telemetry rather than through an error.

The fix looks in the environment first and then falls back to the gateway's credential file. It reads the key into a private variable instead of exporting it to the environment, so it doesn't leak into every later subprocess.

The lesson is that a correct fallback can hide a broken integration, so fallback rate is itself a health metric. "The feature works" and "the model is actually participating" are different questions. The rollout gate now includes a fallback rate and a recent-window "provider degraded" check for this reason.

## Authority is earned in stages

A model doesn't get authority because it exists. It gets authority because its observed performance on my traffic justifies it.

Suppression is off by default, and turning it on goes through stages:

- **A, measurement.** Jev is enabled and answers live traffic, but suppression is off. Every evaluation is recorded (route, probabilities, model version, tokens) in a hash-chained event log, and I attach what the coach actually did. A later deterministic escalation automatically labels earlier suppressions as false negatives.
- **B, guarded suppression.** Only the two cheapest routes may end a wake, and only while the gate holds.
- **C, widen the allowlist.** The next-brief and ask routes, only when the labels justify it.

The gate fails closed. Within a 30-day window, and for the *current Jev model version only*, it requires at least 30 labelled evaluations, at least 15 of them cases Jev would have suppressed at the current threshold, zero false negatives, a weighted miss score of at most 0.15, a fallback rate of at most 0.2, and a non-degraded provider. False negatives are weighted 3× in the miss score, since under-escalation is the failure this gate must never quietly optimize for. Labels are scored against the route Jev *would* have taken with suppression on, which is what lets stage A traffic count as calibration data. Nothing loosens a threshold automatically, and a new model version starts the evidence count over.

## One request, several questions

The two training-watch questions don't cost two HTTP calls. The wrapper can take several typed questions over one shared state and send them as a single request. It insists the contexts are identical and the question ids unique, and each question keeps its own fallback, confidence threshold and telemetry row. The state is the expensive part of the prompt, so it's paid for once.

## Where this fits

Jev handles judgments that are bounded, semantic, and recoverable through a conservative fallback: materiality, routing, relevance, triage, novelty. Uncertainty there can be contained by deterministic policy and escalation. It doesn't decide permissions, safety, writes, idempotency or whether data is fresh, and it's never the record of what's true. Those stay in ordinary code (for writes, the [preview/apply/undo workflow](/notes/guarded-mcp-writes/) from the previous note).

## Limits of this note

I'm describing the design, not publishing results. The thresholds above are defaults in the config, and the live setup, as my docs describe it, enables evaluation while keeping suppression off, so the coach path is unchanged. I haven't built a reproducible comparison between Jev and a larger model, so I'm not claiming one is better. Token savings are a consequence of the split, not the reason for it.

## Current takeaway

Between "ordinary code" and "full agent" there's a useful middle: a constrained semantic judgment inside an otherwise deterministic system. It gets a projected input, sits behind policy, has a fallback that is the old behaviour, and only gains authority when its own track record on my data says it should.
