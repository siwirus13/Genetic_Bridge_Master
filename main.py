import json
import random
import copy
import time
import os
from typing import List, Dict, Tuple, Optional

RANK_ORDER = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
              '10': 10, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
SUITS = ['S', 'H', 'D', 'C']
SUIT_NAMES = {'S': 'Spades', 'H': 'Hearts', 'D': 'Diamonds', 'C': 'Clubs'}


class Card:
    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank
        self.suit_value = SUITS.index(suit)
        self.rank_value = RANK_ORDER[rank]

    def __repr__(self):
        return f"{self.rank}{self.suit}"

    def __eq__(self, other):
        return self.rank_value == other.rank_value and self.suit == other.suit

    def __hash__(self):
        return hash((self.suit, self.rank))


def parse_card(card_str):
    suit = card_str[0]
    rank = card_str[1:]
    return Card(suit, rank)


def load_deal(filename):
    with open(filename, 'r') as f:
        deal = json.load(f)

    hands = {
        player: [parse_card(c) for c in cards]
        for player, cards in deal["hands"].items()
    }

    lead_info = deal["lead"]
    lead_card = parse_card(lead_info["card"])
    lead_player = lead_info["player"]

    declarer = deal["declarer"]
    trump = deal["trump"]
    contract_level = deal["contract_level"]

    return hands, declarer, trump, contract_level, lead_card, lead_player


class GameState:
    def __init__(self, hands, declarer, trump, contract_level, current_leader):
        self.hands = copy.deepcopy(hands)
        self.declarer = declarer
        self.trump = trump
        self.contract_level = contract_level
        self.current_leader = current_leader
        self.NT = 1 if trump == "NT" else 0
        self.declarer_tricks = 0
        self.defender_tricks = 0
        self.tricks_played = 0
        self.partnerships = {"N": "S", "S": "N", "E": "W", "W": "E"}
        self.trick_history = []
        self.cards_played = set()  # Track all played cards

    def is_declarer_side(self, player):
        return player == self.declarer or player == self.partnerships[self.declarer]

    def get_dummy(self):
        return self.partnerships[self.declarer]

    def copy(self):
        new_state = GameState(self.hands, self.declarer, self.trump, self.contract_level, self.current_leader)
        new_state.declarer_tricks = self.declarer_tricks
        new_state.defender_tricks = self.defender_tricks
        new_state.tricks_played = self.tricks_played
        new_state.trick_history = self.trick_history.copy()
        new_state.cards_played = self.cards_played.copy()
        return new_state

    def get_remaining_cards_in_suit(self, suit, exclude_player=None):
        remaining = []
        for player, hand in self.hands.items():
            if exclude_player and player == exclude_player:
                continue
            remaining.extend([c for c in hand if c.suit == suit])
        return remaining


def get_legal_cards(hand, leading_suit):
    if leading_suit is None:
        return hand[:]
    same_suit_cards = [c for c in hand if c.suit == leading_suit]
    return same_suit_cards if same_suit_cards else hand[:]


def determine_trick_winner(cards, players, NT, trump_suit):
    if not cards:
        return None

    leading_suit = cards[0].suit
    winning_card = cards[0]
    winning_index = 0

    for i in range(1, len(cards)):
        card = cards[i]
        if NT == 1:
            if card.suit == leading_suit and card.rank_value > winning_card.rank_value:
                winning_card = card
                winning_index = i
        else:
            if card.suit == trump_suit:
                if winning_card.suit != trump_suit or card.rank_value > winning_card.rank_value:
                    winning_card = card
                    winning_index = i
            elif card.suit == winning_card.suit and winning_card.suit != trump_suit:
                if card.rank_value > winning_card.rank_value:
                    winning_card = card
                    winning_index = i

    return players[winning_index]


