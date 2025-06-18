import json
import random

# Card values
POINTS = {'A': 4, 'K': 3, 'Q': 2, 'J': 1}

# All suits and ranks
SUITS = ['S', 'H', 'D', 'C']
RANKS = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']

# Generate full deck
def full_deck():
    return [s + r for s in SUITS for r in RANKS]

# Count points in a hand
def count_points(hand):
    return sum(POINTS.get(card[1], 0) for card in hand)

# Count trump cards in a hand
def count_trumps(hand, trump):
    if not trump or trump not in SUITS:
        return 0
    return sum(1 for card in hand if card[0] == trump)

# Main generator
def generate_data(ns_point_split, trump_colour, ns_trump_split, contract_level):
    target_np, target_sp = ns_point_split
    target_nt, target_st = ns_trump_split

    deck = full_deck()

    while True:
        random.shuffle(deck)

        hands = {
            'W': deck[0:13],
            'N': deck[13:26],
            'E': deck[26:39],
            'S': deck[39:52]
        }

        np = count_points(hands['N'])
        sp = count_points(hands['S'])
        nt = count_trumps(hands['N'], trump_colour)
        st = count_trumps(hands['S'], trump_colour)

        if (np == target_np and sp == target_sp and nt == target_nt and st == target_st):
            break  # Acceptable hand found

    lead_player = random.choice(['W'])
    lead_card = random.choice(hands[lead_player])

    data = {
        "declarer": "S",
        "trump": trump_colour,
        "contract_level": contract_level,
        "lead": {
            "card": lead_card,
            "player": lead_player
        },
        "hands": hands,
    }

    return data

# Example usage
data = generate_data(
    ns_point_split=(8, 3),
    trump_colour='NT',
    ns_trump_split=(0, 0),
    contract_level=2
)

with open('deals/2NT.json', 'w') as file:
    json.dump(data, file, indent=4)
