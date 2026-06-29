"""
Fetch World Cup 2026 yes/no prices from Polymarket Gamma API.
Returns: {"Brazil": {"Round of 16": {"yes": 0.6287, "no": 0.3713}}, ...}
"""

import requests


def get_wc26_prices() -> dict[str, dict[str, dict[str, float]]]:
    """Return dict of nations with yes/no prices for each knockout round."""
    
    BASE_URL = "https://gamma-api.polymarket.com"
    
    # Mapping of event slugs to display names
    ROUNDS = {
        "world-cup-nation-to-reach-round-of-16": "Round of 16",
        "world-cup-nation-to-reach-quarterfinals": "Quarterfinals",
        "world-cup-nation-to-reach-semifinals": "Semifinals",
        "world-cup-nation-to-reach-final": "Final",
        "world-cup-winner": "Winner"
    }
    
    result = {}
    session = requests.Session()
    session.headers.update({"User-Agent": "wc26-ko-odds/1.0", "Accept": "application/json"})
    
    for slug, round_name in ROUNDS.items():
        # Get event by slug
        response = session.get(f"{BASE_URL}/events", params={"limit": 100, "query": slug}, timeout=30)
        response.raise_for_status()
        event = next((e for e in response.json() if e.get("slug") == slug), None)
        
        if not event:
            continue
            
        # Get markets for this event
        response = session.get(f"{BASE_URL}/markets", params={"event_id": event["id"], "limit": 500}, timeout=30)
        response.raise_for_status()
        markets = response.json()
        
        # Process each market
        for market in markets:
            outcomes = market.get("outcomes", [])
            prices = market.get("outcomePrices", [])
            question = market.get("question", "")
            
            if len(outcomes) != len(prices):
                continue
                
            # Extract team name
            team_name = _clean_team_name(question if len(outcomes) == 2 else outcomes[0] if outcomes else "")
            if not team_name:
                continue
            
            # Get yes/no prices
            if len(outcomes) > 2:  # Multi-outcome: each outcome is a team
                for i, outcome in enumerate(outcomes):
                    clean_name = _clean_team_name(outcome)
                    if clean_name:
                        yes_price = float(prices[i])
                        no_price = 1.0 - yes_price
                        if clean_name not in result:
                            result[clean_name] = {}
                        result[clean_name][round_name] = {"yes": yes_price, "no": no_price}
                        break
            elif len(outcomes) == 2:  # Binary yes/no market
                outcome_map = {outcomes[i]: float(prices[i]) for i in range(2)}
                yes_price = outcome_map.get("Yes", 0.0)
                no_price = outcome_map.get("No", 0.0)
                if team_name not in result:
                    result[team_name] = {}
                result[team_name][round_name] = {"yes": yes_price, "no": no_price}
    
    session.close()
    return result


def _clean_team_name(text: str) -> str | None:
    """Extract clean team name from text."""
    if not text or not isinstance(text, str):
        return None
        
    text = text.strip()
    # Remove common prefixes/suffixes
    for word in ["Will", "will", "the", "to", "reach", "round", "of", "16", "quarterfinals", 
                 "semifinals", "final", "winner", "world", "cup", "2026", "fifa", "nation", 
                 "team", "?", ":", "-", "|", "  "]:
        text = text.replace(word, " ").strip()
    
    # Clean up and title case
    text = " ".join(text.split())
    return text.title() if text and len(text.split()) <= 3 and len(text) < 50 else None


if __name__ == "__main__":
    prices = get_wc26_prices()
    
    if prices:
        print("World Cup 2026 Prices:")
        for team, rounds in prices.items():
            for round_name, yes_no in rounds.items():
                print(f"{team:15s} | {round_name:15s} | Yes: {yes_no['yes']:.4f} | No: {yes_no['no']:.4f}")
    else:
        print("No data available. Events may not be in Gamma API yet.")
        print("Check: https://polymarket.com/event/world-cup-nation-to-reach-round-of-16")
