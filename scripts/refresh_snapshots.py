"""Rebuild the bundled result snapshots in data/snapshots/ from Wikipedia.

    python scripts/refresh_snapshots.py                 # all elections
    python scripts/refresh_snapshots.py uk-ge-2024      # just one
    python scripts/refresh_snapshots.py --html-dir DIR  # parse saved <Page_title>.html files instead of fetching

Requests are spaced out to respect Wikimedia's rate limits.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from election_data import registry, wiki  # noqa: E402


def get_html(title: str, html_dir: Path | None) -> tuple[str, float]:
    if html_dir is not None:
        p = html_dir / f"{title}.html"
        if p.exists() and p.stat().st_size > 10_000:
            return p.read_text(encoding="utf-8"), p.stat().st_mtime
        raise FileNotFoundError(f"{p.name} not in --html-dir")
    page = wiki.fetch(title, max_age=0, retries=6)
    time.sleep(3)
    return page.html, page.fetched_at


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("keys", nargs="*")
    ap.add_argument("--html-dir", type=Path)
    args = ap.parse_args()

    failed = []
    for specs in registry.catalogue(include_discovered=True).values():
        for spec in specs:
            if args.keys and spec.key not in args.keys:
                continue
            if spec.is_upcoming:
                continue
            try:
                html, ts = get_html(spec.page, args.html_dir)
                res = spec.parse(html, spec.year, f"https://en.wikipedia.org/wiki/{spec.page}")
                res.fetched_at = ts
                for extra in spec.extra_pages:
                    try:
                        eh, _ = get_html(extra, args.html_dir)
                        res = registry.apply_extra(spec, res, eh)
                    except Exception as e:  # vote share is optional
                        print(f"  (no vote share for {spec.key}: {e})")
                path = res.save_snapshot()
                top = res.national.iloc[0]
                print(f"OK   {spec.key:16} {len(res.units):3} units  {top['party']} {top['seats']}  -> {path.name}")
            except Exception as e:
                failed.append(spec.key)
                print(f"FAIL {spec.key:16} {e}")
    if failed:
        print("Failed:", ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
