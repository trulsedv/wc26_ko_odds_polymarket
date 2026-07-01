"""Print the World Cup 2026 knockout round bracket with probabilities from Polymarket."""
import json
from math import log10
from pathlib import Path

from polymarket_wc26 import get_wc26_prices


def main() -> None:
    """Print the World Cup 2026 knockout round bracket with probabilities from Polymarket."""
    prices = get_wc26_prices()

    with Path("src/bracket.json").open(encoding="utf-8") as f:
        bracket = json.load(f)

    for round_name, round_matches in bracket["bracket"].items():
        print(f"{round_name}:")
        adv_round_name = bracket["advancement"][round_name]
        for match_name, match in round_matches.items():
            team_a = match["Team A"]
            team_b = match["Team B"]
            team_a_prob = get_team_prob(team_a, adv_round_name, prices)
            team_b_prob = get_team_prob(team_b, adv_round_name, prices)
            rating_diff = calc_rating_diff(team_a_prob) if team_a_prob is not None and team_b_prob is not None else "      "
            team_a_prob_str = get_prob_str(team_a_prob)
            team_b_prob_str = get_prob_str(team_b_prob)
            if "Winner" in match:
                winner = match["Winner"]
                if winner == team_a:
                    print(f"  {match_name:8s}: \033[95m{team_a:22s}\033[0m vs {team_b:22s}")
                    print(12 * " " + f"{team_a_prob_str} %" + 19 * " " + f"{team_b_prob_str} %" + f" ({rating_diff})")
                elif winner == team_b:
                    print(f"  {match_name:8s}: {team_a:22s} vs \033[95m{team_b:22s}\033[0m")
                    print(12 * " " + f"{team_a_prob_str} %" + 19 * " " + f"{team_b_prob_str} %" + f" ({rating_diff})")
            else:
                print(f"  {match_name:8s}: {team_a:22s} vs {team_b:22s}")
                print(12 * " " + f"{team_a_prob_str} %" + 19 * " " + f"{team_b_prob_str} %" + f" ({rating_diff})")


def get_team_prob(team: str, round_name: str, prices: dict) -> float | None:
    """Return the probability of a team winning a given round."""
    if team in prices:
        if round_name in prices[team]:
            return prices[team][round_name]["yes"]
        return 0.0
    return None


def get_prob_str(prob: float | None) -> str:
    """Return a string representation of a probability."""
    if prob is None:
        return "-    "
    return f"{100 * prob:5.1f}"


def calc_rating_diff(prob: float) -> str:
    """Return the rating difference between two teams given their probabilities."""
    if prob <= 0 or prob >= 1:
        return "      "
    return f"{-400 * log10(1 / prob - 1):6.1f}"


if __name__ == "__main__":
    main()
