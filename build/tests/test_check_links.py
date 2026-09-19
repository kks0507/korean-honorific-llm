#!/usr/bin/env python3
"""Unit tests for build/check_links.py — stdlib unittest, no network.

urllib is mocked: `urllib.request.build_opener` returns a fake opener that
answers from a routing table keyed by (url, method).

Run:  python3 -m unittest discover -s build/tests -t build/tests -v
  or: python3 build/tests/test_check_links.py
"""

from __future__ import annotations

import contextlib
import datetime
import io
import json
import shutil
import socket
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import check_links as cl  # noqa: E402

# --------------------------------------------------------------------------
# fake urllib
# --------------------------------------------------------------------------


class FakeResponse:
    def __init__(self, url: str, status: int = 200):
        self.url = url
        self.status = status

    def geturl(self):
        return self.url

    def getcode(self):
        return self.status

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def http_error(url: str, code: int, headers: dict | None = None):
    return urllib.error.HTTPError(url, code, "err", headers or {}, None)


class FakeOpener:
    """routes: {(url, method): FakeResponse | Exception}.  A missing route is
    an AssertionError so a test fails loudly on an unexpected request."""

    def __init__(self, routes: dict, log: list):
        self.routes = routes
        self.log = log

    def open(self, req, timeout=None):
        method = req.get_method()
        self.log.append({"url": req.full_url, "method": method,
                         "timeout": timeout,
                         "ua": req.get_header("User-agent")})
        try:
            outcome = self.routes[(req.full_url, method)]
        except KeyError:
            raise AssertionError(f"unexpected request {method} {req.full_url}")
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


@contextlib.contextmanager
def fake_urllib(routes: dict):
    log: list = []
    with mock.patch.object(cl.urllib.request, "build_opener",
                           side_effect=lambda *h: FakeOpener(routes, log)):
        yield log


A = "https://doi.org/10.1/a"
A_FINAL = "https://publisher.example/article/a"
B = "https://example.org/b"


# --------------------------------------------------------------------------
# check_url
# --------------------------------------------------------------------------


class CheckUrlTests(unittest.TestCase):
    def test_head_ok_follows_redirect(self):
        with fake_urllib({(A, "HEAD"): FakeResponse(A_FINAL, 200)}) as log:
            r = cl.check_url(A)
        self.assertIs(r["verified"], True)
        self.assertEqual(r["method"], "HEAD")
        self.assertEqual(r["status"], 200)
        self.assertEqual(r["final_url"], A_FINAL)
        self.assertIsNone(r["reason"])
        self.assertEqual(len(log), 1)            # no GET when HEAD succeeds

    def test_user_agent_and_timeout(self):
        with fake_urllib({(A, "HEAD"): FakeResponse(A_FINAL)}) as log:
            cl.check_url(A)
        self.assertEqual(log[0]["timeout"], 20.0)
        self.assertEqual(log[0]["ua"], cl.USER_AGENT)
        self.assertNotIn("Python-urllib", log[0]["ua"])

    def test_head_rejected_then_get_ok(self):
        routes = {(A, "HEAD"): http_error(A, 405),
                  (A, "GET"): FakeResponse(A_FINAL, 200)}
        with fake_urllib(routes) as log:
            r = cl.check_url(A)
        self.assertIs(r["verified"], True)
        self.assertEqual(r["method"], "GET")
        self.assertEqual(r["head_status"], 405)
        self.assertEqual([x["method"] for x in log], ["HEAD", "GET"])

    def test_head_network_error_then_get_ok(self):
        routes = {(A, "HEAD"): urllib.error.URLError("reset"),
                  (A, "GET"): FakeResponse(A_FINAL, 200)}
        with fake_urllib(routes):
            r = cl.check_url(A)
        self.assertIs(r["verified"], True)
        self.assertIsNone(r["head_status"])

    def test_bot_block_statuses_are_null(self):
        for code in (403, 429, 401):
            with self.subTest(code=code):
                routes = {(A, "HEAD"): http_error(A_FINAL, code),
                          (A, "GET"): http_error(A_FINAL, code)}
                with fake_urllib(routes):
                    r = cl.check_url(A)
                self.assertIsNone(r["verified"])
                self.assertEqual(r["status"], code)
                self.assertEqual(r["final_url"], A_FINAL)
                self.assertIn("봇 차단", r["reason"])
                self.assertIn(str(code), r["reason"])

    def test_cloudflare_challenge_is_null(self):
        err = http_error(A_FINAL, 503, {"cf-mitigated": "challenge"})
        err2 = http_error(A_FINAL, 503, {"cf-mitigated": "challenge"})
        with fake_urllib({(A, "HEAD"): err, (A, "GET"): err2}):
            r = cl.check_url(A)
        self.assertIsNone(r["verified"])

    def test_head_403_get_200_is_true(self):
        # korean.go.kr's download endpoint answers HEAD with 403, GET with 200
        routes = {(A, "HEAD"): http_error(A, 403),
                  (A, "GET"): FakeResponse(A, 200)}
        with fake_urllib(routes):
            r = cl.check_url(A)
        self.assertIs(r["verified"], True)

    def test_not_found_is_false(self):
        routes = {(A, "HEAD"): http_error(A_FINAL, 404),
                  (A, "GET"): http_error(A_FINAL, 404)}
        with fake_urllib(routes):
            r = cl.check_url(A)
        self.assertIs(r["verified"], False)
        self.assertIn("404", r["reason"])

    def test_server_error_is_false(self):
        routes = {(A, "HEAD"): http_error(A, 500), (A, "GET"): http_error(A, 502)}
        with fake_urllib(routes):
            r = cl.check_url(A)
        self.assertIs(r["verified"], False)
        self.assertEqual(r["status"], 502)

    def test_dns_failure_is_false(self):
        routes = {(A, "HEAD"): urllib.error.URLError("Name or service not known"),
                  (A, "GET"): urllib.error.URLError("Name or service not known")}
        with fake_urllib(routes):
            r = cl.check_url(A)
        self.assertIs(r["verified"], False)
        self.assertIsNone(r["status"])
        self.assertIn("URLError", r["reason"])

    def test_timeout_is_false(self):
        routes = {(A, "HEAD"): socket.timeout("timed out"),
                  (A, "GET"): TimeoutError("timed out")}
        with fake_urllib(routes):
            r = cl.check_url(A)
        self.assertIs(r["verified"], False)
        self.assertIn("timeout", r["reason"])


