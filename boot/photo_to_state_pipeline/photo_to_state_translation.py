import sys
import os
from pathlib import Path
from unittest.mock import MagicMock

# --- MOCK ARDUINO & SUPPRESS PRINTS FOR TESTING ---
# Mock out the arduino control module entirely so it never tries to connect
sys.modules['arduino_control.moveitmoveit'] = MagicMock()

import io
import cv2
from pathlib import Path

# --- PATH SETUP ---
BOOT_DIR = Path(__file__).parent.parent
ROOT_DIR = BOOT_DIR.parent
sys.path.append(str(ROOT_DIR))
sys.path.append(str(ROOT_DIR / "game_structure"))
sys.path.append(str(BOOT_DIR))

# Locations for data and output
TEST_DIR = Path(__file__).parent
DATA_DIR = TEST_DIR  # photo.jpg is now in the same folder

from main.board_layout import get_group
from game_structure.game_state import Card as GCard, Player as GPlayer
from game_structure.card_classification import TemplateCardClassifier
from game_structure.models import CardDetectionResult
import boot.hand_manager as hm

"""
FILE: photo_to_state_translation.py

DESCRIPTION:
    When imported: Provides logical game state translation functions.
    When run directly: Acts as a pipeline that takes `boot/data/photo.jpg` and updates `result_state.txt`.
"""

