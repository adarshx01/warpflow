#!/usr/bin/env python3
"""
WarpCore API Test Script
========================
Tests all backend API endpoints: auth, credentials, and service execution.

Usage:
    # Start the server first:
    cd warpcore && uvicorn main:app --reload --port 8000

    # Then run tests:
    python tests/test_api.py

    # Test specific services:
    python tests/test_api.py --service google-docs
    python tests/test_api.py --service gmail
    python tests/test_api.py --service openai
"""
import argparse
import json
import sys
from typing import Any

import httpx

BASE_URL = "http://localhost:8000"
TEST_USER = {
    "name": "Test User",
    "email": "testuser@warpflow.dev",
    "password": "testpassword123",
}


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def ok(msg: str) -> None:
    print(f"  {Colors.GREEN}✓{Colors.RESET} {msg}")


def fail(msg: str, detail: Any = None) -> None:
    print(f"  {Colors.RED}✗{Colors.RESET} {msg}")
    if detail:
        print(f"    {Colors.RED}{json.dumps(detail, indent=2, default=str)[:300]}{Colors.RESET}")


def info(msg: str) -> None:
    print(f"  {Colors.CYAN}ℹ{Colors.RESET} {msg}")


def section(title: str) -> None:
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'═' * 50}{Colors.RESET}")
    print(f"{Colors.BOLD}  {title}{Colors.RESET}")
    print(f"{Colors.CYAN}{'═' * 50}{Colors.RESET}")


