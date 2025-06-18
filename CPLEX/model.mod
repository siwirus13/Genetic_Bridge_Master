/*********************************************
 * OPL 22.1.2.0 Model
 * Author: siwirus
 * Creation Date: Jun 18, 2025 at 12:17:00 AM
 *********************************************/



// Parameters from data file
string declarer = ...;
string trump = ...;
int contract_level = ...;
string lead_card = ...;
string lead_player = ...;

// Define sets
{string} PLAYERS = {"W", "N", "E", "S"};
{string} SUITS = {"S", "H", "D", "C"};
{string} RANKS = {"2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"};

// Player partnerships
string PARTNER[p in PLAYERS] =
  p == "N" ? "S" :
  p == "S" ? "N" :
  p == "E" ? "W" :
  p == "W" ? "E" : "";

// Rank values for comparison
int RANK_VALUE[r in RANKS] =
  r == "2" ? 2 : r == "3" ? 3 : r == "4" ? 4 : r == "5" ? 5 : r == "6" ? 6 :
  r == "7" ? 7 : r == "8" ? 8 : r == "9" ? 9 : r == "T" ? 10 : r == "J" ? 11 :
  r == "Q" ? 12 : r == "K" ? 13 : 14;

// Card hands for each player (from data file)
{string} hand[PLAYERS] = ...;

// Derive all cards in play
{string} ALL_CARDS = union(p in PLAYERS) hand[p];

string card_suit[ALL_CARDS];
string card_rank[ALL_CARDS];
int card_rank_value[ALL_CARDS];

// Fill arrays
execute {
  for(var c in ALL_CARDS) {
    card_suit[c] = c.substring(0,1);
    card_rank[c] = c.substring(1); // From position 1 to end
    card_rank_value[c] = RANK_VALUE[card_rank[c]];
  }
}
// Number of tricks to play
int NUM_TRICKS = 13;
range TRICKS = 1..NUM_TRICKS;
range POSITIONS = 1..4;  // 4 positions per trick

// Decision Variables
// x[t][pos][p][c] = 1 if player p plays card c at position pos in trick t
dvar boolean x[TRICKS][POSITIONS][PLAYERS][ALL_CARDS];

// Auxiliary variables for trick winners
dvar boolean trick_won_by_declarer[TRICKS];
dvar boolean card_wins_trick[TRICKS][ALL_CARDS];

// Variables for tracking leading suit in each trick
dvar boolean suit_led[TRICKS][SUITS];

// Objective: Maximize declarer tricks
maximize sum(t in TRICKS) trick_won_by_declarer[t];

