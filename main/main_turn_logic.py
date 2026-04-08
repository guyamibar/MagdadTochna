import sys
import os
import cv2
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import numpy as np

# Add project root and relevant directories to sys.path
ROOT = Path(__file__).parent.parent
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / "game_structure"))
sys.path.append(str(ROOT / "prompt_engineering_bot"))

from game_structure.gsd import Gsd, camera_params
from game_structure.phisical_function import grab, drop, move_player
from main.take_image import HighResCamera
from main.board_layout import get_group, get_center_cord
from prompt_engineering_bot.game_engine import analyze_turn
from game_structure.models import DetectedCard, Point2D

# --- Mapping Configuration ---
# Maps board_layout groups to AI-state fields
GROUP_TO_STATE = {
    "PUBPILE": "heaps_heads",
    "MYOPEN": "my_open",
    "MYCLOSED": "my_hand",
    "OPENPLAYER_1": "player2_open",
    "OPENPLAYER_2": "player3_open",
    "DECKPLAYER_1": "player2_deck",
    "DECKPLAYER_2": "player3_deck",
    "MYDECK": "my_deck",
    "PICKUP": "public_deck",
}

def format_card_label(card: DetectedCard) -> str:
    if card.is_face_down:
        return "BACK"
    if card.classification:
        rank = card.classification.rank
        suit_map = {"S": "Spades", "H": "Hearts", "C": "Clubs", "D": "Diamonds"}
        suit = suit_map.get(card.classification.suit, card.classification.suit)
        return f"{rank} of {suit}"
    return "UNKNOWN"

def build_game_state(detected_cards: List[DetectedCard]) -> str:
    """
    Builds the AI-readable game state string from detected cards.
    """
    state_data = {
        "P1": "FALSE", "P2": "FALSE", "P3": "FALSE", "P4": "FALSE", "P5": "FALSE", "P6": "FALSE",
        "MYOPEN": [],
        "MYCLOSED": [],
        "MYDECK": "FALSE",
        "PLAYER2_OPEN": [],
        "PLAYER2_DECK": "FALSE",
        "PLAYER3_OPEN": [],
        "PLAYER3_DECK": "FALSE",
        "PUBLIC_DECK": "FALSE"
    }
    
    # Fill in from detected cards
    for card in detected_cards:
        group_full = get_group(card.center)
        if group_full == "UNKNOWN":
            continue
            
        label = format_card_label(card)
        
        # Handle PUBPILE_i
        if group_full.startswith("PUBPILE_"):
            idx = group_full.split("_")[1]
            state_data[f"P{idx}"] = label
            
        elif group_full.startswith("MYOPEN_"):
            state_data["MYOPEN"].append(label)
            
        elif group_full.startswith("MYCLOSED_"):
            state_data["MYCLOSED"].append(label)
            
        elif group_full == "MYDECK":
            state_data["MYDECK"] = "TRUE"
            
        elif group_full.startswith("OPENPLAYER_1_"):
            state_data["PLAYER2_OPEN"].append(label)
            
        elif group_full.startswith("OPENPLAYER_2_"):
            state_data["PLAYER3_OPEN"].append(label)
            
        elif group_full == "DECKPLAYER_1":
            state_data["PLAYER2_DECK"] = "TRUE"
            
        elif group_full == "DECKPLAYER_2":
            state_data["PLAYER3_DECK"] = "TRUE"
            
        elif group_full == "PICKUP":
            state_data["PUBLIC_DECK"] = "TRUE"

    # Format into string
    lines = []
    for i in range(1, 7):
        lines.append(f"P{i}: {state_data[f'P{i}']}")
    lines.append("")
    lines.append(f"MYOPEN: {state_data['MYOPEN']}")
    lines.append(f"MYCLOSED: {state_data['MYCLOSED']}")
    lines.append(f"MYDECK: {state_data['MYDECK']}")
    lines.append("")
    lines.append(f"PLAYER2_OPEN: {state_data['PLAYER2_OPEN']}")
    lines.append(f"PLAYER2_DECK: {state_data['PLAYER2_DECK']}")
    lines.append("")
    lines.append(f"PLAYER3_OPEN: {state_data['PLAYER3_OPEN']}")
    lines.append(f"PLAYER3_DECK: {state_data['PLAYER3_DECK']}")
    lines.append("")
    lines.append(f"PUBLIC_DECK: {state_data['PUBLIC_DECK']}")
    
    return "\n".join(lines)

def parse_move_line(line: str) -> Optional[Dict]:
    """
    Parses a move line like "* src: MYOPEN, dest: P1, card: Ace of Spades"
    """
    if not line.startswith("*") or "PASS" in line:
        return None
    
    try:
        parts = line.split(",")
        src = parts[0].split(":")[1].strip()
        dest = parts[1].split(":")[1].strip()
        card_label = parts[2].split(":")[1].strip()
        return {"src": src, "dest": dest, "card": card_label}
    except Exception:
        return None

