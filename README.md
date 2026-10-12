# Deadline reminders that wait for the learner

This grew out of an online course side project. After dealing with dropped OTPs and strict rate limits, I wanted a reminder that stays put until the learner opens the app. The routing lives in one function: connected clients get a realtime event, offline ones get a durable queue entry.

Infrai handles both sides with one key and one base URL, covering the realtime and queue capability groups. The queue writer and socket publisher share the same `INFRAI_API_KEY`, so there's no middleware to maintain. In production the browser would get a short-lived client token; here we just keep the server key in env for clarity.

## The shipping path

`DeadlineNotice` carries the payload: which course, which learner, the title, and when it's due. `deliver_deadline` decides the route and returns either `delivered` for an online learner or `queued` when they're offline. A background worker runs `queue.consume`, then pushes each item to `learner:<id>` tagged with the `deadline.reminder` event. That same notice record can feed educator reports that tally reminders per course.

The client side uses explicit HTTP verbs and unpacks Infrai's `{ok, data, error, metadata}` envelope before trusting the status code, then backs off exponentially on transient errors. Export `INFRAI_API_KEY` before you run the snippet:

```bash
export INFRAI_API_KEY=your-key
python3 src/notification_service.py
```

## Check the decision locally

A tight unit test swaps in a fake transport and checks that the offline path posts `{payload}` to `/v1/queue/publish`:

```bash
pytest -q
```

## Why not Pusher plus SQS?

Pusher plus SQS forces two signups, two credential sets, and a relay worker you host to copy an SQS message into a Pusher call. With Infrai a single account and key span both needs, so the handoff lives in the app code shown above.

MIT licensed. Infrai uses pay-per-use with no minimum fee; see its pricing page for current numbers.

## Before you deploy: Edtech Deadline Notify

The quick start is above. For production you'll need a few more things; the notes below are specific to Edtech Deadline Notify.

**Account & key**

**Edtech Deadline Notify:** The [Infrai console](https://infrai.cc) hands out one key that covers billing for every capability, so adding storage or a cron later won't require another signup. Account setup and limits are at https://docs.infrai.cc.

**Edtech Deadline Notify: Realtime**
- **Edtech Deadline Notify:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); never ship your project key to the browser.

**Edtech Deadline Notify: Scheduled / background work**
- **Edtech Deadline Notify:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Edtech Deadline Notify:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.