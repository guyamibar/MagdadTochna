def get_rules():
    return {
        "decks": 1,
        "piles": 1,
        "can_pass": "NO",
        "draw_piles": "YES",
        "draw_decks": "YES",
        "personal_decks": "NO",
        "free_rules": """
        Game: Simplified Uno (Match Suit or Rank)
        1. Play: You may move one card from the hand to a pile if it matches the color/suit OR the rank of the current top card of a pile.
        2. Forced Draw: If you have no matching card in hand, you MUST draw one card from a deck to MYCLOSED.
        3. Post-Draw: If the card you just drew is playable, you may play it immediately. Otherwise, you must pass.
        4. Win Condition: The first player to rid of all the cards wins.
        """
    }
