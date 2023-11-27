"""Miscellaneous methods and classes shared between bots and reports"""

import logging

from collections.abc import Callable, Iterable
from itertools import chain
from pathlib import Path
from shutil import rmtree
from time import time
from typing import Union

import requests

from pwiki.mquery import MQuery
from pwiki.ns import NS
from pwiki.wiki import Wiki

_CACHE_ROOT = Path("/tmp/fastilybot")
_COMMONS = "commons.wikimedia.org"

log = logging.getLogger(__name__)


def cache_hit(p: Path, max_age: int) -> bool:
    """Checks if `max_age` seconds have occured since the last modified time of `p`. 

    Args:
        p (Path): The path to check
        max_age (int): The maximum number of seconds that have elapsed since the last modified time of `p` to consider the cache valid.

    Returns:
        bool: True if `p` exists and `max_age` is greater than the number of seconds elapsed since `p`'s last modified time.
    """
    return p.exists() and time() - p.stat().st_mtime <= max_age


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

    if not cache_hit(r := _CACHE_ROOT / (r_name := f"report{num}.txt"), 3600*12):
        log.debug("Cached copy of '%s' is missing or out of date, downloading a new copy...", r_name)
        r.write_bytes(requests.get("https://fastilybot-reports.toolforge.org/r/" + r_name).content)

    prefix = prefix or ""  # avoid None
    return {prefix + s.replace("_", " ") for s in text.split("\n")} if (text := r.read_text().strip()) else set()


def listify(l: Iterable, should_escape: bool = True, header: str = "") -> str:
    """Convenience method which converts and formats an Iterable into wikitext ready to be posted as a finished database report.

    Args:
        l (Iterable): The Iterable to convert into wikitext
        should_escape (bool, optional): Set `False` to disable escaping of wikilinks. Defaults to True.
        header (str, optional): The header to put at the top of the generated wikitext. Defaults to "".

    Returns:
        str: The report wikitext derived from `l`.
    """
    c = ":" if should_escape else ""
    return header + "\n".join((f"*[[{c}{s}]]" for s in l))


def purge_cache():
    """Deletes all cached files created by fastilybot"""
    rmtree(_CACHE_ROOT, True)


class FastilyBotBase:
    """Base class for FastilyBot bot types"""

    def __init__(self, wiki: Wiki, config_prefix: str = None, auto_login: bool = False) -> None:
        """Initializer, creates a new FastilyBotBase. 

        Args:
            wiki (Wiki): The Wiki object to use. `wiki` is assumed to be logged-in
            config_prefix (str, optional): Config prefix title for extending classes to use.  Does nothing otherwise. Defaults to None.
            auto_login (bool, optional): Enable automatic login of the `com` `Wiki` object, based on the credentials in `wiki`, if applicable. Defaults to False.
        """
        self.wiki: Wiki = wiki
        self.config_prefix: str = config_prefix
        self._auto_login: bool = auto_login

        self._regex_cache: dict = {}
        self._com: Wiki = None

    def _difference_of(self, *l: Union[int, str, tuple, list]) -> set:
        """Subtract database reports and lists of titles from one another.  See `_resolve_entity()` for acceptable inputs.

        Args:
            l (Union[int, str, tuple, list, set]): The object to interpret

        Returns:
            set: The result of the subtraction operation.
        """
        if not isinstance(target := self._resolve_entity(l[0]), set):
            target = set(target)

        for e in l[1:]:
            target = target.difference(self._resolve_entity(e))

        return target

    def _ignore_of(self, sub_title: Union[int, str]) -> str:
        """Convenience method, get the title of an ignore configuration page.

        Args:
            sub_title (Union[int,str]): The sub title (comes after prefix) value to use.  Don't include the `/` prefix.  An `int` in this field will be interpreted as a `str`.

        Returns:
            str: the title of `sub_title`'s ignore configuration
        """
        return self._config_of(sub_title, "Ignore")

    def _regex_for(self, title: str) -> str:
        """Generates a regex matching a template and its redirects, `title`.  This method is cached, so repeated calls to will not result in new queries to the server.

        Args:
            title (str): The template to generate a regex for.

        Returns:
            str: The regex
        """
        if title in self._regex_cache:
            return self._regex_cache[title]

        self._regex_cache[title] = (r := r"(?si)\n?\{\{(Template:)??(" + "|".join([self.wiki.nss(t) for t in (self.wiki.what_links_here(title, True) + [title])]) + r").*?\}\}")
        return r

    def _resolve_entity(self, e: Union[int, str, tuple, list, set], default_nsl: tuple = (NS.FILE,)) -> Iterable[str]:
        """Takes an object and interprets as follows:
            * `int` - fetch the corresponding fastilybot-toolforge report
            * `str` - if this a category title, get category members, if this is a template title, then get the template's transclusions, if userpage or project page, get links and call this method again with each link.
            * `list`/`set` - return the input
            * `tuple` - the first element must be an `int`/`str` and will be interpreted as above.
                * If the first element was a `str`, the remaning elements will be treated as a namespace filter
                * If the first element was an `int`, then the second element will be used as the prefix for all the returned elements.

            WARNING: If namespace was not specified via tuple, then it is assumed to be File namespace!

        Args:
            e (Union[int, str, tuple, list, set]): The object to interpret
            default_nsl (tuple, optional): The default namespace filter (inclusive) to use if it is not specified in `e`.  Set `None` to disable.  Defaults to (NS.FILE,).

        Returns:
            Iterable[str]: The interpreted value of `e` as described above.
        """
        if isinstance(e, (list, set)):
            return e

        if isinstance(e, tuple):
            name = e[0]
            nsl = () if None in e[1:] else e[1:]
        else:
            name = e
            nsl = default_nsl or ()

        if isinstance(name, int):
            return fetch_report(name, self.wiki.ns_manager.canonical_prefix(nsl[0]) if nsl else None)
        elif name.startswith("Category:"):
            return CQuery.category_members(self.wiki, name, list(nsl))
        elif name.startswith("Template:"):
            return CQuery.what_transcludes_here(self.wiki, name, list(nsl))
        elif name.startswith(("User:", "Wikipedia:")):
            return set(chain.from_iterable(self._resolve_entity(s, nsl) for s in self.wiki.links_on_page(name)))

    def _config_of(self, sub_title: Union[int, str], suffix: str) -> str:
        """Convenience method, get the title of a configuration page

        Args:
            sub_title (Union[int,str]): The task number to use
            suffix (str): The sub title name of the configuration subpage (excluding `self.config_prefix`).  Don't include the `/` prefix.  An `int` in this field will be interpreted as a `str`.

        Returns:
            str: The full title of the configuration page
        """
        if self.config_prefix is None:
            raise RuntimeError("You must set config_prefix in the initializer to use this method!")

        return f"{self.config_prefix}{sub_title}/{suffix}"

    @property
    def com(self) -> Wiki:
        """An anonymous Wiki object that points to the Wikimedia Commons.  This property is cached and lazy loaded.

        Returns:
            Wiki: An anonymous Wiki object that points to the Wikimedia Commons. 
        """
        if not self._com:
            self._com = Wiki(_COMMONS, self.wiki.username) if self._auto_login and self.wiki.is_logged_in else Wiki(_COMMONS, cookie_jar=None)

        return self._com


