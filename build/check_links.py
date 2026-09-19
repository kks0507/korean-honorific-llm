#!/usr/bin/env python3
"""Check that every `url` in content/references.json still resolves.

For each reference with a non-empty `url` the script sends a HEAD request
(falling back to GET when HEAD fails), follows redirects, and records the
final URL and HTTP status.  Standard library only (urllib).

Verdicts
    verified = true    final response is 2xx
    verified = null    bot blocking suspected (HTTP 401/403/429, or a
                       Cloudflare challenge); a reason is appended to `note`
    verified = false   any other 4xx/5xx, or a network error / timeout
    (skipped)          `url` is empty; the entry is left untouched

With --write, `verified` and `checked_on` (today, YYYY-MM-DD) are written back
to the file.  The reason for a null/false verdict is appended to `note` as one
marker segment `〔링크 확인 YYYY-MM-DD: …〕`; an older marker is replaced, so
repeated runs do not pile up text, and a true verdict removes it.

Usage:
    python3 build/check_links.py                 # check all, print a table
    python3 build/check_links.py P01 NIKL2011    # only these keys
    python3 build/check_links.py --json          # machine-readable result
    python3 build/check_links.py --write         # record verified/checked_on

Exit status: 0 when nothing is `false`, 1 when some link is broken, 2 on bad
arguments.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import http.cookiejar
import json
import re
import socket
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FILE = ROOT / "content" / "references.json"

USER_AGENT = (
    "Mozilla/5.0 (compatible; korean-honorific-llm-check_links/1.0; "
    "reference link checker)"
)
ACCEPT = "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8"
TIMEOUT = 20.0          # seconds per request
DELAY = 1.0             # seconds between requests
BOT_BLOCK_STATUSES = {401, 403, 429}

MARKER_RE = re.compile(r"\s*(?:/\s*)?〔링크 확인 [^〕]*〕")


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------

def _opener() -> urllib.request.OpenerDirector:
    # A cookie jar per URL: publishers such as Elsevier and Wiley bounce
    # through cookie-setting redirects and loop without one.
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def _request(opener, url: str, method: str, timeout: float) -> dict:
    """One request (redirects followed).  Never raises."""
    req = urllib.request.Request(url, method=method, headers={
        "User-Agent": USER_AGENT,
        "Accept": ACCEPT,
        "Accept-Language": "ko,en;q=0.8",
    })
    try:
        resp = opener.open(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        headers = e.headers or {}
        out = {"method": method, "status": e.code, "final_url": e.geturl() or url,
               "error": f"HTTP {e.code} {e.reason}".strip(),
               "cf_challenge": bool(headers.get("cf-mitigated"))}
        e.close()
        return out
    except urllib.error.URLError as e:
        return {"method": method, "status": None, "final_url": url,
                "error": f"URLError: {e.reason}", "cf_challenge": False}
    except (TimeoutError, socket.timeout) as e:
        return {"method": method, "status": None, "final_url": url,
                "error": f"timeout: {e}", "cf_challenge": False}
    except (OSError, ValueError) as e:     # connection reset, bad URL, ...
        return {"method": method, "status": None, "final_url": url,
                "error": f"{type(e).__name__}: {e}", "cf_challenge": False}
    with resp:
        status = getattr(resp, "status", None) or resp.getcode()
        return {"method": method, "status": status,
                "final_url": resp.geturl() or url, "error": None,
                "cf_challenge": False}


def _ok(status) -> bool:
    return status is not None and 200 <= status < 300


def check_url(url: str, timeout: float = TIMEOUT) -> dict:
    """HEAD, then GET if HEAD did not succeed.  Returns the deciding attempt
    plus a verdict: True / None (bot block suspected) / False."""
    opener = _opener()
    attempt = _request(opener, url, "HEAD", timeout)
    head_status = attempt["status"]
    if not _ok(head_status):
        attempt = _request(opener, url, "GET", timeout)
    status = attempt["status"]
    if _ok(status):
        verdict, reason = True, None
    elif status in BOT_BLOCK_STATUSES or attempt["cf_challenge"]:
        verdict = None
        reason = f"HTTP {status} 봇 차단 추정 — 브라우저로 직접 확인 필요"
    else:
        verdict = False
        reason = attempt["error"] or f"HTTP {status}"
    return {"head_status": head_status, **attempt,
            "verified": verdict, "reason": reason}


# --------------------------------------------------------------------------
# references.json
# --------------------------------------------------------------------------

def update_note(note: str | None, reason: str | None, today: str) -> str:
    """Drop any earlier check_links marker and, if `reason`, append a new one."""
    base = MARKER_RE.sub("", note or "").strip()
    if not reason:
        return base
    marker = f"〔링크 확인 {today}: {reason}〕"
    return f"{base} {marker}" if base else marker


def check_references(refs: list[dict], keys: set[str] | None = None, *,
                     timeout: float = TIMEOUT, delay: float = DELAY,
                     today: str | None = None, sleep=time.sleep) -> list[dict]:
    today = today or _dt.date.today().isoformat()
    results = []
    first = True
    for ref in refs:
        if keys and ref.get("key") not in keys:
            continue
        url = (ref.get("url") or "").strip()
        row = {"n": ref.get("n"), "key": ref.get("key"), "url": url or None}
        if not url:
            row.update(skipped=True, verified=None, reason="url 없음")
            results.append(row)
            continue
        if not first and delay > 0:
            sleep(delay)
        first = False
        row.update(skipped=False, **check_url(url, timeout))
        row["checked_on"] = today
        results.append(row)
    return results


def apply_results(refs: list[dict], results: list[dict]) -> int:
    """Write verdicts into the reference dicts in place.  Returns #changed."""
    by_key = {r["key"]: r for r in results if not r.get("skipped")}
    changed = 0
    for ref in refs:
        res = by_key.get(ref.get("key"))
        if res is None:
            continue
        before = (ref.get("verified"), ref.get("checked_on"), ref.get("note"))
        ref["verified"] = res["verified"]
        ref["checked_on"] = res["checked_on"]
        reason = None if res["verified"] is True else res["reason"]
        ref["note"] = update_note(ref.get("note"), reason, res["checked_on"])
        if before != (ref["verified"], ref["checked_on"], ref["note"]):
            changed += 1
    return changed