# --------------------------------------------------------------------------
# note marker
# --------------------------------------------------------------------------


class NoteTests(unittest.TestCase):
    def test_append_to_empty_and_existing(self):
        self.assertEqual(cl.update_note("", "HTTP 403", "2026-09-19"),
                         "〔링크 확인 2026-09-19: HTTP 403〕")
        self.assertEqual(cl.update_note("검정력", "HTTP 403", "2026-09-19"),
                         "검정력 〔링크 확인 2026-09-19: HTTP 403〕")
        self.assertEqual(cl.update_note(None, None, "2026-09-19"), "")

    def test_marker_replaced_not_stacked(self):
        once = cl.update_note("검정력", "HTTP 403", "2026-09-19")
        twice = cl.update_note(once, "HTTP 429", "2026-09-20")
        self.assertEqual(twice, "검정력 〔링크 확인 2026-09-20: HTTP 429〕")
        self.assertEqual(twice.count("〔링크 확인"), 1)

    def test_marker_removed_when_ok(self):
        noted = cl.update_note("검정력", "HTTP 403", "2026-09-19")
        self.assertEqual(cl.update_note(noted, None, "2026-09-20"), "검정력")

    def test_free_text_brackets_untouched(self):
        note = "DOI 제목 일치(Crossref) 〔수동 메모〕"
        self.assertEqual(cl.update_note(note, None, "2026-09-19"), note)


# --------------------------------------------------------------------------
# check_references / apply_results / main
# --------------------------------------------------------------------------


def _refs() -> list[dict]:
    return [
        {"n": 1, "key": "K1", "apa": "a", "doi": "10.1/a", "url": A,
         "verified": None, "checked_on": None, "note": ""},
        {"n": 2, "key": "K2", "apa": "b", "doi": None, "url": None,
         "verified": None, "checked_on": None, "note": "url 찾는 중"},
        {"n": 3, "key": "K3", "apa": "c", "doi": None, "url": B,
         "verified": True, "checked_on": "2026-01-01", "note": "방법론"},
    ]


