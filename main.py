import json
import random
import copy
import time
import os
from typing import List, Dict, Tuple, Optional

# Global constants (moved to top)
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
        self.trick_history = []  # Store who won each trick

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
        return new_state


def get_legal_cards(hand, leading_suit):
    if leading_suit is None:
        return hand[:]
    same_suit_cards = [c for c in hand if c.suit == leading_suit]
    return same_suit_cards if same_suit_cards else hand[:]


def has_sequence(cards, min_length=3):
    """Check if cards contain a sequence of min_length or more"""
    if len(cards) < min_length:
        return False

    sorted_cards = sorted(cards, key=lambda c: c.rank_value)
    sequence_length = 1

    for i in range(1, len(sorted_cards)):
        if sorted_cards[i].rank_value == sorted_cards[i - 1].rank_value + 1:
            sequence_length += 1
            if sequence_length >= min_length:
                return True
        else:
            sequence_length = 1

    return False


def get_sequence_high(cards):
    """Get highest card from the longest sequence"""
    sorted_cards = sorted(cards, key=lambda c: c.rank_value)
    best_sequence = []
    current_sequence = [sorted_cards[0]]

    for i in range(1, len(sorted_cards)):
        if sorted_cards[i].rank_value == sorted_cards[i - 1].rank_value + 1:
            current_sequence.append(sorted_cards[i])
        else:
            if len(current_sequence) > len(best_sequence):
                best_sequence = current_sequence[:]
            current_sequence = [sorted_cards[i]]

    if len(current_sequence) > len(best_sequence):
        best_sequence = current_sequence[:]

    return max(best_sequence, key=lambda c: c.rank_value) if best_sequence else sorted_cards[-1]


def defensive_card_choice(hand, leading_suit, dummy_hand, cards_played_in_trick, trump, NT):
    """Advanced defensive strategy"""
    legal_cards = get_legal_cards(hand, leading_suit)

    if not legal_cards:
        return None

    # If leading
    if leading_suit is None:
        # Lead from sequence if available
        for suit in SUITS:
            suit_cards = [c for c in legal_cards if c.suit == suit]
            if len(suit_cards) >= 3 and has_sequence(suit_cards):
                return get_sequence_high(suit_cards)

        # Otherwise lead 3rd highest or lowest
        sorted_cards = sorted(legal_cards, key=lambda c: c.rank_value, reverse=True)
        if len(sorted_cards) >= 3:
            return sorted_cards[2]  # 3rd highest
        elif len(sorted_cards) == 2:
            return sorted_cards[1]  # lowest of 2
        else:
            return sorted_cards[0]  # only card

    # Following to a trick - analyze dummy and cards played
    suit_cards = [c for c in legal_cards if c.suit == leading_suit]
    if not suit_cards:
        # Can't follow suit - play lowest card
        return min(legal_cards, key=lambda c: c.rank_value)

    # Get dummy cards in this suit
    dummy_suit_cards = [c for c in dummy_hand if c.suit == leading_suit]

    # Find current winning card
    current_winner = None
    current_winning_value = 0

    for card, player in cards_played_in_trick:
        if hasattr(card, 'suit') and card.suit == leading_suit:
            if card.rank_value > current_winning_value:
                current_winner = card
                current_winning_value = card.rank_value

    # Sort our cards by rank
    sorted_suit_cards = sorted(suit_cards, key=lambda c: c.rank_value)

    # If we can't beat the current winner, play lowest
    if current_winner and all(c.rank_value <= current_winner.rank_value for c in suit_cards):
        return sorted_suit_cards[0]

    # If we're last to play and partner is winning, play lowest
    if len(cards_played_in_trick) == 2 and current_winner:
        # Check if partner might be winning (simplified logic)
        return sorted_suit_cards[0]

    # Try to win economically
    winning_cards = [c for c in suit_cards if c.rank_value > current_winning_value]
    if winning_cards:
        return min(winning_cards, key=lambda c: c.rank_value)

    # Default: play lowest
    return sorted_suit_cards[0]


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


def play_single_trick(state, declarer_strategy=None):
    """Play one trick and return the winner"""
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
                # Use genetic algorithm strategy for declarer side
                card = declarer_strategy.choose_card(state, player, None, [])
            else:
                # Defensive lead
                card = defensive_card_choice(state.hands[player], None,
                                             state.hands[state.get_dummy()], [],
                                             state.trump, state.NT)
            leading_suit = card.suit if card else None
        else:
            # Following player
            if state.is_declarer_side(player) and declarer_strategy:
                card = declarer_strategy.choose_card(state, player, leading_suit,
                                                     list(zip(played_players, played_cards)))
            else:
                card = defensive_card_choice(state.hands[player], leading_suit,
                                             state.hands[state.get_dummy()],
                                             list(zip(played_players, played_cards)),
                                             state.trump, state.NT)

        if card and card in state.hands[player]:
            state.hands[player].remove(card)
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


