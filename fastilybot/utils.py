import logging

from pathlib import Path
from time import time

import requests

_REPORT_DIR = Path("/tmp/fastilybot")

log = logging.getLogger(__name__)


def fetch_report(num: int, prefix: str = "File:"):
    if not _REPORT_DIR.exists():
        _REPORT_DIR.mkdir(exist_ok=True)

    if not (r := _REPORT_DIR / (r_name := f"report{num}.txt")).exists() or (time() - r.stat().st_mtime) / 3600 > 24:
        log.info("Cached copy of '%s' is missing or out of date, downloading a new copy...", r_name)
        r.write_bytes(requests.get("https://fastilybot-reports.toolforge.org/r/" + r_name).content)

    p = prefix or ""
    return {p + s.replace("_", " ") for s in r.read_text().strip().split("\n")}
