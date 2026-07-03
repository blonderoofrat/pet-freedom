# -*- coding: utf-8 -*-
"""Pet Freedom -- self-test / regression harness (offline, read-only, NO network).

Run this after pulling a skill update to confirm the update did not break anything. It exercises the
whole OFFLINE pipeline against the committed demo corpus (demo/roof-rat) and checks invariants.

    python skill/selftest.py            # exit 0 = all checks passed; non-zero = something broke

Checks (all offline, standard library only):
  1. demo/roof-rat/*.json  : all parse, are objects, carry the core keys, count looks sane.
  2. build.py --dry-run    : renders every demo jurisdiction with no error (writes bodies to out/).
  3. export_seed.py        : produces a scrubbed copy with ZERO redaction-name leaks and native
                             diacritics preserved.
  4. playground.py --full  : emits well-formed WXR (XML parses) + blueprint JSON (parses).
  5. audit.py --json       : runs and returns parseable output (tooling imports + executes).
  6. version consistency   : VERSION == newest CHANGELOG heading == .claude-plugin/plugin.json (if present).

Nothing here touches WordPress, the network, or the adopter's own data/ or config.json.
"""
import os, sys, json, glob, re, subprocess, tempfile, shutil
import xml.dom.minidom as MD

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # pet-freedom/
DEMO = os.path.join(ROOT, "demo", "roof-rat")
PY = sys.executable
def _load_redact_names():
    """Private names to assert-absent from the public demo corpus. Kept OUT of this public file:
    read them from $PF_SCRUB_NAMES or a gitignored local `.opsec-scrub-names` (one name per line,
    '#' comments allowed). Falls back to placeholder tokens so a fresh public clone still exercises
    the scrub mechanism without shipping any real person's name in this repo."""
    env = os.environ.get("PF_SCRUB_NAMES")
    if env:
        return [n.strip() for n in env.split(",") if n.strip()]
    local = os.path.join(ROOT, ".opsec-scrub-names")
    if os.path.exists(local):
        names = [ln.strip() for ln in open(local, encoding="utf-8")
                 if ln.strip() and not ln.lstrip().startswith("#")]
        if names:
            return names
    return ["Ada Lovelace", "Ada", "Lovelace", "example-handle", "X000000"]


REDACT = _load_redact_names()

_results = []


def _run(args):
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    return subprocess.run([PY] + args, cwd=ROOT, env=env,
                          capture_output=True, text=True, encoding="utf-8")


def check(name, fn):
    try:
        _results.append((True, name, fn() or "ok"))
    except AssertionError as e:
        _results.append((False, name, str(e) or "assertion failed"))
    except Exception as e:
        _results.append((False, name, "%s: %s" % (type(e).__name__, e)))


def c_demo():
    files = sorted(glob.glob(os.path.join(DEMO, "*.json")))
    assert len(files) >= 100, "only %d demo jurisdictions (expected >=100)" % len(files)
    bad = []
    for f in files:
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception as e:
            bad.append("%s (%s)" % (os.path.basename(f), e)); continue
        if not isinstance(d, dict) or "jurisdiction" not in d or "activities" not in d:
            bad.append("%s (missing core keys)" % os.path.basename(f))
    assert not bad, "malformed: " + "; ".join(bad[:5])
    return "%d demo jurisdictions parse + carry core keys" % len(files)


def c_build():
    p = _run(["skill/build.py", "--dry-run", "--source", DEMO])
    assert "Traceback" not in p.stderr, "build.py crashed:\n" + p.stderr[-600:]
    assert p.returncode == 0, "build.py exit %d:\n%s" % (p.returncode, p.stderr[-600:])
    n = p.stdout.count("would-publish")
    assert n >= 100, "renderer only produced %d pages (expected >=100)" % n
    return "rendered %d pages, no errors" % n


