from state_parser import parse_game_state

def get_tokens(s):
    """Splits '2 of Clubs' into ['2', 'clubs']"""
    return set(s.lower().replace(' of ', ' ').split())

def solve(game_state_text):
    """Refined Algorithmic solver for Simplified Uno with Token Matching."""
    state = parse_game_state(game_state_text)
    my_hand = state.get('MYCLOSED', [])
    piles = state.get('PUBPILE', {})
    top_card_pile = piles.get(1)
    
    if not top_card_pile or top_card_pile == "FALSE":
        if my_hand:
            reasoning = f"The pile is empty. Playing {my_hand[0]}."
            return [f"* PLAY: src: MYCLOSED, dest: P1, card: {my_hand[0]}", "* PASS"], reasoning
        elif state.get('PUBDECK'):
            reasoning = "Empty hand and pile. Drawing."
            return ["* PLAY: src: PUBLIC_DECK, dest: MYCLOSED, card: None", "* PASS"], reasoning
        else:
            return ["* PASS"], "No moves."

    # Robust Token Matching
    pile_tokens = get_tokens(top_card_pile)
    
    match = None
    for card in my_hand:
        card_tokens = get_tokens(card)
        # Intersection: if they share ANY token (like 'clubs' or '2'), it's a match
        if pile_tokens & card_tokens:
            match = card
            break
    
    if match:
        reasoning = f"Matched {top_card_pile} with {match} (shares tokens {pile_tokens & get_tokens(match)})."
        return [f"* PLAY: src: MYCLOSED, dest: P1, card: {match}", "* PASS"], reasoning
            
    if state.get('PUBDECK'):
        reasoning = f"No match found for {top_card_pile} in tokens. Drawing from PUBLIC_DECK."
        return ["* PLAY: src: PUBLIC_DECK, dest: MYCLOSED, card: None", "* PASS"], reasoning
    
    return ["* PASS"], "No match found and no deck."
