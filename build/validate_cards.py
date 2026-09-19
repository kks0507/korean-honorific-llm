#!/usr/bin/env python3
"""Validate 논문 카드 files `content/papers/P??.json` against docs/02_논문카드-스키마.md.

ERRORs are schema/integrity violations (exit 1).  WARNINGs are evidence checks:
quotes and numbers are looked up in the extracted page text (`papers/txt/P??.txt`,
plus the `.layout.txt` variant for numbers) on the cited page ±1.

Usage:
    python3 build/validate_cards.py [P02 P05 ...]   # no args = every card present
    python3 build/validate_cards.py --json          # machine-readable dump
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

# --------------------------------------------------------------------------
# schema constants (docs/02_논문카드-스키마.md is the source of truth)
# --------------------------------------------------------------------------

REQUIRED_TOP = [
    "id", "role", "short", "title", "title_ko", "citation", "one_line",
    "w5h1", "layers", "design", "stimulus_examples", "key_numbers",
    "limitations", "successor_hooks", "open_materials",
    "prior_analysis_check", "verification",
]

ROLES = {"core", "adjacent", "subdata"}
W5H1_KEYS = ["who", "when", "where", "what", "how", "why"]
LAYER_KEYS = ["word", "sentence", "paragraph", "context"]

ENUMS = {
    "citation.status": {"published", "in_press", "preprint", "proceedings"},
    "sentence.kind": {"claim", "hypothesis", "result", "method", "limitation",
                      "future_work"},
    "paragraph.move": {"background", "gap", "claim", "method", "evidence",
                       "interpretation", "limitation", "future_work"},
    "context.axis": {"lineage", "theory", "model_generation", "agreement",
                     "conflict", "field"},
    "successor_hooks.kind": {"author_future_work", "unresolved_confound",
                             "untested_condition", "method_gap",
                             "model_generation"},
    "limitations.stated_by": {"author", "us"},
    "verification.status": {"draft", "verified", "corrected"},
}

# layer minimums: role -> {layer: minimum}
LAYER_MIN = {
    "core":     {"word": 8, "sentence": 12, "paragraph": 8, "context": 5},
    "adjacent": {"word": 8, "sentence": 12, "paragraph": 8, "context": 5},
    "subdata":  {"word": 4, "sentence": 6,  "paragraph": 4, "context": 3},
}
HOOK_MIN = {"core": 3, "adjacent": 2, "subdata": 2}

# arrays whose every entry must carry a page anchor
SRC_ARRAYS = ["stimulus_examples", "key_numbers", "limitations", "successor_hooks"]

SRC_RE = re.compile(r"^p\.(\d+)(-(\d+))?( .*)?$")
HOOK_ID_RE = re.compile(r"^P\d{2}-H\d+$")
CARD_ID_RE = re.compile(r"^P\d{2}$")
QUOTE_MAX_TOKENS = 15
RECALC_MARK = "(재계산)"

NUM_RE = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")

# --------------------------------------------------------------------------
# text normalisation / evidence lookup
# --------------------------------------------------------------------------

_QUOTE_MAP = str.maketrans({
    "‘": "'", "’": "'", "‚": "'", "‛": "'",
    "“": '"', "”": '"', "„": '"', "‟": '"',
    "‐": "-", "‑": "-", "‒": "-", "–": "-",
    "—": "-", "―": "-", "−": "-",
    " ": " ", " ": " ", " ": " ", " ": " ", "​": "",
})


def _strip_punctuation(text: str) -> str:
    """Blank out punctuation, but keep `.`/`,` sitting *between digits*.

    Without the exception `88.2` would normalise to `88 2` and `1,500` to
    `1 500`, and every number lookup against the page text would miss.
    """
    out: list[str] = []
    last = len(text) - 1
    for i, ch in enumerate(text):
        if ch.isalnum() or ch.isspace() or ch == "_":
            out.append(ch)
        elif (ch in ".," and 0 < i < last
                and text[i - 1].isdigit() and text[i + 1].isdigit()):
            out.append(ch)
        else:
            out.append(" ")
    return "".join(out)


def normalise(text: str) -> str:
    """Lowercase, de-hyphenate line breaks, drop punctuation, collapse space."""
    text = text.replace("­", "")               # soft hyphen
    text = re.sub(r"-\s*\n\s*", "", text)           # line-break hyphenation
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_QUOTE_MAP)
    text = text.lower()
    text = _strip_punctuation(text)                 # punctuation differences
    return re.sub(r"\s+", " ", text).strip()


def contains(haystack: str, needle: str) -> bool:
    """Substring test that also tolerates Korean word-spacing differences."""
    if not needle:
        return True
    if needle in haystack:
        return True
    return needle.replace(" ", "") in haystack.replace(" ", "")


MARKER_RE = re.compile(r"^===== \[(P\d{2}) p\.(\d+)/(\d+)\] =====$")


def split_pages(text: str) -> dict[int, str]:
    """Split an extracted P??.txt into {page_number: body}."""
    pages: dict[int, str] = {}
    current: int | None = None
    buf: list[str] = []
    for line in text.splitlines():
        m = MARKER_RE.match(line)
        if m:
            if current is not None:
                pages[current] = "\n".join(buf)
            current = int(m.group(2))
            buf = []
        elif current is not None:
            buf.append(line)
    if current is not None:
        pages[current] = "\n".join(buf)
    return pages


class TextIndex:
    """Lazily loads and normalises papers/txt/P??.txt and P??.layout.txt."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self._cache: dict[tuple[str, bool], dict[int, str]] = {}

    def _pages(self, pid: str, layout: bool) -> dict[int, str]:
        key = (pid, layout)
        if key not in self._cache:
            suffix = ".layout.txt" if layout else ".txt"
            path = self.root / "papers" / "txt" / f"{pid}{suffix}"
            if path.exists():
                raw = split_pages(path.read_text(encoding="utf-8"))
                self._cache[key] = {n: normalise(t) for n, t in raw.items()}
            else:
                self._cache[key] = {}
        return self._cache[key]

    def window(self, pid: str, pages: list[int], layout: bool = False) -> str:
        """Normalised text of the cited pages widened by ±1."""
        want: set[int] = set()
        for p in pages:
            want.update({p - 1, p, p + 1})
        avail = self._pages(pid, layout)
        return " ".join(avail[p] for p in sorted(want) if p in avail)

    def available(self, pid: str) -> bool:
        return bool(self._pages(pid, False))


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def src_pages(src: str) -> list[int] | None:
    """['p.3-5'] -> [3, 4, 5]; None when the anchor is malformed."""
    m = SRC_RE.match(src)
    if not m:
        return None
    start = int(m.group(1))
    end = int(m.group(3)) if m.group(3) else start
    if end < start:
        return [start, end]
    return list(range(start, end + 1))


