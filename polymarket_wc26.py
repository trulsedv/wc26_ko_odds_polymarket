"""
Polymarket Gamma REST API client for World Cup 2026 knockout stage markets.

Fetches yes/no prices for: reach RO16, reach QF, reach SF, reach Final, Winner.
Uses the official Gamma REST API: https://gamma-api.polymarket.com.

NOTE: As of June 2026, the World Cup 2026 events exist on Polymarket.com but may not be
fully available in the Gamma REST API yet. This client will work when the events
become available in the API.

The events can be accessed at:
- https://polymarket.com/event/world-cup-nation-to-reach-round-of-16
- https://polymarket.com/event/world-cup-nation-to-reach-quarterfinals
- https://polymarket.com/event/world-cup-nation-to-reach-semifinals
- https://polymarket.com/event/world-cup-nation-to-reach-final
- https://polymarket.com/event/world-cup-winner
"""

from typing import Any

import requests
from dataclasses import dataclass


@dataclass
class MarketPrice:
    """Represents a Polymarket outcome price."""

    outcome: str  # "Yes" or "No"
    price: float  # Decimal price (0-1)

    @classmethod
    def from_api_data(cls, outcome: str, price: float) -> "MarketPrice":
        """Create MarketPrice from outcome and price."""

        return cls(outcome=outcome, price=price)


@dataclass
class TeamMarket:
    """Represents a team's market data for a specific knockout stage."""

    team: str
    market_type: str  # "reach RO16", "reach QF", etc.
    yes_price: float
    no_price: float
    market_id: str
    question: str

    @property
    def implied_probability_yes(self) -> float:
        """Calculate implied probability for Yes outcome."""

        return self.yes_price * 100

    @property
    def implied_probability_no(self) -> float:
        """Calculate implied probability for No outcome."""

        return self.no_price * 100


