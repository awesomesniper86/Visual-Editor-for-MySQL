#!/usr/bin/env python3
"""Stamp a new version number into every file that needs one.

Usage:
    python scripts/bump_version.py 0.2.0
    python scripts/bump_version.py --bump patch   # 0.1.0 -> 0.1.1
    python scripts/bump_version.py --bump minor   # 0.1.0 -> 0.2.0
    python scripts/bump_version.py --bump major   # 0.1.0 -> 1.0.0
    python scripts/bump_version.py 0.2.0 --force  # bump even if files disagree

Updates, in one run:
    VERSION              (plain text, for shell/packaging scripts)
    app/version.py       (__version__ constant the app imports)
    README.md            ("**Version:** X.Y.Z" line)
    CHANGELOG.md          (adds a new "## X.Y.Z - <date>" section at the top)

Before writing anything, it checks that VERSION, app/version.py, and
README.md all currently agree on the same version number. If they don't
(e.g. someone hand-edited one of them), it stops and changes nothing unless
you pass --force, which bumps everything anyway and just warns about the
mismatch.

If any file is missing its version marker entirely, the script always stops
(--force included) -- there's nothing to force a bump into.
"""

import argparse
import datetime
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "VERSION"
VERSION_PY = ROOT / "app" / "version.py"
README = ROOT / "README.md"
CHANGELOG = ROOT / "CHANGELOG.md"

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")

# (path, pattern-with-one-capture-group) for every file whose *current*
# version we check for agreement before bumping.
VERSION_SOURCES = [
    (VERSION_PY, r'__version__ = "([^"]+)"'),
    (README, r"\*\*Version:\*\* (\S+)"),
]


def read_current_version():
    if not VERSION_FILE.exists():
        sys.exit(f"Can't find {VERSION_FILE} -- nothing to bump from.")
    return VERSION_FILE.read_text().strip()


def find_version_in(path, pattern):
    if not path.exists():
        return None
    match = re.search(pattern, path.read_text())
    return match.group(1) if match else None


def check_agreement(baseline_version, force):
    """Compares VERSION_PY and README's current version against VERSION's.
    Missing markers always abort. Mismatches abort unless force=True."""
    missing = []
    mismatched = []
    for path, pattern in VERSION_SOURCES:
        found = find_version_in(path, pattern)
        if found is None:
            missing.append(path)
        elif found != baseline_version:
            mismatched.append((path, found))

    if missing:
        names = "\n".join(f"  {p.relative_to(ROOT)}" for p in missing)
        sys.exit(
            "Could not find the expected version marker in:\n" + names +
            "\n\nStopping without changing anything -- there's nothing there to bump "
            "(--force doesn't help here; the file needs its marker restored first)."
        )

    if mismatched and not force:
        lines = "\n".join(
            f"  {p.relative_to(ROOT)} has {v}, but {VERSION_FILE.name} has {baseline_version}"
            for p, v in mismatched
        )
        sys.exit(
            "These files disagree on the current version:\n" + lines +
            "\n\nFix them by hand, or re-run with --force to bump everything anyway."
        )

    if mismatched and force:
        print("Proceeding despite version mismatches (--force):")
        for p, v in mismatched:
            print(f"  {p.relative_to(ROOT)} had {v}, {VERSION_FILE.name} had {baseline_version}")


def compute_bumped(current, part):
    major, minor, patch = (int(x) for x in current.split("."))
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    if part == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(part)


def replace_or_die(path, pattern, replacement, flags=0):
    text = path.read_text()
    new_text, count = re.subn(pattern, replacement, text, count=1, flags=flags)
    if count == 0:
        sys.exit(f"Could not find the expected version marker in {path}. Stopping without changing anything.")
    path.write_text(new_text)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("version", nargs="?", help="Exact new version, e.g. 0.2.0")
    group.add_argument("--bump", choices=["major", "minor", "patch"], help="Auto-increment from the current version")
    parser.add_argument(
        "--force", action="store_true",
        help="Bump even if VERSION, app/version.py, and README.md don't currently agree",
    )
    args = parser.parse_args()

    current = read_current_version()
    check_agreement(current, args.force)

    if args.bump:
        new_version = compute_bumped(current, args.bump)
    else:
        new_version = args.version
        if not SEMVER_RE.match(new_version):
            sys.exit(f"'{new_version}' doesn't look like a version (expected e.g. 1.2.3).")

    if new_version == current:
        sys.exit(f"Already at {current} -- nothing to do.")

    # VERSION
    VERSION_FILE.write_text(new_version + "\n")

    # app/version.py
    replace_or_die(
        VERSION_PY,
        r'__version__ = "[^"]+"',
        f'__version__ = "{new_version}"',
    )

    # README.md
    replace_or_die(
        README,
        r"\*\*Version:\*\* \S+",
        f"**Version:** {new_version}",
    )

    # CHANGELOG.md: insert a new section right after the "# Changelog" title
    today = datetime.date.today().isoformat()
    changelog_text = CHANGELOG.read_text()
    if "# Changelog" not in changelog_text:
        sys.exit(f"Could not find the '# Changelog' heading in {CHANGELOG}. Stopping without changing anything.")
    new_entry = f"\n## {new_version} - {today}\n- \n"
    changelog_text = changelog_text.replace("# Changelog", "# Changelog" + new_entry, 1)
    CHANGELOG.write_text(changelog_text)

    print(f"Bumped {current} -> {new_version} in:")
    print(f"  {VERSION_FILE.relative_to(ROOT)}")
    print(f"  {VERSION_PY.relative_to(ROOT)}")
    print(f"  {README.relative_to(ROOT)}")
    print(f"  {CHANGELOG.relative_to(ROOT)} (added a blank entry for you to fill in)")


if __name__ == "__main__":
    main()
