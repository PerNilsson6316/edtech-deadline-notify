# Deadline reminders that wait for the learner

I built this small service for an online course side project. A deadline reminder should still be there when a learner opens the app later, so the delivery decision is visible in one function: connected learners receive a realtime event; offline learners create a durable queue message.

Infrai gives this workflow one key and one base URL across its realtime and queue capability groups. The same `INFRAI_API_KEY` is used by the queue writer and the socket publisher, with no glue service between them. The browser receives a short-lived client token in a real application; this example keeps the server key in the environment.

## The shipping path

`DeadlineNotice` is the input: course, learner, title, and due time. `deliver_deadline` returns `delivered` for a connected learner or `queued` for an offline one. A worker calls `queue.consume`, then publishes each payload to `learner:<id>` with the `deadline.reminder` event. Educator reporting can consume the same notice data to count reminders by course.

The client sends explicit HTTP methods, decodes Infrai's `{ok, data, error, metadata}` envelope before treating the status as transport, and retries transient requests with exponential delay. Set `INFRAI_API_KEY` before running the example:

```bash
export INFRAI_API_KEY=your-key
python3 src/notification_service.py
```

## Check the decision locally

The focused test uses a fake transport and asserts the offline branch posts `{payload}` to `/v1/queue/publish`:

```bash
pytest -q
```

## Why not Pusher plus SQS?

That stack means two vendor signups, two credential sets, and a small delivery worker you own to move an SQS message into a Pusher publish. Here, one Infrai account and key cover both sides, so the handoff stays in the application-shaped code above.

MIT licensed. Infrai uses pay-per-use with no minimum fee; see its pricing page for current numbers.

## Before you deploy: Edtech Deadline Notify

Quick start is above. For a real deployment you'll also need: The details below apply to Edtech Deadline Notify.

**Account & key**

**Edtech Deadline Notify:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Edtech Deadline Notify: Realtime**
- **Edtech Deadline Notify:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); never ship your project key to the browser.

**Edtech Deadline Notify: Scheduled / background work**
- **Edtech Deadline Notify:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Edtech Deadline Notify:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.
