"""Daily collector — scrapes NTES and stores results in Turso.

Designed to run as a GitHub Actions cron job.
Usage: python -m src.collector.daily_collector [--train 12301] [--all]
"""

import argparse
import sys
from src.db.database import get_connection
from src.scraper.ntes_client import create_browser, scrape_single_date, scrape_train
from src.db.repositories.daily_run_repo import upsert_daily_run
from src.utils.logger import get_logger
from src.utils.time_utils import now_ist

log = get_logger(__name__)


def collect_train(train_number: str, browser, backfill: bool = False) -> int:
    """Collect data for a single train. Returns number of runs stored."""
    if backfill:
        runs = scrape_train(train_number, browser)
    else:
        run = scrape_single_date(train_number, browser)
        runs = [run] if run else []

    stored = 0
    for run in runs:
        if run and run.stops:
            upsert_daily_run(run)
            log.info(f"{run.train_number} {run.start_date}: {run.status}, {len(run.stops)} stops")
            stored += 1
    return stored


def collect_all(backfill: bool = False):
    """Collect data for all active trains in the database."""
    conn = get_connection()
    rows = conn.execute("SELECT train_number FROM trains WHERE is_active=1").fetchall()
    train_numbers = [r[0] for r in rows]

    if not train_numbers:
        log.warning("No trains in database. Seed train data first.")
        return

    log.info(f"Collecting {len(train_numbers)} trains (backfill={backfill})")
    browser = create_browser()
    total = 0
    errors = 0

    try:
        for tn in train_numbers:
            try:
                total += collect_train(tn, browser, backfill)
            except Exception as e:
                log.error(f"Failed {tn}: {e}")
                errors += 1
    finally:
        browser.close()

    log.info(f"Done: {total} runs stored, {errors} errors")


def main():
    parser = argparse.ArgumentParser(description="Collect train running data from NTES")
    parser.add_argument("--train", help="Single train number to collect")
    parser.add_argument("--all", action="store_true", help="Collect all active trains")
    parser.add_argument("--backfill", action="store_true", help="Store all dates shown (not just latest)")
    args = parser.parse_args()

    if args.train:
        browser = create_browser()
        try:
            n = collect_train(args.train, browser, args.backfill)
            log.info(f"Stored {n} runs for {args.train}")
        finally:
            browser.close()
    elif args.all:
        collect_all(args.backfill)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