class DeclarerStrategy:
    def __init__(self, genome_size=100):
        self.genome = [random.random() for _ in range(genome_size)]
        self.fitness = 0

    def choose_card(self, state, player, leading_suit, cards_played_in_trick):
        """Choose card based on genetic algorithm weights"""
        legal_cards = get_legal_cards(state.hands[player], leading_suit)

        if not legal_cards:
            return None

        if len(legal_cards) == 1:
            return legal_cards[0]

        # Calculate scores for each legal card based on genome
        card_scores = []

        for card in legal_cards:
            score = 0

            # Feature 1: Card rank (higher is better)
            score += self.genome[0] * (card.rank_value / 14.0)

            # Feature 2: Trump preference
            if not state.NT and card.suit == state.trump:
                score += self.genome[1] * 1.0

            # Feature 3: Length in suit
            suit_length = len([c for c in state.hands[player] if c.suit == card.suit])
            score += self.genome[2] * (suit_length / 13.0)

            # Feature 4: Finesse considerations (simplified)
            if leading_suit and card.suit == leading_suit:
                higher_cards_in_suit = len([c for c in legal_cards
                                            if c.suit == card.suit and c.rank_value > card.rank_value])
                score += self.genome[3] * (1.0 - higher_cards_in_suit / 4.0)

            # Feature 5: Trick position preference
            position_in_trick = len(cards_played_in_trick)
            if position_in_trick == 0:  # Leading
                score += self.genome[4] * 1.0
            elif position_in_trick == 3:  # Last to play
                score += self.genome[5] * 1.0

            # Add more features based on genome
            for i in range(6, min(20, len(self.genome))):
                # Random features for genetic diversity
                feature_value = hash(str(card) + str(i)) % 100 / 100.0
                score += self.genome[i] * feature_value

            card_scores.append((card, score))

        # Choose card with highest score
        best_card = max(card_scores, key=lambda x: x[1])[0]
        return best_card

    def mutate(self, mutation_rate=0.1):
        """Mutate the genome"""
        for i in range(len(self.genome)):
            if random.random() < mutation_rate:
                self.genome[i] = random.random()

    def crossover(self, other):
        """Create offspring through crossover"""
        child = DeclarerStrategy(len(self.genome))
        crossover_point = random.randint(1, len(self.genome) - 1)

        child.genome = self.genome[:crossover_point] + other.genome[crossover_point:]
        return child


def simulate_game(hands, declarer, trump, contract_level, lead_card, lead_player, strategy):
    """Simulate a complete game with given strategy"""
    state = GameState(hands, declarer, trump, contract_level, lead_player)

    # Handle opening lead manually first
    order = ["W", "N", "E", "S"]
    lead_index = order.index(lead_player)
    trick_order = order[lead_index:] + order[:lead_index]

    # Play opening lead card
    if lead_card in state.hands[lead_player]:
        state.hands[lead_player].remove(lead_card)
        played_cards = [lead_card]
        played_players = [lead_player]
        leading_suit = lead_card.suit

        # Complete first trick
        for player in trick_order[1:]:
            if not state.hands[player]:
                continue

            if state.is_declarer_side(player) and strategy:
                card = strategy.choose_card(state, player, leading_suit,
                                            list(zip(played_players, played_cards)))
            else:
                card = defensive_card_choice(state.hands[player], leading_suit,
                                             state.hands[state.get_dummy()],
                                             list(zip(played_players, played_cards)),
                                             state.trump, state.NT)

            if card and card in state.hands[player]:
                state.hands[player].remove(card)
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
    for _ in range(12):
        if not any(state.hands.values()):
            break
        winner, trick_cards = play_single_trick(state, strategy)
        if not winner:
            break

    # Return success (made contract or not), tricks taken, and game state for history
    needed_tricks = 6 + contract_level
    return state.declarer_tricks >= needed_tricks, state.declarer_tricks, state