def find_card_coordinate(src_group: str, card_label: str, detected_cards: List[DetectedCard]) -> Optional[Point2D]:
    """
    Finds the coordinate of a specific card in a specific group.
    """
    # Normalize card label if AI uses "Ace" instead of "A" or similar
    # For now, assume exact match or "None"
    
    for card in detected_cards:
        group_full = get_group(card.center)
        if group_full.startswith(src_group):
            if card_label == "None":
                return card.center
            
            detected_label = format_card_label(card)
            if detected_label == card_label:
                return card.center
                
    # Fallback: if we can't find the exact card, take any card from that group
    for card in detected_cards:
        group_full = get_group(card.center)
        if group_full.startswith(src_group):
            return card.center
            
    # Final fallback: use the center of the first slot in that group from board_layout
    try:
        cx, cy = get_center_cord(f"{src_group}_1" if src_group in ["MYOPEN", "MYCLOSED", "PUBPILE"] else src_group)
        return Point2D(x=cx, y=cy)
    except:
        return None

def execute_physical_move(move: Dict, detected_cards: List[DetectedCard]):
    """
    Executes the move physically using the arm.
    """
    src_group = move["src"]
    dest_group = move["dest"]
    card_label = move["card"]
    
    print(f"Executing: Move {card_label} from {src_group} to {dest_group}")
    
    # 1. Find source coordinate (in warped pixels)
    src_coord_px = find_card_coordinate(src_group, card_label, detected_cards)
    if not src_coord_px:
        print(f"Error: Could not find coordinate for source {src_group}")
        return

    # 2. Find destination coordinate (in warped pixels)
    try:
        # If it's a pile (P1-P6), normalize to PUBPILE_i
        if dest_group.startswith("P") and len(dest_group) == 2:
            dest_group_full = f"PUBPILE_{dest_group[1]}"
        else:
            dest_group_full = dest_group
            
        dx, dy = get_center_cord(dest_group_full)
        dest_coord_px = Point2D(x=dx, y=dy)
    except Exception as e:
        print(f"Error: Could not find coordinate for destination {dest_group}: {e}")
        return

    # 3. Transform pixels to arm units (cm)
    h_file = ROOT / "data" / "H_cam_to_arm.npy"
    if h_file.exists():
        H = np.load(h_file)
        def transform(pt: Point2D):
            p = np.array([[pt.x, pt.y]], dtype=np.float32).reshape(-1, 1, 2)
            res = cv2.perspectiveTransform(p, H)
            return (float(res[0][0][0]), float(res[0][0][1]))
    else:
        # Fallback: Simple scale if calibration is missing (Very approximate!)
        # Based on 200px = 15cm -> 1px = 0.075cm
        print("Warning: H_cam_to_arm.npy not found. Using approximate scaling.")
        def transform(pt: Point2D):
            return (pt.x * 0.075, pt.y * 0.075)

    src_arm = transform(src_coord_px)
    dest_arm = transform(dest_coord_px)

    # 4. Perform the move
    print(f"Moving arm to Source: {src_arm}")
    move_player(src_arm) 
    grab()
    
    print(f"Moving arm to Destination: {dest_arm}")
    move_player(dest_arm)
    drop()

def play_turn(structured_rules: str):
    """
    The main turn-playing function.
    """
    # 1. CV Phase
    print("\n--- PHASE 1: CV ---")
    gsd = Gsd(camera_params=camera_params)
    image = HighResCamera().take_image()
    if image is None:
        print("Failed to capture image.")
        return
        
    res = gsd.process([image])
    print(f"Detected {len(res.open_cards)} open cards and {len(res.face_down_cards)} closed cards.")
    
    # 2. Prompt Engineering Phase
    print("\n--- PHASE 2: AI Strategy ---")
    game_state_str = build_game_state(res.all_cards)
    print("Generated Game State:\n", game_state_str)
    
    move_result = analyze_turn(structured_rules, game_state_str)
    print("\nAI Strategy Reasoning:", move_result.get("strategy", "N/A"))
    print("AI Decision:\n", move_result["final_result"])
    
    # 3. Physical Phase
    print("\n--- PHASE 3: Physical Move ---")
    move_lines = move_result["final_result"].strip().split("\n")
    for line in move_lines:
        move = parse_move_line(line)
        if move:
            execute_physical_move(move, res.all_cards)
        elif "PASS" in line:
            print("Turn Pass.")

if __name__ == "__main__":
    # Example usage:
    # structured_rules = "UNO" # or load from cache
    CACHE_FILE = ROOT / "prompt_engineering_bot" / "data" / "structured_rules_cache.txt"
    if CACHE_FILE.exists():
        structured_rules = CACHE_FILE.read_text(encoding="utf-8")
    else:
        structured_rules = "Follow standard Blackjack rules."
        
    play_turn(structured_rules)
