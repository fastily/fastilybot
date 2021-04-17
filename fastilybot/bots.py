"""Bot tasks for FastilyBot on the English Wikipedia"""

import json
import logging
import re

from collections import defaultdict, deque
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from itertools import chain

from pwiki.gquery import GQuery
from pwiki.mquery import MQuery
from pwiki.ns import NS
from pwiki.oquery import OQuery
from pwiki.wiki import Wiki
from pwiki.wparser import WParser

from .constants import C, T
from .core import CQuery, FastilyBotBase, fetch_report, listify, XQuery

log = logging.getLogger(__name__)


def _yesterday_and_today() -> tuple[datetime, datetime]:
    """Gets the `datetime` of yesterday and today in UTC and truncates the times to midnight.

    Returns:
        tuple[datetime, datetime]: A tuple where the first element is the yesterday `datetime` and the second element is the today `datetime`.
    """
    return (today := datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)) - timedelta(1), today


class Bots(FastilyBotBase):
    """Fastily's Wikipedia bot tasks"""

    def __init__(self, wiki: Wiki) -> None:
        """Initializer, creates a new Bots object.

        Args:
            wiki (Wiki): The Wiki object to use
        """
        super().__init__(wiki, f"User:{wiki.whoami()}/Task/")

        self.mtc_tag: str = f"{{{{Now Commons|%s|date={datetime.utcnow():%-d %B %Y}|bot={self.wiki.username}}}}}"

    ##################################################################################################
    ######################################## H E L P E R S ###########################################
    ##################################################################################################

    def _category_members_recursive(self, title: str) -> set:
        """Recursively fetch pages in the category specified by `title`.  Includes logic to avoid category loops.

        Args:
            title (str): The category to recursively get members of.

        Returns:
            set: All recursively fetched members of the category
        """
        q = deque([title])
        visited = set()
        out = set()

        cat_ns = self.wiki.ns_manager.stringify(NS.CATEGORY)

        while q:
            if (cat := q.pop()) in visited:
                continue

            for s in self.wiki.category_members(cat):
                if self.wiki.which_ns(s) == cat_ns:
                    q.append(s)
                else:
                    out.add(s)

            visited.add(cat)

        return out

    def _file_notifier(self, talk_template_base: str, titles: Iterable[str]) -> None:
        """Shared functionality of file deletion notification bots (`dated_deleteion_notifier`, `ffd_notifier`).

        Args:
            talk_template_base (str): The template to add to the talk pages of users to notifiy.  Do not include `Template:` prefix.
            titles (Iterable[str]): The titles to process.
        """
        yesterday, today = _yesterday_and_today()

        d = defaultdict(list)
        for f in titles:
            if uploader := self.wiki.first_editor_of(f):
                d[self.wiki.convert_ns(uploader, NS.USER_TALK)].append(f)

        # remove talk pages with nobots
        ignore_list = set(CQuery.what_transcludes_here(self.wiki, T.B, NS.USER_TALK))
        d = {k: v for k, v in d.items() if k not in ignore_list}

        # skip talk pages which are redirects
        redirs = OQuery.resolve_redirects(self.wiki, list(d.keys()))
        d = {k: v for k, v in d.items() if k == redirs[k]}

        img_links = MQuery.what_links_here(self.wiki, list(chain.from_iterable(d.values())))
        for uploader_talk, uploads in d.items():
            # optimization, uploader pages that already contain a backlink
            if not (targets := {t for t in uploads if uploader_talk not in img_links[t]}):
                continue

            # aggregate links from all revisions in the past day and remove them if they were in targets
            if not (targets := targets.difference(chain.from_iterable(WParser.revision_metadata(self.wiki, r, links=True)["links"] for r in self.wiki.revisions(uploader_talk, start=yesterday, end=today)))):
                continue

            targets = list(targets)
            also = listify(targets[1:], header='\n\nAlso:\n') if len(targets) > 1 else ''
            self.wiki.edit(uploader_talk, append=f"\n\n{{{{subst:{talk_template_base}|{targets[0]}}}}}{also}\n" + "{{subst:User:FastilyBot/BotNote}}", summary="BOT: Some of your file(s) may need attention")

    ##################################################################################################
    ########################################### B O T S ##############################################
    ##################################################################################################

    def date_now_commons(self):
        """Fills in the date parameter for instances of `{{Now Commons}}` that are lacking it.  Task 11"""
        ncd_regex = self._regex_for(T.NCD)
        subst_ncd = f"\n{{{{subst:{self.wiki.nss(T.NCD)}}}}}"

        for s in self._difference_of(self.wiki.category_members("Category:Wikipedia files with the same name on Wikimedia Commons as of unknown date", NS.FILE), self._category_members_recursive("Category:Wikipedia files reviewed on Wikimedia Commons")):
            self.wiki.replace_text(s, ncd_regex, subst_ncd, "BOT: Dating Now Commons tag")

    def dated_deletion_notifier(self):
        """Notifies uploaders if their files have been nominated for dated deletion.  Task 6"""
        idk_l = set(chain.from_iterable(MQuery.what_transcludes_here(self.wiki, self.wiki.links_on_page(self._ignore_of(6))).values()))

        target_suffix = f"{_yesterday_and_today()[0]:%-d %B %Y}"

        for root_cat, talk_template in json.loads(self.wiki.page_text(self._config_of(6, "Rules"))).items():
            if not (target_cat := next((s for s in self.wiki.category_members(root_cat, NS.CATEGORY) if s.endswith(target_suffix)), None)):
                log.debug("'%s' does not seem to have a category matching yesterday's date of '%s'", root_cat, target_suffix)
                continue

            self._file_notifier(talk_template, self._difference_of(target_cat, idk_l))

    def ffd_notifier(self):
        """Notifies uploaders if their files have been nominated for ffd.  Task 12"""
        ffd_snippet = re.compile(r"\|log\s*\=\s*" + (target_suffix := f"{_yesterday_and_today()[0]:%Y %B %-d}"))
        self._file_notifier(self._config_of(12, "Note"), [title for title, text in MQuery.page_text(self.wiki, self.wiki.links_on_page("Wikipedia:Files for discussion/" + target_suffix, NS.FILE)).items() if ffd_snippet.search(text)])

    def find_deleted_on_commons(self):
        """Replace instances of `{{Nominated for deletion on Commons}}` on files that have been deleted on Commons with `{{Deleted on Commons}}`.  Task 8"""
        nfdc_regex = re.compile(self._regex_for(T.NFDC))
        dc_title = self.wiki.nss(T.DC)

        # grab all files and alleged commons copies
        d = {}
        for k, v in (t_table := MQuery.page_text(self.wiki, CQuery.what_transcludes_here(self.wiki, T.NFDC, NS.FILE))).items():
            try:
                if (t := nfdc_regex.search(v).group()) and (target := self.wiki.parse(text=t).templates[0]):
                    d[k] = str(target.get_param("1", k))
            except Exception:
                log.warning("Could not parse text of '%s'", k)

        # normalize
        n_table = OQuery.normalize_titles(self.wiki, list(d.values()))
        d = {k: self.wiki.convert_ns(n_table[v], NS.FILE) for k, v in d.items()}

        # remove existent files and files that were not actually deleted
        e_table = XQuery.exists_filter(self.com, list(d.values()))  # only pages that exist
        for k, v in d.items():
            if v not in e_table and next(GQuery.logs(self.com, v, log_action="delete/delete"), None):
                self.wiki.edit(k, nfdc_regex.sub(f"\n{{{{{dc_title}|{self.wiki.nss(v)}}}}}", t_table[k]), "BOT: This file was deleted on Commons")

    def find_license_conflicts(self):
        """Finds files which are labled as both free and non-free.  Task 5"""
        for s in self._difference_of(2, self._ignore_of(5)):
            self.wiki.edit(s, prepend="{{Wrong-license}}\n", summary="BOT: Marking conflict in copyright status")

    def flag_files_nominated_for_deletion_on_commons(self):
        """Replaces instances of `{{Now Commons}}` with `{{Nominated for deletion on Commons}}` if the duplicate on Commons has been nominated for deletion.  Task 7"""
        ncd_regex = self._regex_for(T.NCD)
        nfdc_base = self.wiki.nss(T.NFDC)

        dl = set(CQuery.what_transcludes_here(self.com, T.DTT, NS.FILE))
        for title, dupes in MQuery.duplicate_files(self.wiki, CQuery.what_transcludes_here(self.wiki, T.NCD, NS.FILE), False, True).items():
            if target := next((s for s in dupes if s in dl), None):
                self.wiki.replace_text(title, ncd_regex, f"\n{{{{{nfdc_base}|{self.wiki.nss(target)}}}}}", "BOT: This file has been nominated for deletion on Commons")

    def flag_files_saved_from_deletion_on_commons(self):
        """Replaces of `{{Nominated for deletion on Commons}}` with `{{Now Commons}}` for files that are no longer up for deletion on Commons.  Task 9 """
        nfdc_regex = self._regex_for(T.NFDC)

        dl = set(CQuery.what_transcludes_here(self.com, T.DTT, NS.FILE))
        for title, dupes in MQuery.duplicate_files(self.wiki, CQuery.what_transcludes_here(self.wiki, T.NFDC, NS.FILE), False, True).items():
            if dupes and not dl.intersection(dupes):
                self.wiki.replace_text(title, nfdc_regex, f"\n{{{{subst:{T.NCD}|{self.wiki.nss(dupes[0])}}}}}", "BOT: This file is no longer up for deletion on Commons")

    def flag_orphaned_free_images(self):
        """Finds freely licensed files with no fileusage and tags them with `{{Orphan image}}`.  Task 10"""
        oi_title = self.wiki.nss(T.OI)
        for s in XQuery.exists_filter(self.wiki, list(self._difference_of(3, 9, T.B, T.DF, 4, self._ignore_of(10)))):
            self.wiki.edit(s, append=f"\n{{{{{oi_title}}}}}", summary="BOT: this file has no inbound file usage")

    def mtc_clerk(self):
        """Find and fix tags for files tagged for transfer to Commons which have already transferred.  Task 1"""
        ncd_l = set(CQuery.what_transcludes_here(self.wiki, T.NCD))
        mtc_regex = self._regex_for(T.CTC)

        d = {k: v[0] for k, v in MQuery.duplicate_files(self.wiki, list(self._difference_of(fetch_report(1).intersection(CQuery.what_transcludes_here(self.wiki, T.CTC, NS.FILE)),
                                                                                            T.KL, C.CTC_II)), False, True).items() if v}
        texts = MQuery.page_text(self.wiki, list(d.keys()))

        for k, v in d.items():
            if (n := re.sub(mtc_regex, "", texts[k])) != texts[k]:
                self.wiki.edit(k, ("" if k in ncd_l else self.mtc_tag % v + "\n") + n, "BOT: This file has already been copied to Commons")

    def untag_unorphaned_images(self):
        """Removes the Orphan image tag from free files which are no longer orphaned.  Task 4"""
        oi_regex = self._regex_for(T.OI)

        for s in (self._difference_of(9, self._difference_of(3, 4), T.B) & fetch_report(6)):
            self.wiki.replace_text(s, oi_regex, summary="BOT: File contains inbound links")

    def remove_bad_mtc(self):
        """Removes the MTC tag from files which do not appear to be eligible for Commons.  Task 2"""
        l = self._difference_of(T.CTC, self._category_members_recursive(C.CTC_H), C.CTC_II)

        mtc_regex = self._regex_for(T.CTC)

        for s in chain.from_iterable(l.intersection(CQuery.category_members(self.wiki, cat, NS.FILE)) for cat in self.wiki.links_on_page(self._config_of(2, "Blacklist"))):
            self.wiki.replace_text(s, mtc_regex, summary="BOT: This file does not appear to be eligible for Commons")

    def nominated_for_deleteion_on_commons(self):
        """Replaces `{{Now Commons}}` locally with `{{Nominated for deletion on Commons}}` if the file is nominated for deletion on Commons.  Task 7"""
        ncd_regex = self._regex_for(T.NCD)
        l = set(CQuery.what_transcludes_here(self.com, T.DTT, NS.FILE))

        for k, v in MQuery.duplicate_files(self.wiki, CQuery.what_transcludes_here(self.wiki, T.NCD, NS.FILE), False, True).items():
            if v and v[0] in l:
                self.wiki.replace_text(k, ncd_regex, f"{{{{Nominated for deletion on Commons|{self.wiki.nss(v[0])}}}}}", "BOT: File is up for deletion on Commons")
