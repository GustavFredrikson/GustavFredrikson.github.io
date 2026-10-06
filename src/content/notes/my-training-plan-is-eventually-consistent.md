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
Wednesday: hamstring a little more noticeable
   ↓
Thursday:  more fatigue than the load explains
   ↓
Saturday:  weather moves the long session
   ↓
Sunday:    a workout says fitness is better than assumed
```

Nothing catastrophic happened. The inputs drifted. At no point that week was the plan synchronized with reality, and it never will be. What I'm actually doing is continuously trying to make

```text
desired training state ≈ actual athlete state
```

with some lag that never goes to zero. That's the sense in which the plan is eventually consistent.

I run an AI coach on top of my Intervals.icu data, and building it is what forced me to think about this properly. But this note is about training, not the software. The software just made the assumptions impossible to leave implicit.

## The plan has a desired state, and workouts aren't it

The thing I care about isn't `5 × 1 km @ threshold`. That's an action. The desired state is something like:

```text
By July 2027 (IRONMAN 70.3 Jönköping):
- aerobic durability for a 70.3 bike
- run durability that survives coming off that bike
- a swim that's continuous and calm at race rhythm
- healthy enough to train consistently all year
- fatigue within recoverable bounds along the way
```

Individual workouts are attempts to move the system toward that state.

If you've used Kubernetes, this is the declarative model. You don't fundamentally care that a container starts at 13:04; you care that the service you declared becomes true, and the controller works out the steps. In the same way, I don't fundamentally care whether I do Thursday's prescribed session. I care whether the adaptation Thursday's session was meant to produce happens.

That's a training argument, not just a software one. It's why the coach's policy says to prefer continuity and consistency over completing every session or maximizing weekly hours, and why it separates *key* sessions from *supporting* ones. When something has to give, supporting work is scaled or removed first, because the key sessions carry most of the intended adaptation.

## The athlete is observed, never read directly

The coach can see a lot: workouts with power, pace and heart rate, Garmin's sleep, HRV and resting heart rate, training-load curves, my answers to short questions about readiness, effort and soreness, and any symptoms I report.

None of these gives it:

```text
athlete.readiness = 0.73
```

They're noisy proxies. In distributed-systems terms, there are several replicas of my state, and none of them is authoritative. On any given morning all of these can be true at once:

- Garmin thinks recovery is poor.
- My legs feel good.
- HRV is low.
- Yesterday's session went well.
- Sleep was bad because of a few beers, not accumulated training fatigue.

The athlete is partially observable. A good coach, human or not, has always worked this way. Writing it down as a system just makes it hard to pretend otherwise.

## Every observation is stale

Training decisions run on history. My latest FTP test says what I could do the day I did it. Last night's HRV is already a few hours old when I read it. Fitness metrics like CTL are a 42-day weighted average, so they deliberately carry old information. Even how I feel when I wake up can change after a ten-minute warm-up.

Every training decision is made against a stale replica of the athlete:

```text
actual physiology
   ↓  physiological response
   ↓  sensor measurement
   ↓  watch → Garmin → Intervals.icu
   ↓  ingestion into the coach
   ↓  reasoning
   ↓  next prescription
