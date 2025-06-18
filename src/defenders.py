from src.Game_Engine import get_legal_cards, get_current_trick_winner


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
        position_in_trick = len(cards_played_in_trick)

        # CRITICAL HARD-CODED RULE: Never waste honors on opponent's higher honors
        if (leading_suit is not None and
                card.suit == leading_suit and
                winning_card and
                not partner_winning and
                OptimalDefense._is_opponent(current_winner, player, state) and
                card.rank_value >= 11 and  # Our card is honor (J, Q, K, A)
                card.rank_value < winning_card.rank_value):  # But lower than winning card
            # Don't waste honors on opponent's higher honors!
            return 500  # Massive penalty to prevent this

        if leading_suit is None:
            # Leading the trick - trump contracts need different strategy
            if not state.NT:  # Trump contract
                score += OptimalDefense._evaluate_trump_opening_lead(state, player, card)
            else:  # NT contract
                score += OptimalDefense._evaluate_nt_opening_lead(state, player, card)

        else:
            # Following to a trick
            if not state.NT:  # Trump contract
                score += OptimalDefense._evaluate_trump_follow(
                    state, player, card, leading_suit, cards_played_in_trick,
                    partner_winning, current_winner, winning_card, position_in_trick)
            else:  # NT contract
                score += OptimalDefense._evaluate_nt_follow(
                    state, player, card, leading_suit, cards_played_in_trick,
                    partner_winning, current_winner, winning_card, position_in_trick)

        return score

    @staticmethod
    def _evaluate_trump_opening_lead(state, player, card):
        """Evaluate opening lead in trump contracts"""
        score = 0
        same_suit_cards = [c for c in state.hands[player] if c.suit == card.suit]
        suit_length = len(same_suit_cards)

        # TRUMP CONTRACT STRATEGY: Focus on quick tricks and trump control

        # 1. CASH ACES IMMEDIATELY - they might get trumped later
        if card.rank_value == 14:  # Ace
            if card.suit != state.trump:  # Non-trump ace
                score -= 50  # Very strong preference for leading aces in side suits
            else:
                # Trump ace - only lead if very long trumps or desperate
                trump_length = len([c for c in state.hands[player] if c.suit == state.trump])
                if trump_length >= 5:
                    score -= 20  # OK to lead trump ace with length
                else:
                    score += 10  # Usually don't lead trump ace

        # 2. Lead from AK combinations for immediate tricks
        elif card.rank_value == 13:  # King
            has_ace = any(c.rank_value == 14 and c.suit == card.suit for c in state.hands[player])
            if has_ace and card.suit != state.trump:
                score -= 40  # Excellent lead from AK in side suit

        # 3. Singleton leads can be very effective (partner might give ruff)
        if suit_length == 1 and card.suit != state.trump:
            # Check if it's a safe singleton (not an ace we need to cash)
            if card.rank_value <= 10:
                score -= 30  # Good singleton lead for potential ruff
            elif card.rank_value == 14:  # Singleton ace
                score -= 45  # Must cash singleton ace immediately

        # 4. Trump leads - generally avoid unless specific reasons
        if card.suit == state.trump:
            score += 15  # General penalty for trump leads
            # Exception: very long trumps or specific tactical reasons
            if suit_length >= 5:
                score -= 10  # Reduce penalty with trump length

        # 5. Passive leads - avoid giving away tricks
        if card.rank_value >= 11 and suit_length <= 3:  # Short suit honor
            if not (card.rank_value == 14 or  # Ace (must cash)
                    (card.rank_value == 13 and any(c.rank_value == 14 and c.suit == card.suit
                                                   for c in state.hands[player]))):  # King from AK
                score += 25  # Penalty for dangerous honor leads

        return score

    @staticmethod
    def _evaluate_trump_follow(state, player, card, leading_suit, cards_played_in_trick,
                               partner_winning, current_winner, winning_card, position_in_trick):
        """Evaluate following in trump contracts"""
        score = 0

        if partner_winning:
            # Partner is winning - don't interfere!
            if card.suit == leading_suit:
                score = -card.rank_value * 15  # Play low when following suit
                if winning_card and card.rank_value > winning_card.rank_value:
                    score += 200  # Never override partner's winner
            elif card.suit == state.trump:
                # Don't trump partner's winner unless desperate
                score += 300  # Massive penalty
            else:
                # Discarding - be very careful
                score = OptimalDefense._evaluate_trump_discard(state, player, card)

        else:
            # Partner not winning - need to compete
            if card.suit == leading_suit:
                # Following suit
                if winning_card and card.rank_value > winning_card.rank_value:
                    # Can win with this card
                    score = -(card.rank_value - winning_card.rank_value) * 5  # Win cheaply
                else:
                    # Can't win - play low
                    score = -card.rank_value * 3

            elif card.suit == state.trump:
                # CRITICAL: Trump usage strategy
                if winning_card and winning_card.suit != state.trump:
                    # Can trump a side suit - this is often good!
                    trump_cards_in_hand = [c for c in state.hands[player] if c.suit == state.trump]
                    if len(trump_cards_in_hand) >= 3:  # Have trump length
                        score = -card.rank_value * 8  # Good to trump, prefer low trumps
                    else:
                        score = -card.rank_value * 4  # Trump but more carefully

                elif winning_card and winning_card.suit == state.trump:
                    # Need to overtrump
                    if card.rank_value > winning_card.rank_value:
                        score = (card.rank_value - winning_card.rank_value) * 2  # Overtrump cheaply
                    else:
                        score += 100  # Can't overtrump - bad situation

            else:
                # Discarding
                score = OptimalDefense._evaluate_trump_discard(state, player, card)

        return score

    @staticmethod
    def _evaluate_trump_discard(state, player, card):
        """Evaluate discarding in trump contracts - very important!"""
        score = card.rank_value  # Base: prefer discarding low cards

        # NEVER discard winners in trump contracts - they're precious!
        same_suit_cards = [c for c in state.hands[player] if c.suit == card.suit]
        if same_suit_cards:
            remaining_higher = state.get_remaining_cards_in_suit(card.suit, player)
            higher_out = len([c for c in remaining_higher if c.rank_value > card.rank_value])

            # Even stricter penalties for discarding winners in trump contracts
            if card.rank_value >= 14:  # Ace
                score += 500  # NEVER discard aces
            elif card.rank_value >= 13 and higher_out <= 1:  # King with ace out
                score += 200
            elif card.rank_value >= 12 and higher_out <= 2:  # Queen
                score += 100
            elif card.rank_value >= 11 and higher_out <= 3:  # Jack
                score += 75

        # In trump contracts, side suit length is less important
        # Focus on keeping winners and potential trump tricks
        if card.suit == state.trump:
            # Don't discard trumps unless desperate
            score += 50

        return score

    @staticmethod
    def _evaluate_nt_opening_lead(state, player, card):
        """Evaluate opening lead in NT contracts"""
        score = 0
        same_suit_cards = [c for c in state.hands[player] if c.suit == card.suit]
        suit_length = len(same_suit_cards)

        # NT STRATEGY: Establish long suits
        score -= suit_length * 8  # Strong preference for length

        # Check for solid sequences (AKQ, KQJ, QJT, etc.)
        sequence_bonus = OptimalDefense._get_sequence_bonus(same_suit_cards, card)
        score -= sequence_bonus

        # Lead 4th best from long suits without solid sequence
        if suit_length >= 4 and sequence_bonus < 10:
            sorted_suit = sorted(same_suit_cards, key=lambda c: c.rank_value, reverse=True)
            if len(sorted_suit) >= 4 and card == sorted_suit[3]:
                score -= 20  # Strong preference for 4th best

        # Don't lead unsupported aces in NT unless very long suit
        if card.rank_value == 14:  # Ace
            has_king = any(c.rank_value == 13 and c.suit == card.suit for c in state.hands[player])
            if not has_king and suit_length < 6:
                score += 25  # Heavy penalty

        return score

    @staticmethod
    def _evaluate_nt_follow(state, player, card, leading_suit, cards_played_in_trick,
                            partner_winning, current_winner, winning_card, position_in_trick):
        """Evaluate following in NT contracts"""
        score = 0

        if partner_winning:
            # Partner is winning - don't waste high cards!
            if card.suit == leading_suit:
                # Following suit with partner winning - play low
                score = -card.rank_value * 10  # Strongly prefer low cards
                # Extra penalty for playing higher than partner's winning card
                if winning_card and card.rank_value > winning_card.rank_value:
                    score += 50  # Heavy penalty for overriding partner
            else:
                # Discarding - preserve winners, discard losers
                score = OptimalDefense._evaluate_discard(state, player, card)
        else:
            # Partner not winning - need to compete intelligently
            if card.suit == leading_suit:
                # Following suit - position-dependent strategy
                if position_in_trick == 3:  # Fourth hand (last to play)
                    if winning_card and card.rank_value > winning_card.rank_value:
                        # Can win - prefer minimal winning card
                        score = (card.rank_value - winning_card.rank_value) * 2
                        # But check if partner might have led from strength
                        if (len(cards_played_in_trick) >= 1 and
                                OptimalDefense._partner_led_from_strength(cards_played_in_trick[0][0])):
                            score -= 10  # Bonus for supporting partner's lead
                    else:
                        # Can't win - play lowest
                        score = -card.rank_value * 3

                elif position_in_trick == 1:  # Second hand
                    # Second hand plays low UNLESS covering an honor
                    if winning_card and winning_card.rank_value >= 12:  # Q, K, A led
                        # Try to cover honor with next higher honor
                        if card.rank_value > winning_card.rank_value and card.rank_value <= winning_card.rank_value + 2:
                            score = -(card.rank_value - winning_card.rank_value)  # Prefer immediate cover
                        elif card.rank_value > winning_card.rank_value:
                            score = card.rank_value - winning_card.rank_value + 10  # Don't waste high cards
                        else:
                            score = -card.rank_value * 2  # Play low
                    else:
                        # Low card led - second hand low
                        score = -card.rank_value * 2

                else:  # Third hand (position_in_trick == 2)
                    # Third hand high - but coordinate with partner
                    if len(cards_played_in_trick) >= 1:
                        first_card, first_player = cards_played_in_trick[0]
                        if (current_winner == first_player and
                                winning_card and
                                card.rank_value > winning_card.rank_value):
                            # Partner led and is winning - don't override!
                            score = 100  # Heavy penalty
                        else:
                            # Try to win the trick or force out declarer's honors
                            if winning_card and card.rank_value > winning_card.rank_value:
                                score = -(card.rank_value - winning_card.rank_value) * 3  # Win cheaply
                            else:
                                # Can't win - play high to force out honors
                                score = -card.rank_value + 8
                    else:
                        # First to play in third position (shouldn't happen normally)
                        score = -card.rank_value + 8
            else:
                # Discarding
                score = OptimalDefense._evaluate_discard(state, player, card)

        return score

    @staticmethod
    def _get_sequence_bonus(suit_cards, card):
        """Calculate bonus for leading from solid sequences"""
        if len(suit_cards) < 2:
            return 0

        sorted_cards = sorted(suit_cards, key=lambda c: c.rank_value, reverse=True)
        card_index = next((i for i, c in enumerate(sorted_cards) if c == card), -1)

        if card_index == -1:
            return 0

        # Check for sequences starting from this card
        sequence_length = 1
        for i in range(card_index + 1, len(sorted_cards)):
            if sorted_cards[i].rank_value == sorted_cards[i - 1].rank_value - 1:
                sequence_length += 1
            else:
                break

        # Bonus based on sequence length and position
        if sequence_length >= 3:
            return 25  # Strong sequence
        elif sequence_length == 2 and card_index == 0:
            return 15  # Top of doubleton sequence
        elif sequence_length == 2:
            return 10  # Part of sequence

        return 0

    @staticmethod
    def _evaluate_discard(state, player, card):
        """Evaluate discarding this card when not following suit"""
        score = card.rank_value  # Base: prefer discarding low cards

        # CRITICAL: Don't discard winners!
        same_suit_cards = [c for c in state.hands[player] if c.suit == card.suit]
        if same_suit_cards:
            remaining_higher = state.get_remaining_cards_in_suit(card.suit, player)
            higher_out = len([c for c in remaining_higher if c.rank_value > card.rank_value])

            # Strong penalty for discarding likely winners
            if card.rank_value >= 14:  # Ace
                score += 200  # Never discard aces
            elif card.rank_value >= 13 and higher_out <= 1:  # King with ace out
                score += 100
            elif card.rank_value >= 12 and higher_out <= 2:  # Queen with A,K out
                score += 75
            elif card.rank_value >= 11 and higher_out <= 3:  # Jack with A,K,Q out
                score += 50
            elif card.rank_value >= 10 and higher_out <= 4:  # Ten
                score += 25

        # Consider suit length - prefer keeping length in weak suits
        suit_length = len(same_suit_cards)
        if suit_length <= 2:
            score += 10  # Penalty for shortening already short suits

        # In NT, prefer keeping length in major suits
        if state.NT and card.suit in ['S', 'H']:
            score += 5

        return score

    @staticmethod
    def _guess_partner_long_suit(state, player):
        """Try to identify partner's likely long suit from bidding/play"""
        # This is a simplified version - in real bridge you'd use bidding info
        partner = state.get_partner(player)

        # Look at partner's known cards (from previous tricks)
        # This would need to be implemented based on your game state tracking
        # For now, return None as we don't have this information
        return None

    @staticmethod
    def _is_opponent(player_to_check, current_player, state):
        """Check if player_to_check is an opponent of current_player"""
        partner = state.get_partner(current_player)
        return player_to_check != current_player and player_to_check != partner

    @staticmethod
    def _partner_led_from_strength(led_card):
        """Determine if partner likely led from a strong holding"""
        # Check if partner led an honor or fourth-best from length
        if led_card.rank_value >= 11:  # Honor lead (J, Q, K, A)
            return True
        elif led_card.rank_value <= 7:  # Low card - might be fourth best
            return True
        return False