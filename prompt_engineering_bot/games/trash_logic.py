def get_rules():
    return {
        "decks": 1,
        "piles": 10,
        "can_pass": "NO",
        "draw_piles": "NO",
        "draw_decks": "YES",
        "personal_decks": "NO",
        "free_rules": """
        Game: Trash (10-Slot Variation)
        1. Setup: There are 10 public piles (PUBPILE_1 to PUBPILE_10), representing slots for ranks Ace through 10.
        2. Action (Draw): Draw one card from PUBDECK_1 to MYCLOSED.
        3. Action (Place): If the rank of the card matches an empty slot (e.g., a 5 for PUBPILE_5), move it to that pile.
        4. Chain Reaction: If you place a card in a slot, and that slot already had a card, move the old card to MYCLOSED and try to place it in its correct slot.
        5. Win: Be the first to fill all 10 slots with the correct ranks.
        """
    }
