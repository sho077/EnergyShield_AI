#!/usr/bin/env python3
"""Validate the source registry.

Dataset: data/reference/source_registry.csv
Read-only: this script never modifies the source CSV.

The registry is the index that makes every other dataset traceable, so the
check that matters most is COVERAGE IN BOTH DIRECTIONS:

* every reference dataset on disk must appear in the registry, and
* every dataset_file the registry names must actually exist.

Either gap breaks traceability. A dataset with no registry entry is
untraceable; a registry entry pointing at nothing is a broken promise.

It also verifies that every source_url actually used by a reference dataset is
registered, so a source cannot be used without being declared.

Exit codes: 0 PASS, 1 critical FAIL, 2 dataset unreadable.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _common as c  # noqa: E402

DATASET = "source registry"

EXPECTED_COLUMNS = [
    "source_id", "dataset_name", "dataset_file", "source_name", "authority_level",
    "source_url", "data_type", "update_frequency", "retrieval_method",
    "last_checked", "notes",
]

REQUIRED_COLUMNS = EXPECTED_COLUMNS  # everything here is mandatory

AUTHORITY_LEVELS = {
    "official_india", "official_international", "authoritative_public",
    "commercial", "secondary",
}

# Reference datasets that must each have at least one registry entry.
EXPECTED_DATASET_FILES = {
    "data/reference/refineries.csv",
    "data/reference/strategic_reserves.csv",
    "data/reference/ports.csv",
    "data/reference/suppliers.csv",
    "data/reference/crude_grades.csv",
    "data/reference/chokepoints.csv",
    "data/reference/routes.csv",
    "data/reference/route_nodes.csv",
    "data/reference/sanctions.csv",
    "data/reference/energy_prices_reference.csv",
    # Added in Phase 2 step 1 (network link layer).
    "data/reference/network_links.csv",
    "data/reference/pipelines.csv",
}

# The registry does not register itself; that would be circular.
SELF = "data/reference/source_registry.csv"


def registered_files(rows):
    files = set()
    for row in rows:
        for part in (row.get("dataset_file") or "").split(";"):
            part = part.strip()
            if part:
                files.add(part)
    return files


def check_coverage(rep, rows, repo_root):
    rep.section("L. DATASET COVERAGE (registry <-> disk)")
    registered = registered_files(rows)

    missing = sorted(EXPECTED_DATASET_FILES - registered)
    if missing:
        rep.fail("Reference dataset(s) with NO registry entry -- untraceable: "
                 "{}".format(missing))
    else:
        rep.ok("All {} reference datasets have at least one registry entry".format(
            len(EXPECTED_DATASET_FILES)))

    broken = sorted(f for f in registered
                    if not f.startswith("docs/") and not (repo_root / f).is_file())
    if broken:
        rep.fail("Registry entry(ies) naming a file that does not exist: {}".format(broken))
    else:
        rep.ok("Every dataset_file named by the registry exists on disk")

    on_disk = {"data/reference/" + p.name
               for p in (repo_root / "data" / "reference").glob("*.csv")}
    unregistered = sorted(on_disk - registered - {SELF})
    if unregistered:
        rep.fail("Reference CSV(s) present on disk but absent from the registry: "
                 "{}".format(unregistered))
    else:
        rep.ok("No reference CSV on disk is missing from the registry")

    rep.metric("datasets_registered", len(registered))


def check_source_urls_registered(rep, rows, repo_root):
    """A source used by a dataset but never declared here is untraceable."""
    rep.section("M. SOURCE URL COVERAGE")
    registered_urls = {(r.get("source_url") or "").strip() for r in rows}
    # Registry notes legitimately mention companion URLs; count those too.
    notes_blob = " ".join((r.get("notes") or "") for r in rows)

    unregistered = {}
    reference_dir = repo_root / "data" / "reference"
    for path in sorted(reference_dir.glob("*.csv")):
        if "data/reference/" + path.name == SELF:
            continue
        try:
            header, data_rows, _ = c.load_rows(path)
        except (OSError, UnicodeDecodeError, ValueError):
            continue
        url_columns = [h for h in header if h.endswith("source_url")]
        for row in data_rows:
            for col in url_columns:
                url = (row.get(col) or "").strip()
                if not url:
                    continue
                if url in registered_urls or url in notes_blob:
                    continue
                unregistered.setdefault(path.name, set()).add(url)

    if unregistered:
        rep.fail("source_url(s) used by a dataset but not declared in the registry: "
                 "{}".format({k: sorted(v) for k, v in unregistered.items()}))
    else:
        rep.ok("Every source_url used by a reference dataset is declared in the registry")


def check_authority_levels(rep, rows):
    rep.section("N. AUTHORITY LEVELS")
    bad = ["{}: {!r}".format(r["source_id"], r.get("authority_level"))
           for r in rows
           if (r.get("authority_level") or "").strip() not in AUTHORITY_LEVELS]
    if bad:
        rep.fail("authority_level value(s) outside {}: {}".format(
            sorted(AUTHORITY_LEVELS), bad))
    else:
        rep.ok("Every authority_level is one of the five defined levels")

    from collections import Counter
    counts = Counter((r.get("authority_level") or "").strip() for r in rows)
    for level in sorted(AUTHORITY_LEVELS):
        rep.info("{:<24} {} source(s)".format(level, counts.get(level, 0)))

    commercial = [r["source_id"] for r in rows
                  if (r.get("authority_level") or "").strip() == "commercial"]
    if commercial:
        rep.warn("Commercial source(s) registered: {} -- confirm each is used only "
                 "where no official source exists".format(commercial))
    else:
        rep.ok("No source is registered at 'commercial' level")

    secondary = [r["source_id"] for r in rows
                 if (r.get("authority_level") or "").strip() == "secondary"]
    if secondary:
        rep.info("{} source(s) at 'secondary' level -- this project's own modelling, "
                 "not external evidence: {}".format(len(secondary), secondary))


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    default_csv = c.REFERENCE_DIR / "source_registry.csv"
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--csv", type=Path, default=default_csv)
    args = parser.parse_args()

    repo_root = c.REFERENCE_DIR.parent.parent

    if not args.csv.is_file():
        print("  [ERROR] Dataset not found: {}".format(args.csv))
        return 2
    try:
        header, rows, ragged = c.load_rows(args.csv)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        print("  [ERROR] Could not read dataset: {}".format(exc))
        return 2

    c.banner(DATASET, args.csv, len(rows))
    rep = c.Report(DATASET)
    rep.metric("row_count", len(rows))

    if not c.check_schema(rep, header, ragged, EXPECTED_COLUMNS):
        rep.section("SUMMARY")
        print("  Schema is broken; per-field checks were skipped.")
        return 1

    c.check_unique_id(rep, rows, "source_id", r"^SRC\d{3}$")
    c.check_required(rep, rows, REQUIRED_COLUMNS)
    c.check_provenance(rep, rows, date_columns=("last_checked",),
                       require_https=False,
                       provenance_columns=["source_name", "source_url", "last_checked"])
    c.check_whitespace(rep, rows, header)

    check_coverage(rep, rows, repo_root)
    check_source_urls_registered(rep, rows, repo_root)
    check_authority_levels(rep, rows)

    return rep.finish()


if __name__ == "__main__":
    sys.exit(main())
