
import argparse
from fastilybot.bots import Bots
import logging

from collections.abc import Iterable

from rich.logging import RichHandler

from pwiki.wgen import load_px, setup_px
from pwiki.wiki import Wiki

from .core import purge_cache
from .reports import Reports

log = logging.getLogger(__name__)


def _determine_tasks(individual: str, do_all: bool = False, total_ids: int = 0) -> Iterable[int]:
    """Convenience method, parses the task list arguments and returns the list of ids to process.  Note that `do_all` takes precedence over `individual`.

    Args:
        individual (str): The argument passed for individual tasks (this is a comma deliminated str with int ids)
        do_all (bool): The flag indicating if all available tasks should be run
        total_ids (int): If `do_all` is `True`, then return a range from 1 -> total_ids + 1.

    Returns:
        Iterable[int]: The ids to process.  `None` if there are no tasks to be run.
    """
    if do_all:
        return range(1, total_ids + 1)
    elif individual:
        return [int(s) for s in individual.split(",")]


def _main():
    """Main driver, invoked when this file is run directly."""
    for lg in (logging.getLogger("pwiki"), logging.getLogger("fastilybot")):
        lg.addHandler(RichHandler(rich_tracebacks=True))
        lg.setLevel("DEBUG")

    cli_parser = argparse.ArgumentParser(description="FastilyBot CLI")
    cli_parser.add_argument('-u', type=str, default="FastilyBot", metavar="username", help="the username to use")
    cli_parser.add_argument('-b', type=str, metavar="bot_id", help="comma deliminated ids of bot tasks to run")
    cli_parser.add_argument('-r', type=str, metavar="report_id", help="comma deliminated ids of report tasks to run")
    cli_parser.add_argument("--all-reports", action='store_true', dest="all_reports", help="runs all possible reports tasks")
    cli_parser.add_argument("--purge-cache", action='store_true', dest="purge_cache", help="delete all cached files created by fastilybot and exit")
    cli_parser.add_argument("--wgen", action='store_true', help="run wgen password manager")
    args = cli_parser.parse_args()

    if args.purge_cache:
        purge_cache()
        return

    if args.wgen:
        setup_px()
        return

    if not (args.r or args.b):
        cli_parser.print_help()
        return

    wiki = Wiki(username=args.u, password=load_px().get(args.u))

    if bot_ids := _determine_tasks(args.b):
        b = Bots(wiki)

        for id in bot_ids:
            if id == 1:
                b.mtc_helper()
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
                pass  # retired
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
