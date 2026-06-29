"""Fetch World Cup 2026 yes/no prices for all nations from Polymarket Gamma API."""

import json
from pathlib import Path

import requests


def get_wc26_prices() -> dict[str, dict[str, dict[str, float]]]:
    """Return dict of nations with yes/no prices for each knockout round."""
    base_url = "https://gamma-api.polymarket.com"

    with Path("event_ids.json").open(encoding="utf-8") as f:
        events_ids = json.load(f)

    result = {}
    session = requests.Session()
    session.headers.update({"User-Agent": "wc26-ko-odds/1.0", "Accept": "application/json"})

    for round_name, event_id in events_ids.items():
        response = session.get(f"{base_url}/events", params={"id": event_id}, timeout=30)
        response.raise_for_status()
        event = response.json()[0]
        markets = event["markets"]

        for market in markets:
            if market["active"] is False:
                continue
            team_name = market["groupItemTitle"]
            prices = json.loads(market["outcomePrices"])
            yes_price = float(prices[0])
            no_price = float(prices[1])
            team_name = get_team_name(team_name)
            if team_name is None:
                continue
            if team_name not in result:
                result[team_name] = {}
            result[team_name][round_name] = {"yes": yes_price, "no": no_price}
            if yes_price + no_price > 1:
                print(f"Warning: yes/no prices for {team_name} in {round_name} sum to more than 1: {yes_price + no_price:.4f}")

    session.close()
    result = dict(sorted(result.items()))
    return result


def get_team_name(team: str) -> str | None:
    """Return the official team name from the nations.json mapping."""
    with Path("nations.json").open(encoding="utf-8") as f:
        nations = json.load(f)
    for official_name, aliases in nations.items():
        if team == official_name or team in aliases:
            return official_name
    return None


if __name__ == "__main__":
    prices = get_wc26_prices()
    print("World Cup 2026 Prices:")
    for team, rounds in prices.items():
        for round_name, yes_no in rounds.items():
            print(f"{team:22s} | {round_name:15s} | Yes: {yes_no['yes']:.4f} | No: {yes_no['no']:.4f}")
