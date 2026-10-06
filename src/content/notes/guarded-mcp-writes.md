---
title: Guarding state-changing MCP tools with preview, apply, and undo
summary: How I let an agent prepare changes to an external calendar without making every tool call a write, and what the design still leaves open.
date: 2026-10-06
tags: [MCP, Agents, Python, SQLite]
---

I run a small MCP server that gives an agent access to my Intervals.icu training data and calendar. Read access was simple: the agent can misread a chart, but reading changes nothing.

Write access is a different trust boundary. Once a tool call can move, rewrite or delete a planned session, a wrong argument is no longer a wrong answer. It changes state somewhere else. The question became: how can an agent prepare and carry out changes to external state without every tool call being immediately destructive?

## The problem

The first implementation exposed the API directly as MCP tools: `create_event`, `create_events_bulk`, `update_event`, `delete_event` and `delete_events_bulk`. They were mostly thin wrappers around the matching API calls, and the last one deleted every event in a date range.

That worked, and it exposed something I hadn't thought through. "Move Thursday's session to Friday?" followed by "sure" feels like approval, but the model builds the tool arguments after that exchange. The user agreed to a sentence; the API received a payload. If the two differ (a wrong event id, a description the model decided to tidy up), nothing notices. With direct mutation tools, the model's intent and the user's authorization get folded into one tool call.

## Requirements

The requirement became that the agent can freely *prepare* changes, but *executing* one needs something narrower than "the user said yes at some point":

- The agent can propose a change and get a field-level diff back, with nothing written remotely.
- Approval covers the exact, normalized mutation that was previewed, not whatever the agent sends later.
- Approval expires and is single-use.
- If the remote object has changed since the preview, the old approval no longer applies.
- An operation never executes twice, including on retries.
- A successful change can be reversed where that's practical.
- The operator can turn writes off entirely.

## The workflow

Four tools replaced the five mutators:

- `preview_event_change` validates, normalizes and stores a proposed create, bulk create, update or delete, and returns a diff, a `preview_id`, a `confirmation_token` and an expiry.
- `apply_event_change(preview_id, confirmation_token)` executes the stored proposal.
- `undo_event_change(operation_id, undo_token)` reverses it.
- `get_event_change_status(operation_id)` reports state without exposing tokens.

The old functions remain for trusted Python code, and a test asserts that none of them appear in the MCP tool list. Writes are also off by default: unless the operator sets `ICU_COACH_WRITE_MODE=guarded`, apply and undo refuse to run.

A preview for moving an event looks like this (synthetic data):

```json
{
  "status": "preview",
  "preview_id": "chg_3f9a1c0d2b7e4a6f8c11",
  "confirmation_token": "confirm_…",
  "expires_at": "2026-07-11T12:15:00+00:00",
  "action": "update",
  "diff": [
    { "field": "start_date_local",
      "before": "2026-07-16T08:00:00",
      "after": "2026-07-17T08:00:00" }
  ],
  "next_step": "After explicit user approval, call apply_event_…"
}
```

Apply takes no event data as input, only the id and the token. The payload that runs is the one stored at preview time, so the agent can't get one diff approved and then send another. The token scopes an approval obtained elsewhere; in the current implementation it does not itself prove that a human gave that approval. More on that below.

## The state machine

`preview_event_change` creates a row in a local SQLite table with status `pending`, and that `status` column is the state machine:

```text
preview_event_change
        │
        ▼
     pending ──(TTL passed)──────────▶ expired
        │ valid token, claimed
        ▼
     applying ──(recheck/API error)──▶ apply_failed
        │
        ▼
     applied
        │ valid undo token
        ▼
     undoing ──(recheck/API error)──▶ undo_failed
        │
        ▼
     undone
```

Every transition is conditional on the current status (`... WHERE id = ? AND status = 'applying'`), and nothing returns to `pending`.

The transition that matters most is `pending → applying`. It runs in a `BEGIN IMMEDIATE` transaction, which takes SQLite's write lock before reading the row, and it commits before any external call is made. Simplified:

```python
def claim_apply(self, preview_id, token):
    with self._connect() as conn:
        conn.execute("BEGIN IMMEDIATE")  # lock before the read
        row = select_row(conn, preview_id)
        if row["status"] != "pending":
            raise ChangeControlError("... cannot be applied")
        if now >= row["expires_at"]:
            mark_expired_and_commit(conn, preview_id)
            raise ChangeControlError("... expired")
        if not hmac.compare_digest(row["apply_token_hash"],
                                   sha256(token)):
            raise ChangeControlError("Invalid confirmation token")
        set_status(conn, preview_id, "applying")
    # committed: no other caller can claim this preview now
```

A concurrent or retried apply finds `applying`, `applied` or `apply_failed`, never `pending`. That makes apply at-most-once, not exactly-once. If the process dies between the claim and `finish_apply`, the row stays in `applying`. I would rather have a stuck row that needs a person to look at it than an automatic retry that might write twice.

## Approval as a capability

The obvious alternative was an `approved` flag that apply checks. A flag could be given expiry, scope and one-use semantics, but none of them come with it: a bare boolean doesn't say what was approved, for how long, or how many times, and it isn't something a caller has to possess. Anything that can call apply with the right id benefits from it.

Instead, the preview returns a capability: `confirm_` followed by `secrets.token_urlsafe(24)`, 192 random bits. Holding it, together with the preview id, is what allows the apply. The rest comes from how it's stored:

