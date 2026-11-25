"""Helpers for turning Wikipedia tables into DataFrames robustly."""
from __future__ import annotations

import io
import re
import warnings

import pandas as pd
from bs4 import BeautifulSoup


def soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def tables(html_or_soup, min_rows: int = 0, must_contain: tuple[str, ...] = ()) -> list[pd.DataFrame]:
    """Parse each <table> separately so one malformed table can't break the rest."""
    s = soup(html_or_soup) if isinstance(html_or_soup, str) else html_or_soup
    out = []
    for tb in s.find_all("table"):
        if len(tb.find_all("tr")) < min_rows:
            continue
        if must_contain:
            txt = tb.get_text(" ")
            if not all(m in txt for m in must_contain):
                continue
        for bad in tb.find_all(["sup", "style"]):
            bad.decompose()   # drop footnote markers like [12]
        for el in tb.find_all(attrs={"rowspan": True}):
            if not str(el["rowspan"]).isdigit():
                del el["rowspan"]
        for el in tb.find_all(attrs={"colspan": True}):
            if not str(el["colspan"]).isdigit():
                del el["colspan"]
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                out.append(pd.read_html(io.StringIO(str(tb)))[0])
        except Exception:
            continue
    return out


def clean(s) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    s = re.sub(r"\[[^\]]*\]", "", str(s))
    return re.sub(r"\s+", " ", s).strip()


def num(s) -> float | None:
    s = clean(s).replace(",", "").replace("%", "").replace("−", "-").replace("–", "")
    try:
        return float(s)
    except ValueError:
        return None


def flat_cols(df: pd.DataFrame) -> list[str]:
    if isinstance(df.columns, pd.MultiIndex):
        return [" | ".join(clean(c) for c in col) for col in df.columns]
    return [clean(c) for c in df.columns]
