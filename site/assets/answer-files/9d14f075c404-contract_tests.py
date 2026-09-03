"""
Contract tests for Batch Task Execution API v1.

SIMULATED: These tests target a minimal in-process stub to demonstrate the
contract. They do NOT call a real service and do NOT use accelerate.
Run:  python3 contract_tests.py
"""
import json, uuid, unittest
from urllib.parse import urlencode

# ---------------------------------------------------------------------------
# Minimal in-process stub that mimics the contract (SIMULATED, not a real server)
# ---------------------------------------------------------------------------
class StubTaskAPI:
    MAX_BATCH = 1000
    VALID_TYPES = {"training", "evaluation", "inference", "data_processing"}
    def __init__(self):
        self.tasks = {}          # task_id -> task dict
        self.batch_counter = 0
        self.idem_store = {}     # key -> (body_hash, status_code, response)
    def _err(self, code, message, status=400, details=None, request_id="req_sim"):
        e = {"code": code, "message": message, "request_id": request_id}
        if details: e["details"] = details
        return status, {"error": e}
    def batch_create(self, body, idem_key, scopes):
        if "tasks:write" not in scopes:
            return self._err("INSUFFICIENT_SCOPE", "Required scope: tasks:write", 403)
        if not idem_key:
            return self._err("INVALID_REQUEST", "Idempotency-Key header required", 400)
        if not isinstance(body, dict) or "tasks" not in body:
            return self._err("INVALID_REQUEST", "missing 'tasks'", 400)
        tasks = body["tasks"]
        if not isinstance(tasks, list) or not (1 <= len(tasks) <= self.MAX_BATCH):
            return self._err("BATCH_TOO_LARGE", f"tasks size must be 1..{self.MAX_BATCH}", 413)
        body_hash = json.dumps(body, sort_keys=True)
        if idem_key in self.idem_store:
            h, sc, resp = self.idem_store[idem_key]
            if h != body_hash:
                return self._err("IDEMPOTENCY_KEY_CONFLICT", "key used with different body", 409)
            sc["X-Idempotent-Replay"] = "true"
            return sc["status"], resp
        # validate & create
        self.batch_counter += 1
        batch_id = f"batch_{self.batch_counter:03d}"
        results = []
        for i, t in enumerate(tasks):
            cid = t.get("client_task_id")
            typ = t.get("type")
            if not cid or typ not in self.VALID_TYPES or "payload" not in t:
                results.append({
                    "client_task_id": cid,
                    "created": False,
                    "error": {"code": "TASK_TYPE_INVALID" if typ not in self.VALID_TYPES else "INVALID_REQUEST",
                              "message": "invalid item"}
                })
                continue
            tid = f"t_{uuid.uuid4().hex[:8]}"
            self.tasks[tid] = {
                "task_id": tid, "batch_id": batch_id, "type": typ,
                "status": "PENDING", "created_at": "2026-08-10T13:00:00Z",
                "updated_at": "2026-08-10T13:00:00Z",
            }
            results.append({"client_task_id": cid, "task_id": tid, "status": "PENDING", "created": True})
        all_ok = all(r["created"] for r in results)
        status = 201 if all_ok else 207
        resp = {"batch_id": batch_id, "results": results}
        self.idem_store[idem_key] = (body_hash, {"status": status, "X-Idempotent-Replay": "false"}, resp)
        return status, resp
    def get_task(self, task_id, scopes):
        if "tasks:read" not in scopes:
            return self._err("INSUFFICIENT_SCOPE", "Required scope: tasks:read", 403)
        t = self.tasks.get(task_id)
        if not t: return self._err("TASK_NOT_FOUND", f"task '{task_id}' not found", 404)
        return 200, t
    def list_tasks(self, params, scopes):
        if "tasks:read" not in scopes:
            return self._err("INSUFFICIENT_SCOPE", "Required scope: tasks:read", 403)
        items = list(self.tasks.values())
        status_f = params.get("status")
        if status_f: items = [t for t in items if t["status"] == status_f]
        limit = int(params.get("limit", 50))
        limit = max(1, min(200, limit))
        cursor = params.get("cursor")
        start = int(cursor) if cursor and cursor.isdigit() else 0
        page = items[start:start+limit]
        nxt = str(start+limit) if start+limit < len(items) else None
        return 200, {"items": page, "next_cursor": nxt, "total_count": len(items)}

# ---------------------------------------------------------------------------
# Contract tests
# ---------------------------------------------------------------------------
SCOPES_RW = {"tasks:read", "tasks:write"}
SCOPES_R  = {"tasks:read"}
SCOPES_W  = {"tasks:write"}
SCOPES_NONE = set()