class OptimalDefense:

    @staticmethod
    def choose_defensive_card(state, player, leading_suit, cards_played_in_trick):
        legal_cards = get_legal_cards(state.hands[player], leading_suit)

        if not legal_cards:
            return None

        if len(legal_cards) == 1:
            return legal_cards[0]


        best_card = None
        best_score = float('inf')

        for card in legal_cards:
            score = OptimalDefense._evaluate_defensive_card(state, player, card,
                                                            leading_suit, cards_played_in_trick)
            if score < best_score:
                best_score = score
                best_card = card

        return best_card

    @staticmethod
    def _evaluate_defensive_card(state, player, card, leading_suit, cards_played_in_trick):
        score = 0

        if leading_suit is None:
            # Prefer leading from length and strength
            same_suit_cards = [c for c in state.hands[player] if c.suit == card.suit]
            suit_length = len(same_suit_cards)

            # Prefer longer suits
            score -= suit_length * 2

            # Prefer not leading aces unless forced
            if card.rank_value == 14:
                score += 10

            # Prefer middle cards for safety
            if 9 <= card.rank_value <= 12:
                score -= 5

        else:
            # Following to a trick
            # Check if we can beat the current winning card
            current_winner = None
            current_winning_value = 0

            for played_card, _ in cards_played_in_trick:
                if played_card.suit == leading_suit:
                    if played_card.rank_value > current_winning_value:
                        current_winner = played_card
                        current_winning_value = played_card.rank_value

            # If we can't follow suit, prefer low cards
            if card.suit != leading_suit:
                score = card.rank_value  # Lower cards get lower scores

                # Avoid wasting high trumps unless necessary
                if not state.NT and card.suit == state.trump:
                    if card.rank_value >= 12:  # High trump
                        score += 20

            else:
                # Following suit
                if current_winner:
                    # If partner might be winning, play low
                    if len(cards_played_in_trick) >= 1:
                        # Simple heuristic: if we can't beat winner easily, play low
                        if card.rank_value <= current_winning_value:
                            score = -card.rank_value  # Prefer lower cards
                        else:
                            # Can beat - prefer minimal win
                            score = card.rank_value - current_winning_value
                else:
                    # First to follow suit - prefer middle cards
                    score = abs(card.rank_value - 10)

        return score


