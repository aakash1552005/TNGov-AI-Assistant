"""Production Verification Suite (Issue 7).

Single-command script to perform end-to-end evidence collection and audit
against the live production Railway backend (or local backend).

Usage:
  python backend/evaluation/production_verify.py [--url https://backend-production-0a73.up.railway.app]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
import urllib.error

DEFAULT_BACKEND_URL = "https://backend-production-0a73.up.railway.app"

class Verifier:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.results: list[dict[str, str]] = []
        self.passed = 0
        self.failed = 0

    def log(self, category: str, status: str, evidence: str):
        symbol = "[PASS]" if status == "PASS" else "[FAIL]"
        print(f"{symbol} [{category}] {evidence}")
        self.results.append({"category": category, "status": status, "evidence": evidence})
        if status == "PASS":
            self.passed += 1
        else:
            self.failed += 1

    def _http_get(self, path: str) -> tuple[int, dict]:
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url, headers={"User-Agent": "ProductionVerifier/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return resp.status, data
        except urllib.error.HTTPError as e:
            return e.code, {}
        except Exception as e:
            return 500, {"error": str(e)}

    def _http_post(self, path: str, payload: dict) -> tuple[int, dict]:
        url = f"{self.base_url}{path}"
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json", "User-Agent": "ProductionVerifier/1.0"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return resp.status, data
        except urllib.error.HTTPError as e:
            try:
                err_data = json.loads(e.read().decode("utf-8"))
            except Exception:
                err_data = {"error": str(e)}
            return e.code, err_data
        except Exception as e:
            return 500, {"error": str(e)}

    def verify_all(self):
        print("=" * 75)
        print(f"      PRODUCTION VERIFICATION SUITE — {self.base_url}")
        print("=" * 75)

        # 1. Health
        code, data = self._http_get("/health")
        if code == 200 and data.get("status") == "healthy":
            self.log("Health Check", "PASS", f"Status 200, app={data.get('app')}, provider={data.get('llm_provider')}")
        else:
            self.log("Health Check", "FAIL", f"HTTP {code}: {data}")

        # 2. Admin Stats
        code, data = self._http_get("/admin/stats")
        total_chunks = data.get("total_chunks", 0)
        if code == 200 and total_chunks > 0:
            self.log("Admin Stats", "PASS", f"Total Chunks: {total_chunks}, BM25 Chunks: {data.get('bm25_indexed_chunks')}")
        else:
            self.log("Admin Stats", "FAIL", f"HTTP {code}: {data}")

        # 3. Admin Version
        code, data = self._http_get("/admin/version")
        commit = data.get("git_commit", "")
        if code == 200 and commit:
            self.log("Admin Version", "PASS", f"Git Commit: {commit}, LLM: {data.get('llm_model')}")
        else:
            self.log("Admin Version", "FAIL", f"HTTP {code}: {data}")

        # 4. Admin Dataset
        code, data = self._http_get("/admin/dataset")
        docs = data.get("documents", [])
        if code == 200 and len(docs) > 0:
            self.log("Admin Dataset", "PASS", f"Documents Count: {len(docs)}, Sample Chunk IDs: {len(data.get('chunk_ids_sample', []))}")
        else:
            self.log("Admin Dataset", "FAIL", f"HTTP {code}: {data}")

        # 5. Admin Feedback
        code, data = self._http_get("/admin/feedback")
        if code == 200 and "total_feedback" in data:
            self.log("Admin Feedback", "PASS", f"Total Feedback: {data.get('total_feedback')}, Up: {data.get('up_count')}")
        else:
            self.log("Admin Feedback", "FAIL", f"HTTP {code}: {data}")

        # 6. Retrieval & Citations
        code, data = self._http_post("/chat", {"question": "What is Pudhumai Penn?"})
        citations = data.get("citations", [])
        session_id = data.get("session_id")
        msg_id = data.get("message_id")
        if code == 200 and len(citations) > 0:
            top_cite = citations[0]
            self.log(
                "Retrieval & Citations",
                "PASS",
                f"Top Citation: '{top_cite.get('scheme_name')}' ({top_cite.get('document_name')}, p.{top_cite.get('page_number')})",
            )
        else:
            self.log("Retrieval & Citations", "FAIL", f"HTTP {code}: {data}")

        # 7. Refusal / Anti-hallucination (Issue 1 pre-LLM topic guard verification)
        code, data = self._http_post("/chat", {"question": "What is NASA Mars rover welfare scheme in Tamil Nadu?"})
        llm_called = data.get("retrieval_metadata", {}).get("llm_called", True)
        answer = data.get("answer", "")
        if code == 200 and not llm_called and "only answers officially indexed" in answer.lower():
            self.log("Pre-LLM Refusal", "PASS", "OOD query successfully rejected before LLM call")
        else:
            self.log("Pre-LLM Refusal", "FAIL", f"llm_called={llm_called}, Answer snippet: {answer[:100]}")

        # 8. Conversation Memory (Multi-turn)
        if session_id:
            code, data = self._http_post("/chat", {"question": "Who can apply?", "session_id": session_id})
            ans = data.get("answer", "").lower()
            if code == 200 and ("pudhumai" in ans or "female" in ans or "girl" in ans or "student" in ans):
                self.log("Conversation Memory", "PASS", "Context retained from previous turn")
            else:
                self.log("Conversation Memory", "FAIL", f"Answer did not reflect previous turn context: {ans[:100]}")
        else:
            self.log("Conversation Memory", "FAIL", "Skipped because previous chat turn failed to return session_id")

        # 9. Session History
        if session_id:
            code, data = self._http_get(f"/chat/{session_id}")
            messages = data.get("messages", [])
            if code == 200 and len(messages) >= 2:
                self.log("Session History", "PASS", f"Retrieved {len(messages)} messages for session {session_id}")
            else:
                self.log("Session History", "FAIL", f"HTTP {code}, Messages count: {len(messages)}")

        # 10. Feedback Submission
        if session_id and msg_id:
            fb_payload = {"session_id": session_id, "message_id": msg_id, "rating": "up", "comment": "Verification test"}
            code, data = self._http_post("/feedback", fb_payload)
            if code == 200 and data.get("status") == "success":
                self.log("Feedback Submission", "PASS", "Feedback recorded successfully")
            else:
                self.log("Feedback Submission", "FAIL", f"HTTP {code}: {data}")

        print("\n" + "=" * 75)
        print(f"VERIFICATION SUMMARY: {self.passed} PASSED, {self.failed} FAILED")
        print("=" * 75)
        return self.failed == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Production Verification Suite")
    parser.add_argument("--url", default=DEFAULT_BACKEND_URL, help="Base backend URL")
    args = parser.parse_args()

    verifier = Verifier(args.url)
    success = verifier.verify_all()
    sys.exit(0 if success else 1)
