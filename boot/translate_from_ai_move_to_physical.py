import sys
import re
from pathlib import Path

# --- PATH SETUP ---
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))
sys.path.append(str(ROOT_DIR / "game_structure"))

from main.board_layout import get_center_cord
from game_structure.phisical_function import move_player, grab, drop, flip
from boot.translate_photo_to_game_state import get_occupied_slots
import boot.hand_manager as hm

# Lists to track which areas are typically face-up or face-down
OPEN_AREAS = ["PUBPILE", "MYOPEN", "OPENPLAYER"]
CLOSED_AREAS = ["MYCLOSED", "PICKUP", "MYDECK", "DECKPLAYER"]

def is_face_up_area(group_name: str) -> bool:
    """Returns True if the group name belongs to an area where cards are face-up."""
    return any(area in group_name for area in OPEN_AREAS)

def is_face_down_area(group_name: str) -> bool:
    """Returns True if the group name belongs to an area where cards are face-down."""
    return any(area in group_name for area in CLOSED_AREAS)

def find_next_empty_slot(base_name: str, occupied_set: set) -> str:
    if base_name not in ["MYOPEN", "MYCLOSED"]:
        return base_name
    for i in range(1, 7):
        candidate = f"{base_name}_{i}"
        if candidate not in occupied_set:
            return candidate
    return f"{base_name}_1"

def translate_and_execute(ai_move_text: str):
    print(f"\n⚙️ Processing AI Move:\n{ai_move_text}")
    print("🔍 Scanning table for occupied slots...")
    occupied_slots = get_occupied_slots(None) # Note: Requires res, usually called from bootstrap with real data
    
    lines = ai_move_text.strip().split('\n')
    for line in lines:
        line = line.strip()
        if not line or "PASS" in line.upper():
            continue
            
        if "src:" in line and "dest:" in line:
            try:
                src_match = re.search(r"src:\s*([^,]+)", line)
                dest_match = re.search(r"dest:\s*([^,]+)", line)
                
                if src_match and dest_match:
                    src_raw = src_match.group(1).strip().upper()
                    dest_raw = dest_match.group(1).strip().upper()
                    
                    src_name = normalize_group_name(src_raw)
                    dest_name = find_next_empty_slot(dest_raw, occupied_slots)
                    if dest_name == dest_raw:
                        dest_name = normalize_group_name(dest_raw)
                    
                    print(f"🎯 Action: Move from {src_name} to {dest_name}")
                    src_coords = get_center_cord(src_name)
                    dest_coords = get_center_cord(dest_name)
                    
                    # 1. Grab
                    move_player(src_coords)
                    grab()

                    # --- HAND MANAGEMENT: LEAVING MYCLOSED ---
                    if src_name.startswith("MYCLOSED"):
                        hm.remove_from_hand(src_name)

                    # --- HAND MANAGEMENT: ENTERING MYCLOSED ---
                    # If we are putting a card into our hand, we look at it FIRST
                    card_identity = "Unknown"
                    if dest_name.startswith("MYCLOSED"):
                        # Logic: Flip it up, look at it, then flip it back down to store it
                        print("🔄 INFO: Inspecting card before putting in MYCLOSED hand...")
                        flip() # Flip up to see rank
                        card_identity = hm.look_at_card()
                        flip() # Flip back down to keep it secret/closed
                        hm.add_to_hand(dest_name, card_identity)

                    # 2. State Flipping
                    if "MYOPEN" in dest_name and is_face_down_area(src_name):
                        flip()
                    elif "MYCLOSED" in dest_name and is_face_up_area(src_name):
                        # Note: If it was already flipped for inspection above, 
                        # this logic might need coordination. For now, we assume simple sequence.
                        flip()
                    
                    # 3. Drop
                    move_player(dest_coords)
                    drop()
                    
                    occupied_slots.add(dest_name)
                    if src_name in occupied_slots:
                        occupied_slots.remove(src_name)
                        
            except Exception as e:
                print(f"❌ Error during physical execution: {e}")

def normalize_group_name(name: str) -> str:
    name = name.upper().replace("*", "").replace(":", "").strip()
    if re.match(r"^P\d+$", name):
        return f"PUBPILE_{name[1:]}"
    if name == "MYCLOSED":
        return "MYCLOSED_1"
    if name == "MYOPEN":
        return "MYOPEN_1"
    return name
