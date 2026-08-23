#!/usr/bin/env python3
"""Run every Phase 1 validator and return one overall PASS/FAIL.

Usage, from anywhere:

    python data/validation/validate_phase1.py            # full output
    python data/validation/validate_phase1.py --quiet    # summary table only

Each validator is run as a SEPARATE PROCESS rather than imported, so one
validator crashing cannot take the suite down or contaminate another's state,
and each keeps its own documented exit-code contract:

    0  PASS   -- all critical checks passed (warnings may still be present)
    1  FAIL   -- at least one critical check failed
    2  ERROR  -- the dataset could not be read at all

The suite exits 0 only if every validator exits 0.

It also verifies that the pre-existing, independently validated refinery
dataset is byte-for-byte unchanged, by comparing its SHA-256 against the digest
recorded when this suite was written. That check is advisory: a legitimate
sourced refresh of PPAC data will change the digest, and the operator is
expected to re-verify and update REFINERY_SHA256 deliberately rather than
having the suite silently accept a change.
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

VALIDATION_DIR = Path(__file__).resolve().parent
REPO_ROOT = VALIDATION_DIR.parent.parent

# Ordered so that foundational datasets are validated before the datasets whose
# referential integrity depends on them.
VALIDATORS = [
    ("refineries", "validate_refineries.py"),
    ("strategic_reserves", "validate_strategic_reserves.py"),
    ("ports", "validate_ports.py"),
    ("crude_grades", "validate_crude_grades.py"),
    ("suppliers", "validate_suppliers.py"),
    ("chokepoints", "validate_chokepoints.py"),
    ("routes", "validate_routes.py"),
    ("sanctions", "validate_sanctions.py"),
    ("energy_prices_reference", "validate_energy_prices_reference.py"),
    ("source_registry", "validate_source_registry.py"),
]

REFINERY_CSV = REPO_ROOT / "data" / "reference" / "refineries.csv"
REFINERY_SHA256 = "42478cc981477214b56fa462348a867007b31748e2c1c48315f84a3097199dee"

EXIT_MEANING = {0: "PASS", 1: "FAIL", 2: "ERROR"}


def sha256_of(path):
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_refinery_untouched(quiet):
    """Advisory integrity check on the pre-existing refinery dataset."""
    print()
    print("=" * 72)
    print("PRE-EXISTING DATASET INTEGRITY")
    print("=" * 72)

    if not REFINERY_CSV.is_file():
        print("  [FAIL]  refineries.csv is missing")
        return False

    actual = sha256_of(REFINERY_CSV)
    print("  refineries.csv sha256 : {}".format(actual))

    if REFINERY_SHA256 and actual == REFINERY_SHA256:
        print("  [PASS]  Byte-for-byte identical to the recorded baseline")
    elif REFINERY_SHA256:
        print("  [WARN]  Digest differs from the recorded baseline")
        print("          recorded: {}".format(REFINERY_SHA256))
        print("          If this was a deliberate, sourced PPAC refresh, re-verify the")
        print("          totals and update REFINERY_SHA256 in this file. If it was not,")
        print("          restore the file from version control.")
    else:
        print("  [INFO]  No baseline digest recorded; nothing to compare against")

    # The content check below is the one that actually matters, and it is run by
    # validate_refineries.py itself. This is only a tamper hint.
    return True


def run_one(name, script, quiet):
    path = VALIDATION_DIR / script
    if not path.is_file():
        print("\n  [ERROR] Validator not found: {}".format(path))
        return name, 2, ""

    if not quiet:
        print()
        print("#" * 72)
        print("# {}".format(name))
        print("#" * 72)

    result = subprocess.run(
        [sys.executable, str(path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    output = (result.stdout or "") + (result.stderr or "")
    if not quiet:
        print(output.rstrip())
    return name, result.returncode, output


def summarise(output):
    """Pull the warning/failure counts out of a validator's own summary block."""
    warnings = failures = "?"
    for line in output.splitlines():
        # Case-insensitive so this reads both the shared Report format
        # ("warnings : 1") and validate_refineries.py's own older layout
        # ("Warnings              : 5").
        stripped = line.strip().lower()
        if ":" not in stripped:
            continue
        label, _, tail = stripped.partition(":")
        tail = tail.strip()
        # Only a bare count counts. Both validators also print a "Warnings
        # (non-blocking):" heading that ends in a colon with no number, and
        # that must not overwrite the real tally.
        if not tail.isdigit():
            continue
        label = label.strip()
        if label.startswith("warnings"):
            warnings = tail
        elif label.startswith(("critical failures", "critical_failures")):
            failures = tail
    return failures, warnings


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    parser = argparse.ArgumentParser(
        description="Run every Phase 1 validator and return one overall PASS/FAIL.")
    parser.add_argument("--quiet", action="store_true",
                        help="print only the summary table")
    args = parser.parse_args()

    print("=" * 72)
    print("EnergyShield-AI :: PHASE 1 VALIDATION SUITE")
    print("=" * 72)
    print("Repository : {}".format(REPO_ROOT))
    print("Validators : {}".format(len(VALIDATORS)))
    print("Mode       : read-only (no source file is modified)")

    check_refinery_untouched(args.quiet)

    results = [run_one(name, script, args.quiet) for name, script in VALIDATORS]

    print()
    print("=" * 72)
    print("PHASE 1 SUMMARY")
    print("=" * 72)
    print("  {:<28} {:>6}  {:>8}  {:>8}".format("dataset", "result", "critical", "warnings"))
    print("  " + "-" * 56)

    failed = []
    for name, code, output in results:
        verdict = EXIT_MEANING.get(code, "EXIT {}".format(code))
        critical, warnings = summarise(output)
        print("  {:<28} {:>6}  {:>8}  {:>8}".format(name, verdict, critical, warnings))
        if code != 0:
            failed.append((name, verdict))

    print()
    print("  validators run    : {}".format(len(results)))
    print("  validators passed : {}".format(len(results) - len(failed)))
    print("  validators failed : {}".format(len(failed)))

    if failed:
        print()
        for name, verdict in failed:
            print("    - {} : {}".format(name, verdict))
        print()
        print("  PHASE 1 RESULT: FAIL")
        return 1

    print()
    print("  PHASE 1 RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
