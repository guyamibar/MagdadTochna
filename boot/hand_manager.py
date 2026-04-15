import sys
import json
from pathlib import Path

# --- PATH SETUP ---
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

# Path to the persistent storage files
HAND_STATE_FILE = ROOT_DIR / "prompt_engineering_bot" / "data" / "hand_state.txt"
PICKUP_STATE_FILE = ROOT_DIR / "prompt_engineering_bot" / "data" / "pickup.txt"

# Import the actual implementation from the physical function folder

def load_hand():
    """Loads the hand state from the text file. Creates it if missing."""
    default_hand = {f"MYCARDS_{i}": [None, None] for i in range(1, 7)}
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
    """Saves the current hand state to the text file and updates memory."""
    global CLOSED
    CLOSED = hand_dict
    try:
        HAND_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        HAND_STATE_FILE.write_text(json.dumps(hand_dict, indent=4), encoding="utf-8")
    except Exception as e:
        print(f"❌ [HandManager] Error saving hand state: {e}")

def load_pickup():
    """Loads the pickup state."""
    default = [None, None]
    if not PICKUP_STATE_FILE.exists():
        return default
    try:
        content = PICKUP_STATE_FILE.read_text(encoding="utf-8")
        if not content.strip():
            return default
        return json.loads(content)
    except:
        return default

def save_pickup(data):
    """Saves the pickup state."""
    try:
        PICKUP_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        PICKUP_STATE_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")
    except Exception as e:
        print(f"❌ [HandManager] Error saving pickup state: {e}")

# Initial load on import
CLOSED = load_hand()
PICKUP = load_pickup()

def add_to_hand(slot_name, card_val, status="CLOSED"):
    """Updates the CLOSED state and saves to disk."""
    global CLOSED
    if slot_name in CLOSED:
        CLOSED[slot_name] = [card_val, status]
        save_hand(CLOSED)
        print(f"📥 [HandManager] Persistent: Added {card_val} ({status}) to {slot_name}")

def remove_from_hand(slot_name):
    """Clears a card from the state and saves to disk."""
    global CLOSED
    if slot_name in CLOSED:
        card_data = CLOSED[slot_name]
        CLOSED[slot_name] = [None, "CLOSED"]
        save_hand(CLOSED)
        print(f"📤 [HandManager] Persistent: Removed {card_data[0]} from {slot_name}")
        return card_data[0]
    return None

def get_hand_list(status_filter=None):
    """Returns a list of card names, optionally filtered by status."""
    if status_filter:
        return [val[0] for val in CLOSED.values() if val[0] is not None and val[1] == status_filter]
    return [val[0] for val in CLOSED.values() if val[0] is not None]

def flip_card_status(slot_name):
    """Toggles the status of a card between OPEN and CLOSED."""
    global CLOSED, PICKUP
    if slot_name in ["PICKUP", "PUBLIC_DECK"]:
        current_status = PICKUP[1]
        new_status = "OPEN" if current_status == "CLOSED" else "CLOSED"
        PICKUP[1] = new_status
        save_pickup(PICKUP)
        print(f"🔄 [HandManager] Flipped Pickup to {new_status}")
        return

    if slot_name in CLOSED and CLOSED[slot_name][0] is not None:
        current_status = CLOSED[slot_name][1]
        new_status = "OPEN" if current_status == "CLOSED" else "CLOSED"
        CLOSED[slot_name][1] = new_status
        save_hand(CLOSED)
        print(f"🔄 [HandManager] Flipped {slot_name} to {new_status}")
