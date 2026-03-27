from state_parser import parse_game_state

def solve(game_state_text):
    """Algorithmic solver for War with Reasoning and new format."""
    state = parse_game_state(game_state_text)
    reasoning = "In War, you must play the next card from your personal deck to the central battle pile (P1)."
    return ["* PLAY: src: MYDECK, dest: P1, card: None", "* PASS"], reasoning
