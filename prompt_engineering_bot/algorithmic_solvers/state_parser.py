import re
import json

def clean_card_name(card_str):
    card_str = card_str.strip().lower().strip('"')
    if not card_str or card_str == "false" or card_str == "none":
        return None
    parts = card_str.replace(" of ", " ").split()
    if len(parts) >= 2:
        return f"{parts[0].capitalize()} of {parts[1].capitalize()}"
    return card_str.capitalize()

def parse_game_state(text):
    """
    Parses the NEW robust format:
    P1: K of diamonds
    MYOPEN: ["card1", "card2"]
    MYDECK: TRUE
    ...
    """
    state = {
        'PUBPILE': {},
        'MYOPEN': [],
        'MYCLOSED': [],
        'MYDECK': False,
        'PLAYER2_OPEN': [],
        'PLAYER2_DECK': False,
        'PLAYER3_OPEN': [],
        'PLAYER3_DECK': False,
        'PUBDECK': False
    }

    lines = text.split('\n')
    for line in lines:
        line = line.split('#')[0].strip() # Remove comments
        if not line or ':' not in line: continue
        
        key, val = [x.strip() for x in line.split(':', 1)]
        
        # P1-P6
        if re.match(r"P[1-6]", key):
            idx = int(key[1])
            cleaned = clean_card_name(val)
            if cleaned: state['PUBPILE'][idx] = cleaned
            
        # Lists: MYOPEN, MYCLOSED, PLAYERn_OPEN
        elif key in ["MYOPEN", "MYCLOSED", "PLAYER2_OPEN", "PLAYER3_OPEN"]:
            try:
                # Expecting JSON-like list: ["card1", "card2"]
                cards = json.loads(val)
                state[key] = [clean_card_name(c) for c in cards if clean_card_name(c)]
            except:
                # Fallback for simple comma list: [card1, card2]
                content = val.strip('[]')
                if content and "FALSE" not in content.upper() and "NONE" not in content.upper():
                    state[key] = [clean_card_name(c) for c in content.split(',') if c.strip()]

        # Booleans: MYDECK, PLAYERn_DECK, PUBLIC_DECK
        elif key in ["MYDECK", "PLAYER2_DECK", "PLAYER3_DECK", "PUBLIC_DECK"]:
            bool_val = "TRUE" in val.upper()
            if key == "PUBLIC_DECK": state['PUBDECK'] = bool_val
            else: state[key] = bool_val

    return state
