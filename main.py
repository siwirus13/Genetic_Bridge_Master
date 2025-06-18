import time
import copy
from src.Game_Engine import GameState, load_deal
from src.simulation import simulate_game
from src.declarer import genetic_algorithm


def show_detailed_results(state, declarer, contract_level, best_strategy):
    """Display detailed results matching OPL solver format"""
    partnerships = {"N": "S", "S": "N", "E": "W", "W": "E"}

    print("=" * 60)
    print("      GENETIC ALGORITHM BRIDGE SOLVER RESULTS")
    print("=" * 60)
    print(f"Contract: {contract_level}{state.trump} by {declarer}")
    print(f"Opening lead: {state.trick_history[0]['cards'][0][1]} by {state.trick_history[0]['cards'][0][0]}")
    print(f"Needed tricks: {6 + contract_level}")
    print(f"Declarer tricks: {state.declarer_tricks}")
    print()

    # Show detailed trick analysis
    print("Trick-by-trick analysis:")
    print("-" * 40)

    for trick in state.trick_history:
        trick_num = trick['trick_num']
        winner = trick['winner']
        cards = trick['cards']

        print(f"Trick {trick_num:2d}: ", end="")
        for player, card in cards:
            print(f"{player}:{card} ", end="")

        if state.is_declarer_side(winner):
            print("(Declarer side wins)")
        else:
            print("(Defense wins)")

    print("-" * 40)

    needed_tricks = 6 + contract_level
    if state.declarer_tricks >= needed_tricks:
        overtricks = state.declarer_tricks - needed_tricks
        print("✅ CONTRACT MADE!")
        if overtricks > 0:
            print(f"   +{overtricks} overtricks!")
    else:
        undertricks = needed_tricks - state.declarer_tricks
        print("❌ CONTRACT FAILED!")
        print(f"   Down {undertricks} tricks")

    print("=" * 60)

    # Show strategy analysis
    print("\nStrategy Analysis:")
    print(f"Best fitness achieved: {best_strategy.fitness:.2f}")
    print(f"Genome diversity: {len(set(round(g, 2) for g in best_strategy.genome[:20]))}/20 (first 20 genes)")


def main(deal_file):
    """Main function to run the genetic algorithm bridge solver"""
    # Load deal
    hands, declarer, trump, contract_level, lead_card, lead_player = load_deal(deal_file)

    print("=" * 60)
    print("        GENETIC ALGORITHM BRIDGE SOLVER")
    print("=" * 60)
    print(f"Contract: {contract_level}{trump} by {declarer}")
    print(f"Opening lead: {lead_card} by {lead_player}")
    print(f"Declarer needs {6 + contract_level} tricks to make contract")
    print()

    # Show hands
    print("Hands:")
    for p in "NESW":
        cards_display = sorted(hands[p], key=lambda c: (c.suit_value, c.rank_value))
        print(f"{p}: {cards_display}")
    print()

    # Run genetic algorithm
    start_time = time.time()
    best_strategy = genetic_algorithm(hands, declarer, trump, contract_level,
                                      lead_card, lead_player)
    end_time = time.time()

    print(f"\nOptimization completed in {end_time - start_time:.1f} seconds")
    print("Playing final game with best strategy found...\n")

    # Play final game with best strategy
    test_hands = copy.deepcopy(hands)
    made_contract, final_tricks, final_state = simulate_game(
        test_hands, declarer, trump, contract_level, lead_card, lead_player, best_strategy)

    # Show detailed results
    show_detailed_results(final_state, declarer, contract_level, best_strategy)


if __name__ == "__main__":
    main('utils/deals/4H.json')
    main('utils/deals/2NT.json')
    main('utils/deals/3NT.json')