```

Each arrow adds latency and uncertainty, and a few have bitten me:

- **Sync lag.** In one two-week stretch Garmin delivered partial data six times. One morning's resting heart rate read 56; after the full sync it was 50. A decision made at 06:30 would have used the wrong number.
- **Acting on old state.** In April a scheduled job ran in the evening instead of the morning, read that morning's wellness, and trimmed a bike session I had already ridden. The coach noticed the ride was already matched to a completed activity and reverted the edit. Net calendar change: zero. Now it checks whether a session has been done before touching it.
- **Arrival is not quality.** The coach's instructions say plainly that "fresh sleep" must never mean only that Garmin's data arrived. "The data is current" and "I slept well" are different facts that are easy to merge.

So staleness is explicit now. Each source has a maximum age (two days for wellness, two weeks for activities and calendar), and a source is labelled fresh, stale, partial or missing rather than silently trusted. A missing cache is "unavailable", not "empty", because an empty calendar looks exactly like a decision to delete every future workout. My answers to questions expire too: a readiness answer is good for twelve hours. The morning review runs at 06:30 as a provisional read, at 07:15 as the real one, and again at 08:30 if sleep data hadn't arrived. That's a read-repair schedule for a body.

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

That doesn't make planning useless. A season still needs structure: general preparation, build, race-specific work, taper, race, recovery. Within that, my coach works in a repeating build, build, transition cycle, with named blocks for what each few weeks are for. That's the intent.

Periodization describes where the system should be going. Reconciliation decides what to do today to keep it going there.

## Strong consistency would be bad for me

Imagine a system that insists reality match the plan:

```text
Tuesday threshold failed
→ state inconsistent
→ retry threshold on Wednesday
```

That's often the worst available move. It stacks two hard days, and it treats the calendar, not the adaptation, as the thing that must be true.

Training has perturbations that should simply be absorbed. Miss one session? Often nothing needs to happen. A bad night? Lower today's intensity. Illness? The desired trajectory itself bends for a while. A race costs more than expected? Bring the recovery week forward.

In my coaching log the phrase "no make-up planned" shows up again and again, and it's correct every time. You don't replay every missed write until the original schedule is restored. The system converges toward the training objective, not toward historical compliance with a calendar.

Eventual consistency also has a cost, and it's worth tracking. This spring, illness and life combined to drop run-threshold work three weeks in a row. Each individual decision was right. The accumulated drift was still real, and the coach flagged it and made threshold a requirement for the following week. Absorbing perturbations is not the same as ignoring them.

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

A few of the rules it encodes:

- **Symptoms beat the chart.** In May I woke with a sore throat while HRV and resting heart rate both looked green. Threshold was dropped anyway. Over the next days it went from "no intensity", to "no strength either", to full rest once a cough appeared. A morning later the wellness numbers were the best of the week, and they still didn't decide anything. Wellness can rebound a day or two before symptoms do.
- **Known alcohol is not unexplained bad sleep.** A hangover still shapes today's dose, because the readiness is genuinely lower. But it's not evidence that training load is too high, so it doesn't feed into decisions about progression. Twice this spring a dip that looked like overreach turned out to be a hangover. The first time the coach had already trimmed two sessions and reverted them once I told it. The second time it had confidently ruled alcohol out, and was wrong. The lesson it logged was to ask before diagnosing. Unknown alcohol status is treated as no confounder at all, and the coach is told never to infer alcohol from the data.
- **A positive signal doesn't add training.** Feeling fresh is not a reason to add unplanned work. Asymmetry is deliberate: it's much easier to undo training I didn't do than training I did.
- **A known injury has a standing rule.** The hamstring currently carries one: treat a flare as an injury, and end the run if it flares early. That isn't re-litigated every morning against HRV.

The hardest part isn't collecting more state. It's deciding which state gets to win when the replicas disagree.

## Some writes require a human

The coach owns a lot. It may reshape any future planned workout in my calendar: duration, intensity, session choice. On a given morning it may adjust only today's session, only one of them, only if it's more than 45 minutes away, and only if it hasn't already been done. It can't touch completed activities, past events, race-day events or anything that isn't a workout. Larger calendar edits are previewed as a diff and applied only after I approve that exact change.

Other changes aren't reconciliation at all. They change the desired state:

```text
"I've decided not to race Jönköping."
"I want to prioritise running for six weeks."
"This pain is different from before."
"I'm willing to accept more injury risk for this race."
```

Those don't belong to the controller. Races and blocks live in a version-controlled config, not in the coach's working memory; it's told to add a new race to the config rather than to its own state. Coaching principles change through a reviewed pull request with a version bump. Runtime context can't quietly override them.

That gives a clean split:

```text
Human:    defines goals and important constraints
Coach:    reconciles training toward those goals
Sensors:  provide observations
Athlete:  executes, and produces new state
```

The human and the athlete are the same person, which is the one place where the analogy gets odd. On a bad morning I'm the least reliable component in the system and also the only one allowed to change its goals.

## Controllers can destabilize the system

This is where the analogy stops being a metaphor.

A naive controller reacts to every reading:

```text
HRV down one morning   → cancel intervals
HRV up next morning    → add intensity
poor workout           → cut load
great workout          → raise load
```

Now the plan oscillates. In control terms that's an over-sensitive controller with too much gain, and it injects noise into the athlete instead of removing it.

My coach is a feedback controller, so it needs the standard defences, and it has them:

- **Trends, not point values.** HRV and resting heart rate are compared with a seven-day median, and need at least three samples before a baseline counts. A yellow reading means HRV at or below 85% of that median; red means 70%.
- **Hysteresis.** Progressing a key session takes three comparable successes at 95% or better of the target, plus signs that the load was absorbed. Reducing takes at least two comparable outcomes below 80%. One missed or incomplete session doesn't establish a trend. The gap between those two thresholds is a dead band where the answer is "hold".
- **Minimum dwell time.** There's a three-day cooldown between material replans. Inside it, anything short of a red flag goes back to "hold".
- **Bounded steps.** One major lever per decision, and each lever has a small maximum: a few minutes of duration, two percentage points of intensity, one rep. Reversing direction, from progress to reduce or back, needs a stated reason and new evidence.
- **Explicit exceptions.** Safety signals bypass all of the above. A cough doesn't wait out a cooldown.

The policy also bans two simple rules that look like control but aren't: a universal 10% weekly increase, and a fixed acute-to-chronic workload threshold. Both answer every situation with the same gain. And it names the failure mode directly: avoid both always-push and always-reduce decisions.

## Eventual consistency doesn't mean winging it

The obvious objection is that this is just "train by feel" with extra vocabulary. It's the opposite. There's still a long-term goal, progression, periodization, constraints, an expected adaptation, and accumulated load that the system tracks whether I'm paying attention or not. The flexibility lives inside a deliberate control system, with written rules about what each signal is allowed to do.

A good adaptive plan should be rigid about its objectives and flexible about its implementation.

I still want to arrive in Jönköping next July fit enough to race the way I've planned. I just no longer expect every intermediate state to match a spreadsheet I wrote months earlier.
