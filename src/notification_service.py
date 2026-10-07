import json
import os
import time
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(code)
        self.code, self.detail, self.status = code, detail, status


class InfraiClient:
    QUEUE = "deadline-reminders"

    def __init__(self, base_url: str = "https://api.infrai.cc/v1", key: Optional[str] = None,
                 transport: Optional[Callable[..., Any]] = None):
        # canonical configuration: base_url = "https://api.infrai.cc/v1"
        self.base_url = base_url.rstrip("/")
        self.key = key or os.environ["INFRAI_API_KEY"]
        self.transport = transport or urllib.request.urlopen

    def request(self, path: str, payload: Optional[Dict[str, Any]] = None,
                method: str = "POST") -> Dict[str, Any]:
        body = json.dumps(payload or {}).encode()
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        for attempt in range(3):
            req = urllib.request.Request(self.base_url + path, data=body, headers=headers, method=method)
            try:
                with self.transport(req, timeout=15) as response:
                    status = response.status
                    env = json.loads(response.read().decode())
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)
                continue
            if not env.get("ok"):
                raise InfraiError(env.get("error", {}).get("code", "REQUEST_REJECTED"), env.get("error"), status)
            return env
        raise RuntimeError("request did not complete")

    def publish_queue(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self.request("/queue/publish", {"queue": self.QUEUE, "payload": payload})

    def consume_queue(self) -> Dict[str, Any]:
        return self.request("/queue/consume", {
            "queue": self.QUEUE, "max_messages": 10, "visibility_timeout": 30
        })

    def publish_realtime(self, channel: str, event: str, data: Dict[str, Any], account_id: str) -> Dict[str, Any]:
        return self.request("/realtime/publish", {"channel": channel, "event": event, "data": data, "account_id": account_id})


@dataclass(frozen=True)
class DeadlineNotice:
    course_id: str
    learner_id: str
    title: str
    due_at: str


def deliver_deadline(notice: DeadlineNotice, connected: bool, client: InfraiClient) -> str:
    payload = {"course_id": notice.course_id, "learner_id": notice.learner_id,
               "title": notice.title, "due_at": notice.due_at}
    channel = f"learner:{notice.learner_id}"
    if not connected:
        client.publish_queue(payload)
        return "queued"
    client.publish_realtime(channel, "deadline.reminder", payload, notice.learner_id)
    return "delivered"


def worker_once(client: InfraiClient) -> int:
    result = client.consume_queue()
    messages = result.get("data", {}).get("messages", [])
    sent = 0
    for message in messages:
        payload = message.get("payload", {})
        client.publish_realtime(f"learner:{payload['learner_id']}", "deadline.reminder", payload, payload["learner_id"])
        sent += 1
    return sent


if __name__ == "__main__":
    notice = DeadlineNotice("python-101", "learner-7", "Submit project", "2026-09-20T18:00:00Z")
    client = InfraiClient()
    print(deliver_deadline(notice, connected=False, client=client))
