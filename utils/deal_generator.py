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
    return sum(1 for card in hand if card[0] == trump)

# Main generator
def generate_data(points, trump_colour, trump_amount, contract_level):
    deck = full_deck()
    random.shuffle(deck)

    while True:
        random.shuffle(deck)
        # Try different splits of 13 cards for each player
        hands = {
            'N': deck[0:13],
            'S': deck[13:26],
            'E': deck[26:39],
            'W': deck[39:52]
        }

        ns_points = count_points(hands['N']) + count_points(hands['S'])
        ns_trumps = count_trumps(hands['N'], trump_colour) + count_trumps(hands['S'], trump_colour)

        if ns_points == points and ns_trumps == trump_amount:
            break  # Acceptable hand found

    lead_player = random.choice(['N', 'S', 'E', 'W'])
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

data = generate_data(points=25, trump_colour='H', trump_amount=9, contract_level=4)

with open('4H.json', 'w') as file:
    json.dump(data, file, indent=4)