class CQuery:
    """Collection of methods for performing queries on a Wiki and caching the results."""

    @staticmethod
    def _do_query(wiki: Wiki, fn: Callable[..., list[str]], title: str, nsl: Union[list[Union[NS, str]], NS, str] = [], expiry: int = 10) -> list[str]:
        """Performs a query and caches the result on disk.  If a matching, non-expired cached query was found, then that result will be returned.

        Args:
            wiki (Wiki): The Wiki object to use
            fn (Callable[..., list[str]]): The method to call on cache miss.
            title (str): The title to query
            nsl (Union[list[Union[NS, str]], NS, str], optional): If set, only return results in these namespaces.  Defaults to [].
            expiry (int, optional): The amount of time, in minutes, before the cached result should be considered outdated. Defaults to 10.

        Returns:
            list[str]: The result of the query
        """
        if not isinstance(nsl, list):
            nsl = [nsl]

        (p := _CACHE_ROOT / wiki.domain / wiki.which_ns(title)).mkdir(parents=True, exist_ok=True)
        if not cache_hit(cache := p / (wiki.nss(title) + ("_" + "_".join(sorted([wiki.ns_manager.stringify(n) for n in nsl])) if nsl else "") + ".txt"), 60*expiry):
            log.debug("Cache miss for '%s', downloading new copy...", title)
            cache.write_text("\n".join(l := fn(title, nsl)))
            return l

        return out.split("\n") if (out := cache.read_text().strip()) else []  # handle empty files

    @staticmethod
    def category_members(wiki: Wiki, title: str, ns: Union[list[Union[NS, str]], NS, str] = []) -> list[str]:
        """Fetches the elements in a category.

        Args:
            wiki (Wiki): The Wiki object to use
            title (str): The title of the category to fetch elements from.  Must include `Category:` prefix.
            ns (Union[list[Union[NS, str]], NS, str], optional): Only return results that are in these namespaces. Optional, leave blank to disable

        Returns:
            list[str]: a `list` containing `title`'s category members.
        """
        return CQuery._do_query(wiki, wiki.category_members, title, ns)

    @staticmethod
    def what_transcludes_here(wiki: Wiki, title: str, ns: Union[list[Union[NS, str]], NS, str] = []) -> list[str]:
        """Fetch pages that translcude a page.  If querying for templates, you must include the `Template:` prefix.

        Args:
            wiki (Wiki): The Wiki object to use
            title (str): The title to query
            ns (Union[list[Union[NS, str]], NS, str], optional): Restrict returned output to titles in these namespaces. Optional, set to empty list to disable. Defaults to [].

        Returns:
            list[str]: The list of pages that transclude `title`.
        """
        return CQuery._do_query(wiki, wiki.what_transcludes_here, title, ns)


class XQuery:
    """Collection of extended Wiki queries"""

    @staticmethod
    def exists_filter(wiki: Wiki, titles: Iterable[str], existent: bool = True) -> set[str]:
        """Check if elements in `titles` exist, then filter the results by `existent`.

        Args:
            wiki (Wiki): The Wiki to use
            titles (Iterable[str]): The titles to check
            existent (bool, optional): Set `True` to only return titles that exist.  Set `False` to only fetch titles that don't exist. Defaults to True.

        Returns:
            set[str]: The list of titles filtered by `existent`
        """
        return {k for k, v in MQuery.exists(wiki, titles if isinstance(titles, list) else list(titles)).items() if existent == v}
