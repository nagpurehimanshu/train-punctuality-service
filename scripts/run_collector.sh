#!/bin/bash
cd "$(dirname "$0")/.."
source .venv/bin/activate
python3 -m src.collector.daily_collector --all 2>&1 | tee -a data/collector.log
