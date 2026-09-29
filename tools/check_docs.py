# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ruan Pato

"""Check publication-candidate Markdown links without scanning ignored local files."""

import argparse
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]


def slug(value):
    value = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", value)
    return re.sub(r"[^\w\- ]", "", value.lower()).replace(" ", "-")


def external(url):
    if urlsplit(url).hostname in {"localhost", "127.0.0.1", "example.invalid"}:
        return url, "local/example; verified separately"
    if url.startswith("https://github.com/ruanpato/tracequota"):
        return url, "private repository; verified through authenticated GitHub access"
    try:
        with urlopen(Request(url, headers={"User-Agent": "TraceQuota-docs-check/0.2"}), timeout=20) as response:
            return url, response.status
    except HTTPError as exc:
        return url, exc.code
    except (URLError, TimeoutError) as exc:
        return url, str(exc)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--external", action="store_true", help="Also check public URLs over the network")
    args = parser.parse_args()
    files = (
        subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT)
        .decode()
        .split("\0")
    )
    errors, urls, links = [], set(), 0
    markdown = sorted({ROOT / f for f in files if f.endswith(".md")})
    for path in markdown:
        content = re.sub(r"```.*?```", "", path.read_text(), flags=re.S)
        for target in re.findall(r"!?\[[^]]*\]\(([^)]+)\)", content):
            target = target.split(' "', 1)[0].strip("<>")
            if target.startswith(("http://", "https://")):
                urls.add(target)
                continue
            if target.startswith("mailto:"):
                continue
            links += 1
            relative, _, anchor = unquote(target).partition("#")
            destination = (path.parent / relative).resolve() if relative else path
            if not destination.is_relative_to(ROOT) or not destination.exists():
                errors.append(f"{path.relative_to(ROOT)}: missing or out-of-repository target {target}")
            elif anchor and destination.suffix == ".md":
                headings = re.findall(r"^#+\s+(.*)$", destination.read_text(), flags=re.M)
                if anchor not in {slug(h) for h in headings}:
                    errors.append(f"{path.relative_to(ROOT)}: missing heading {target}")
    print(f"Checked {len(markdown)} Markdown files and {links} local links.")
    if args.external:
        with ThreadPoolExecutor(max_workers=6) as pool:
            for url, status in pool.map(external, sorted(urls)):
                if status in (404, 410):
                    errors.append(f"Broken public link ({status}): {url}")
                elif isinstance(status, int) and status >= 400:
                    print(f"UNVERIFIED HTTP {status}: {url}")
                elif isinstance(status, str):
                    print(f"NOTE {url}: {status}")
        print(f"Checked {len(urls)} external URLs; network restrictions are reported separately.")
    for error in errors:
        print("FAIL " + error)
    if errors:
        return 1
    print("PASS documentation links.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