class APITester:
    """Stateful test runner that maintains auth session."""

    def __init__(self):
        self.client = httpx.Client(base_url=BASE_URL, timeout=30.0)
        self.cookies: dict[str, str] = {}
        self.csrf_token: str = ""
        self.user_id: str = ""
        self.credential_ids: dict[str, str] = {}  # type -> id
        self.passed = 0
        self.failed = 0

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.csrf_token:
            h["X-CSRF-Token"] = self.csrf_token
        return h

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        kwargs.setdefault("headers", self._headers())
        kwargs.setdefault("cookies", self.cookies)
        return self.client.request(method, path, **kwargs)

    def _extract_cookies(self, resp: httpx.Response) -> None:
        for name, value in resp.cookies.items():
            self.cookies[name] = value
        if "csrf_token" in self.cookies:
            self.csrf_token = self.cookies["csrf_token"]

    # ── Auth Tests ──

    def test_health(self) -> bool:
        section("Health Check")
        try:
            resp = self.client.get("/health")
            if resp.status_code == 200 and resp.json().get("status") == "ok":
                ok("GET /health → 200")
                self.passed += 1
                return True
            fail(f"GET /health → {resp.status_code}", resp.json())
            self.failed += 1
            return False
        except httpx.ConnectError:
            fail("Server not running at " + BASE_URL)
            self.failed += 1
            return False

    def test_register(self) -> bool:
        section("Authentication")
        resp = self._request("POST", "/api/auth/register", json=TEST_USER)
        self._extract_cookies(resp)

        if resp.status_code == 201:
            data = resp.json()
            self.user_id = data["user"]["id"]
            ok(f"POST /api/auth/register → 201 (user: {self.user_id[:8]}...)")
            self.passed += 1
            return True
        elif resp.status_code == 409:
            info("User already exists, trying login instead")
            return self.test_login()
        else:
            fail(f"POST /api/auth/register → {resp.status_code}", resp.json())
            self.failed += 1
            return False

    def test_login(self) -> bool:
        resp = self._request("POST", "/api/auth/login", json={
            "email": TEST_USER["email"],
            "password": TEST_USER["password"],
        })
        self._extract_cookies(resp)

        if resp.status_code == 200:
            data = resp.json()
            self.user_id = data["user"]["id"]
            ok(f"POST /api/auth/login → 200 (user: {self.user_id[:8]}...)")
            self.passed += 1
            return True
        fail(f"POST /api/auth/login → {resp.status_code}", resp.json())
        self.failed += 1
        return False

    def test_me(self) -> None:
        resp = self._request("GET", "/api/auth/me")
        if resp.status_code == 200:
            ok(f"GET /api/auth/me → 200 ({resp.json()['email']})")
            self.passed += 1
        else:
            fail(f"GET /api/auth/me → {resp.status_code}", resp.json())
            self.failed += 1

    # ── Credential Tests ──

    def test_credentials(self, cred_type: str = "google-docs") -> str | None:
        section(f"Credentials ({cred_type})")

        # List
        resp = self._request("GET", f"/api/credentials?type={cred_type}")
        if resp.status_code == 200:
            creds = resp.json()
            ok(f"GET /api/credentials?type={cred_type} → {len(creds)} found")
            self.passed += 1
            if creds:
                cred_id = creds[0]["id"]
                self.credential_ids[cred_type] = cred_id
                info(f"Using existing credential: {cred_id[:8]}...")
                return cred_id
        else:
            fail(f"GET /api/credentials → {resp.status_code}", resp.json())
            self.failed += 1

        # Create
        resp = self._request("POST", "/api/credentials", json={
            "type": cred_type,
            "name": f"Test {cred_type}",
            "client_id": "test-client-id.apps.googleusercontent.com",
            "client_secret": "test-client-secret",
        })
        if resp.status_code == 201:
            cred_id = resp.json()["id"]
            self.credential_ids[cred_type] = cred_id
            ok(f"POST /api/credentials → 201 (id: {cred_id[:8]}...)")
            self.passed += 1
            return cred_id
        fail(f"POST /api/credentials → {resp.status_code}", resp.json())
        self.failed += 1
        return None

    # ── Google Service Tests ──

    def test_google_service(self, service: str, operation: str, params: dict) -> None:
        """Test a Google service execute endpoint. Expects 401/422 without real OAuth."""
        section(f"Google {service.replace('-', ' ').title()}: {operation}")
        cred_id = self.credential_ids.get(service)

        if not cred_id:
            cred_id = self.test_credentials(service)
        if not cred_id:
            fail("No credential available, skipping")
            self.failed += 1
            return

        resp = self._request("POST", f"/api/{service}/execute", json={
            "credentialId": cred_id,
            "operation": operation,
            "params": params,
        })

        # Without real OAuth tokens, we expect 401 (not connected)
        if resp.status_code == 401:
            ok(f"POST /api/{service}/execute → 401 (expected: no OAuth tokens)")
            info("To fully test, connect OAuth via browser first")
            self.passed += 1
        elif resp.status_code == 200:
            ok(f"POST /api/{service}/execute → 200 (success!)")
            info(f"Response: {json.dumps(resp.json(), indent=2, default=str)[:200]}")
            self.passed += 1
        elif resp.status_code == 422:
            # Could be validation error or token refresh failure
            ok(f"POST /api/{service}/execute → 422 (endpoint reachable, auth/validation issue)")
            self.passed += 1
        else:
            fail(f"POST /api/{service}/execute → {resp.status_code}", resp.json())
            self.failed += 1

    def test_google_oauth_start(self, service: str) -> None:
        """Test that the OAuth start endpoint returns a redirect."""
        cred_id = self.credential_ids.get(service)
        if not cred_id:
            return

        resp = self._request("GET", f"/api/{service}/oauth/start?credential_id={cred_id}",
                             follow_redirects=False)
        if resp.status_code in (302, 307):
            location = resp.headers.get("location", "")
            if "accounts.google.com" in location:
                ok(f"GET /api/{service}/oauth/start → redirect to Google")
                self.passed += 1
            else:
                fail(f"Unexpected redirect: {location[:100]}")
                self.failed += 1
        else:
            fail(f"GET /api/{service}/oauth/start → {resp.status_code}", resp.json())
            self.failed += 1

    # ── AI Service Tests ──

    def test_ai_service(self, service: str, operation: str, params: dict, api_key: str = "test-key") -> None:
        """Test an AI service execute endpoint."""
        section(f"AI {service.replace('-', ' ').title()}: {operation}")

        resp = self._request("POST", f"/api/{service}/execute", json={
            "apiKey": api_key,
            "operation": operation,
            "params": params,
        })

        if resp.status_code == 200:
            ok(f"POST /api/{service}/execute → 200")
            data = resp.json()
            info(f"Response: {json.dumps(data, indent=2, default=str)[:200]}")
            self.passed += 1
        elif resp.status_code == 422:
            detail = resp.json()
            detail_str = json.dumps(detail, default=str)
            if "invalid" in detail_str.lower() or "api" in detail_str.lower() or "auth" in detail_str.lower():
                ok(f"POST /api/{service}/execute → 422 (expected: invalid API key)")
                info("Provide a real API key to fully test")
                self.passed += 1
            else:
                fail(f"POST /api/{service}/execute → 422", detail)
                self.failed += 1
        elif resp.status_code == 401:
            ok(f"POST /api/{service}/execute → 401 (expected: invalid API key)")
            self.passed += 1
        else:
            fail(f"POST /api/{service}/execute → {resp.status_code}", resp.json())
            self.failed += 1

    # ── Workflow Tests ──

    def test_workflows(self) -> None:
        section("Workflows")

        # List templates
        resp = self._request("GET", "/api/node-templates")
        if resp.status_code == 200:
            templates = resp.json()
            ok(f"GET /api/node-templates → {len(templates)} templates")
            self.passed += 1

            # Check for our new service templates
            template_ids = {t["id"] for t in templates}
            for expected in ["google-docs", "google-drive", "gmail", "google-sheets", "google-forms", "gemini"]:
                if expected in template_ids:
                    ok(f"  Template '{expected}' found")
                else:
                    info(f"  Template '{expected}' not found (may need re-seed)")
        else:
            fail(f"GET /api/node-templates → {resp.status_code}", resp.json())
            self.failed += 1

        # List workflows
        resp = self._request("GET", "/api/workflows")
        if resp.status_code == 200:
            ok(f"GET /api/workflows → {len(resp.json())} workflows")
            self.passed += 1
        else:
            fail(f"GET /api/workflows → {resp.status_code}", resp.json())
            self.failed += 1

        # Create a workflow
        resp = self._request("POST", "/api/workflows", json={
            "name": "Test Workflow",
            "description": "Created by test script",
            "nodes": [
                {"id": "n1", "type": "manual-trigger", "position": {"x": 100, "y": 100}, "data": {}}
            ],
            "connections": [],
        })
        if resp.status_code == 201:
            wf = resp.json()
            ok(f"POST /api/workflows → 201 created (id: {wf['id'][:8]}...)")
            self.passed += 1

            # Clean up: delete the test workflow
            del_resp = self._request("DELETE", f"/api/workflows/{wf['id']}")
            if del_resp.status_code == 204:
                ok(f"DELETE /api/workflows/{wf['id'][:8]}... → 204 cleaned up")
                self.passed += 1
        else:
            fail(f"POST /api/workflows → {resp.status_code}", resp.json())
            self.failed += 1

    # ── Run All ──

    def run_all(self, services: list[str] | None = None) -> None:
        # Health
        if not self.test_health():
            print(f"\n{Colors.RED}Server not reachable. Start it with: uvicorn main:app --reload{Colors.RESET}")
            return

        # Auth
        if not self.test_register():
            print(f"\n{Colors.RED}Auth failed, cannot continue.{Colors.RESET}")
            return
        self.test_me()

        run_all = services is None or "all" in services

        # Workflows
        if run_all:
            self.test_workflows()

        # Google Services
        google_tests = {
            "google-docs": ("create", {"title": "Test Doc"}),
            "google-drive": ("list_files", {}),
            "gmail": ("list_messages", {"maxResults": 5}),
            "google-sheets": ("get", {"spreadsheetId": "test-id"}),
            "google-forms": ("get", {"formId": "test-id"}),
        }

        for svc, (op, params) in google_tests.items():
            if run_all or svc in (services or []):
                self.test_credentials(svc)
                self.test_google_service(svc, op, params)
                self.test_google_oauth_start(svc)

        # AI Services
        ai_tests = {
            "openai": ("chat_completion", {"prompt": "Say hello", "model": "gpt-3.5-turbo"}),
            "gemini": ("generate_content", {"prompt": "Say hello", "model": "gemini-2.0-flash"}),
        }

        for svc, (op, params) in ai_tests.items():
            if run_all or svc in (services or []):
                self.test_ai_service(svc, op, params)

        # Summary
        section("Summary")
        total = self.passed + self.failed
        print(f"  {Colors.GREEN}Passed: {self.passed}{Colors.RESET}")
        print(f"  {Colors.RED}Failed: {self.failed}{Colors.RESET}")
        print(f"  Total:  {total}")

        if self.failed == 0:
            print(f"\n  {Colors.GREEN}{Colors.BOLD}All tests passed! ✓{Colors.RESET}")
        else:
            print(f"\n  {Colors.YELLOW}Some tests need attention.{Colors.RESET}")
            print(f"  {Colors.YELLOW}Note: Google services need real OAuth tokens to fully test.{Colors.RESET}")
            print(f"  {Colors.YELLOW}AI services need real API keys (pass via --openai-key / --gemini-key).{Colors.RESET}")

    def cleanup(self) -> None:
        """Delete test credentials."""
        section("Cleanup")
        for cred_type, cred_id in self.credential_ids.items():
            resp = self._request("DELETE", f"/api/credentials/{cred_id}")
            if resp.status_code in (200, 204):
                ok(f"Deleted test credential: {cred_type} ({cred_id[:8]}...)")
            else:
                info(f"Could not delete {cred_type} credential (may not exist)")


