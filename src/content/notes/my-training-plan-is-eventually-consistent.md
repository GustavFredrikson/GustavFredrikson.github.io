---
title: My training plan is eventually consistent
summary: What endurance training taught me about desired state, stale data, reconciliation and human overrides.
date: 2026-10-06
tags: [Training, Agents, Systems]
---

For years I thought a training plan was a schedule. I now think that's the wrong abstraction.

A schedule says that if Tuesday has 5 × 1 km at threshold, Tuesday's job is to run 5 × 1 km at threshold. It looks deterministic:

```text
Monday     Easy run
Tuesday    Threshold run
Wednesday  Swim
Thursday   Bike intervals
Friday     Easy run
Saturday   Long run
Sunday     Long ride
```

But my body doesn't expose a transactional API. What actually happens over a week looks more like this:

```text
planned week
   ↓
Tuesday:   short, poor sleep
   ↓
Wednesday: a hamstring a little more noticeable
   ↓
Thursday:  more fatigue than the load explains
   ↓
Saturday:  weather moves the long session
   ↓
Sunday:    a workout says fitness is better than assumed
```

Nothing catastrophic happened. The inputs drifted, and the plan was never synchronized with reality. What I'm actually doing is continuously trying to make

```text
desired training state ≈ actual athlete state
```

with some lag that never goes to zero.

This isn't eventual consistency in the formal sense. My body isn't a replicated database, and it never converges once the updates stop, because the updates never stop: the goal moves, the athlete changes, and training itself perturbs the state. But the useful part of the analogy holds. The plan and observed reality are always somewhat out of sync, and the job is to converge toward an objective rather than to enforce every intermediate state.

I run an AI coach on my training data, and building it forced me to make these assumptions explicit. But this note is about training, not the software.

## The plan has a desired state, and workouts aren't it

The thing I care about isn't `5 × 1 km @ threshold`. That's an action. The desired state is something like:

```text
By race day next summer:
- aerobic durability for a long bike leg
- run durability that survives coming off that bike
- a swim that's continuous and calm at race rhythm
- healthy enough to train consistently all year
- fatigue within recoverable bounds along the way
```

Individual workouts are attempts to move the system toward that state.

If you've used Kubernetes, this is the declarative model. You don't care that a container starts at 13:04; you care that the declared service becomes true. In the same way, I don't fundamentally care whether I do Thursday's session. I care whether the adaptation it was meant to produce happens.

That's a training argument, not just a software one. It's why my coach separates a few *key* sessions each week from *supporting* ones, and cuts supporting work first when something has to give.

## The athlete is observed, never read directly

The coach can see a lot: workouts with power, pace and heart rate, sleep, HRV and resting heart rate from my watch, training-load curves, my answers to short questions about readiness and soreness, and any symptoms I report.

None of these gives it:

```text
athlete.readiness = 0.73
```

They're noisy proxies. In distributed-systems terms, there are several replicas of my state, and none of them is authoritative. On any given morning all of these can be true at once:

- The watch thinks recovery is poor.
- My legs feel good.
- HRV is low.
- Yesterday's session went well.
- Sleep was bad because of a few beers, not accumulated training fatigue.

The athlete is partially observable. Good coaches have always worked this way; writing it down as a system just makes it hard to pretend otherwise.

## Every observation is stale

My latest FTP test says what I could do the day I did it. Fitness metrics like CTL are a 42-day weighted average, so they deliberately carry old information. Even how I feel when I wake up can change after a ten-minute warm-up.

Every training decision is made against a stale replica of the athlete:

```text
actual physiology
   ↓  physiological response
   ↓  sensor measurement
   ↓  watch → vendor cloud → training platform
   ↓  ingestion into the coach
   ↓  reasoning
   ↓  next prescription
```

