
from src.Game_Engine import GameState, determine_trick_winner
from src.defenders import OptimalDefense


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