subject to {

  // Constraint 1: Each card is played exactly once
  forall(p in PLAYERS, c in hand[p])
    sum(t in TRICKS, pos in POSITIONS) x[t][pos][p][c] == 1;

  // Constraint 2: Each player plays exactly one card per trick
  forall(t in TRICKS, p in PLAYERS)
    sum(pos in POSITIONS, c in hand[p]) x[t][pos][p][c] == 1;

  // Constraint 3: The led suit is determined by the card played at position 1
  forall(t in TRICKS, s in SUITS)
    suit_led[t][s] == sum(p in PLAYERS, c in hand[p]: card_suit[c] == s)
                      x[t][1][p][c];

  // Constraint 4: Follow suit if possible
  // If a player has cards of the led suit, they must play one
  forall(t in TRICKS, p in PLAYERS, pos in 2..4, s in SUITS) {
    // If suit s is led and player p has cards of suit s, they must play one
    suit_led[t][s] * (sum(c in hand[p]: card_suit[c] == s) 1) <=
    sum(c in hand[p]: card_suit[c] == s) x[t][pos][p][c] +
    (1 - suit_led[t][s]) +
    (1 - (sum(c in hand[p]: card_suit[c] == s) 1 >= 1));
  }

  // Constraint 5: Opening lead constraint
  forall(p in PLAYERS, c in hand[p])
    (p == lead_player && c == lead_card) => x[1][1][p][c] == 1;

  // Constraint 6: Trick winner determination (FIXED - simplified approach)
  // A card can only win if it's played
  forall(t in TRICKS, c in ALL_CARDS)
    card_wins_trick[t][c] <= sum(p in PLAYERS, pos in POSITIONS: c in hand[p]) x[t][pos][p][c];

  // Constraint 7: Trump cards beat non-trump cards (when trump exists)
  forall(t in TRICKS, c in ALL_CARDS: trump != "NT" && card_suit[c] == trump)
    card_wins_trick[t][c] <= 1 - sum(c2 in ALL_CARDS, p in PLAYERS, pos in POSITIONS:
      c2 in hand[p] && card_suit[c2] == trump && card_rank_value[c2] > card_rank_value[c])
      x[t][pos][p][c2];

  // Constraint 8: Non-trump cards can only win if highest of led suit and no trumps played
  forall(t in TRICKS, c in ALL_CARDS, s in SUITS:
    (trump == "NT" || card_suit[c] != trump) && card_suit[c] == s) {

    // Must be highest of its suit
    card_wins_trick[t][c] <= suit_led[t][s] *
      (1 - sum(c2 in ALL_CARDS, p in PLAYERS, pos in POSITIONS:
        c2 in hand[p] && card_suit[c2] == s && card_rank_value[c2] > card_rank_value[c])
        x[t][pos][p][c2]);

    // If trump exists, no trump cards should be played
    if (trump != "NT") {
      card_wins_trick[t][c] <= 1 - sum(c2 in ALL_CARDS, p in PLAYERS, pos in POSITIONS:
        c2 in hand[p] && card_suit[c2] == trump) x[t][pos][p][c2];
    }
  }

  // Constraint 9: Exactly one card wins each trick
  forall(t in TRICKS)
    sum(c in ALL_CARDS) card_wins_trick[t][c] == 1;

  // Constraint 10: Declarer wins trick if declarer or partner's card wins
  forall(t in TRICKS) {
    trick_won_by_declarer[t] <=
      sum(c in hand[declarer]) card_wins_trick[t][c] +
      sum(c in hand[PARTNER[declarer]]) card_wins_trick[t][c];

    trick_won_by_declarer[t] >=
      sum(c in hand[declarer]) card_wins_trick[t][c] +
      sum(c in hand[PARTNER[declarer]]) card_wins_trick[t][c] - 1;
  }
}

// Post-processing: Calculate results
execute {
  var needed_tricks = 6 + contract_level;
  var declarer_tricks_won = 0;

  for(var t in TRICKS) {
    if(trick_won_by_declarer[t] == 1) {
      declarer_tricks_won++;
    }
  }

  writeln("==================");
  writeln("         CPLEX BRIDGE SOLVER RESULTS");
  writeln("===================");
  writeln("Contract: " + contract_level + trump + " by " + declarer);
  writeln("Opening lead: " + lead_card + " by " + lead_player);
  writeln("Needed tricks: " + needed_tricks);
  writeln("Declarer tricks: " + declarer_tricks_won);
  writeln();

  // Show detailed trick analysis
  writeln("Trick-by-trick analysis:");
  writeln("-----------------------------");

  for(var t in TRICKS) {
    write("Trick " + t + ": ");

    for(var pos in POSITIONS) {
      for(var p in PLAYERS) {
        for(var c in hand[p]) {
          if(x[t][pos][p][c] == 1) {
            write(p + ":" + c + " ");
          }
        }
      }
    }

    if(trick_won_by_declarer[t] == 1) {
      writeln("(Declarer side wins)");
    } else {
      writeln("(Defense wins)");
    }
  }

  writeln("-----------------");

  if(declarer_tricks_won >= needed_tricks) {
    var overtricks = declarer_tricks_won - needed_tricks;
    writeln("✅ CONTRACT MADE!");
    if(overtricks > 0) {
      writeln("   +" + overtricks + " overtricks!");
    }
  } else {
    var undertricks = needed_tricks - declarer_tricks_won;
    writeln("❌ CONTRACT FAILED!");
    writeln("   Down " + undertricks + " tricks");
  }

  writeln("=====================");
}