Each arrow adds latency and uncertainty, and a few have bitten me. In one two-week stretch the watch data arrived partially synced six times; one morning's resting heart rate read 56 and was really 50 once the rest arrived. Another time a scheduled job ran in the evening instead of the morning, read that morning's wellness, and trimmed a bike session I had already ridden. The coach noticed the ride was already done and reverted its own edit.

The fix wasn't faster data. It was naming states that had been blurred together. "The sleep data has arrived" and "I slept well" are different facts. And "missing", "stale" and "empty" are three different states: a calendar the coach failed to read looks exactly like a calendar where every future workout was deleted, so the two must never share a representation. Every source now carries an age and a label, and nothing is silently trusted because it happens to be there.

## Reconciliation beats scheduling

Instead of this:

```text
if today == "Tuesday":
    do_threshold_session()
```

the loop is conceptually this:

```text
while season_active:
    observed = observe_athlete()            # stale, partial, conflicting
    desired  = season_objectives()
    delta    = compare(observed, desired)
    action   = choose_stimulus(delta, fatigue, constraints,
                               recent_training, injury_risk)
    execute(action)
    observe_response()
```

Here is the whole thing as a picture:

```text
                    ┌──────────────────────┐
                    │     Season goals     │
                    │    (desired state)   │
                    └──────────┬───────────┘
                               ▼
  ┌──────────────┐  ┌──────────────────────┐
  │ Wearables    │─▶│                      │
  │ Workouts     │─▶│ Coach reconciliation │
  │ My feedback  │─▶│        loop          │
  └──────▲───────┘  └──────────┬───────────┘
         │                     ▼
         │          ┌──────────────────────┐
         │          │    Next stimulus     │
         │          │  swim / bike / run   │
         │          └──────────┬───────────┘
         │                     ▼
         │          ┌──────────────────────┐
         └──────────│       Athlete        │
                    │    (actual state)    │
                    └──────────────────────┘
```

That doesn't make planning useless. A season still needs structure: general preparation, build, race-specific work, taper, race, recovery. That's the intent.

Periodization describes where the system should be going. Reconciliation decides what to do today to keep it going there.

And most days, reconciliation should decide to do nothing. If the plan is sensible and life is normal, the best action is to execute it. Adaptivity earns its keep at the edges: accumulated fatigue, illness, missed sessions, unexpectedly good adaptation, changed constraints. A controller that modifies the plan every day is probably worse than the static plan it replaced. Adaptive doesn't mean constantly changing.

## Don't replay missed work

Imagine a system that insists reality match the plan:

```text
Tuesday threshold failed
→ state inconsistent
→ retry threshold on Wednesday
```

That's often the worst available move. It stacks two hard days, and it treats the calendar, not the adaptation, as the thing that must be true.

Training has perturbations that should simply be absorbed. Miss one session, and often nothing needs to happen. Get ill, and the trajectory itself bends for a while.

In my coaching log the phrase "no make-up planned" shows up again and again, and it's correct every time. You don't replay every missed write until the original schedule is restored. The system converges toward the training objective, not toward historical compliance with a calendar.

Absorbing perturbations isn't free, though. This spring, illness and life dropped run-threshold work three weeks in a row. Each decision was right, and the accumulated drift was still real; the coach flagged it and made threshold a requirement the following week. Local decisions can all be correct while the cumulative drift becomes a problem, so the drift has to be observed too.

## Conflict resolution is the hard part

Here's a realistic morning:

```text
Plan:            threshold run
Training load:   normal
Sleep:           bad
HRV:             low
Why bad sleep:   alcohol
Legs:            fine
Tomorrow:        hard bike
Hamstring:       1/10 irritation
```

What wins? That's a conflict-resolution policy, and the signals shouldn't have equal authority. My coach has an explicit evidence order, roughly:

```text
safety, symptoms and calendar
  > did the session achieve its stimulus
  > comparable past executions
  > effort and local response
  > wellness trends
  > performance trends
  > model inference
```

