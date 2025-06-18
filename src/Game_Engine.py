import json
import copy


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

def get_legal_cards(hand, leading_suit):
    same_suit_cards = [c for c in hand if c.suit == leading_suit]
    return same_suit_cards if same_suit_cards else hand[:]

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

    def get_partner(self, player):
        return self.partnerships[player]

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

def get_current_trick_winner(cards_played_in_trick, NT, trump_suit):
    """Determine who is currently winning the trick"""
    if not cards_played_in_trick:
        return None, None

    cards = [card for card, player in cards_played_in_trick]
    players = [player for card, player in cards_played_in_trick]

    leading_suit = cards[0].suit
    winning_card = cards[0]
    winning_player = players[0]

    for i in range(1, len(cards)):
        card = cards[i]
        if NT == 1:
            if card.suit == leading_suit and card.rank_value > winning_card.rank_value:
                winning_card = card
                winning_player = players[i]
        else:
            if card.suit == trump_suit:
                if winning_card.suit != trump_suit or card.rank_value > winning_card.rank_value:
                    winning_card = card
                    winning_player = players[i]
            elif card.suit == winning_card.suit and winning_card.suit != trump_suit:
                if card.rank_value > winning_card.rank_value:
                    winning_card = card
                    winning_player = players[i]

    return winning_player, winning_card