- **Hashed.** The ledger keeps only the token's SHA-256 and compares with `hmac.compare_digest`. The plaintext appears once, in the preview response, and reading the database doesn't give you a usable token.
- **Short-lived.** Previews expire after a configurable TTL. The default is 15 minutes, and the allowed range is 1 to 60.
- **One-shot.** A wrong token doesn't use up the preview. The right one does, whether the apply then succeeds or fails.
- **Scoped to the configured account.** The row stores a hash of the athlete id, and apply refuses if the server is now configured for someone else.

Read-only mode is checked *before* the claim, so turning writes off doesn't burn pending previews; a test confirms the row stays `pending`. And since rows hold event content, the ledger directory is created `0700` and the database file `0600`, which is also tested.

What the token doesn't do is prove that a human said yes. It goes back to the agent in the same response as the diff. The agent is told to wait for explicit approval, and `apply_event_change` is annotated as destructive so the client can ask before running it. The token limits what an approval can authorize. It doesn't produce the approval. A stricter version would send the token out of band, to the user rather than the model, so that pasting it back *is* the approval. I haven't built that.

## Binding approval to observed state

This is the part I care about most. What a human approved was a specific mutation against a specific observed state. If that state changes before execution, the approval shouldn't authorize the mutation any more.

For updates and deletes, the preview fetches the current event, refuses it if it's already paired with a completed activity or marked non-editable, and snapshots a fixed set of fields (date, name, description, type, category, target, indoor flag, duration, load, tags, colour, pairing, editability) with a canonical hash:

```python
def canonical_hash(value):
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

expected_before_hash = canonical_hash(event_snapshot(before))
```

After claiming, apply fetches the event again and compares before sending anything:

```python
current = await api_get_event(client, event_id)
if canonical_hash(event_snapshot(current)) != \
        record["expected_before_hash"]:
    raise ChangeControlError(
        f"event {event_id} changed after preview; "
        "create a fresh preview")
```

One failure case I specifically wanted to avoid:

1. The agent previews moving "Tempo 3×10 min" from Thursday to Friday. The diff shows a single field, `start_date_local`.
2. I approve it.
3. Before apply runs, the event changes somewhere else. Say I swap it for an easy run in the web app, or a watch sync pairs it with a completed activity.
4. The agent calls apply with the old preview id and token.
5. The new snapshot hashes differently. Apply raises, the row moves to `apply_failed` and no update request is sent. A new preview, against the new state, needs a new approval.

The stale patch, "set the date to Friday", would still have been valid against the new event. But I approved moving the session I saw, not whatever is at that event id now. Failing closed costs one extra preview. Tests cover both variants and assert that no update call is made.

This is a time-of-check/time-of-use problem: the check is a person reading a diff, the use is a write minutes later. Rechecking at apply time shrinks the window from however long the person took to answer to the gap between one GET and the following write. It doesn't close it. My client doesn't make conditional writes, so an edit that lands inside that gap would still go through. The snapshot also covers only the fields listed above, and a change to any other field won't invalidate a preview. Creates have no prior state to bind to, so a create preview is bound only to its own payload.

## Undo

A successful apply returns a second capability, an `undo_` token, hashed and single-use like the first. It's separate because undoing is a decision of its own.

Undo runs the same state check in reverse: it re-fetches each affected event and compares it with the snapshot recorded after the apply. If someone edited the event since, undo refuses rather than overwrite their edit, and the row moves to `undo_failed`.

**Undo is compensation, not rollback.** No transaction spans my ledger and the remote API, so undo is a new write that tries to recreate the earlier state:

- Undoing a create deletes the event.
- Undoing an update writes back the previous values of only the fields the change touched.
- Undoing a delete re-creates the event from its snapshot. It gets a new id, and anything that pointed at the old id doesn't follow it.
- Undoing a bulk create checks every event first and only then deletes them.

Apply compensates the same best-effort way, deleting a created workout that fails its read-back check or a bulk create that comes back short. Those cleanup calls can fail too. Undo tokens also don't currently expire.

## What this does not solve

- **Whether the proposal is any good.** The workflow ensures the change that runs is the one previewed, not that it was sensible.
- **Careless approval.** A diff only helps if someone reads it, and a bulk preview of up to 25 events is easy to skim.
- **A leaked or misused token.** The agent holds the token. Whoever holds an unexpired one can apply that single preview, exactly as stored, once. That is a smaller blast radius, but it is still access.
- **Authentication and authorization.** The server uses stdio and runs with the permissions of whoever starts it, API key included. The ledger is not an access-control system.
- **The remaining race window** and unsnapshotted fields, described above.
- **Ambiguous outcomes.** Local state can't always tell whether the remote write happened. `apply_failed` doesn't always mean nothing changed: an update that fails its read-back check has already been written. Reconciling that is manual, as is recovering a row stuck in `applying`.
- **Side effects outside the calendar.** If a workout synced to a device before it was undone, the undo doesn't follow it there.

## Current takeaway

For state-changing agent tools, I now prefer treating approval as a narrow, expiring capability tied to an observed state. The agent can propose freely. Execution requires a capability for one stored mutation, and that capability becomes useless after one claim, after expiry, or when the state the proposal was based on no longer matches. I prefer that to treating "the user said yes somewhere in the conversation" as authorization.