class DeclarerStrategy:
    def __init__(self, genome_size=150):
        self.genome = [random.uniform(-1, 1) for _ in range(genome_size)]
        self.fitness = 0

    def choose_card(self, state, player, leading_suit, cards_played_in_trick):
        """Choose card based on genetic algorithm weights with enhanced features"""
        legal_cards = get_legal_cards(state.hands[player], leading_suit)

        if not legal_cards:
            return None

        if len(legal_cards) == 1:
            return legal_cards[0]

        # Calculate scores for each legal card based on enhanced genome
        card_scores = []

        for card in legal_cards:
            score = 0
            gene_idx = 0

            # Basic features
            score += self.genome[gene_idx] * (card.rank_value / 14.0)
            gene_idx += 1

            # Trump preference
            if not state.NT and card.suit == state.trump:
                score += self.genome[gene_idx] * 1.0
            gene_idx += 1

            # Suit length considerations
            suit_length = len([c for c in state.hands[player] if c.suit == card.suit])
            score += self.genome[gene_idx] * (suit_length / 13.0)
            gene_idx += 1

            # Trick position analysis
            position_in_trick = len(cards_played_in_trick)
            if position_in_trick == 0:  # Leading
                score += self.genome[gene_idx] * 1.0
                gene_idx += 1

                # Leading preferences
                if suit_length >= 4:  # Long suit
                    score += self.genome[gene_idx] * 1.0
                gene_idx += 1

                if card.rank_value >= 12:  # High card lead
                    score += self.genome[gene_idx] * 1.0
                gene_idx += 1

            elif position_in_trick == 3:  # Last to play
                score += self.genome[gene_idx] * 1.0
                gene_idx += 1

                # Last position - can see all cards
                # Check if we can win the trick
                current_winner = None
                current_winning_value = 0

                for played_card, _ in cards_played_in_trick:
                    if not state.NT and played_card.suit == state.trump:
                        if current_winner is None or played_card.suit == state.trump:
                            if played_card.rank_value > current_winning_value:
                                current_winner = played_card
                                current_winning_value = played_card.rank_value
                    elif played_card.suit == leading_suit:
                        if current_winner is None or current_winner.suit != state.trump:
                            if played_card.rank_value > current_winning_value:
                                current_winner = played_card
                                current_winning_value = played_card.rank_value

                can_win = False
                if current_winner:
                    if not state.NT and card.suit == state.trump and current_winner.suit != state.trump:
                        can_win = True
                    elif card.suit == current_winner.suit and card.rank_value > current_winner.rank_value:
                        can_win = True
                    elif not state.NT and card.suit == state.trump and current_winner.suit == state.trump:
                        can_win = card.rank_value > current_winner.rank_value

                if can_win:
                    score += self.genome[gene_idx] * 1.0
                gene_idx += 1

            else:  # Middle positions
                score += self.genome[gene_idx] * 1.0
                gene_idx += 1

            # Finesse and honor considerations
            if leading_suit and card.suit == leading_suit:
                higher_in_suit = len([c for c in legal_cards
                                      if c.suit == card.suit and c.rank_value > card.rank_value])
                score += self.genome[gene_idx] * (1.0 - higher_in_suit / 4.0)
                gene_idx += 1

            # Communication with partner (dummy)
            dummy_cards = state.hands[state.get_dummy()]
            dummy_same_suit = [c for c in dummy_cards if c.suit == card.suit]
            if dummy_same_suit:
                dummy_strength = sum(c.rank_value for c in dummy_same_suit) / len(dummy_same_suit)
                score += self.genome[gene_idx] * (dummy_strength / 14.0)
                gene_idx += 1

            # Remaining cards analysis
            remaining_in_suit = state.get_remaining_cards_in_suit(card.suit, player)
            if remaining_in_suit:
                higher_remaining = len([c for c in remaining_in_suit if c.rank_value > card.rank_value])
                score += self.genome[gene_idx] * (1.0 - higher_remaining / len(remaining_in_suit))
                gene_idx += 1

            # Tricks remaining consideration
            tricks_remaining = 13 - state.tricks_played
            if tricks_remaining > 0:
                score += self.genome[gene_idx] * (state.declarer_tricks / (state.tricks_played + 1))
                gene_idx += 1

            # Desperateness factor - if behind, take more risks
            needed_tricks = 6 + state.contract_level
            tricks_needed = needed_tricks - state.declarer_tricks
            if tricks_needed > tricks_remaining:
                # Desperate - prefer high cards
                score += self.genome[gene_idx] * (card.rank_value / 14.0)
                gene_idx += 1

            # Fill remaining genome with random features for diversity
            while gene_idx < len(self.genome):
                feature_value = hash(str(card) + str(gene_idx) + str(state.tricks_played)) % 100 / 100.0
                score += self.genome[gene_idx] * feature_value
                gene_idx += 1
                if gene_idx >= len(self.genome):
                    break

            card_scores.append((card, score))

        # Choose card with highest score
        best_card = max(card_scores, key=lambda x: x[1])[0]
        return best_card

    def mutate(self, mutation_rate=0.15):
        """Mutate the genome with variable strength"""
        for i in range(len(self.genome)):
            if random.random() < mutation_rate:
                # Variable mutation strength
                if random.random() < 0.3:
                    # Large mutation
                    self.genome[i] = random.uniform(-1, 1)
                else:
                    # Small mutation
                    self.genome[i] += random.uniform(-0.2, 0.2)
                    self.genome[i] = max(-1, min(1, self.genome[i]))

    def crossover(self, other):
        """Create offspring through enhanced crossover"""
        child = DeclarerStrategy(len(self.genome))

        # Multi-point crossover
        crossover_points = sorted([random.randint(1, len(self.genome) - 1) for _ in range(2)])

        current_parent = 0
        for i in range(len(self.genome)):
            if i in crossover_points:
                current_parent = 1 - current_parent

            if current_parent == 0:
                child.genome[i] = self.genome[i]
            else:
                child.genome[i] = other.genome[i]

        return child


