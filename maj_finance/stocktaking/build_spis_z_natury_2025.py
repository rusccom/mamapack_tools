from .data import collect_data
from .settings import OUTPUT_PATH, REPORT_DIR
from .workbook import write_workbook


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (rows, audit), suppliers = collect_data()
    write_workbook(rows, audit, suppliers)
    print(f"output={OUTPUT_PATH}")
    print(f"rows={len(rows)} total_value={audit['total_value']}")


if __name__ == "__main__":
    main()