def numeric_tokens(value: str) -> list[str]:
    return NUM_RE.findall(value)


def number_present(haystack: str, token: str) -> bool:
    pat = re.compile(rf"(?<![\d.]){re.escape(token)}(?![\d.]?\d)")
    if pat.search(haystack):
        return True
    bare = token.replace(",", "")
    if bare != token:
        stripped = re.sub(r"(?<=\d),(?=\d{3})", "", haystack)
        if re.search(rf"(?<![\d.]){re.escape(bare)}(?![\d.]?\d)", stripped):
            return True
    return False


def walk_quotes(node, path: str = "") -> list[tuple[str, str]]:
    """Every value stored under a key literally named 'quote', with its path."""
    found: list[tuple[str, str]] = []
    if isinstance(node, dict):
        for k, v in node.items():
            sub = f"{path}.{k}" if path else k
            if k == "quote" and isinstance(v, str):
                found.append((sub, v))
            else:
                found.extend(walk_quotes(v, sub))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            found.extend(walk_quotes(v, f"{path}[{i}]"))
    return found


class Report:
    def __init__(self, card_id: str, path: str):
        self.id = card_id
        self.path = path
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "path": self.path,
            "errors": self.errors,
            "warnings": self.warnings,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
        }


# --------------------------------------------------------------------------
# checks
# --------------------------------------------------------------------------

def check_src(rep: Report, where: str, entry, pages_total: int | None) -> list[int]:
    """Validate an entry's `src`; return the cited page numbers (possibly [])."""
    if not isinstance(entry, dict):
        rep.error(f"{where}: entry is not an object")
        return []
    src = entry.get("src")
    if not isinstance(src, str) or not src.strip():
        rep.error(f"{where}: missing `src`")
        return []
    pages = src_pages(src)
    if pages is None:
        rep.error(f"{where}: `src` {src!r} does not match ^p\\.(\\d+)(-(\\d+))?( .*)?$")
        return []
    if pages_total is not None:
        bad = [p for p in pages if p < 1 or p > pages_total]
        if bad:
            rep.error(
                f"{where}: `src` {src!r} cites page(s) {bad} outside 1..{pages_total}"
            )
            return []
    return pages


def check_enum(rep: Report, where: str, entry: dict, field: str, enum_key: str) -> None:
    allowed = ENUMS[enum_key]
    value = entry.get(field)
    if value not in allowed:
        rep.error(
            f"{where}: `{field}` {value!r} not in "
            f"{{{', '.join(sorted(allowed))}}}"
        )


