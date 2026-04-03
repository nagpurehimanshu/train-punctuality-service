"""Seed initial train data from erail.in.

Usage: python -m scripts.seed_data --trains 12301,12302,12951,12952
       python -m scripts.seed_data --popular  (seeds top ~50 popular trains)
"""

import argparse
import sys
import time
import httpx

sys.path.insert(0, ".")
from src.db.database import init_db, get_connection
from src.utils.time_utils import now_ist
from src.utils.logger import get_logger

log = get_logger(__name__)

# Top popular long-distance trains to seed
POPULAR_TRAINS = [
    "12301", "12302",  # Howrah Rajdhani
    "12305", "12306",  # Howrah Rajdhani (via Patna)
    "12951", "12952",  # Mumbai Rajdhani
    "12953", "12954",  # August Kranti Rajdhani
    "12259", "12260",  # Sealdah Duronto
    "12627", "12628",  # Karnataka Express
    "12621", "12622",  # Tamil Nadu Express
    "12723", "12724",  # Telangana Express
    "12839", "12840",  # Chennai Mail
    "12561", "12562",  # Swatantrata Senani Express
    "12309", "12310",  # Rajdhani (Patna)
    "12313", "12314",  # Sealdah Rajdhani
    "12001", "12002",  # Bhopal Shatabdi
    "12003", "12004",  # Lucknow Shatabdi
    "12005", "12006",  # Kalka Shatabdi
    "12049", "12050",  # Gatimaan Express
    "12269", "12270",  # Chennai Duronto
    "12213", "12214",  # Delhi Sarai Rohilla Duronto
    "12245", "12246",  # Howrah Duronto
    "12559", "12560",  # Shiv Ganga Express
    "12801", "12802",  # Purushottam Express
    "12381", "12382",  # Poorva Express
    "12303", "12304",  # Poorva Express (via Gaya)
    "22691", "22692",  # Rajdhani (Bangalore)
]


def fetch_train_info(train_number: str) -> dict | None:
    """Fetch train metadata from erail.in."""
    try:
        r = httpx.get(
            f"https://erail.in/rail/getTrains.aspx?TrainNo={train_number}&DataSource=0&Language=0",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15,
        )
        if r.status_code != 200 or not r.text or r.text.startswith("<"):
            return None

        # Parse tilde-delimited format
        # Format: ~~~...^TRAIN_NO~TRAIN_NAME~ORIGIN_NAME~ORIGIN_CODE~DEST_NAME~DEST_CODE~...~RUN_DAYS_BITMAP~...~TRAIN_TYPE~...
        parts = r.text.split("~")
        if len(parts) < 20:
            return None

        # Find the train data after the ^ marker
        train_idx = None
        for i, p in enumerate(parts):
            if p.startswith("^") or (p and p[0].isdigit() and len(p) == 5):
                train_idx = i
                break

        if train_idx is None:
            # Try finding by train number
            for i, p in enumerate(parts):
                if p.strip("^") == train_number:
                    train_idx = i
                    break

        if train_idx is None:
            return None

        tn = parts[train_idx].strip("^")
        return {
            "train_number": tn,
            "train_name": parts[train_idx + 1] if len(parts) > train_idx + 1 else "",
            "origin_name": parts[train_idx + 2] if len(parts) > train_idx + 2 else "",
            "origin_code": parts[train_idx + 3] if len(parts) > train_idx + 3 else "",
            "dest_name": parts[train_idx + 4] if len(parts) > train_idx + 4 else "",
            "dest_code": parts[train_idx + 5] if len(parts) > train_idx + 5 else "",
        }
    except Exception as e:
        log.error(f"Failed to fetch {train_number}: {e}")
        return None


def seed_train(train_number: str) -> bool:
    info = fetch_train_info(train_number)
    if not info:
        log.warning(f"Could not fetch info for {train_number}")
        return False

    conn = get_connection()
    conn.execute(
        """INSERT OR IGNORE INTO trains
           (train_number, train_name, origin_code, destination_code, run_days, updated_at)
           VALUES (?, ?, ?, ?, '["Daily"]', ?)""",
        (info["train_number"], info["train_name"], info["origin_code"], info["dest_code"], now_ist().isoformat()),
    )

    # Auto-create origin and destination stations
    for code, name in [(info["origin_code"], info["origin_name"]), (info["dest_code"], info["dest_name"])]:
        if code:
            conn.execute(
                "INSERT OR IGNORE INTO stations (station_code, station_name, updated_at) VALUES (?, ?, ?)",
                (code, name, now_ist().isoformat()),
            )

    conn.commit()
    log.info(f"Seeded {info['train_number']} {info['train_name']} ({info['origin_code']}→{info['dest_code']})")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trains", help="Comma-separated train numbers")
    parser.add_argument("--popular", action="store_true", help="Seed popular trains")
    args = parser.parse_args()

    init_db()

    trains = []
    if args.popular:
        trains = POPULAR_TRAINS
    elif args.trains:
        trains = [t.strip() for t in args.trains.split(",")]
    else:
        parser.print_help()
        sys.exit(1)

    success = 0
    for tn in trains:
        if seed_train(tn):
            success += 1
        time.sleep(1)  # rate limit

    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) FROM trains").fetchone()[0]
    log.info(f"Done: {success}/{len(trains)} seeded. Total trains in DB: {total}")


if __name__ == "__main__":
    main()