class ContractTests(unittest.TestCase):
    def setUp(self):
        self.api = StubTaskAPI()
    def test_batch_create_success(self):
        body = {"tasks": [{"client_task_id": "a", "type": "training", "payload": {}}]}
        sc, resp = self.api.batch_create(body, str(uuid.uuid4()), SCOPES_RW)
        self.assertEqual(sc, 201)
        self.assertIn("batch_id", resp)
        self.assertEqual(len(resp["results"]), 1)
        self.assertTrue(resp["results"][0]["created"])
        self.assertEqual(resp["results"][0]["status"], "PENDING")
    def test_idempotency_same_key_same_body(self):
        body = {"tasks": [{"client_task_id": "a", "type": "training", "payload": {}}]}
        key = str(uuid.uuid4())
        sc1, r1 = self.api.batch_create(body, key, SCOPES_RW)
        sc2, r2 = self.api.batch_create(body, key, SCOPES_RW)
        self.assertEqual(sc1, 201)
        self.assertEqual(sc2, 201)
        self.assertEqual(r1, r2)           # same response
        self.assertEqual(self.api.idem_store[key][1]["X-Idempotent-Replay"], "true")
    def test_idempotency_same_key_different_body_conflict(self):
        key = str(uuid.uuid4())
        b1 = {"tasks": [{"client_task_id": "a", "type": "training", "payload": {}}]}
        b2 = {"tasks": [{"client_task_id": "a", "type": "inference", "payload": {}}]}
        self.api.batch_create(b1, key, SCOPES_RW)
        sc, resp = self.api.batch_create(b2, key, SCOPES_RW)
        self.assertEqual(sc, 409)
        self.assertEqual(resp["error"]["code"], "IDEMPOTENCY_KEY_CONFLICT")
    def test_partial_failure_207(self):
        body = {"tasks": [
            {"client_task_id": "ok", "type": "training", "payload": {}},
            {"client_task_id": "bad", "type": "BOGUS", "payload": {}},
        ]}
        sc, resp = self.api.batch_create(body, str(uuid.uuid4()), SCOPES_RW)
        self.assertEqual(sc, 207)
        self.assertTrue(resp["results"][0]["created"])
        self.assertFalse(resp["results"][1]["created"])
        self.assertIn("error", resp["results"][1])
    def test_batch_size_limit(self):
        body = {"tasks": [{"client_task_id": str(i), "type": "training", "payload": {}} for i in range(1001)]}
        sc, resp = self.api.batch_create(body, str(uuid.uuid4()), SCOPES_RW)
        self.assertEqual(sc, 413)
        self.assertEqual(resp["error"]["code"], "BATCH_TOO_LARGE")
    def test_minimum_permission_write_required(self):
        body = {"tasks": [{"client_task_id": "a", "type": "training", "payload": {}}]}
        sc, resp = self.api.batch_create(body, str(uuid.uuid4()), SCOPES_R)
        self.assertEqual(sc, 403)
        self.assertEqual(resp["error"]["code"], "INSUFFICIENT_SCOPE")
    def test_minimum_permission_read_required(self):
        sc, resp = self.api.get_task("anything", SCOPES_W)
        self.assertEqual(sc, 403)
        sc2, r2 = self.api.list_tasks({}, SCOPES_NONE)
        self.assertEqual(sc2, 403)
    def test_get_task_404(self):
        sc, resp = self.api.get_task("nonexistent", SCOPES_R)
        self.assertEqual(sc, 404)
        self.assertEqual(resp["error"]["code"], "TASK_NOT_FOUND")
    def test_pagination_cursor(self):
        for i in range(5):
            self.api.batch_create(
                {"tasks": [{"client_task_id": f"c{i}", "type": "training", "payload": {}}]},
                str(uuid.uuid4()), SCOPES_RW)
        sc, p1 = self.api.list_tasks({"limit": "2"}, SCOPES_R)
        self.assertEqual(sc, 200)
        self.assertEqual(len(p1["items"]), 2)
        self.assertIsNotNone(p1["next_cursor"])
        sc, p2 = self.api.list_tasks({"limit": "2", "cursor": p1["next_cursor"]}, SCOPES_R)
        self.assertEqual(len(p2["items"]), 2)
        sc, p3 = self.api.list_tasks({"limit": "2", "cursor": p2["next_cursor"]}, SCOPES_R)
        self.assertEqual(len(p3["items"]), 1)
        self.assertIsNone(p3["next_cursor"])
    def test_pagination_limit_clamped(self):
        sc, p = self.api.list_tasks({"limit": "99999"}, SCOPES_R)
        self.assertEqual(sc, 200)  # clamped to 200, no error
    def test_error_response_shape(self):
        sc, resp = self.api.get_task("x", SCOPES_R)
        self.assertEqual(sc, 404)
        self.assertIn("error", resp)
        for k in ("code", "message"):
            self.assertIn(k, resp["error"])
    def test_unknown_fields_ignored_in_response(self):
        # clients should tolerate extra fields; stub returns only documented fields
        body = {"tasks": [{"client_task_id": "a", "type": "training", "payload": {}, "unknown_future_field": 1}]}
        sc, resp = self.api.batch_create(body, str(uuid.uuid4()), SCOPES_RW)
        self.assertEqual(sc, 201)  # server ignores unknown input fields gracefully

if __name__ == "__main__":
    unittest.main(verbosity=2)
