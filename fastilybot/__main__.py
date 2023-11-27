"""Main entry point for Fastilybot"""

import argparse
import logging

from collections.abc import Iterable

from rich.logging import RichHandler

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
    args = cli_parser.parse_args()

    if args.purge_cache:
        purge_cache()
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

    wiki = Wiki(username=args.u)

    if wiki.exists(f"User:{wiki.username}/shutoff"):
        log.info("killswitch triggered, exiting...")
        return

    if bot_ids := _determine_tasks(args.b):
        b = Bots(wiki)

        for id in bot_ids:
            match id:
                case 1:
                    b.mtc_clerk()
                case 2:
                    b.remove_bad_mtc()
                case 3:
                    pass  # see Report 5
                case 4:
                    b.untag_unorphaned_images()
                case 5:
                    b.find_license_conflicts()
                case 6:
                    b.dated_file_deletion_notifier()
                case 7:
                    b.flag_files_nominated_for_deletion_on_commons()
                case 8:
                    b.find_deleted_on_commons()
                case 9:
                    b.flag_files_saved_from_deletion_on_commons()
                case 10:
                    b.flag_orphaned_free_images()
                case 11:
                    b.date_now_commons()
                case 12:
                    b.ffd_notifier()
                case 13:
                    pass  # blanket approval for Reports
                case 14:
                    b.prod_notifier()
                case 15:
                    b.keep_local_now_commons()
                case 16:
                    pass  # see Task 14
                case 17:
                    b.outdated_ffdc()
                case _:
                    log.warning("No such bot task (%d), skipping", id)

    if report_ids := _determine_tasks(args.r, args.all_reports, 18):
        r = Reports(wiki)

        for id in report_ids:
            match id:
                case 1:
                    r.shadows_commons_page()
                case 2:
                    r.orphaned_files_for_discussion()
                case 3:
                    r.all_free_license_tags()
                case 4:
                    r.orphaned_timed_text()
                case 5:
                    r.malformed_spi_reports()
                case 6:
                    r.orphaned_keep_local()
                case 7:
                    pass  # part of all_free_license_tags()
                case 8:
                    r.oversized_fair_use_files()
                case 9:
                    r.missing_file_copyright_tags()
                case 10:
                    r.duplicate_on_commons()
                case 11:
                    r.low_resolution_free_files()
                case 12:
                    r.possibly_unsourced_files()
                case 13:
                    r.impossible_daily_deletion()
                case 14:
                    r.shadows_commons_non_free()
                case 15:
                    r.non_free_pdfs()
                case 16:
                    r.orphaned_file_talk()
                case 17:
                    r.orphaned_pdfs()
                case 18:
                    r.transcluded_non_existent_templates()
                case 19:
                    r.flickr_files()
                case 20:
                    r.large_ip_talk_pages()
                case 21:
                    r.large_user_talk_pages()
                case 22:
                    r.multi_ext_filenames()
                case 23:
                    r.getty_files()
                case 24:
                    r.ap_files()
                case 25:
                    r.unfiled_rfas()
                case 26:
                    r.fully_protected_user_talk()
                case 27:
                    r.orphaned_keep_local_with_commons_duplicate()
                case _:
                    log.warning("No such report id (%d), skipping", id)

    wiki.save_cookies()


if __name__ == "__main__":
    _main()
