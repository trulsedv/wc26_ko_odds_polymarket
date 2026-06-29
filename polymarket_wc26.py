"""
Polymarket API client for World Cup 2026 knockout stage markets.
Fetches yes/no prices for: reach RO16, reach QF, reach SF, reach Final, Winner
"""

import requests
from typing import List, Dict, Optional, Any
from dataclasses import dataclass


@dataclass
class MarketPrice:
    """Represents a Polymarket outcome price."""
    outcome: str  # "Yes" or "No"
    price: float  # Decimal price (0-1)
    
    @classmethod
    def from_api_data(cls, data: Dict[str, Any], outcome_key: str) -> "MarketPrice":
        """Create MarketPrice from Polymarket API data."""
        price = float(data.get(outcome_key, {}).get("price", 0))
        return cls(outcome=outcome_key, price=price)


@dataclass 
class TeamMarket:
    """Represents a team's market data for a specific knockout stage."""
    team: str
    market_type: str  # "reach RO16", "reach QF", etc.
    yes_price: float
    no_price: float
    market_id: str
    
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
    Client for fetching World Cup 2026 knockout stage markets from Polymarket.
    
    Usage:
        client = PolymarketWC26()
        markets = client.get_all_team_markets()
        for market in markets:
            print(f"{market.team} - {market.market_type}: Yes={market.yes_price}, No={market.no_price}")
    """
    
    BASE_URL = "https://pm-api.inhouse.polymarket.com/api/v1"
    
    # Target market types for World Cup 2026
    TARGET_MARKET_TYPES = [
        "reach RO16",
        "reach QF", 
        "reach SF",
        "reach Final",
        "Winner"
    ]
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "wc26-ko-odds-polymarket/1.0",
            "Accept": "application/json"
        })
    
    def _query_graphql(self, query: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a GraphQL query against Polymarket API."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
            
        response = self.session.post(
            f"{self.BASE_URL}/graphql",
            json=payload,
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()
    
    def _get_events(self) -> List[Dict[str, Any]]:
        """Get World Cup 2026 events from Polymarket."""
        query = """
        query GetEvents {
            events(
                first: 50,
                filter: { categorySlug: "sports", subcategorySlug: "soccer" }
            ) {
                edges {
                    node {
                        id
                        slug
                        name
                        startDate
                        conditions {
                            id
                            condition
                        }
                    }
                }
            }
        }
        """
        result = self._query_graphql(query)
        events = []
        
        for edge in result.get("data", {}).get("events", {}).get("edges", []):
            node = edge.get("node", {})
            name = node.get("name", "").lower()
            # Filter for World Cup 2026
            if "2026" in name and ("world cup" in name or "wc26" in name or "fifa" in name):
                events.append(node)
        
        return events
    
    def _get_markets_for_event(self, event_id: str) -> List[Dict[str, Any]]:
        """Get all markets for a specific event."""
        query = """
        query GetMarkets($eventId: String!) {
            markets(
                first: 100,
                filter: { eventId: $eventId }
            ) {
                edges {
                    node {
                        id
                        slug
                        question
                        event { id }
                        outcomes {
                            id
                            outcome
                            price
                            probability
                        }
                    }
                }
            }
        }
        """
        result = self._query_graphql(query, {"eventId": event_id})
        markets = []
        
        for edge in result.get("data", {}).get("markets", {}).get("edges", []):
            node = edge.get("node", {})
            if node:
                markets.append(node)
        
        return markets
    
    def _get_all_markets(self) -> List[Dict[str, Any]]:
        """Get all World Cup 2026 markets."""
        events = self._get_events()
        all_markets = []
        
        for event in events:
            markets = self._get_markets_for_event(event["id"])
            all_markets.extend(markets)
        
        return all_markets
    
    def _match_market_type(self, question: str) -> Optional[str]:
        """Match market question to target market types."""
        question_lower = question.lower()
        
        for target in self.TARGET_MARKET_TYPES:
            if target.lower() in question_lower:
                # Special handling for "Winner" to avoid false positives
                if target.lower() == "winner" and "winner" in question_lower:
                    return target
                return target
        
        return None
    
    def _extract_team_name(self, question: str, market_type: str) -> str:
        """Extract team name from market question."""
        question = question.replace(market_type, "").replace("Will", "").replace("will", "")
        question = question.replace("?", "").strip()
        
        # Remove common prefixes/suffixes
        for prefix in ["reach the", "reach", "win the", "win", "be", "be the"]:
            question = question.replace(prefix, "").strip()
        
        # Clean up
        question = question.replace("  ", " ").strip()
        return question.title()
    
    def get_all_team_markets(self) -> List[TeamMarket]:
        """
        Get all team markets for World Cup 2026 knockout stages.
        
        Returns:
            List of TeamMarket objects with yes/no prices.
        """
        all_markets = self._get_all_markets()
        team_markets = []
        
        for market in all_markets:
            question = market.get("question", "")
            outcomes = market.get("outcomes", [])
            
            market_type = self._match_market_type(question)
            if not market_type:
                continue
            
            # Skip if outcomes don't have Yes/No
            outcome_map = {o["outcome"]: float(o.get("price", 0)) for o in outcomes}
            
            if "Yes" not in outcome_map or "No" not in outcome_map:
                continue
            
            try:
                team_name = self._extract_team_name(question, market_type)
                team_market = TeamMarket(
                    team=team_name,
                    market_type=market_type,
                    yes_price=outcome_map["Yes"],
                    no_price=outcome_map["No"],
                    market_id=market["id"]
                )
                team_markets.append(team_market)
            except Exception:
                # Skip markets with invalid data
                continue
        
        return team_markets
    
    def get_markets_by_type(self, market_type: str) -> List[TeamMarket]:
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
    
    def get_team_markets(self, team: str) -> List[TeamMarket]:
        """
        Get all knockout stage markets for a specific team.
        
        Args:
            team: Team name (case insensitive)
            
        Returns:
            List of TeamMarket objects for the specified team.
        """
        all_markets = self.get_all_team_markets()
        return [m for m in all_markets if m.team.lower() == team.lower()]
    
    def get_prices_dict(self) -> Dict[str, Dict[str, Dict[str, float]]]:
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
        result = {}
        
        for market in all_markets:
            if market.market_type not in result:
                result[market.market_type] = {}
            
            result[market.market_type][market.team] = {
                "yes": market.yes_price,
                "no": market.no_price
            }
        
        return result
    
    def close(self):
        """Close the HTTP session."""
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def get_wc26_markets() -> List[TeamMarket]:
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


def get_prices_by_market_type(market_type: str) -> Dict[str, Dict[str, float]]:
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


# Example usage
if __name__ == "__main__":
    print("Fetching World Cup 2026 markets from Polymarket...")
    
    try:
        client = PolymarketWC26()
        
        # Get all markets
        markets = client.get_all_team_markets()
        print(f"\nFound {len(markets)} markets")
        
        # Print first 10
        for market in markets[:10]:
            print(f"{market.team:20s} | {market.market_type:15s} | Yes: {market.yes_price:.3f} | No: {market.no_price:.3f}")
        
        # Get as dictionary
        prices = client.get_prices_dict()
        print(f"\nMarket types found: {list(prices.keys())}")
        
        client.close()
        
    except Exception as e:
        print(f"Error: {e}")
