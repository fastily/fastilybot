
import argparse
import logging

from rich.logging import RichHandler

from pwiki.wgen import load_px, setup_px
from pwiki.wiki import Wiki

from fastilybot.reports import Reports

log = logging.getLogger(__name__)


def main():

    for lg in (logging.getLogger("pwiki"), logging.getLogger("fastilybot")):
        lg.addHandler(RichHandler(rich_tracebacks=True))
        lg.setLevel("DEBUG")

    cli_parser = argparse.ArgumentParser(description="FastilyBot CLI")
    cli_parser.add_argument('-b', type=str, help="comma deliminated ids of bot tasks to run")
    cli_parser.add_argument('-r', type=str, help="comma deliminated ids of report tasks to run")
    cli_parser.add_argument('-u', type=str, default="FastilyBot", help="the default username to use")
    cli_parser.add_argument("--wgen", action='store_true', help="run wgen password manager")
    args = cli_parser.parse_args()

    if args.wgen:
        setup_px()
        return

    if not (args.r or args.b):
        cli_parser.print_help()
        return

    wiki = Wiki(username=args.u, password=load_px().get(args.u))

    if args.r:
        r = Reports(wiki)

        for id in [int(s) for s in args.r.split(",")]:
            if id == 1:
                pass
            elif id == 2:
                pass
            elif id == 3:
                pass
            elif id == 4:
                pass
            elif id == 5:
                pass
            elif id == 6:
                pass
            elif id == 7:
                pass
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
            else:
                log.warning("No such report id (%d), skipping", id)

    wiki.save_cookies()


if __name__ == "__main__":
    main()