A few of the rules that fall out of it:

- **Symptoms beat the chart.** One morning in May I woke with a sore throat while HRV and resting heart rate both looked green. Threshold was dropped anyway, and over the next days it went from "no intensity" to full rest once a cough appeared. Meanwhile the wellness numbers had the best morning of the week. Wellness can rebound a day or two before symptoms do.
- **The same signal can mean different things.** Bad sleep should change today's workout whatever caused it. But bad sleep from accumulated training stress is evidence that load is too high, and bad sleep from alcohol isn't. Same observation, different inference about the system underneath. The coach learned this the hard way: it twice read a hangover as overreach, and once confidently ruled alcohol out. Now it asks before diagnosing.
- **A positive signal doesn't add training.** Feeling fresh is not a reason to add unplanned work. The asymmetry is deliberate: it's much easier to recover from training I didn't do than from training I did.
- **A known injury has a standing rule.** A niggling hamstring gets one rule, decided in advance, rather than being renegotiated every morning against HRV.

More sensor data doesn't solve any of this. The hardest part isn't collecting more state. It's deciding which state gets to win when the replicas disagree.

## Controllers can destabilize the system

This is where control theory becomes more useful than the distributed-systems analogy.

A naive controller reacts to every reading:

```text
HRV down one morning   → cancel intervals
HRV up next morning    → add intensity
poor workout           → cut load
great workout          → raise load
```

Now the plan oscillates. That's an over-sensitive controller with too much gain, and it injects noise into the athlete instead of removing it.

The coach is a feedback controller with delayed, noisy measurements, so it needs the standard defences:

- **Trends, not point values.** Readings are compared with a rolling baseline, so a single bad morning doesn't trigger a change.
- **Hysteresis.** Progressing a key session takes several comparable successes. Reducing takes repeated under-performance. One missed session doesn't establish a trend. Between the two thresholds is a dead band where the answer is "hold".
- **Minimum dwell time.** After a material change, the plan has to stay put for a few days before it can change again.
- **Bounded steps.** One major lever per decision, each with a small maximum. Reversing direction needs a stated reason and new evidence.
- **Explicit exceptions.** Safety signals bypass all of the above. A cough doesn't wait out a cooldown.

The policy also bans two simple rules that look like control but aren't: a universal 10% weekly increase, and a fixed acute-to-chronic workload threshold. Both answer every situation with the same gain. And it names the failure mode directly: avoid both always-push and always-reduce decisions.

## Who is allowed to change the desired state?

The coach owns a lot. It can reshape planned workouts: duration, intensity, session choice. Same-day changes are deliberately narrow, and bigger calendar edits are shown to me as a diff before anything is written.

Other changes aren't reconciliation at all. They change the desired state:

```text
"I've decided not to do that race."
"I want to prioritise running for six weeks."
"This pain is different from before."
"I'm willing to accept more injury risk for this race."
```

Those don't belong to the controller. Races and training blocks live in a version-controlled config, not in the coach's working memory, and its coaching principles change only through a reviewed change. Nothing it reasons about at runtime can quietly override them.

That gives a clean split:

```text
Human:    defines goals and important constraints
Coach:    reconciles training toward those goals
Sensors:  provide observations
Athlete:  executes, and produces new state
```

The human and the athlete are the same person, which is the one place where the analogy gets odd. On a bad morning I'm the least reliable component in the system and also the only one allowed to change its goals.

## Eventual consistency doesn't mean winging it

The obvious objection is that this is just "train by feel" with extra vocabulary. It's the opposite. There's still a goal, progression, periodization, constraints and accumulated load. The flexibility lives inside a deliberate control system, with written rules about what each signal is allowed to do.

A good adaptive plan should be rigid about its objectives and flexible about its implementation.

I still want to arrive at the start line next summer fit enough to race the way I've planned. I just no longer expect every intermediate state to match a spreadsheet I wrote months earlier.