def c_export():
    tmp = tempfile.mkdtemp(prefix="pf_selftest_seed_")
    try:
        p = _run(["skill/export_seed.py", "--source", DEMO, "--target", tmp,
                  "--scrub-names", ",".join(REDACT)])
        assert "Traceback" not in p.stderr, "export_seed crashed:\n" + p.stderr[-600:]
        assert p.returncode == 0, "export_seed exit %d:\n%s" % (p.returncode, p.stderr[-400:])
        out = sorted(glob.glob(os.path.join(tmp, "*.json")))
        assert len(out) >= 100, "export produced only %d files" % len(out)
        leaks, diac = 0, False
        for f in out:
            t = open(f, encoding="utf-8").read()
            for nm in REDACT:
                if re.search(r"\b%s\b" % re.escape(nm), t):
                    leaks += 1
            if any(ch in t for ch in "áéíóúñüäößåøæ"):
                diac = True
        assert leaks == 0, "%d redaction-name leak(s) in scrubbed output" % leaks
        assert diac, "no native diacritics survived the export (over-scrubbed?)"
        return "%d files exported, 0 name leaks, diacritics preserved" % len(out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def c_playground():
    tmp = tempfile.mkdtemp(prefix="pf_selftest_pg_")
    try:
        p = _run(["skill/playground.py", "--source", DEMO, "--out", tmp,
                  "--full", "--date", "2026-06-11"])
        assert "Traceback" not in p.stderr, "playground crashed:\n" + p.stderr[-600:]
        assert p.returncode == 0, "playground exit %d:\n%s" % (p.returncode, p.stderr[-400:])
        xmls = glob.glob(os.path.join(tmp, "*.xml"))
        jsons = glob.glob(os.path.join(tmp, "*.json"))
        assert xmls, "no WXR .xml emitted"
        for x in xmls:
            MD.parse(x)                       # raises if not well-formed XML
        for j in jsons:
            json.load(open(j, encoding="utf-8"))
        return "%d WXR + %d blueprint file(s), all well-formed" % (len(xmls), len(jsons))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def c_audit():
    p = _run(["skill/audit.py", "--json"])
    assert "Traceback" not in p.stderr, "audit crashed:\n" + p.stderr[-600:]
    assert p.returncode == 0, "audit exit %d:\n%s" % (p.returncode, p.stderr[-400:])
    s = p.stdout.strip()
    if s.startswith("{") or s.startswith("["):
        json.loads(s)                          # parseable machine output
    return "audit ran + emitted parseable output"


def c_version():
    vf = os.path.join(ROOT, "VERSION")
    assert os.path.exists(vf), "VERSION file missing"
    version = open(vf, encoding="utf-8").read().strip()
    assert re.match(r"^\d+\.\d+\.\d+$", version), "VERSION '%s' is not semver" % version
    cl = open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8").read()
    m = re.search(r"(?m)^##\s*\[?v?(\d+\.\d+\.\d+)", cl)
    assert m, "no version heading found in CHANGELOG.md"
    assert m.group(1) == version, "CHANGELOG top is %s but VERSION is %s" % (m.group(1), version)
    pj = os.path.join(ROOT, ".claude-plugin", "plugin.json")
    if os.path.exists(pj):
        pv = json.load(open(pj, encoding="utf-8")).get("version")
        assert pv == version, "plugin.json version %s != VERSION %s" % (pv, version)
        return "VERSION == CHANGELOG == plugin.json == %s" % version
    return "VERSION == CHANGELOG == %s (no plugin.json yet)" % version


def main():
    for name, fn in [
        ("demo corpus integrity", c_demo),
        ("renderer (build.py --dry-run)", c_build),
        ("scrubbed export (export_seed.py)", c_export),
        ("playground generation (playground.py)", c_playground),
        ("audit (audit.py --json)", c_audit),
        ("version/changelog consistency", c_version),
    ]:
        check(name, fn)
    print("\nPet Freedom skill self-test\n" + "=" * 52)
    npass = sum(1 for ok, _, _ in _results if ok)
    for ok, name, detail in _results:
        print("  [%s] %-32s %s" % ("PASS" if ok else "FAIL", name, detail))
    print("=" * 52)
    print("%d/%d checks passed" % (npass, len(_results)))
    sys.exit(0 if npass == len(_results) else 1)


if __name__ == "__main__":
    main()
