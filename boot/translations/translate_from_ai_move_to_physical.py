import sys
import re
import time
from pathlib import Path

# --- PATH SETUP ---
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))
if str(ROOT_DIR / "game_structure") not in sys.path:
    sys.path.append(str(ROOT_DIR / "game_structure"))

from main.board_layout import get_center_cord

# Updated imports based on the provided phisical_function.py
from game_structure.phisical_function import (
    move_player, grab, drop, flip,
    put_card_in_basket, align_basket, grab_from_basket, move_to_safe_position,
    dealer_shoot, take_and_analyze_shot_card, look_at_card,
    pixels_to_physical
)
from boot.photo_to_state_pipeline.photo_to_state_translation import get_occupied_slots
import boot.hand_manager as hm

# Lists to track which areas are typically face-up or face-down
OPEN_AREAS = ["PUBPILE", "MYCARDS", "OPENPLAYER", "MYOPEN"]
CLOSED_AREAS = ["MYCARDS", "PICKUP", "MYDECK", "DECKPLAYER", "PUBLIC_DECK", "MYCLOSED"]


def is_face_up_area(group_name: str) -> bool:
    return any(area in group_name for area in OPEN_AREAS)


def is_face_down_area(group_name: str) -> bool:
    return any(area in group_name for area in CLOSED_AREAS)


def find_next_empty_slot(base_name: str, occupied_set: set) -> str:
    if base_name not in ["MYOPEN", "MYCLOSED", "MYCARDS"]:
        return base_name

    physical_base = "MYCARDS"
    for i in range(1, 7):
        candidate = f"{physical_base}_{i}"
        if candidate not in occupied_set:
            return candidate
    return f"{physical_base}_1"


def normalize_group_name(name: str) -> str:
    name = name.upper().replace("*", "").replace(":", "").strip()
    if re.match(r"^P\d+$", name):
        return f"PUBPILE_{name[1:]}"
    if name in ["MYCLOSED", "MYOPEN", "MYCARDS"]:
        return "MYCARDS_1"
    if name == "PUBLIC_DECK":
        try:
            get_center_cord("PUBLIC_DECK")
            return "PUBLIC_DECK"
        except:
            return "PICKUP"
    return name


