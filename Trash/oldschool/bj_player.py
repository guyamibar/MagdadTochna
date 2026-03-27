from game_env import hand_value, VALUES


class Agent:
    def __init__(self, resources: float = 10_000.0):
        self.resources = resources
        self.running_count = 0  # Hi-Lo style count

    # ------------- COUNT UPDATE -------------
    def update_count(self, card):
        """
        Basic Hi-Lo style counting:
        - 2–6  -> +1
        - 7–9  -> 0
        - 10,A -> -1
        """
        rank = card[:-1]
        v = VALUES[rank]

        if v in (2, 3, 4, 5, 6):
            self.running_count += 1
        elif v in (10, 11):  # 10s & Aces
            self.running_count -= 1

    # -----------------------------------------
    # Decision: Enter the round?
    # -----------------------------------------
    #def should_enter(self):
        """
        Decide whether to join this round after:
        - seeing X other-player cards
        - seeing dealer's upcard
        - updating running_count

        We use a different threshold if dealer upcard is strong.
        """
     #   return self.running_count >= 3

    # -----------------------------------------
    # Decision: How many "units" to risk this round
    # -----------------------------------------
    def allocate_units(self):
        """
        Resource allocation based on running count.
        This is abstract; units are not money, just 'weight' of the round.
        """
        c = self.running_count
        base = max(self.resources * 0.01, 1.0)  # 1% of resources, at least 1

        if c <= 1:
            return base*0.1
        if c == 2:
            return 2 * base
        return 10 * base  # very good state

    # -----------------------------------------
    # Decision: Hit or Stand?
    # -----------------------------------------
    def decide_action_simple(self, hand, deck, dealer_upcard):
        """
        Smarter policy:
        - uses running count (deck composition)
        - uses bust probability
        - uses soft/hard hand
        - slightly adjusts by dealer upcard
        """
        value = hand_value(hand)
        count = self.running_count
        bust = deck.bust_probability(value)
        return "hit" if bust < 0.5 else "stand"

    def decide_action(self, hand, deck, dealer_upcard):
        """
        Smart hit/stand decision:
        - running count influences aggressiveness
        - bust probability from deck
        - soft/hard hand
        - dealer upcard strength
        """
        value = hand_value(hand)
        count = self.running_count

        # ---- Soft hand detection ----
        # Soft = hand contains Ace counted as 11
        soft = False
        ranks = [r for (r, s) in hand]
        if "A" in ranks:
            # if subtracting 10 keeps us <= 21 → Ace is acting as 11
            if value <= 21 and value - 10 <= 11:
                soft = True

        # ---- Bust probability of hitting ----
        bust_prob = deck.bust_probability(value)

        # ---- Dealer strength ----
        dealer_rank = dealer_upcard[0][:-1]  # e.g. "K", "9", "A"
        dealer_val = VALUES[dealer_rank]
        dealer_strong = dealer_val >= 7
        dealer_weak = dealer_val <= 6

        # ------------------------------------
        # 1) HIGH COUNT → Conservative / safer
        # ------------------------------------
        if count >= 3:
            # Dealer strong → sometimes need to fight back
            if dealer_strong:
                if value <= 11:
                    return "hit"
                if value >= 18:
                    return "stand"
                return "hit" if bust_prob < 0.30 else "stand"

            # Dealer weak → standing is very powerful
            if soft and value >= 18:
                return "stand"
            if value >= 15:
                return "stand"

            # Marginal totals
            return "hit" if bust_prob < 0.40 else "stand"

        # ------------------------------------
        # 2) NEUTRAL COUNT → Normal strategy
        # ------------------------------------
        if -2 <= count <= 2:

            # Soft totals
            if soft:
                if value <= 17:
                    return "hit"
                return "stand"

            # Hard totals
            if value >= 17:
                return "stand"
            if value <= 11:
                return "hit"

            # Mid-range (12–16)
            if dealer_strong:
                return "hit" if bust_prob < 0.50 else "stand"
            else:
                return "hit" if bust_prob < 0.40 else "stand"

        # ------------------------------------
        # 3) LOW COUNT (≤ -3) → Aggressive
        # ------------------------------------
        # Deck rich in small cards → hitting is safer
        if value <= 16:
            return "hit"

        # For larger totals: only hit with low bust chance
        return "hit" if bust_prob < 0.25 else "stand"