def validate_card(path: Path, root: Path, manifest: dict, index: TextIndex) -> Report:
    card_id = path.stem
    rep = Report(card_id, str(path))

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        rep.error(f"invalid JSON: {exc}")
        return rep
    except OSError as exc:
        rep.error(f"unreadable: {exc}")
        return rep

    if not isinstance(data, dict):
        rep.error("top level is not a JSON object")
        return rep

    # --- top-level keys -------------------------------------------------
    for key in REQUIRED_TOP:
        if key not in data:
            rep.error(f"missing required top-level key `{key}`")

    if data.get("id") != card_id:
        rep.error(f"`id` {data.get('id')!r} does not match filename {path.name}")

    role = data.get("role")
    if role not in ROLES:
        rep.error(f"`role` {role!r} not in {{{', '.join(sorted(ROLES))}}}")

    entry = manifest.get(card_id)
    pages_total = entry["pages"] if entry else None
    if entry is None:
        rep.warn(f"{card_id} absent from papers/txt/manifest.json — page range unchecked")

    citation = data.get("citation")
    if isinstance(citation, dict):
        check_enum(rep, "citation", citation, "status", "citation.status")
    elif "citation" in data:
        rep.error("`citation` is not an object")

    verification = data.get("verification")
    if isinstance(verification, dict):
        check_enum(rep, "verification", verification, "status", "verification.status")
    elif "verification" in data:
        rep.error("`verification` is not an object")

    # --- w5h1 -----------------------------------------------------------
    w5h1 = data.get("w5h1")
    if not isinstance(w5h1, dict):
        if "w5h1" in data:
            rep.error("`w5h1` is not an object")
    else:
        for key in W5H1_KEYS:
            if key not in w5h1:
                rep.error(f"w5h1: missing `{key}`")
                continue
            block = w5h1[key]
            if not isinstance(block, dict):
                rep.error(f"w5h1.{key}: not an object")
                continue
            headline = block.get("headline")
            if not isinstance(headline, str) or not headline.strip():
                rep.error(f"w5h1.{key}: missing or empty `headline`")
            items = block.get("items")
            if not isinstance(items, list) or not items:
                rep.error(f"w5h1.{key}: `items` missing or empty")
                continue
            for i, item in enumerate(items):
                check_src(rep, f"w5h1.{key}.items[{i}]", item, pages_total)

    # --- layers ---------------------------------------------------------
    layers = data.get("layers")
    minimums = LAYER_MIN.get(role if role in LAYER_MIN else "core")
    sentence_entries: list[tuple[int, dict, list[int]]] = []
    if not isinstance(layers, dict):
        if "layers" in data:
            rep.error("`layers` is not an object")
    else:
        for layer in LAYER_KEYS:
            seq = layers.get(layer)
            if not isinstance(seq, list):
                rep.error(f"layers.{layer}: missing or not an array")
                continue
            need = minimums[layer]
            if len(seq) < need:
                rep.error(
                    f"layers.{layer}: {len(seq)} entries, role {role!r} needs >= {need}"
                )
            for i, item in enumerate(seq):
                where = f"layers.{layer}[{i}]"
                pages = check_src(rep, where, item, pages_total)
                if not isinstance(item, dict):
                    continue
                if layer == "sentence":
                    check_enum(rep, where, item, "kind", "sentence.kind")
                    sentence_entries.append((i, item, pages))
                elif layer == "paragraph":
                    check_enum(rep, where, item, "move", "paragraph.move")
                elif layer == "context":
                    check_enum(rep, where, item, "axis", "context.axis")

    # --- src-bearing arrays ---------------------------------------------
    for name in SRC_ARRAYS:
        seq = data.get(name)
        if seq is None:
            continue
        if not isinstance(seq, list):
            rep.error(f"`{name}` is not an array")
            continue
        for i, item in enumerate(seq):
            where = f"{name}[{i}]"
            pages = check_src(rep, where, item, pages_total)
            if not isinstance(item, dict):
                continue
            if name == "limitations":
                check_enum(rep, where, item, "stated_by", "limitations.stated_by")
            elif name == "successor_hooks":
                check_enum(rep, where, item, "kind", "successor_hooks.kind")
                hid = item.get("id")
                if not isinstance(hid, str) or not HOOK_ID_RE.match(hid):
                    rep.error(f"{where}: `id` {hid!r} is not of the form `P02-H1`")
                elif not hid.startswith(f"{card_id}-H"):
                    rep.error(f"{where}: `id` {hid!r} does not belong to {card_id}")

    hooks = data.get("successor_hooks")
    if isinstance(hooks, list):
        need = HOOK_MIN.get(role, 2)
        if len(hooks) < need:
            rep.error(
                f"successor_hooks: {len(hooks)} entries, role {role!r} needs >= {need}"
            )

    # --- quote length (anywhere in the document) ------------------------
    for where, quote in walk_quotes(data):
        n = len(quote.split())
        if n > QUOTE_MAX_TOKENS:
            rep.error(
                f"{where}: quote is {n} tokens, limit is {QUOTE_MAX_TOKENS} "
                f"({quote[:60]!r}...)"
            )

    # --- WARNING: anchor checks -----------------------------------------
    if not index.available(card_id):
        rep.warn(f"papers/txt/{card_id}.txt not found — anchor checks skipped")
        return rep

    for i, item, pages in sentence_entries:
        quote = item.get("quote")
        if not isinstance(quote, str) or not quote.strip() or not pages:
            continue
        needle = normalise(quote)
        hay = index.window(card_id, pages, layout=False)
        if not contains(hay, needle):
            hay2 = index.window(card_id, pages, layout=True)
            if not contains(hay2, needle):
                rep.warn(
                    f"layers.sentence[{i}]: quote not found on {item.get('src')} ±1 "
                    f"({quote[:50]!r})"
                )

    def check_numbers(where: str, value, pages: list[int]) -> None:
        if not isinstance(value, str) or not pages:
            return
        if RECALC_MARK in value:
            return
        tokens = numeric_tokens(value)
        if not tokens:
            return
        hay = index.window(card_id, pages, layout=False)
        hay_layout = None
        for tok in tokens:
            if number_present(hay, tok):
                continue
            if hay_layout is None:
                hay_layout = index.window(card_id, pages, layout=True)
            if number_present(hay_layout, tok):
                continue
            rep.warn(f"{where}: number {tok!r} (from {value!r}) not found on "
                     f"cited page(s) ±1")

    for i, item, pages in sentence_entries:
        numbers = item.get("numbers")
        if isinstance(numbers, list):
            for j, num in enumerate(numbers):
                check_numbers(f"layers.sentence[{i}].numbers[{j}]", num, pages)

    key_numbers = data.get("key_numbers")
    if isinstance(key_numbers, list):
        for i, item in enumerate(key_numbers):
            if not isinstance(item, dict):
                continue
            pages = src_pages(item.get("src", "")) or []
            if pages_total is not None:
                pages = [p for p in pages if 1 <= p <= pages_total]
            check_numbers(f"key_numbers[{i}].value", item.get("value"), pages)

    return rep


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------

