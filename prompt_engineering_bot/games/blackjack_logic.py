def get_rules():
    return {
        "decks": 1,
        "piles": 1,
        "can_pass": "YES",
        "draw_piles": "NO",
        "draw_decks": "YES",
        "personal_decks": "NO",
        "free_rules": """
        Game: Blackjack (Strategy Logic)
        1. Card Values: 2-10 are face value. Jack, Queen, King are 10. Aces are 11 (unless sum > 21, then 1).
        2. Objective: Achieve a hand total as close to 21 as possible without exceeding it.
        3. Win Condition: If MYCLOSED hand total is exactly 21, you win immediately.
        4. Bust Condition: If hand total > 21, you lose.
        5. Mandatory Turn Action: 
           - If total < 17: You must HIT (draw from PUBDECK_1 to MYCLOSED).
           - If total >= 17: You must STAND (PASS turn).
        6. Ace Logic: Always calculate Aces as 11 first. Only reduce to 1 if the total exceeds 21.
        """
    }
