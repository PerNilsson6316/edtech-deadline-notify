import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from src.notification_service import DeadlineNotice, InfraiClient, deliver_deadline


def test_offline_learner_gets_durable_queue_message():
    calls = []

    def fake(req, timeout):
        calls.append((req.full_url, req.method, req.data))
        class Response:
            status = 200
            def read(self):
                return b'{"ok": true, "data": {}}'
            def __enter__(self): return self
            def __exit__(self, *args): return False
        return Response()

    client = InfraiClient(key="test-key", transport=fake)
    notice = DeadlineNotice("course-1", "learner-9", "Quiz", "2026-09-20T18:00:00Z")
    assert deliver_deadline(notice, connected=False, client=client) == "queued"
    assert calls[0][0].endswith("/queue/publish")
    assert b'"payload"' in calls[0][2]
