# -*- coding: utf-8 -*-
"""Pet Freedom -- check for and apply skill updates.

Architecture A (Brian, 2026-06-13): the user clones this repo into their own project; Claude checks
GitHub and pulls updates with their consent. The user's config.json + data/ are gitignored, so a pull
never touches them. Consent is TIERED: apply a non-breaking update (PATCH/MINOR) once the self-test
passes; pause for a MAJOR (breaking) update.

  python skill/update.py                 # CHECK ONLY: installed vs latest + changelog delta + tier
  python skill/update.py --apply         # apply a PATCH/MINOR update: git pull + selftest, roll back on fail
  python skill/update.py --apply --yes   # also allow a MAJOR (breaking) update without prompting

This is the ONE tool that touches the network (to read the latest VERSION + CHANGELOG from GitHub). It
never publishes to WordPress and never touches the user's data/ or config.json.
"""
import os, sys, re, subprocess, argparse
import urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # pet-freedom/
RAW = "https://raw.githubusercontent.com/blonderoofrat/pet-freedom/%s/%s"
REFS = ("main", "master")   # try these branch names in order


def parse_semver(s):
    m = re.match(r"\s*v?(\d+)\.(\d+)\.(\d+)", s or "")
    if not m:
        raise ValueError("not a semver: %r" % s)
    return tuple(int(x) for x in m.groups())


def cmp_semver(a, b):
    a, b = parse_semver(a), parse_semver(b)
    return (a > b) - (a < b)


def classify_bump(frm, to):
    a, b = parse_semver(frm), parse_semver(to)
    if b[0] != a[0]:
        return "major"
    if b[1] != a[1]:
        return "minor"
    return "patch"


def changelog_delta(changelog, installed, latest):
    """Return the CHANGELOG sections newer than `installed`, up to and including `latest`."""
    parts = re.split(r"(?m)^(##\s+\[?v?\d+\.\d+\.\d+.*)$", changelog or "")
    out = []
    for i in range(1, len(parts), 2):
        heading = parts[i]
        body = parts[i + 1] if i + 1 < len(parts) else ""
        m = re.search(r"(\d+\.\d+\.\d+)", heading)
        if not m:
            continue
        ver = m.group(1)
        try:
            if cmp_semver(ver, installed) > 0 and cmp_semver(ver, latest) <= 0:
                out.append(heading.strip() + "\n" + body.rstrip())
        except ValueError:
            continue
    return "\n\n".join(out).strip()


def read_local_version():
    return open(os.path.join(ROOT, "VERSION"), encoding="utf-8").read().strip()


def fetch(path):
    """Fetch a repo file from GitHub raw, trying known branch names. Returns text or raises."""
    last = None
    for ref in REFS:
        try:
            with urllib.request.urlopen(RAW % (ref, path), timeout=15) as resp:
                return resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            last = e
            if e.code == 404:
                continue
            raise
        except urllib.error.URLError as e:
            last = e
            break
    raise last or RuntimeError("could not fetch %s" % path)


def _git(args):
    return subprocess.run(["git", "-C", ROOT] + args, capture_output=True, text=True, encoding="utf-8")


def is_git_clone():
    return _git(["rev-parse", "--is-inside-work-tree"]).returncode == 0


def check():
    installed = read_local_version()
    try:
        latest = fetch("VERSION").strip()
        changelog = fetch("CHANGELOG.md")
    except Exception as e:
        print("Could not read the latest version from GitHub (%s). You are on %s." % (e, installed))
        return {"ok": False, "reason": "unreachable", "installed": installed}
    if cmp_semver(latest, installed) <= 0:
        print("Up to date (installed %s, latest %s)." % (installed, latest))
        return {"ok": True, "update": False, "installed": installed, "latest": latest}
    bump = classify_bump(installed, latest)
    delta = changelog_delta(changelog, installed, latest)
    print("UPDATE AVAILABLE: %s -> %s  (%s)\n" % (installed, latest, bump.upper()))
    print(delta or "(no changelog detail found)")
    if bump == "major":
        print("\nThis is a MAJOR (possibly breaking) update. Apply with: python skill/update.py --apply --yes")
    else:
        print("\nNon-breaking. Apply with: python skill/update.py --apply")
    return {"ok": True, "update": True, "installed": installed, "latest": latest, "bump": bump}


def apply(allow_major=False):
    if not is_git_clone():
        print("This install is not a git clone, so I can't pull. Re-download the latest from "
              "https://github.com/blonderoofrat/pet-freedom and replace the skill files "
              "(your config.json + data/ are separate and safe).")
        return 2
    st = check()
    if not st.get("ok") or not st.get("update"):
        return 0
    if st["bump"] == "major" and not allow_major:
        print("\nHeld back: MAJOR (breaking) update. Re-run with --yes after reviewing the changes above.")
        return 3
    prev = _git(["rev-parse", "HEAD"]).stdout.strip()
    print("\nPulling...")
    pull = _git(["pull", "--ff-only"])
    if pull.returncode != 0:
        print("git pull failed (local changes to tracked files?). Nothing changed.\n" + (pull.stderr or pull.stdout))
        return 4
    print("Running self-test...")
    test = subprocess.run([sys.executable, os.path.join(ROOT, "skill", "selftest.py")],
                          capture_output=True, text=True, encoding="utf-8")
    sys.stdout.write((test.stdout or "")[-1500:])
    if test.returncode != 0:
        print("\nSelf-test FAILED after update. Rolling back to %s." % prev[:8])
        _git(["reset", "--hard", prev])
        print("Rolled back. The update was not kept. Please report this.")
        return 5
    print("\nUpdated to %s. Self-test passed. (Re-run skill/build.py to apply any renderer "
          "changes to your live site.)" % read_local_version())
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Check for and apply Pet Freedom skill updates (git-clone install).")
    ap.add_argument("--apply", action="store_true", help="apply the update (default: check only)")
    ap.add_argument("--yes", action="store_true", help="allow a MAJOR (breaking) update without prompting")
    a = ap.parse_args(argv)
    if a.apply:
        sys.exit(apply(allow_major=a.yes))
    check()


if __name__ == "__main__":
    main()
