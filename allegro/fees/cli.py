import argparse
import json
from pathlib import Path

from allegro.core.auth import poll_device_token, refresh_token, request_device_grant
from allegro.core.client import AllegroClient
from allegro.core.credentials import load_credentials
from allegro.core.token_store import load_token, save_token

from .billing import fetch_entries
from .converted import summarize_pln
from .currency import currencies, currency_of
from .exchange import rates_to_pln
from .marketplaces import MARKETPLACES
from .period import iso_utc
from .summary import summarize


def main() -> None:
    args = parse_args()
    credentials = load_credentials(Path.cwd())
    token = ensure_token(credentials)
    client = AllegroClient(token["access_token"])
    print(json.dumps(report(client, args), ensure_ascii=False, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="from_date", required=True)
    parser.add_argument("--to", dest="to_date", required=True)
    parser.add_argument("--marketplace", default="")
    parser.add_argument("--all-marketplaces", action="store_true")
    return parser.parse_args()


def ensure_token(credentials) -> dict:
    token = try_refresh(credentials)
    if token:
        return token
    grant = request_device_grant(credentials)
    print(f"AUTH_URL={grant.url}", flush=True)
    print(f"USER_CODE={grant.user_code}", flush=True)
    token = poll_device_token(credentials, grant)
    save_token(token)
    return token


def try_refresh(credentials) -> dict:
    try:
        token = refresh_token(credentials, load_token())
    except Exception:
        return {}
    if token.get("access_token"):
        save_token(token)
        return token
    return {}


def build_report(start: str, end: str, entries: list[dict]) -> dict:
    rate_map = rates_to_pln(currencies(entries), end)
    report = summarize(entries)
    report["period"] = {"from": start, "to": end}
    report["entries"] = len(entries)
    report["currencies"] = currencies(entries)
    report["exchange_rates"] = rate_map
    report["converted_to_pln"] = summarize_pln(entries, rate_map)
    return report


def report(client: AllegroClient, args: argparse.Namespace) -> dict:
    if args.all_marketplaces:
        return all_marketplaces_report(client, args)
    return single_report(client, args, args.marketplace)


def single_report(client: AllegroClient, args: argparse.Namespace, marketplace: str) -> dict:
    start = iso_utc(args.from_date)
    end = iso_utc(args.to_date, True)
    entries = fetch_entries(client, start, end, marketplace)
    report = build_report(args.from_date, args.to_date, entries)
    report["marketplace"] = marketplace or "default"
    return report


def all_marketplaces_report(client: AllegroClient, args: argparse.Namespace) -> dict:
    entries_by_market = {market: fetch_market(client, args, market) for market in MARKETPLACES}
    reports = market_reports(args, entries_by_market)
    entries = sum(entries_by_market.values(), [])
    rate_map = rates_to_pln(currencies(entries), args.to_date)
    return {
        "period": {"from": args.from_date, "to": args.to_date},
        "entries": len(entries),
        "currencies": currencies(entries),
        "exchange_rates": rate_map,
        "converted_to_pln": summarize_pln(entries, rate_map),
        "by_currency": currency_reports(args, entries),
        "marketplaces": reports,
    }


def market_reports(args: argparse.Namespace, entries_by_market: dict[str, list[dict]]) -> dict:
    return {
        market: build_market_report(args, market, entries)
        for market, entries in entries_by_market.items()
    }


def build_market_report(args: argparse.Namespace, market: str, entries: list[dict]) -> dict:
    report = build_report(args.from_date, args.to_date, entries)
    report["marketplace"] = market
    return report


def fetch_market(client: AllegroClient, args: argparse.Namespace, marketplace: str) -> list[dict]:
    start = iso_utc(args.from_date)
    end = iso_utc(args.to_date, True)
    return fetch_entries(client, start, end, marketplace)


def currency_reports(args: argparse.Namespace, entries: list[dict]) -> dict:
    return {
        currency: build_report(args.from_date, args.to_date, filter_currency(entries, currency))
        for currency in currencies(entries)
    }


def filter_currency(entries: list[dict], currency: str) -> list[dict]:
    return [entry for entry in entries if currency_of(entry) == currency]


if __name__ == "__main__":
    main()
