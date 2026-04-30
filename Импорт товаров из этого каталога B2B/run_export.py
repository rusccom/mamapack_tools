import argparse
from pathlib import Path

from b2b_client import collect_variants
from shopify_export import write_csv


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--search", default="")
    return parser.parse_args()


def resolve_search_text(args):
    if args.search.strip():
        return args.search.strip()
    value = input("Что искать в B2B: ").strip()
    if value:
        return value
    raise SystemExit("Поисковая строка не указана.")


def main():
    args = parse_args()
    search_text = resolve_search_text(args)
    base_dir = Path(__file__).resolve().parent
    variants = collect_variants(search_text)
    target, products_count, rows_count = write_csv(base_dir, search_text, variants)
    print(f"Search: {search_text}")
    print(f"Products: {products_count}")
    print(f"Rows: {rows_count}")
    print(f"File: {target}")


if __name__ == "__main__":
    main()