class CheckReferencesTests(unittest.TestCase):
    ROUTES = {(A, "HEAD"): FakeResponse(A_FINAL),
              (B, "HEAD"): http_error(B, 403), (B, "GET"): http_error(B, 403)}

    def test_skip_empty_url_and_sleep_between_requests(self):
        sleep = mock.Mock()
        with fake_urllib(self.ROUTES) as log:
            res = cl.check_references(_refs(), today="2026-09-19", sleep=sleep)
        self.assertEqual([r["key"] for r in res], ["K1", "K2", "K3"])
        self.assertTrue(res[1]["skipped"])
        self.assertNotIn(None, [x["url"] for x in log])
        # 2 urls requested -> exactly one pause, of 1 second
        sleep.assert_called_once_with(1.0)
        self.assertEqual(res[0]["checked_on"], "2026-09-19")

    def test_key_filter(self):
        with fake_urllib(self.ROUTES) as log:
            res = cl.check_references(_refs(), {"K3"}, today="2026-09-19",
                                      sleep=lambda s: None)
        self.assertEqual([r["key"] for r in res], ["K3"])
        self.assertEqual({x["url"] for x in log}, {B})

    def test_apply_results(self):
        refs = _refs()
        with fake_urllib(self.ROUTES):
            res = cl.check_references(refs, today="2026-09-19",
                                      sleep=lambda s: None)
        changed = cl.apply_results(refs, res)
        self.assertEqual(changed, 2)
        k1, k2, k3 = refs
        self.assertIs(k1["verified"], True)
        self.assertEqual(k1["checked_on"], "2026-09-19")
        self.assertEqual(k1["note"], "")
        # skipped entry untouched
        self.assertEqual(k2, _refs()[1])
        # bot block: verified null + reason appended to the existing note
        self.assertIsNone(k3["verified"])
        self.assertEqual(k3["checked_on"], "2026-09-19")
        self.assertTrue(k3["note"].startswith("방법론 〔링크 확인 2026-09-19: HTTP 403"))
        # fields other than verified/checked_on/note are never touched
        for before, after in zip(_refs(), refs):
            for field in ("n", "key", "apa", "doi", "url"):
                self.assertEqual(before[field], after[field])

    def test_summary(self):
        with fake_urllib(self.ROUTES):
            res = cl.check_references(_refs(), today="2026-09-19",
                                      sleep=lambda s: None)
        self.assertEqual(cl.summarize(res), {
            "total": 3, "checked": 2, "verified_true": 1, "verified_null": 1,
            "verified_false": 0, "skipped_no_url": 1})


class MainTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.file = self.tmp / "references.json"
        self.data = {"meta": {"task": "test"}, "references": _refs()}
        # the real file has no trailing newline; keep whatever it had
        self.file.write_text(json.dumps(self.data, ensure_ascii=False, indent=2),
                             encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_main(self, *args, routes=None):
        out = io.StringIO()
        with fake_urllib(routes or CheckReferencesTests.ROUTES), \
                contextlib.redirect_stdout(out):
            code = cl.main([*args, "--file", str(self.file), "--delay", "0"])
        return code, out.getvalue()

    def test_dry_run_does_not_write(self):
        before = self.file.read_text(encoding="utf-8")
        code, out = self.run_main()
        self.assertEqual(code, 0)
        self.assertIn("1 true, 1 null, 0 false", out)
        self.assertEqual(self.file.read_text(encoding="utf-8"), before)

    def test_json_output(self):
        code, out = self.run_main("--json")
        payload = json.loads(out)
        self.assertEqual(payload["summary"]["checked"], 2)
        by_key = {r["key"]: r for r in payload["results"]}
        self.assertEqual(by_key["K1"]["final_url"], A_FINAL)
        self.assertIsNone(by_key["K3"]["verified"])

    def test_write(self):
        code, _ = self.run_main("--write", "--json")
        self.assertEqual(code, 0)
        text = self.file.read_text(encoding="utf-8")
        self.assertFalse(text.endswith("\n"))
        saved = json.loads(text)
        today = datetime.date.today().isoformat()
        k1, k2, k3 = saved["references"]
        self.assertIs(k1["verified"], True)
        self.assertEqual(k1["checked_on"], today)
        self.assertIsNone(k2["checked_on"])
        self.assertIsNone(k3["verified"])
        self.assertIn(f"〔링크 확인 {today}: HTTP 403", k3["note"])
        self.assertEqual(saved["meta"], self.data["meta"])
        # a second run replaces the marker instead of stacking it
        self.run_main("--write")
        again = json.loads(self.file.read_text(encoding="utf-8"))
        self.assertEqual(again["references"][2]["note"].count("〔링크 확인"), 1)

    def test_broken_link_exit_1(self):
        routes = {(A, "HEAD"): http_error(A, 404), (A, "GET"): http_error(A, 404),
                  (B, "HEAD"): FakeResponse(B)}
        code, out = self.run_main(routes=routes)
        self.assertEqual(code, 1)
        self.assertIn("FAIL", out)

    def test_unknown_key_exit_2(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code, _ = self.run_main("NOPE")
        self.assertEqual(code, 2)
        self.assertIn("NOPE", err.getvalue())


if __name__ == "__main__":
    unittest.main()