def load_manifest(root: Path) -> dict:
    path = Path(root) / "papers" / "txt" / "manifest.json"
    if not path.exists():
        return {}
    try:
        return {r["id"]: r for r in json.loads(path.read_text(encoding="utf-8"))}
    except (json.JSONDecodeError, KeyError, TypeError):
        return {}


def card_paths(root: Path, ids: list[str] | None) -> tuple[list[Path], list[str]]:
    cards_dir = Path(root) / "content" / "papers"
    missing: list[str] = []
    if ids:
        paths = []
        for cid in ids:
            p = cards_dir / f"{cid}.json"
            if p.exists():
                paths.append(p)
            else:
                missing.append(cid)
        return paths, missing
    return sorted(cards_dir.glob("P??.json")), missing


def validate(root: Path, ids: list[str] | None = None) -> dict:
    root = Path(root)
    manifest = load_manifest(root)
    index = TextIndex(root)
    paths, missing = card_paths(root, ids)

    reports = [validate_card(p, root, manifest, index) for p in paths]
    files = [r.as_dict() for r in reports]
    errors = sum(f["error_count"] for f in files)
    warnings = sum(f["warning_count"] for f in files)

    return {
        "root": str(root),
        "files": files,
        "missing": missing,
        "totals": {
            "files": len(files),
            "errors": errors + len(missing),
            "warnings": warnings,
        },
        "ok": errors == 0 and not missing,
    }


def print_human(result: dict) -> None:
    for cid in result["missing"]:
        print(f"ERROR  {cid}: content/papers/{cid}.json not found")

    if not result["files"]:
        print("no card files found under content/papers/")

    for f in result["files"]:
        status = "OK  " if f["error_count"] == 0 else "FAIL"
        print(f"{status} {f['id']}  errors={f['error_count']} "
              f"warnings={f['warning_count']}")
        for msg in f["errors"]:
            print(f"       ERROR    {msg}")
        for msg in f["warnings"]:
            print(f"       WARNING  {msg}")

    t = result["totals"]
    print("-" * 60)
    print(f"{t['files']} card(s): {t['errors']} error(s), {t['warnings']} warning(s)")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ids", nargs="*", help="card ids, e.g. P02 P05 (default: all)")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--json", action="store_true", dest="as_json",
                    help="dump the full result as JSON to stdout")
    args = ap.parse_args(argv)

    ids = []
    for raw in args.ids:
        cid = Path(raw).stem
        if not CARD_ID_RE.match(cid):
            print(f"ERROR: {raw!r} is not a card id like P02", file=sys.stderr)
            return 2
        ids.append(cid)

    result = validate(Path(args.root), ids or None)

    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_human(result)

    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
