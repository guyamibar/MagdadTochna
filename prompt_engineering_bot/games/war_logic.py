def get_rules():
    return {
        "decks": 1,
        "piles": 1,
        "can_pass": "NO",
        "draw_piles": "NO",
        "draw_decks": "NO",
        "personal_decks": "NO",
        "free_rules": """
        Game: War (Standard)
        1. Setup: Each player has a personal hidden deck (MYDECK).
        2. Play: You must move the top card of MYDECK to PUBPILE_1.
        3. Comparison: The player who moved the card with the strictly HIGHER rank wins the turn. Rank order: 2, 3, 4, 5, 6, 7, 8, 9, 10, J, Q, K, A (High).
        4. War Condition: If the ranks are equal, it is a War (draw again).
        5. Win: The objective is to win all cards from the other player's deck.
        """
    }
