from utils import get_legal_cards, get_current_trick_winner


class OptimalDefense:



    @staticmethod
    def choose_defensive_card(state, player, leading_suit, cards_played_in_trick):
        legal_cards = get_legal_cards(state.hands[player], leading_suit)

        if len(legal_cards) == 1:
            return legal_cards[0]

        # Determine current trick winner and if partner is winning
        current_winner, winning_card = get_current_trick_winner(cards_played_in_trick, state.NT, state.trump)
        partner = state.get_partner(player)
        partner_winning = (current_winner == partner)

        best_card = None
        best_score = float('inf')

        for card in legal_cards:
            score = OptimalDefense._evaluate_defensive_card(
                state, player, card, leading_suit, cards_played_in_trick,
                partner_winning, current_winner, winning_card)
            if score < best_score:
                best_score = score
                best_card = card

        return best_card

    @staticmethod
    def _evaluate_defensive_card(state, player, card, leading_suit, cards_played_in_trick,
                                 partner_winning, current_winner, winning_card):
        score = 0
        partner = state.get_partner(player)

        if leading_suit is None:
            # Leading the trick - standard opening lead principles
            same_suit_cards = [c for c in state.hands[player] if c.suit == card.suit]
            suit_length = len(same_suit_cards)

            # Prefer leading from length
            score -= suit_length * 3

            # Avoid leading aces unless from AK combination or very long suit
            if card.rank_value == 14:  # Ace
                has_king = any(c.rank_value == 13 and c.suit == card.suit for c in state.hands[player])
                if not has_king and suit_length < 5:
                    score += 15  # Heavy penalty for leading unsupported ace

            # Prefer leading low from honor sequences
            if card.rank_value >= 11:  # J, Q, K, A
                higher_cards = [c for c in same_suit_cards if c.rank_value > card.rank_value]
                if len(higher_cards) >= 1:  # Has higher card(s)
                    score -= 5  # Good to lead from sequence

            # Prefer fourth best from long suits
            if suit_length >= 4:
                sorted_suit = sorted(same_suit_cards, key=lambda c: c.rank_value, reverse=True)
                if len(sorted_suit) >= 4 and card == sorted_suit[3]:  # Fourth highest
                    score -= 8

        else:
            # Following to a trick
            position_in_trick = len(cards_played_in_trick)

            # KEY IMPROVEMENT: Check if partner is winning
            if partner_winning:
                # Partner is winning - don't waste high cards!
                if card.suit == leading_suit:
                    # Following suit with partner winning - play low
                    score = -card.rank_value * 2  # Strongly prefer low cards

                    # Extra penalty for playing higher than partner's winning card
                    if winning_card and card.rank_value > winning_card.rank_value:
                        score += 50  # Heavy penalty for overruffing partner

                elif not state.NT and card.suit == state.trump:
                    # Don't trump partner's winning card unless desperate
                    score += 100  # Very heavy penalty

                else:
                    # Discarding - prefer low cards
                    score = card.rank_value

            else:
                # Partner not winning or we're first/second to play
                if card.suit == leading_suit:
                    # Following suit
                    if position_in_trick == 3:  # Last to play
                        # Try to win if possible with minimal card
                        if winning_card and card.rank_value > winning_card.rank_value:
                            score = card.rank_value - winning_card.rank_value  # Minimal win
                        else:
                            score = -card.rank_value  # Can't win, play low
                    else:
                        # Second hand low principle, but cover honors
                        if winning_card and winning_card.rank_value >= 11:  # Honor on table
                            if card.rank_value > winning_card.rank_value:
                                score = card.rank_value - winning_card.rank_value + 5
                            else:
                                score = -card.rank_value
                        else:
                            score = abs(card.rank_value - 9)  # Prefer middle cards

                elif not state.NT and card.suit == state.trump:
                    # Trump consideration
                    if winning_card and winning_card.suit != state.trump:
                        # Can trump - prefer low trumps unless desperate
                        tricks_needed = (6 + state.contract_level) - state.declarer_tricks
                        tricks_remaining = 13 - state.tricks_played

                        if tricks_needed > tricks_remaining - 2:  # Desperate situation
                            score = -card.rank_value  # Use any trump
                        else:
                            score = card.rank_value + 10  # Prefer not to trump unless necessary
                    else:
                        score = card.rank_value + 20  # Avoid wasting trumps

                else:
                    # Discarding off-suit
                    score = card.rank_value  # Prefer low cards

                    # Slight preference for keeping potential winners
                    same_suit_in_hand = [c for c in state.hands[player] if c.suit == card.suit]
                    if same_suit_in_hand and card.rank_value >= 12:  # High card
                        remaining_higher = state.get_remaining_cards_in_suit(card.suit, player)
                        higher_out = len([c for c in remaining_higher if c.rank_value > card.rank_value])
                        if higher_out <= 2:  # Might be a winner
                            score += 5

        return score