class PolymarketWC26:
    """
    Client for fetching World Cup 2026 knockout stage markets from Polymarket Gamma REST API.

    Usage:
        client = PolymarketWC26()

        # Method 1: Get markets from specific event slugs (most reliable when available)
        event_markets = client.get_markets_from_specific_events()

        # Method 2: Get all team markets automatically
        markets = client.get_all_team_markets()

        # Method 3: Get prices as dictionary
        prices_dict = client.get_prices_dict()

        for market in markets:
            print(f"{market.team} - {market.market_type}: Yes={market.yes_price}, No={market.no_price}")
    """

    BASE_URL = "https://gamma-api.polymarket.com"

    # Target market types for World Cup 2026
    TARGET_MARKET_TYPES: list[str] = [
        "reach RO16",
        "reach QF",
        "reach SF",
        "reach Final",
        "Winner",
    ]

    # Known event slugs for World Cup 2026 (from the URLs provided)
    TARGET_EVENT_SLUGS: list[str] = [
        "world-cup-nation-to-reach-round-of-16",
        "world-cup-nation-to-reach-quarterfinals",
        "world-cup-nation-to-reach-semifinals",
        "world-cup-nation-to-reach-final",
        "world-cup-winner",
    ]

    def __init__(self, timeout: int = 30) -> None:
        """Initialize the PolymarketWC26 client."""

        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "wc26-ko-odds-polymarket/1.0",
            "Accept": "application/json",
        })

    def _get_events(self, limit: int = 200) -> list[dict[str, Any]]:
        """Get events from Gamma API."""

        url = f"{self.BASE_URL}/events"
        params = {
            "limit": limit,
            "active": "true",
        }

        response = self.session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()

        return response.json()

    def _get_event_by_slug(self, slug: str) -> dict[str, Any] | None:
        """Get a specific event by its slug."""

        # First try to get all events and filter
        events = self._get_events(limit=1000)

        for event in events:
            if event.get("slug") == slug:
                return event

        # If not found, try search
        url = f"{self.BASE_URL}/events"
        params = {
            "limit": 50,
            "query": slug,
        }

        response = self.session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        for event in data:
            if event.get("slug") == slug:
                return event

        return None

    def _get_markets_for_event(self, event_id: str) -> list[dict[str, Any]]:
        """Get all markets for a specific event."""

        url = f"{self.BASE_URL}/markets"
        params = {
            "event_id": event_id,
            "limit": 500,
        }

        response = self.session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()

        return response.json()

    def _get_all_markets_from_events(self) -> list[dict[str, Any]]:
        """Get all markets from World Cup 2026 events."""

        all_markets: list[dict[str, Any]] = []

        # Try to get events first and filter for World Cup 2026
        events = self._get_events(limit=1000)

        for event in events:
            title = event.get("title", "").lower()
            slug = event.get("slug", "").lower()

            # Check if this is a World Cup 2026 event
            is_wc_event = False
            if ("world cup" in title or "wc26" in title or "fifa" in title) and "2026" in title:
                is_wc_event = True
            elif any(target_slug in slug for target_slug in self.TARGET_EVENT_SLUGS):
                is_wc_event = True
            elif "world cup" in slug or "wc26" in slug or "fifa" in slug:
                is_wc_event = True

            if is_wc_event:
                markets = self._get_markets_for_event(event["id"])
                all_markets.extend(markets)

        return all_markets

    def _slug_to_market_type(self, slug: str) -> str:
        """Convert event slug to market type."""

        if "round-of-16" in slug:
            return "reach RO16"
        if "quarterfinals" in slug:
            return "reach QF"
        if "semifinals" in slug:
            return "reach SF"
        if "final" in slug and "winner" not in slug:
            return "reach Final"
        if "winner" in slug:
            return "Winner"

        return "Unknown"

    def _match_market_type(self, question: str) -> str | None:
        """Match market question to target market types."""

        question_lower = question.lower()

        # Check for each market type with various phrasings
        if "winner" in question_lower and "world cup" in question_lower:
            return "Winner"
        if "round of 16" in question_lower or "ro16" in question_lower or "reach round of 16" in question_lower:
            return "reach RO16"
        if "quarterfinals" in question_lower or "quarter final" in question_lower or "qf" in question_lower or "reach quarterfinals" in question_lower:
            return "reach QF"
        if "semifinals" in question_lower or "semi final" in question_lower or "sf" in question_lower or "reach semifinals" in question_lower:
            return "reach SF"
        if "final" in question_lower and "winner" not in question_lower:
            return "reach Final"

        # Fallback: check for any of our target types
        for target in self.TARGET_MARKET_TYPES:
            if target.lower() in question_lower:
                return target

        return None

    def _extract_team_name(self, question: str, market_type: str) -> str:
        """Extract team name from market question."""

        question = question.replace(market_type, "").replace("Will", "").replace("will", "")
        question = question.replace("?", "").strip()

        # Remove common prefixes/suffixes for World Cup markets
        for prefix in ["reach the", "reach", "win the", "win", "be", "be the", "to reach", "the"]:
            question = question.replace(prefix, "").strip()

        # Remove World Cup related text
        for wc_text in ["world cup", "2026", "fifa", "nation", "team", "to"]:
            question = question.replace(wc_text, "").strip()

        # Clean up multiple spaces and special characters
        question = question.replace("  ", " ").strip()
        question = " ".join(question.split())  # Remove extra whitespace

        return question.title()

    def _extract_team_name_from_multi_outcome(self, outcome: str) -> str:
        """Extract team name from a multi-outcome market outcome."""

        # Clean up the outcome text
        outcome = outcome.strip()

        # Remove any non-team text
        for text in ["Will", "will", "the", "to", "reach", "round of 16", "quarterfinals", "semifinals", "final", "winner", "world cup", "2026", "fifa"]:
            outcome = outcome.replace(text, "").strip()

        # Clean up
        outcome = " ".join(outcome.split())

        return outcome.title()

    def get_markets_from_specific_events(self) -> dict[str, list[TeamMarket]]:
        """
        Get markets from the specific event slugs provided by the user.

        This is the most reliable method when the events exist in the Gamma API.

        Returns:
            Dictionary with event slugs as keys and list of TeamMarket objects as values.
        """

        result: dict[str, list[TeamMarket]] = {}

        for slug in self.TARGET_EVENT_SLUGS:
            event = self._get_event_by_slug(slug)
            if event:
                markets = self._get_markets_for_event(event["id"])
                team_markets: list[TeamMarket] = []
                market_type = self._slug_to_market_type(slug)

                for market in markets:
                    question = market.get("question", "")
                    outcomes = market.get("outcomes", [])
                    outcome_prices = market.get("outcomePrices", [])

                    # Handle binary yes/no markets
                    if len(outcomes) == 2 and len(outcome_prices) == 2:
                        try:
                            # Handle both ["Yes", "No"] and ["No", "Yes"] orderings
                            if outcomes[0] == "Yes" and outcomes[1] == "No":
                                yes_price = float(outcome_prices[0])
                                no_price = float(outcome_prices[1])
                            elif outcomes[0] == "No" and outcomes[1] == "Yes":
                                yes_price = float(outcome_prices[1])
                                no_price = float(outcome_prices[0])
                            else:
                                # If outcomes are not Yes/No, try to interpret as team names
                                continue

                            team_name = self._extract_team_name(question, market_type)

                            # Skip if team name is empty or too generic
                            if not team_name or len(team_name.split()) < 1:
                                continue

                            team_market = TeamMarket(
                                team=team_name,
                                market_type=market_type,
                                yes_price=yes_price,
                                no_price=no_price,
                                market_id=market["id"],
                                question=question,
                            )
                            team_markets.append(team_market)
                        except (ValueError, IndexError):
                            continue

                    # Handle multi-outcome markets (where each outcome is a team)
                    elif len(outcomes) > 2:
                        # In multi-outcome markets, each outcome represents a team
                        # The price represents the probability of that team reaching the stage
                        for i, outcome in enumerate(outcomes):
                            if i < len(outcome_prices):
                                try:
                                    team_probability = float(outcome_prices[i])
                                    team_name = self._extract_team_name_from_multi_outcome(outcome)

                                    # Skip if team name is empty or too generic
                                    if not team_name or len(team_name.split()) < 1:
                                        continue

                                    # In multi-outcome markets, the probability is the "yes" probability
                                    # The "no" probability is 1 - yes_probability
                                    team_market = TeamMarket(
                                        team=team_name,
                                        market_type=market_type,
                                        yes_price=team_probability,
                                        no_price=1.0 - team_probability,
                                        market_id=market["id"],
                                        question=question,
                                    )
                                    team_markets.append(team_market)
                                except (ValueError, IndexError):
                                    continue

                result[slug] = team_markets
            else:
                result[slug] = []  # Event not found, but include it in results

        return result

    def get_all_team_markets(self) -> list[TeamMarket]:
        """
        Get all team markets for World Cup 2026 knockout stages.

        Returns:
            List of TeamMarket objects with yes/no prices.
        """

        all_markets = self._get_all_markets_from_events()
        team_markets: list[TeamMarket] = []

        for market in all_markets:
            question = market.get("question", "")
            outcomes = market.get("outcomes", [])
            outcome_prices = market.get("outcomePrices", [])

            market_type = self._match_market_type(question)
            if not market_type:
                continue

            # Handle binary yes/no markets
            if len(outcomes) == 2 and len(outcome_prices) == 2:
                # Map outcomes to prices
                outcome_price_map: dict[str, float] = {}
                for i, outcome in enumerate(outcomes):
                    if i < len(outcome_prices):
                        try:
                            price = float(outcome_prices[i])
                            outcome_price_map[outcome] = price
                        except (ValueError, IndexError):
                            continue

                if "Yes" not in outcome_price_map or "No" not in outcome_price_map:
                    continue

                try:
                    team_name = self._extract_team_name(question, market_type)
                    # Skip if team name is empty or too generic
                    if not team_name or len(team_name.split()) < 1:
                        continue

                    team_market = TeamMarket(
                        team=team_name,
                        market_type=market_type,
                        yes_price=outcome_price_map["Yes"],
                        no_price=outcome_price_map["No"],
                        market_id=market["id"],
                        question=question,
                    )
                    team_markets.append(team_market)
                except Exception:
                    # Skip markets with invalid data
                    continue

            # Handle multi-outcome markets (where each outcome is a team)
            elif len(outcomes) > 2:
                # In multi-outcome markets, each outcome represents a team
                for i, outcome in enumerate(outcomes):
                    if i < len(outcome_prices):
                        try:
                            team_probability = float(outcome_prices[i])
                            team_name = self._extract_team_name_from_multi_outcome(outcome)

                            # Skip if team name is empty or too generic
                            if not team_name or len(team_name.split()) < 1:
                                continue

                            # In multi-outcome markets, the probability is the "yes" probability
                            team_market = TeamMarket(
                                team=team_name,
                                market_type=market_type,
                                yes_price=team_probability,
                                no_price=1.0 - team_probability,
                                market_id=market["id"],
                                question=question,
                            )
                            team_markets.append(team_market)
                        except (ValueError, IndexError):
                            continue

        return team_markets

    def get_markets_by_type(self, market_type: str) -> list[TeamMarket]:
        """
        Get markets for a specific knockout stage type.

        Args:
            market_type: One of "reach RO16", "reach QF", "reach SF", "reach Final", "Winner"

        Returns:
            List of TeamMarket objects for the specified type.
        """

        if market_type not in self.TARGET_MARKET_TYPES:
            raise ValueError(f"Invalid market type. Must be one of: {self.TARGET_MARKET_TYPES}")

        all_markets = self.get_all_team_markets()

        return [m for m in all_markets if m.market_type == market_type]

    def get_team_markets(self, team: str) -> list[TeamMarket]:
        """
        Get all knockout stage markets for a specific team.

        Args:
            team: Team name (case insensitive)

        Returns:
            List of TeamMarket objects for the specified team.
        """

        all_markets = self.get_all_team_markets()

        return [m for m in all_markets if m.team.lower() == team.lower()]

    def get_prices_dict(self) -> dict[str, dict[str, dict[str, float]]]:
        """
        Get all prices as a nested dictionary.

        Returns:
            Dict structured as:
            {
                "reach RO16": {
                    "Team1": {"yes": 0.45, "no": 0.55},
                    "Team2": {"yes": 0.60, "no": 0.40},
                    ...
                },
                "reach QF": { ... },
                ...
            }
        """

        all_markets = self.get_all_team_markets()
        result: dict[str, dict[str, dict[str, float]]] = {}

        for market in all_markets:
            if market.market_type not in result:
                result[market.market_type] = {}

            result[market.market_type][market.team] = {
                "yes": market.yes_price,
                "no": market.no_price,
            }

        return result

    def close(self) -> None:
        """Close the HTTP session."""

        self.session.close()

    def __enter__(self) -> "PolymarketWC26":
        """Enter context manager."""

        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager."""

        self.close()


def get_wc26_markets() -> list[TeamMarket]:
    """
    Convenience function to get all World Cup 2026 knockout markets.

    Returns:
        List of TeamMarket objects.
    """

    client = PolymarketWC26()
    try:
        return client.get_all_team_markets()
    finally:
        client.close()


def get_prices_by_market_type(market_type: str) -> dict[str, dict[str, float]]:
    """
    Convenience function to get prices for a specific market type.

    Args:
        market_type: One of the TARGET_MARKET_TYPES

    Returns:
        Dictionary of team names to their yes/no prices.
    """

    client = PolymarketWC26()
    try:
        prices_dict = client.get_prices_dict()
        return prices_dict.get(market_type, {})
    finally:
        client.close()


def get_markets_from_events() -> dict[str, list[TeamMarket]]:
    """
    Convenience function to get markets from specific World Cup 2026 events.

    This is the most reliable method when the events exist in the Gamma API.

    Returns:
        Dictionary with event slugs as keys and list of TeamMarket objects as values.
    """

    client = PolymarketWC26()
    try:
        return client.get_markets_from_specific_events()
    finally:
        client.close()


# Example usage
if __name__ == "__main__":
    print("Fetching World Cup 2026 markets from Polymarket Gamma API...")
    print("NOTE: The World Cup 2026 events may not be available in the Gamma API yet.")
    print("They exist on Polymarket.com but might not be indexed in the API.")
    print("This client will work automatically when they become available.\n")

    try:
        client = PolymarketWC26()

        # Try the specific events approach first (most reliable)
        print("Trying specific event slugs...")
        event_markets = client.get_markets_from_specific_events()
        print(f"Events checked: {list(event_markets.keys())}")

        total_markets = 0
        for event_slug, markets_list in event_markets.items():
            print(f"  {event_slug}: {len(markets_list)} markets")
            total_markets += len(markets_list)
            if markets_list:
                print(f"    Sample: {markets_list[0].team} - {markets_list[0].market_type}: Yes={markets_list[0].yes_price:.4f}, No={markets_list[0].no_price:.4f}")

        if total_markets == 0:
            print("\nNo markets found from specific events. Trying general search...")
            # Get all markets
            markets = client.get_all_team_markets()
            print(f"Found {len(markets)} markets from general search")

            # Print first 10
            for market in markets[:10]:
                print(f"  {market.team:20s} | {market.market_type:15s} | Yes: {market.yes_price:.3f} | No: {market.no_price:.3f}")

        # Get as dictionary
        prices = client.get_prices_dict()
        print(f"\nMarket types found: {list(prices.keys())}")

        # Print summary
        for market_type, teams in prices.items():
            print(f"  {market_type}: {len(teams)} teams")
            # Show first 3 teams for each type
            for team_name, prices_dict in list(teams.items())[:3]:
                print(f"    {team_name}: Yes={prices_dict['yes']:.3f}, No={prices_dict['no']:.3f}")

        client.close()

        if total_markets == 0 and len(prices) == 0:
            print("\n" + "=" * 60)
            print("NO DATA AVAILABLE YET")
            print("=" * 60)
            print("The World Cup 2026 events exist on Polymarket.com but are not yet")
            print("available in the Gamma REST API. This is normal for very new events.")
            print("\nThe client is ready and will work automatically when the events")
            print("become available in the API.")
            print("\nYou can check the events manually at:")
            for slug in client.TARGET_EVENT_SLUGS:
                print(f"  https://polymarket.com/event/{slug}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
