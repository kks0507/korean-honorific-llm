#!/usr/bin/env python3
"""papers/pdf/P??_*.pdf -> papers/txt/P??.txt (+ .layout.txt) + manifest.json

Reading-order extraction (plain `pdftotext`, WITHOUT -layout) because several
papers are two-column and -layout interleaves the columns.  A `-layout` variant
is written alongside for tables.

Usage:  python3 build/extract_text.py [--root DIR]
Exits non-zero if any PDF yields 0 words or marker count != page count.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

PDFINFO = "/usr/local/bin/pdfinfo"
PDFTOTEXT = "/usr/local/bin/pdftotext"

PDF_GLOB = "P??_*.pdf"
MARKER_RE = re.compile(r"^===== \[(P\d{2}) p\.(\d+)/(\d+)\] =====$")

# "ARTICLE IN PRESS" style diagonal watermarks leak stray 1-2 letter uppercase
# fragments onto their own lines (S, ES, PR, IN, LE, C, TI, R, A ...).
STRAY_RE = re.compile(r"^[A-Z]{1,2}$")

# ...but a bare 1-2 uppercase line is *also* how real table labels come out
# (P03's H / NH honorific condition codes, SD, SE, M, B ...).  A watermark is
# stamped on every page, so only drop a stray token that recurs on at least
# this fraction of the document's pages.  Measured separation is wide: P04's
# nine watermark letters sit at 59/59 pages, every other paper's stray tokens
# at <= 3/12.
WATERMARK_PAGE_RATIO = 0.5

BLANK_WORD_THRESHOLD = 5

# Papers whose two-column body comes out line-interleaved in plain mode.
# `-raw` (content-stream order) restores the reading order for these.
RAW_IDS = {"P07"}


def marker(pid: str, page: int, total: int) -> str:
    return f"===== [{pid} p.{page}/{total}] ====="


def run(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"{' '.join(cmd)} failed (rc={proc.returncode}): "
            f"{proc.stderr.decode('utf-8', 'replace').strip()}"
        )
    return proc.stdout.decode("utf-8", "replace")


def page_count(pdf: Path) -> int:
    out = run([PDFINFO, str(pdf)])
    for line in out.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":", 1)[1].strip())
    raise RuntimeError(f"no page count in pdfinfo output for {pdf}")


def stray_tokens(text: str) -> set[str]:
    return {s for ln in text.splitlines() if STRAY_RE.match(s := ln.strip())}


def watermark_tokens(raw_pages: list[str]) -> set[str]:
    """Stray 1-2 uppercase tokens that recur on most pages -> watermark debris."""
    if not raw_pages:
        return set()
    counts: dict[str, int] = {}
    for page in raw_pages:
        for tok in stray_tokens(page):
            counts[tok] = counts.get(tok, 0) + 1
    cutoff = len(raw_pages) * WATERMARK_PAGE_RATIO
    return {tok for tok, n in counts.items() if n >= cutoff}


def clean(text: str, drop: set[str]) -> str:
    """Drop watermark debris; keep everything else verbatim."""
    return "\n".join(ln for ln in text.splitlines() if ln.strip() not in drop)


def extract_page(pdf: Path, page: int, layout: bool) -> str:
    cmd = [PDFTOTEXT, "-f", str(page), "-l", str(page)]
    if layout:
        cmd.append("-layout")
    elif pdf.name[:3] in RAW_IDS:
        cmd.append("-raw")
    cmd += [str(pdf), "-"]
    return run(cmd)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_document(
    pdf: Path, pid: str, pages: int, layout: bool
) -> tuple[str, list[int], set[str]]:
    raw = [extract_page(pdf, page, layout) for page in range(1, pages + 1)]
    drop = watermark_tokens(raw)
    parts: list[str] = []
    per_page: list[int] = []
    for page, text in enumerate(raw, start=1):
        body = clean(text, drop)
        per_page.append(len(body.split()))
        parts.append(marker(pid, page, pages) + "\n" + body.rstrip("\n") + "\n")
    return "\n".join(parts), per_page, drop


def process(pdf: Path, txt_dir: Path) -> dict:
    pid = pdf.name[:3]
    pages = page_count(pdf)

    plain, per_page, drop = build_document(pdf, pid, pages, layout=False)
    layout_doc, _, _ = build_document(pdf, pid, pages, layout=True)

    plain_path = txt_dir / f"{pid}.txt"
    layout_path = txt_dir / f"{pid}.layout.txt"
    plain_path.write_text(plain, encoding="utf-8")
    layout_path.write_text(layout_doc, encoding="utf-8")

    markers = sum(1 for ln in plain.splitlines() if MARKER_RE.match(ln))
    words = sum(per_page)
    blanks = [i + 1 for i, w in enumerate(per_page) if w < BLANK_WORD_THRESHOLD]

    return {
        "id": pid,
        "pdf": pdf.name,
        "pages": pages,
        "words": words,
        "words_per_page": per_page,
        "sha256": sha256_of(pdf),
        "blank_pages": blanks,
        "watermark_dropped": sorted(drop),
        "_markers": markers,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    pdf_dir = root / "papers" / "pdf"
    txt_dir = root / "papers" / "txt"
    txt_dir.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(pdf_dir.glob(PDF_GLOB))
    if not pdfs:
        print(f"ERROR: no {PDF_GLOB} under {pdf_dir}", file=sys.stderr)
        return 1

    records: list[dict] = []
    problems: list[str] = []

    for pdf in pdfs:
        rec = process(pdf, txt_dir)
        if rec["words"] == 0:
            problems.append(f"{rec['id']}: extraction produced 0 words")
        if rec["_markers"] != rec["pages"]:
            problems.append(
                f"{rec['id']}: {rec['_markers']} markers != {rec['pages']} pages"
            )
        records.append(rec)

    manifest = [{k: v for k, v in r.items() if not k.startswith("_")} for r in records]
    (txt_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"{'ID':<5} {'PAGES':>5} {'WORDS':>8} {'W/PG':>6}  BLANK PAGES")
    print("-" * 56)
    for r in records:
        avg = r["words"] // r["pages"] if r["pages"] else 0
        blanks = ", ".join(str(p) for p in r["blank_pages"]) or "-"
        print(f"{r['id']:<5} {r['pages']:>5} {r['words']:>8} {avg:>6}  {blanks}")
    print("-" * 56)
    print(
        f"{len(records)} PDFs, {sum(r['pages'] for r in records)} pages, "
        f"{sum(r['words'] for r in records)} words -> {txt_dir}"
    )

    if problems:
        print("\nFAILED:", file=sys.stderr)
        for p in problems:
            print("  " + p, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
