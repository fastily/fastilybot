# fastilybot
[![Build Status](https://github.com/fastily/fastilybot/workflows/build/badge.svg)](#)
[![Python 3.9+](https://upload.wikimedia.org/wikipedia/commons/4/4f/Blue_Python_3.9%2B_Shield_Badge.svg)](https://www.python.org)
[![MediaWiki 1.35+](https://upload.wikimedia.org/wikipedia/commons/b/b3/Blue_MediaWiki_1.35%2B_Shield_Badge.svg)](https://www.mediawiki.org/wiki/MediaWiki)
[![License: GPL v3](https://upload.wikimedia.org/wikipedia/commons/8/86/GPL_v3_Blue_Badge.svg)](https://www.gnu.org/licenses/gpl-3.0.en.html)

Fastily's Wikipedia Bots.

This repository contains the rewritten and improved successor to the original [fastilybot](https://github.com/fastily/fastilybot-old).

### Install
```bash
pip install fastilybot
```

### Usage
```
usage: __main__.py [-h] [-u username] [-b bot_id] [-r report_id] [--all-reports] [--no-color] [--purge-cache] [--wgen]

FastilyBot CLI

optional arguments:
  -h, --help     show this help message and exit
  -u username    the username to use
  -b bot_id      comma deliminated ids of bot tasks to run
  -r report_id   comma deliminated ids of report tasks to run
  --all-reports  runs all possible reports tasks
  --no-color     disables colored log output
  --purge-cache  delete all cached files created by fastilybot and exit
  --wgen         run wgen password manager
```

### See Also
* [toollabs reports](https://tools.wmflabs.org/fastilybot-reports/)