def execute_arm_move(line: str, occupied_slots: set):
    """Parses and executes a single movement, ensuring safe flipping logic."""
    try:
        src_match = re.search(r"src:\s*([^,]+)", line, re.IGNORECASE)
        dest_match = re.search(r"dest:\s*([^,]+)", line, re.IGNORECASE)
        card_match = re.search(r"card:\s*([^,\n]+)", line, re.IGNORECASE)

        if not (src_match and dest_match):
            return

        src_raw = src_match.group(1).strip().upper()
        dest_raw = dest_match.group(1).strip().upper()
        src_card_val = card_match.group(1).strip() if card_match else "Unknown"

        src_name = normalize_group_name(src_raw)
        dest_name = find_next_empty_slot(dest_raw, occupied_slots)
        if dest_name == dest_raw:
            dest_name = normalize_group_name(dest_raw)

        print(f"\n==================================================")
        print(f"🎯 [Turn Sequence] Move {src_card_val} from {src_name} to {dest_name}")
        print(f"==================================================")

        # --- PHASE 1: ACQUIRE SOURCE COORDINATES ---
        is_dealer_draw = src_name in ["PUBLIC_DECK", "PICKUP"]

        if is_dealer_draw:
            print(f"🌟 [Phase 1] NEW CARD: Drawing from Dealer.")
            dealer_shoot(1, 1)
            print("🦾 [Arm] Moving out of the camera's view to (3.5, 6)...")
            move_player((3.5, 6))
            time.sleep(1.5)  # Give the arm a moment to finish moving so it doesn't blur the photo!
            (card_x, card_y), card_angle = take_and_analyze_shot_card()
            if(card_x ==0 and card_y ==0 and card_angle == 0):
                print("🚨 [Safety Halt] Could not locate the dealt card. Aborting sequence.")
                return  # Stops the entire function right here
            src_coords = pixels_to_physical(card_x, card_y)
            src_angle = card_angle
        else:
            print(f"📦 [Phase 1] EXISTING CARD: Picking up from board.")
            pixel_coords = get_center_cord(src_name)
            src_coords = pixels_to_physical(pixel_coords[0], pixel_coords[1])
            src_angle = 0

        # --- PHASE 2: ACQUIRE DESTINATION COORDINATES ---
        dest_pixel_coords = get_center_cord(dest_name)
        dest_coords = pixels_to_physical(dest_pixel_coords[0], dest_pixel_coords[1])
        target_angle = 90 if ("PLAYER" in dest_name) else 0

        # --- PHASE 3: LOGIC & MEMORY ---
        print(f"\n🧠 [Phase 3] LOGIC & ORIENTATION")

        is_currently_face_up = is_face_up_area(src_name)
        needs_to_be_face_up = (dest_raw == "MYOPEN" or "PUBPILE" in dest_name)

        current_physical_coords = src_coords

        # Outbound memory clear
        if src_name.startswith("MYCARDS"):
            hm.remove_from_hand(src_name)
        elif is_dealer_draw:
            hm.save_pickup([None, "CLOSED"])

        # Inspection & Inbound Memory Logic
        if dest_name.startswith("MYCARDS") and dest_raw in ["MYCLOSED", "MYCARDS"]:
            print("🔄 INFO: Inspecting card for internal memory...")

            # --- התיקון שכאן: קוראים את הקלף רק כשהוא סגור בסלסלה ---
            if not is_currently_face_up:
                print("👁️ [Vision] Card is FACE-DOWN in basket. Scanning from below...")
                card_identity = look_at_card()
                hm.add_to_hand(dest_name, card_identity, status="CLOSED")
            else:
                # הקלף פתוח, המצלמה התחתונה לא תראה את הערך שלו. נשתמש במידע מה-AI.
                print(f"⚠️ [Vision] Card is FACE-UP. Cannot scan from below. Using known value: {src_card_val}")
                card_identity = src_card_val if src_card_val != "Unknown" else "Unknown Card"
                hm.add_to_hand(dest_name, card_identity, status="CLOSED")

            needs_to_be_face_up = False

        elif dest_name.startswith("MYCARDS") and dest_raw == "MYOPEN":
            hm.add_to_hand(dest_name, src_card_val, status="OPEN")
            needs_to_be_face_up = True

        elif dest_name in ["PICKUP", "PUBLIC_DECK"]:
            hm.save_pickup([src_card_val, "CLOSED"])
            needs_to_be_face_up = False

        # --- PHASE 4: EXECUTION & FINAL FLIP ---
        if is_currently_face_up != needs_to_be_face_up:
            print(f"🔄 [Action] Flipping card to match {dest_name} rules.")
            flip(current_physical_coords, target_angle, dest_coords)

            if src_name.startswith("MYCARDS"):
                hm.flip_card_status(src_name)
        else:
            if current_physical_coords == src_coords:
                print(f"🧺 [Phase 4] ROUTING & PLACEMENT (No Flip)")
                put_card_in_basket(src_coords, src_angle)

                print("🦾 [Arm] Moving to safe resting position away from basket.")
                move_to_safe_position()

                align_basket(target_angle)
                grab_from_basket(dest_coords, target_angle)

        # Update board occupancy
        occupied_slots.add(dest_name)
        if src_name in occupied_slots:
            occupied_slots.remove(src_name)

        print(f"✅ Move Complete.\n")

    except Exception as e:
        print(f"❌ [Arm] Error processing line '{line}': {e}")


def execute_dealer_deal(line: str):
    """Parses and executes a 'PLAYER X: N' dealer instruction."""
    try:
        match = re.search(r"([^:]+):\s*(\d+)", line)
        if not match:
            return

        label = match.group(1).strip().upper()
        count = int(match.group(2))

        if count <= 0:
            return

        # Determine player ID based on angle mapping in phisical_function.py
        # 0: Left, 1: Center, 2: Right
        player_id = 1
        if "PLAYER 1" in label or "MY" in label:
            player_id = 1
        elif "PLAYER 2" in label:
            player_id = 0
        elif "PLAYER 3" in label:
            player_id = 2
        else:
            return

        print(f"🚀 [Dealer] Dealing {count} cards to {label} (Player ID {player_id})...")
        dealer_shoot(player_id, count)

    except Exception as e:
        print(f"❌ [Dealer] Error: {e}")


def translate_and_execute(move_text: str):
    """Main entry point to parse and execute instructions."""
    print(f"\n⚙️ Translating Instructions:\n{move_text}\n")

    occupied_slots = get_occupied_slots(None)

    lines = move_text.strip().split('\n')
    for line in lines:
        line = line.strip()
        if not line or "PASS" in line.upper():
            continue

        if "SRC:" in line.upper() and "DEST:" in line.upper():
            execute_arm_move(line, occupied_slots)
        elif re.search(r"([^:]+):\s*\d+", line):
            execute_dealer_deal(line)
        else:
            print(f"⚠️ [Translator] Skipping unrecognized line: {line}")


def read_and_execute_next_move():
    """Reads the next move from the data file and executes it."""
    next_move_file = ROOT_DIR / "prompt_engineering_bot" / "data" / "next_move.txt"

    if next_move_file.exists():
        print(f"📖 Reading next move from {next_move_file}...")
        with open(next_move_file, "r") as f:
            move_text = f.read()

        if move_text.strip():
            translate_and_execute(move_text)
        else:
            print("Empty next_move.txt file.")
    else:
        print(f"File not found: {next_move_file}")


if __name__ == "__main__":
    read_and_execute_next_move()