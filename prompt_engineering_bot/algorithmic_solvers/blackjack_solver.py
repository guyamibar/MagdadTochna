from state_parser import parse_game_state

def get_card_value(card_rank, current_total):
    rank_clean = card_rank.lower().strip()
    if rank_clean in ['jack', 'queen', 'king', '10']:
        return 10
    if rank_clean == 'ace':
        return 11 if current_total + 11 <= 21 else 1
    if rank_clean.isdigit():
        return int(rank_clean)
    return 0

def solve(game_state_text):
    """Algorithmic solver for Blackjack with Reasoning and new format."""
    state = parse_game_state(game_state_text)
    my_cards = state.get('MYOPEN', []) + state.get('MYCLOSED', [])
    total = 0
    aces = 0
    for card in my_cards:
        if " of " in card.lower(): rank = card.split(' of ')[0]
        else: rank = card.split(' ')[0]
        if rank.lower() == 'ace': aces += 1
        else: total += get_card_value(rank, total)
    for _ in range(aces):
        total += 11 if total + 11 <= 21 else 1
            
    if total < 17:
        reasoning = f"Current total is {total}, which is less than 17. Must HIT."
        return ["* PLAY: src: PUBLIC_DECK, dest: MYOPEN, card: None", "* PASS"], reasoning
    else:
        reasoning = f"Current total is {total}, which is 17 or higher. Must STAND."
        return ["* PASS"], reasoning