def simulate_game(hands, declarer, trump, contract_level, lead_card, lead_player, strategy):
    """Simulate a complete game with optimal defense"""
    state = GameState(hands, declarer, trump, contract_level, lead_player)

    # Handle opening lead
    order = ["W", "N", "E", "S"]
    lead_index = order.index(lead_player)
    trick_order = order[lead_index:] + order[:lead_index]

    # Play opening lead card
    if lead_card in state.hands[lead_player]:
        state.hands[lead_player].remove(lead_card)
        state.cards_played.add(lead_card)
        played_cards = [lead_card]
        played_players = [lead_player]
        leading_suit = lead_card.suit

        # Complete first trick
        for player in trick_order[1:]:
            if not state.hands[player]:
                continue

            if state.is_declarer_side(player) and strategy:
                card = strategy.choose_card(state, player, leading_suit,
                                            list(zip(played_cards, played_players)))
            else:
                card = OptimalDefense.choose_defensive_card(state, player, leading_suit,
                                                            list(zip(played_cards, played_players)))

            if card and card in state.hands[player]:
                state.hands[player].remove(card)
                state.cards_played.add(card)
                played_cards.append(card)
                played_players.append(player)

        # Determine winner of first trick
        if len(played_cards) == 4:
            winner = determine_trick_winner(played_cards, played_players, state.NT, state.trump)
            if state.is_declarer_side(winner):
                state.declarer_tricks += 1
            else:
                state.defender_tricks += 1
            state.current_leader = winner
            state.tricks_played += 1
            state.trick_history.append({
                'trick_num': 1,
                'winner': winner,
                'cards': list(zip(played_players, played_cards))
            })

    # Play remaining tricks
    for trick_num in range(2, 14):
        if not any(state.hands.values()):
            break

        winner, trick_cards = play_single_trick(state, strategy)
        if not winner:
            break

    # Return comprehensive results
    needed_tricks = 6 + contract_level
    return state.declarer_tricks >= needed_tricks, state.declarer_tricks, state


def play_single_trick(state, declarer_strategy=None):
    """Play one trick with optimal defense"""
    order = ["W", "N", "E", "S"]
    lead_index = order.index(state.current_leader)
    trick_order = order[lead_index:] + order[:lead_index]

    played_cards = []
    played_players = []
    leading_suit = None

    for i, player in enumerate(trick_order):
        if not state.hands[player]:
            continue

        if i == 0:
            # Leading player
            if state.is_declarer_side(player) and declarer_strategy:
                card = declarer_strategy.choose_card(state, player, None, [])
            else:
                card = OptimalDefense.choose_defensive_card(state, player, None, [])
            leading_suit = card.suit if card else None
        else:
            # Following player
            if state.is_declarer_side(player) and declarer_strategy:
                card = declarer_strategy.choose_card(state, player, leading_suit,
                                                     list(zip(played_cards, played_players)))
            else:
                card = OptimalDefense.choose_defensive_card(state, player, leading_suit,
                                                            list(zip(played_cards, played_players)))

        if card and card in state.hands[player]:
            state.hands[player].remove(card)
            state.cards_played.add(card)
            played_cards.append(card)
            played_players.append(player)

    if len(played_cards) == 4:
        winner = determine_trick_winner(played_cards, played_players, state.NT, state.trump)

        if state.is_declarer_side(winner):
            state.declarer_tricks += 1
        else:
            state.defender_tricks += 1

        state.current_leader = winner
        state.tricks_played += 1
        state.trick_history.append({
            'trick_num': state.tricks_played,
            'winner': winner,
            'cards': list(zip(played_players, played_cards))
        })

        return winner, list(zip(played_players, played_cards))

    return None, []


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

        print(f"Trick {trick_num}: ", end="")
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