def show_trick_summary(state, declarer, contract_level):
    """Display a summary of who won each trick"""
    partnerships = {"N": "S", "S": "N", "E": "W", "W": "E"}
    declarer_side = [declarer, partnerships[declarer]]

    print("\n" + "=" * 60)
    print("                   TRICK SUMMARY")
    print("=" * 60)

    declarer_tricks_won = []
    defender_tricks_won = []

    for trick in state.trick_history:
        trick_num = trick['trick_num']
        winner = trick['winner']

        if winner in declarer_side:
            declarer_tricks_won.append(trick_num)
        else:
            defender_tricks_won.append(trick_num)

    print(f"Contract: {contract_level}{state.trump} by {declarer}")
    print(f"Declarer side: {declarer} & {partnerships[declarer]}")
    print(f"Defender side: {''.join([p for p in 'NESW' if p not in declarer_side])}")
    print()

    print(f"Declarer side won {len(declarer_tricks_won)} tricks:")
    if declarer_tricks_won:
        print(f"  Tricks: {', '.join(map(str, declarer_tricks_won))}")
    else:
        print("  No tricks won")

    print(f"Defender side won {len(defender_tricks_won)} tricks:")
    if defender_tricks_won:
        print(f"  Tricks: {', '.join(map(str, defender_tricks_won))}")
    else:
        print("  No tricks won")

    print()
    needed_tricks = 6 + contract_level
    if len(declarer_tricks_won) >= needed_tricks:
        overtricks = len(declarer_tricks_won) - needed_tricks
        print(f"✅ CONTRACT MADE! ({needed_tricks} needed, {len(declarer_tricks_won)} taken)")
        if overtricks > 0:
            print(f"   +{overtricks} overtricks!")
    else:
        undertricks = needed_tricks - len(declarer_tricks_won)
        print(f"❌ CONTRACT FAILED! ({needed_tricks} needed, {len(declarer_tricks_won)} taken)")
        print(f"   Down {undertricks} tricks")

    print("=" * 60)


def genetic_algorithm(hands, declarer, trump, contract_level, lead_card, lead_player,
                      population_size=50, generations=100):
    """Run genetic algorithm to find best declarer strategy"""

    # Initialize population
    population = [DeclarerStrategy() for _ in range(population_size)]

    print(f"Running genetic algorithm with {population_size} strategies for {generations} generations...")

    for generation in range(generations):
        # Evaluate fitness for each strategy
        for strategy in population:
            success_count = 0
            total_tricks = 0

            # Test strategy multiple times with slight variations
            for _ in range(5):
                # Add small random variations to test robustness
                test_hands = copy.deepcopy(hands)
                made_contract, tricks, _ = simulate_game(test_hands, declarer, trump,
                                                         contract_level, lead_card, lead_player, strategy)
                if made_contract:
                    success_count += 1
                total_tricks += tricks

            # Fitness based on success rate and average tricks
            strategy.fitness = success_count * 10 + (total_tricks / 5)

        # Sort by fitness
        population.sort(key=lambda x: x.fitness, reverse=True)

        if generation % 20 == 0:
            best_fitness = population[0].fitness
            print(f"Generation {generation}: Best fitness = {best_fitness:.2f}")

        # Create next generation
        next_generation = population[:population_size // 4]  # Keep top 25%

        # Crossover and mutation
        while len(next_generation) < population_size:
            parent1 = random.choice(population[:population_size // 2])
            parent2 = random.choice(population[:population_size // 2])

            child = parent1.crossover(parent2)
            child.mutate()
            next_generation.append(child)

        population = next_generation

    return population[0]  # Return best strategy


def main(deal):
    # Load deal
    hands, declarer, trump, contract_level, lead_card, lead_player = load_deal(deal)

    print(f"Contract: {contract_level}{trump} by {declarer}")
    print(f"Opening lead: {lead_card} by {lead_player}")
    print(f"Declarer needs {6 + contract_level} tricks to make contract\n")

    # Show hands
    print("Hands:")
    for p in "NESW":
        print(f"{p}: {sorted(hands[p], key=lambda c: (c.suit_value, c.rank_value))}")
    print()

    # Run genetic algorithm to find best strategy
    best_strategy = genetic_algorithm(hands, declarer, trump, contract_level,
                                      lead_card, lead_player)

    print(f"\nBest strategy found! Playing final game...")

    # Play one final game and show trick summary
    test_hands = copy.deepcopy(hands)
    made_contract, final_tricks, final_state = simulate_game(test_hands, declarer, trump,
                                                             contract_level, lead_card, lead_player,
                                                             best_strategy)

    # Show detailed trick summary
    show_trick_summary(final_state, declarer, contract_level)


if __name__ == "__main__":
    main('4H.json')