def get_current_game_state(res: CardDetectionResult) -> str:
    if res is None:
        return "ERROR: No detection data provided."

    # Force a reload of the hand state from disk so we don't use stale memory
    hm.CLOSED = hm.load_hand()

    tpl_classifier = TemplateCardClassifier()
    print("🗂️ Translating physical card positions to logical game state...")
    
    piles_mapping = {f"PUBPILE_{i}": None for i in range(1, 7)}
    public_deck = False
    my_open_cards = []
    my_face_down_slots = []
    my_deck_exists = False
    players_data = {
        "1": {"open": [], "hand": 0, "deck": False},
        "2": {"open": [], "hand": 0, "deck": False}
    }
    
    for card in res.open_cards:
        group_name = get_group(card.center)
        
        is_back = False
        if card.classification and card.classification.label not in [None, "NO_TFLITE", "Unknown"]:
            if card.classification.label == "BACK":
                is_back = True
            else:
                rank, suit = card.classification.rank, card.classification.suit
        elif card.warped_image is not None:
            tpl_res = tpl_classifier.classify_image(card.warped_image)
            if tpl_res.label == "BACK":
                is_back = True
            else:
                rank, suit = tpl_res.rank, tpl_res.suit
        else:
            rank, suit = "Unknown", "Unknown"
            
        if is_back:
            # Treat this card as a face-down card instead
            if group_name == "PICKUP" or group_name == "PUBLIC_DECK":
                public_deck = True
            elif group_name.startswith("MYCARDS"):
                my_face_down_slots.append(group_name)
            elif group_name == "MYDECK":
                my_deck_exists = True
            elif group_name == "DECKPLAYER_1":
                players_data["1"]["deck"] = True
            elif group_name == "DECKPLAYER_2":
                players_data["2"]["deck"] = True
            elif "OPENPLAYER_1" in group_name:
                players_data["1"]["hand"] += 1
            elif "OPENPLAYER_2" in group_name:
                players_data["2"]["hand"] += 1
            continue
            
        gcard = GCard(rank=rank, suit=suit)
        if group_name in piles_mapping:
            piles_mapping[group_name] = gcard
        elif group_name.startswith("MYCARDS"):
            my_open_cards.append((group_name, gcard))
        elif "OPENPLAYER_1" in group_name:
            players_data["1"]["open"].append(gcard)
        elif "OPENPLAYER_2" in group_name:
            players_data["2"]["open"].append(gcard)
        elif group_name == "DECKPLAYER_1":
            players_data["1"]["deck"] = True
        elif group_name == "DECKPLAYER_2":
            players_data["2"]["deck"] = True
        elif group_name == "MYDECK":
            my_deck_exists = True
        elif group_name == "PICKUP" or group_name == "PUBLIC_DECK":
            public_deck = True
    
    for card in res.face_down_cards:
        group_name = get_group(card.center)
        if group_name == "PICKUP" or group_name == "PUBLIC_DECK":
            public_deck = True
        elif group_name.startswith("MYCARDS"):
            my_face_down_slots.append(group_name)
        elif group_name == "MYDECK":
            my_deck_exists = True
        elif group_name == "DECKPLAYER_1":
            players_data["1"]["deck"] = True
        elif group_name == "DECKPLAYER_2":
            players_data["2"]["deck"] = True
        elif "OPENPLAYER_1" in group_name:
            players_data["1"]["hand"] += 1
        elif "OPENPLAYER_2" in group_name:
            players_data["2"]["hand"] += 1

    # --- FINAL FORMATTING ---
    output = []
    for i in range(1, 7):
        pile_key = f"PUBPILE_{i}"
        card = piles_mapping.get(pile_key)
        val = f"{card.rank} of {card.suit}" if card else "FALSE"
        output.append(f"P{i}: {val}")
    output.append("")

    memory_modified = False
    
    # 1. Update hand_state with open cards from the photo
    for slot, c in my_open_cards:
        val_str = f"{c.rank} of {c.suit}"
        if hm.CLOSED.get(slot) != [val_str, "OPEN"]:
            hm.CLOSED[slot] = [val_str, "OPEN"]
            memory_modified = True

    # 2. Update hand_state with closed cards from the photo
    for slot in my_face_down_slots:
        data = hm.CLOSED.get(slot)
        if data and isinstance(data, list) and len(data) >= 2 and data[0] is not None:
            if data[1] != "CLOSED":
                hm.CLOSED[slot] = [data[0], "CLOSED"]
                memory_modified = True
        else:
            if hm.CLOSED.get(slot) != ["Unknown", "CLOSED"]:
                hm.CLOSED[slot] = ["Unknown", "CLOSED"]
                memory_modified = True

    # 3. Update hand_state with empty cards from the photo
    for slot in list(hm.CLOSED.keys()):
        is_open_in_vision = any(s == slot for s, _ in my_open_cards)
        is_face_down_in_vision = slot in my_face_down_slots
        if not is_open_in_vision and not is_face_down_in_vision:
            if hm.CLOSED.get(slot) != [None, None]:
                hm.CLOSED[slot] = [None, None]
                memory_modified = True

    if memory_modified:
        hm.save_hand(hm.CLOSED)

    # 4. Generate output based purely on hand_state
    my_open_list = []
    my_closed_list = []
    for slot, data in hm.CLOSED.items():
        if data and isinstance(data, list) and len(data) >= 2:
            card_val, status = data[0], data[1]
            if status == "OPEN":
                my_open_list.append(f'"{card_val}"')
            elif status == "CLOSED":
                my_closed_list.append(f'"{card_val}"')

    output.append(f"MYOPEN: [{', '.join(my_open_list)}]")
    output.append(f"MYCLOSED: [{', '.join(my_closed_list)}]")
    output.append(f"MYDECK: {str(my_deck_exists).upper()}")
    output.append("")

    for p_idx in ["1", "2"]:
        p_num = int(p_idx) + 1
        data = players_data[p_idx]
        open_list = [f'"{c.rank} of {c.suit}"' for c in data["open"]]
        output.append(f"PLAYER{p_num}_OPEN: [{', '.join(open_list)}]")
        output.append(f"PLAYER{p_num}_DECK: {str(data['deck']).upper()}")
        output.append("")

    output.append(f"PUBLIC_DECK: {str(public_deck).upper()}")
    return "\n".join(output)