def load(path: Path) -> tuple[dict, bool]:
    text = path.read_text(encoding="utf-8")
    return json.loads(text), text.endswith("\n")


def save(path: Path, data: dict, trailing_newline: bool) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2)
    path.write_text(text + ("\n" if trailing_newline else ""), encoding="utf-8")


def summarize(results: list[dict]) -> dict:
    checked = [r for r in results if not r.get("skipped")]
    return {
        "total": len(results),
        "checked": len(checked),
        "verified_true": sum(r["verified"] is True for r in checked),
        "verified_null": sum(r["verified"] is None for r in checked),
        "verified_false": sum(r["verified"] is False for r in checked),
        "skipped_no_url": len(results) - len(checked),
    }


def print_human(results: list[dict], summary: dict) -> None:
    mark = {True: "OK  ", None: "??  ", False: "FAIL"}
    for r in results:
        if r.get("skipped"):
            print(f"[{r['n']:>2}] SKIP {r['key']}: url 없음")
            continue
        line = (f"[{r['n']:>2}] {mark[r['verified']]} {r['key']}: "
                f"{r['method']} {r['status']}  {r['final_url']}")
        if r["verified"] is not True:
            line += f"  ({r['reason']})"
        print(line)
    print(f"-- {summary['checked']} checked: {summary['verified_true']} true, "
          f"{summary['verified_null']} null, {summary['verified_false']} false; "
          f"{summary['skipped_no_url']} without url")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("keys", nargs="*", help="reference keys (default: all)")
    ap.add_argument("--file", default=str(DEFAULT_FILE),
                    help="references.json path")
    ap.add_argument("--write", action="store_true",
                    help="write verified/checked_on (and note markers) back")
    ap.add_argument("--json", action="store_true", dest="as_json",
                    help="print the result as JSON")
    ap.add_argument("--timeout", type=float, default=TIMEOUT)
    ap.add_argument("--delay", type=float, default=DELAY)
    args = ap.parse_args(argv)

    path = Path(args.file)
    data, trailing_newline = load(path)
    refs = data.get("references", [])
    known = {r.get("key") for r in refs}
    unknown = [k for k in args.keys if k not in known]
    if unknown:
        print(f"ERROR: unknown key(s): {', '.join(unknown)}", file=sys.stderr)
        return 2

    results = check_references(refs, set(args.keys) or None,
                               timeout=args.timeout, delay=args.delay)
    summary = summarize(results)

    if args.write:
        changed = apply_results(refs, results)
        save(path, data, trailing_newline)
        summary["written"] = changed

    if args.as_json:
        print(json.dumps({"summary": summary, "results": results},
                         ensure_ascii=False, indent=2))
    else:
        print_human(results, summary)
        if args.write:
            print(f"-- wrote {path} ({summary['written']} entries changed)")

    return 1 if summary["verified_false"] else 0


if __name__ == "__main__":
    sys.exit(main())
