import sys
import json
from pathlib import Path

# --- PATH SETUP ---
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

# Path to the persistent storage file
HAND_STATE_FILE = ROOT_DIR / "prompt_engineering_bot" / "data" / "hand_state.txt"

# Import the actual implementation from the physical function folder
from game_structure.phisical_function import look_at_card

def load_hand():
    """Loads the hand state from the text file. Creates it if missing."""
    default_hand = {f"MYCLOSED_{i}": None for i in range(1, 7)}
    if not HAND_STATE_FILE.exists():
        return default_hand
    try:
        content = HAND_STATE_FILE.read_text(encoding="utf-8")
        if not content.strip():
            return default_hand
        return json.loads(content)
    except Exception as e:
        print(f"⚠️ [HandManager] Error loading hand state: {e}")
        return default_hand

def save_hand(hand_dict):
    """Saves the current hand state to the text file."""
    try:
        HAND_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        HAND_STATE_FILE.write_text(json.dumps(hand_dict, indent=4), encoding="utf-8")
    except Exception as e:
        print(f"❌ [HandManager] Error saving hand state: {e}")

# Initial load on import
CLOSED = load_hand()

def add_to_hand(slot_name, card_val):
    """Updates the CLOSED state and saves to disk."""
    global CLOSED
    if slot_name in CLOSED:
        CLOSED[slot_name] = card_val
        save_hand(CLOSED)
        print(f"📥 [HandManager] Persistent: Added {card_val} to {slot_name}")

def remove_from_hand(slot_name):
    """Clears a card from the state and saves to disk."""
    global CLOSED
    if slot_name in CLOSED:
        card_val = CLOSED[slot_name]
        CLOSED[slot_name] = None
        save_hand(CLOSED)
        print(f"📤 [HandManager] Persistent: Removed {card_val} from {slot_name}")
        return card_val
    return None

def get_hand_list():
    """Returns a list of card names currently in MYCLOSED slots."""
    return [val for val in CLOSED.values() if val is not None]