def get_occupied_slots(res: CardDetectionResult) -> set:
    if res is None: return set()
    occupied = set()
    for card in res.open_cards + res.face_down_cards:
        group_name = get_group(card.center)
        if group_name != "UNKNOWN": occupied.add(group_name)
    return occupied

def translate_photo_to_file():
    # Suppression of prints during module imports
    old_stdout = sys.stdout
    sys.stdout = open(os.devnull, 'w')
    try:
        from game_structure.gsd import Gsd, camera_params
        from boot.hand_manager import save_pickup
    finally:
        sys.stdout.close()
        sys.stdout = old_stdout

    photo_path = DATA_DIR / "photo.jpg"
    out_path = ROOT_DIR / "prompt_engineering_bot" / "data" / "current_game_state_input.txt"
    marks_path = TEST_DIR / "photo_with_marks.jpg"
    classes_path = TEST_DIR / "photo_with_classes.jpg"
    layout_path = ROOT_DIR / "main" / "board_layout_shafir_02.jpg"
    
    if not photo_path.exists():
        print(f"❌ Error: Could not find '{photo_path}'")
        return False
        
    print(f"📂 Loading '{photo_path}'...")
    img = cv2.imread(str(photo_path))
    gsd = Gsd(camera_params=camera_params)
    res = gsd.process([img])
    img_annotated = res.annotated_image
    
    if img_annotated is None:
        print(f"❌ Error: Failed to process '{photo_path}'.")
        return False

    # --- Process PICKUP cards ---
    pickup_cards = []
    tpl_classifier = TemplateCardClassifier()
    for c in res.face_down_cards:
        if get_group(c.center) == "PICKUP": pickup_cards.append([None, "CLOSED"])
    for c in res.open_cards:
        if get_group(c.center) == "PICKUP":
            is_back = False
            if c.classification and c.classification.label not in [None, "NO_TFLITE", "Unknown"]:
                if c.classification.label == "BACK":
                    is_back = True
                else:
                    rank, suit = c.classification.rank, c.classification.suit
            elif c.warped_image is not None:
                tpl_res = tpl_classifier.classify_image(c.warped_image)
                if tpl_res.label == "BACK":
                    is_back = True
                else:
                    rank, suit = tpl_res.rank, tpl_res.suit
            else: 
                rank, suit = "Unknown", "Unknown"
                
            if is_back:
                pickup_cards.append([None, "CLOSED"])
            else:
                pickup_cards.append([f"{rank} of {suit}", "OPEN"])

    if len(pickup_cards) == 0: save_pickup([None, None])
    elif len(pickup_cards) == 1: save_pickup(pickup_cards[0])
    else: save_pickup(pickup_cards)
    
    state_str = get_current_game_state(res)
    with open(out_path, "w", encoding="utf-8") as f: f.write(state_str)
        
    print("🖍️ Drawing debug marks...")
    marked_img = img_annotated.copy()
    def draw_card(card, label):
        x, y = int(card.center.x), int(card.center.y)
        cv2.circle(marked_img, (x, y), 8, (0, 0, 255), -1)
        cv2.putText(marked_img, f"{label} ({x},{y})", (x + 10, y), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 3)
    for c in res.open_cards:
        lbl = c.classification.label if c.classification and c.classification.label not in [None, "NO_TFLITE", "Unknown"] else "Unknown"
        draw_card(c, lbl)
    for c in res.face_down_cards: draw_card(c, "Face Down")
    cv2.imwrite(str(marks_path), marked_img)
    
    if layout_path.exists():
        layout_img = cv2.imread(str(layout_path))
        if layout_img is not None:
            h, w = marked_img.shape[:2]
            layout_resized = cv2.resize(layout_img, (w, h))
            blended = cv2.addWeighted(marked_img, 0.7, layout_resized, 0.3, 0)
            cv2.imwrite(str(classes_path), blended)
    
    print(f"✅ State saved to {out_path}")
    return True

if __name__ == "__main__":
    translate_photo_to_file()
