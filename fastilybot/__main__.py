"""Main entry point for Fastilybot"""

import argparse
import logging

from collections.abc import Iterable

from rich.logging import RichHandler

from pwiki.wgen import load_px, setup_px
from pwiki.wiki import Wiki

from .bots import Bots
from .core import purge_cache
from .reports import Reports

log = logging.getLogger(__name__)


def _determine_tasks(individual: str, do_all: bool = False, total_ids: int = 0) -> Iterable[int]:
    """Convenience method, parses the task list arguments and returns the list of ids to process.  Note that `do_all` takes precedence over `individual`.

    Args:
        individual (str): The argument passed for individual tasks (this is a comma delimitated str with int ids)
        do_all (bool, optional): The flag indicating if all available tasks should be run. Defaults to False.
        total_ids (int, optional): If `do_all` is `True`, then return a range from 1 -> total_ids + 1. Defaults to 0.

    Returns:
        Iterable[int]: The ids to process.  `None` if there are no tasks to be run.
    """
    if do_all:
        return range(1, total_ids + 1)
    elif individual:
        return [int(s) for s in individual.split(",")]


def _main():
    """Main driver, invoked when this file is run directly."""
    cli_parser = argparse.ArgumentParser(description="FastilyBot CLI")
    cli_parser.add_argument('-u', type=str, default="FastilyBot", metavar="username", help="the username to use")
    cli_parser.add_argument('-b', type=str, metavar="bot_id", help="comma deliminated ids of bot tasks to run")
    cli_parser.add_argument('-r', type=str, metavar="report_id", help="comma deliminated ids of report tasks to run")
    cli_parser.add_argument("--all-reports", action='store_true', dest="all_reports", help="runs all possible reports tasks")
    cli_parser.add_argument("--no-color", action='store_true', dest="no_color", help="disables colored log output")
    cli_parser.add_argument("--purge-cache", action='store_true', dest="purge_cache", help="delete all cached files created by fastilybot and exit")
    cli_parser.add_argument("--wgen", action='store_true', help="run wgen password manager")
    args = cli_parser.parse_args()

    if args.purge_cache:
        purge_cache()
        return

    if args.wgen:
        setup_px()
        return

    if not any((args.all_reports, args.r, args.b)):
        cli_parser.print_help()
        return

    if args.no_color:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("{asctime}: {levelname}: {message}", "%Y-%m-%d %H:%M:%S", "{"))
    else:
        handler = RichHandler(rich_tracebacks=True)
    for s in ("pwiki", "fastilybot"):
        lg = logging.getLogger(s)
        lg.addHandler(handler)
        lg.setLevel("DEBUG")

    wiki = Wiki(username=args.u, password=load_px().get(args.u))

    if wiki.exists(f"User:{wiki.username}/shutoff"):
        log.info("killswitch triggered, exiting...")
        return

    if bot_ids := _determine_tasks(args.b):
        b = Bots(wiki)

        for id in bot_ids:
            if id == 1:
                b.mtc_clerk()
            elif id == 2:
                b.remove_bad_mtc()
            elif id == 3:
                pass  # see Report 5
            elif id == 4:
                b.untag_unorphaned_images()
            elif id == 5:
                b.find_license_conflicts()
            elif id == 6:
                b.dated_deletion_notifier()
            elif id == 7:
                b.flag_files_nominated_for_deletion_on_commons()
            elif id == 8:
                b.find_deleted_on_commons()
            elif id == 9:
                b.flag_files_saved_from_deletion_on_commons()
            elif id == 10:
                b.flag_orphaned_free_images()
            elif id == 11:
                b.date_now_commons()
            elif id == 12:
                b.ffd_notifier()
            else:
                log.warning("No such bot task (%d), skipping", id)

    if report_ids := _determine_tasks(args.r, args.all_reports, 18):
        r = Reports(wiki)

        for id in report_ids:
            if id == 1:
                r.shadows_commons_page()
            elif id == 2:
                r.orphaned_files_for_discussion()
            elif id == 3:
                r.all_free_license_tags()
            elif id == 4:
                r.mtc_redirects()
            elif id == 5:
                r.malformed_spi_reports()
            elif id == 6:
                r.orphaned_keep_local()
            elif id == 7:
                pass  # part of all_free_license_tags()
            elif id == 8:
                r.oversized_fair_use_files()
            elif id == 9:
                r.missing_file_copyright_tags()
            elif id == 10:
                r.duplicate_on_commons()
            elif id == 11:
                r.low_resolution_free_files()
            elif id == 12:
                r.possibly_unsourced_files()
            elif id == 13:
                r.impossible_daily_deletion()
            elif id == 14:
                r.shadows_commons_non_free()
            elif id == 15:
                r.non_free_pdfs()
            elif id == 16:
                r.orphaned_file_talk()
            elif id == 17:
                r.orphaned_pdfs()
            elif id == 18:
                r.transcluded_non_existent_templates()
            else:
                log.warning("No such report id (%d), skipping", id)

    wiki.save_cookies()


if __name__ == "__main__":
    _main()
