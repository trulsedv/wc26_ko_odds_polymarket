"""
Polymarket Gamma REST API client for World Cup 2026 knockout stage markets.
Fetches yes/no prices for: reach RO16, reach QF, reach SF, reach Final, Winner.
Uses: https://gamma-api.polymarket.com
"""

import requests
from dataclasses import dataclass
from typing import Any


@dataclass
class TeamMarket:
    team: str
    market_type: str
    yes_price: float
    no_price: float
    market_id: str


class PolymarketWC26:
    BASE_URL = "https://gamma-api.polymarket.com"
    EVENT_SLUGS = [
        "world-cup-nation-to-reach-round-of-16",
        "world-cup-nation-to-reach-quarterfinals",
        "world-cup-nation-to-reach-semifinals",
        "world-cup-nation-to-reach-final",
        "world-cup-winner",
    ]

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "wc26-ko-odds-polymarket/1.0", "Accept": "application/json"})

    def _get_event(self, slug: str) -> dict[str, Any] | None:
        """Get event by slug."""
        for limit in [100, 500, 1000]:
            response = self.session.get(f"{self.BASE_URL}/events", params={"limit": limit, "query": slug}, timeout=self.timeout)
            response.raise_for_status()
            for event in response.json():
                if event.get("slug") == slug:
                    return event
        return None

    def _get_markets(self, event_id: str) -> list[dict[str, Any]]:
        """Get markets for event."""
        response = self.session.get(f"{self.BASE_URL}/markets", params={"event_id": event_id, "limit": 500}, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def _slug_to_type(self, slug: str) -> str:
        """Convert slug to market type."""
        if "round-of-16" in slug: return "reach RO16"
        if "quarterfinals" in slug: return "reach QF"
        if "semifinals" in slug: return "reach SF"
        if "final" in slug and "winner" not in slug: return "reach Final"
        if "winner" in slug: return "Winner"
        return "Unknown"

    def _extract_team(self, text: str) -> str:
        """Extract clean team name from text."""
        for word in ["Will", "will", "the", "to", "reach", "round", "of", "16", "quarterfinals", "semifinals", "final", "winner", "world", "cup", "2026", "fifa", "nation", "team", "?"]:
            text = text.replace(word, "").strip()
        return " ".join(text.split()).title()

    def _process_market(self, market: dict[str, Any], market_type: str) -> TeamMarket | None:
        """Process a single market into TeamMarket."""
        question = market.get("question", "")
        outcomes = market.get("outcomes", [])
        prices = market.get("outcomePrices", [])
        
        if len(outcomes) != len(prices):
            return None
            
        # Handle multi-outcome markets (each outcome is a team)
        if len(outcomes) > 2:
            for i, outcome in enumerate(outcomes):
                team_name = self._extract_team(outcome)
                if not team_name:
                    continue
                return TeamMarket(
                    team=team_name,
                    market_type=market_type,
                    yes_price=float(prices[i]),
                    no_price=1.0 - float(prices[i]),
                    market_id=market["id"]
                )
        
        # Handle binary yes/no markets
        elif len(outcomes) == 2:
            outcome_map = {outcomes[i]: float(prices[i]) for i in range(2) if i < len(prices)}
            if "Yes" not in outcome_map or "No" not in outcome_map:
                return None
                
            team_name = self._extract_team(question)
            if not team_name:
                return None
                
            return TeamMarket(
                team=team_name,
                market_type=market_type,
                yes_price=outcome_map["Yes"],
                no_price=outcome_map["No"],
                market_id=market["id"]
            )
        
        return None

    def get_markets_from_events(self) -> dict[str, list[TeamMarket]]:
        """Get markets from the 5 World Cup 2026 events."""
        result = {}
        for slug in self.EVENT_SLUGS:
            event = self._get_event(slug)
            markets = self._get_markets(event["id"]) if event else []
            market_type = self._slug_to_type(slug)
            
            team_markets = []
            for market in markets:
                processed = self._process_market(market, market_type)
                if processed:
                    team_markets.append(processed)
            
            result[slug] = team_markets
        return result

    def get_all_team_markets(self) -> list[TeamMarket]:
        """Get all team markets combined."""
        all_markets = []
        for slug, markets in self.get_markets_from_events().items():
            all_markets.extend(markets)
        return all_markets

    def get_prices_dict(self) -> dict[str, dict[str, dict[str, float]]]:
        """Get prices as nested dict: {market_type: {team: {yes: float, no: float}}}."""
        result = {}
        for market in self.get_all_team_markets():
            if market.market_type not in result:
                result[market.market_type] = {}
            result[market.market_type][market.team] = {"yes": market.yes_price, "no": market.no_price}
        return result

    def close(self):
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# Convenience functions
def get_markets_from_events() -> dict[str, list[TeamMarket]]:
    with PolymarketWC26() as client:
        return client.get_markets_from_events()

def get_all_team_markets() -> list[TeamMarket]:
    with PolymarketWC26() as client:
        return client.get_all_team_markets()

def get_prices_dict() -> dict[str, dict[str, dict[str, float]]]:
    with PolymarketWC26() as client:
        return client.get_prices_dict()


if __name__ == "__main__":
    print("Fetching World Cup 2026 markets from Polymarket Gamma API...")
    
    with PolymarketWC26() as client:
        event_markets = client.get_markets_from_events()
        
        total = 0
        for slug, markets in event_markets.items():
            print(f"{slug}: {len(markets)} markets")
            total += len(markets)
            if markets:
                m = markets[0]
                print(f"  Sample: {m.team} - {m.market_type}: Yes={m.yes_price:.3f}, No={m.no_price:.3f}")
        
        if total == 0:
            print("\nNo markets found. Events may not be in Gamma API yet.")
            print("Check: https://polymarket.com/event/world-cup-nation-to-reach-round-of-16")
