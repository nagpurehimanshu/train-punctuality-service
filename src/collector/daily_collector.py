"""Daily collector — scrapes NTES and stores results in Turso.

Designed to run as a GitHub Actions cron job with parallel shards.
Usage:
  python -m src.collector.daily_collector --all
  python -m src.collector.daily_collector --all --shard 0 --total-shards 3
  python -m src.collector.daily_collector --train 12301
"""

import argparse
import sys
import time
from src.db.database import get_connection
from src.scraper.ntes_client import create_browser, scrape_single_date, scrape_train
from src.db.repositories.daily_run_repo import upsert_daily_run
from src.utils.logger import get_logger
from src.utils.time_utils import now_ist

log = get_logger(__name__)

MAX_RETRIES = 2
RETRY_DELAYS = [10, 30]


def collect_train(train_number: str, browser, backfill: bool = False) -> int:
    """Collect data for a single train with retry on transient errors."""
    for attempt in range(MAX_RETRIES + 1):
        try:
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
        except Exception as e:
            if attempt < MAX_RETRIES and ("SOCKS" in str(e) or "net::" in str(e) or "Timeout" in str(e)):
                log.warning(f"{train_number} attempt {attempt + 1} failed: {e}, retrying in {RETRY_DELAYS[attempt]}s")
                time.sleep(RETRY_DELAYS[attempt])
            else:
                raise


def collect_all(backfill: bool = False, shard: int | None = None, total_shards: int | None = None):
    """Collect data for trains running today, optionally limited to a shard."""
    import json

    conn = get_connection()
    today_name = now_ist().strftime("%a")  # Mon, Tue, ...

    rows = conn.execute(
        "SELECT train_number, run_days FROM trains WHERE is_active=1 ORDER BY train_number"
    ).fetchall()

    train_numbers = []
    for r in rows:
        rd = json.loads(r[1])
        if "Daily" in rd or today_name in rd:
            train_numbers.append(r[0])

    if not train_numbers:
        log.warning("No trains scheduled for today.")
        return

    if shard is not None and total_shards is not None:
        train_numbers = [t for i, t in enumerate(train_numbers) if i % total_shards == shard]
        log.info(f"Shard {shard}/{total_shards}: {len(train_numbers)} trains for {today_name} (backfill={backfill})")
    else:
        log.info(f"Collecting {len(train_numbers)} trains for {today_name} (backfill={backfill})")

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
    parser.add_argument("--shard", type=int, help="Shard index (0-based)")
    parser.add_argument("--total-shards", type=int, help="Total number of shards")
    args = parser.parse_args()

    if args.train:
        browser = create_browser()
        try:
            n = collect_train(args.train, browser, args.backfill)
            log.info(f"Stored {n} runs for {args.train}")
        finally:
            browser.close()
    elif args.all:
        collect_all(args.backfill, args.shard, args.total_shards)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
