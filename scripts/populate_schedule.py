"""Populate train_schedule table from already-collected daily_stop_times data.

Usage: python -m scripts.populate_schedule
"""

import sys
sys.path.insert(0, ".")
from src.db.database import get_connection
from src.utils.logger import get_logger

log = get_logger(__name__)


def populate():
    conn = get_connection()

    # Get distinct train+station combos from collected data, using the most recent run
    rows = conn.execute(
        """SELECT dst.train_number, dst.station_code, dst.sequence,
                  dst.scheduled_arrival, dst.scheduled_departure, dst.platform_number
           FROM daily_stop_times dst
           INNER JOIN (
               SELECT train_number, station_code, MAX(run_date) as max_date
               FROM daily_stop_times
               GROUP BY train_number, station_code
           ) latest ON dst.train_number = latest.train_number
                    AND dst.station_code = latest.station_code
                    AND dst.run_date = latest.max_date
           ORDER BY dst.train_number, dst.sequence"""
    ).fetchall()

    inserted = 0
    for r in rows:
        train_number, station_code, sequence, sched_arr, sched_dep, platform = r
        conn.execute(
            """INSERT OR REPLACE INTO train_schedule
               (train_number, station_code, sequence, scheduled_arrival, scheduled_departure, platform_default)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (train_number, station_code, sequence, sched_arr, sched_dep, platform),
        )
        inserted += 1

    conn.commit()
    log.info(f"Populated {inserted} schedule entries")

    # Also update station names from daily_stop_times where we have better names
    conn.execute(
        """UPDATE stations SET station_name = (
               SELECT s2.station_name FROM stations s2 WHERE s2.station_code = stations.station_code
           ) WHERE station_name = station_code"""
    )
    conn.commit()


if __name__ == "__main__":
    populate()