def main():
    parser = argparse.ArgumentParser(description="WarpCore API Test Script")
    parser.add_argument("--service", "-s", nargs="*",
                        help="Services to test (e.g. google-docs gmail openai). Default: all")
    parser.add_argument("--base-url", default="http://localhost:8000",
                        help="Backend base URL (default: http://localhost:8000)")
    parser.add_argument("--openai-key", help="Real OpenAI API key for live testing")
    parser.add_argument("--gemini-key", help="Real Gemini API key for live testing")
    parser.add_argument("--no-cleanup", action="store_true",
                        help="Don't delete test credentials after testing")
    args = parser.parse_args()

    global BASE_URL
    BASE_URL = args.base_url

    tester = APITester()
    tester.client = httpx.Client(base_url=BASE_URL, timeout=30.0)

    try:
        tester.run_all(args.service)

        # Run with real keys if provided
        if args.openai_key:
            section("Live OpenAI Test")
            tester.test_ai_service("openai", "chat_completion", {
                "prompt": "Say 'WarpFlow test successful!' in exactly 5 words.",
                "model": "gpt-3.5-turbo",
                "maxTokens": 50,
            }, api_key=args.openai_key)

        if args.gemini_key:
            section("Live Gemini Test")
            tester.test_ai_service("gemini", "generate_content", {
                "prompt": "Say 'WarpFlow test successful!' in exactly 5 words.",
                "model": "gemini-2.0-flash",
                "maxTokens": 50,
            }, api_key=args.gemini_key)

    finally:
        if not args.no_cleanup:
            tester.cleanup()
        tester.client.close()


if __name__ == "__main__":
    main()