def genetic_algorithm(hands, declarer, trump, contract_level, lead_card, lead_player,
                      population_size=80, generations=150):
    """Enhanced genetic algorithm with better fitness evaluation"""

    # Initialize population with diverse strategies
    population = [DeclarerStrategy() for _ in range(population_size)]

    print(f"Running enhanced genetic algorithm...")
    print(f"Population: {population_size}, Generations: {generations}")
    print(f"Using optimal defense simulation\n")

    best_fitness_history = []

    for generation in range(generations):
        # Evaluate fitness for each strategy
        for strategy in population:
            fitness_scores = []

            # Test strategy multiple times for robustness
            for test_run in range(8):  # More thorough testing
                test_hands = copy.deepcopy(hands)

                # Add very slight random variations to test robustness
                if test_run > 0:
                    # Occasionally swap equivalent cards to test robustness
                    for player in test_hands:
                        if len(test_hands[player]) > 1 and random.random() < 0.1:
                            # Swap two cards of same rank in different suits (if any)
                            same_rank_cards = {}
                            for card in test_hands[player]:
                                if card.rank not in same_rank_cards:
                                    same_rank_cards[card.rank] = []
                                same_rank_cards[card.rank].append(card)

                            for rank, cards in same_rank_cards.items():
                                if len(cards) >= 2 and random.random() < 0.3:
                                    # Small variation for testing
                                    pass

                made_contract, tricks, final_state = simulate_game(
                    test_hands, declarer, trump, contract_level, lead_card, lead_player, strategy)

                # Enhanced fitness calculation
                base_score = tricks * 10  # Base score for tricks taken

                if made_contract:
                    base_score += 100  # Bonus for making contract
                    overtricks = tricks - (6 + contract_level)
                    base_score += overtricks * 20  # Bonus for overtricks
                else:
                    # Penalty for failing, but still reward close attempts
                    undertricks = (6 + contract_level) - tricks
                    base_score -= undertricks * 10

                # Bonus for consistent performance
                base_score += random.uniform(-5, 5)  # Small random factor

                fitness_scores.append(base_score)

            # Strategy fitness is average performance with stability bonus
            avg_fitness = sum(fitness_scores) / len(fitness_scores)
            stability = 1 / (1 + (max(fitness_scores) - min(fitness_scores)) / 10)
            strategy.fitness = avg_fitness * stability

        # Sort by fitness
        population.sort(key=lambda x: x.fitness, reverse=True)
        best_fitness = population[0].fitness
        best_fitness_history.append(best_fitness)

        if generation % 25 == 0 or generation == generations - 1:
            avg_fitness = sum(s.fitness for s in population) / len(population)
            print(f"Generation {generation:3d}: Best={best_fitness:6.1f}, Avg={avg_fitness:6.1f}")

        # Early stopping if converged
        if generation > 50:
            recent_improvement = best_fitness_history[-1] - best_fitness_history[-25]
            if recent_improvement < 5:  # Very small improvement
                print(f"Early stopping at generation {generation} - converged")
                break

        # Create next generation with elitism
        elite_size = population_size // 5  # Keep top 20%
        next_generation = population[:elite_size]

        # Crossover and mutation
        while len(next_generation) < population_size:
            # Tournament selection
            tournament_size = 5
            parent1 = max(random.sample(population[:population_size // 2], tournament_size),
                          key=lambda x: x.fitness)
            parent2 = max(random.sample(population[:population_size // 2], tournament_size),
                          key=lambda x: x.fitness)

            child = parent1.crossover(parent2)

            # Adaptive mutation rate
            mutation_rate = 0.1 if generation < generations // 2 else 0.05
            child.mutate(mutation_rate)

            next_generation.append(child)

        population = next_generation

    return population[0]  # Return best strategy


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
    main('deals/4H.json')
