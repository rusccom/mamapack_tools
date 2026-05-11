from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = ROOT / "store_reports" / "finance" / "2025-12"
CACHE_PATH = REPORT_DIR / "spis_z_natury_2025-12-31_cache.json"
OUTPUT_PATH = REPORT_DIR / "spis_z_natury_2025-12-31.xlsx"
WARSAW = ZoneInfo("Europe/Warsaw")
WAREHOUSE_KEY = "bl_67231"
STOCK_DAY = "2025-12-31"
AFTER_STOCK_DAY = "2026-01-01"
