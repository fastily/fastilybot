"""miscellaneous methods and classes shared between bots and reports"""

import logging

from collections.abc import Callable
from pathlib import Path
from time import time
from typing import Union

import requests

from pwiki.ns import NS
from pwiki.wiki import Wiki

_CACHE_ROOT = Path("/tmp/fastilybot")

log = logging.getLogger(__name__)


def fetch_report(num: int, prefix: str = "File:") -> set:
    """Fetches the specified numbered report from `fastilybot-reports` on toolforge.  Downloaded reports are cached for 24h.

    Args:
        num (int): The report id to download.
        prefix (str, optional): A prefix to add to the beginning of each returned str. Defaults to "File:".

    Returns:
        set: The `set` of elements retrieved from the report.
    """
    if not _CACHE_ROOT.exists():
        _CACHE_ROOT.mkdir(exist_ok=True)

    if not (r := _CACHE_ROOT / (r_name := f"report{num}.txt")).exists() or (time() - r.stat().st_mtime) / 3600 > 24:
        log.debug("Cached copy of '%s' is missing or out of date, downloading a new copy...", r_name)
        r.write_bytes(requests.get("https://fastilybot-reports.toolforge.org/r/" + r_name).content)  # TODO: replace with urllib?

    p = prefix or ""
    return {p + s.replace("_", " ") for s in r.read_text().strip().split("\n")}


class CQuery:
    """Collection of methods for performing queries on a Wiki and caching the results."""

    @staticmethod
    def _do_query(wiki: Wiki, fn: Callable[..., list[str]], title: str, nsl: list[Union[NS, str]] = [], expiry: int = 10) -> list[str]:
        (p := _CACHE_ROOT / wiki.domain / wiki.which_ns(title)).mkdir(parents=True, exist_ok=True)
        cache = p / (wiki.nss(title) + ("_" + "_".join(sorted([wiki.ns_manager.stringify(n) for n in nsl])) if nsl else "") + ".txt")

        if not cache.exists() or (time() - cache.stat().st_mtime) / 60 > expiry:
            log.debug("Cache miss for '%s', downloading new copy...", title)
            cache.write_text("\n".join(l := fn(title, *nsl)))
            return l

        return cache.read_text().strip().split("\n")

    @staticmethod
    def category_members(wiki: Wiki, title: str, *ns: Union[NS, str]) -> list[str]:
        return CQuery._do_query(wiki, wiki.category_members, title, list(ns))

    @staticmethod
    def what_transcludes_here(wiki: Wiki, title: str, *ns: Union[NS, str]) -> list[str]:
        return CQuery._do_query(wiki, wiki.what_transcludes_here, title, list(ns))
