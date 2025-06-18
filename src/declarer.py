from Game_Engine import get_legal_cards, get_current_trick_winner, simulate_game
import copy
import random



class DeclarerStrategy:
    def __init__(self, genome_size=60):
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
                current_winner, winning_card = get_current_trick_winner(cards_played_in_trick, state.NT, state.trump)

                can_win = False
                if winning_card:
                    if not state.NT and card.suit == state.trump and winning_card.suit != state.trump:
                        can_win = True
                    elif card.suit == winning_card.suit and card.rank_value > winning_card.rank_value:
                        can_win = True
                    elif not state.NT and card.suit == state.trump and winning_card.suit == state.trump:
                        can_win = card.rank_value > winning_card.rank_value

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

    def mutate(self, mutation_rate=0.2):
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

def genetic_algorithm(hands, declarer, trump, contract_level, lead_card, lead_player,
                      population_size=40, generations=70):
    """Enhanced genetic algorithm with better fitness evaluation"""

    # Initialize population with diverse strategies
    population = [DeclarerStrategy() for _ in range(population_size)]

    print(f"Running enhanced genetic algorithm...")
    print(f"Population: {population_size}, Generations: {generations}")
    print(f"Using improved optimal defense simulation\n")

    best_fitness_history = []

    for generation in range(generations):
        # Evaluate fitness for each strategy
        for strategy in population:
            fitness_scores = []

            # Test strategy multiple times for robustness
            for test_run in range(4):  # More thorough testing
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
