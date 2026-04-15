# Proportional Table Layout based on GSD dimensions
import sys
import cv2
import numpy as np
from pathlib import Path
from typing import Tuple, List, Dict

# Add project root and game_structure to sys.path
root = Path(__file__).parent.parent
sys.path.append(str(root))
sys.path.append(str(root / "game_structure"))

from game_structure.models import Point2D
from game_structure.gsd import TABLE_WIDTH, TABLE_HEIGHT

# Scale: 200 pixels = 160 mm (16 cm) -> 1 px = 0.8 mm
CARD_W = 70   # 56mm / 0.8
CARD_H = 108  # 86mm / 0.8

# Forgiving hit-box size for detection (larger than actual card)
BOX_W = 105
BOX_H = 140

# --- Fixed Object Regions ---
BOTTOM_OBJ_Y_START = TABLE_HEIGHT - 330

# Adjusted TOP_OBJECT to sit between the physical cards without overlap
TOP_OBJ_X_START = 240
TOP_OBJ_X_END = 480
TOP_OBJ_Y_END = 250

# PICKUP moved to Row 3 (previously Row 2)
PICKUP_X_START = 400
PICKUP_X_END = 560
PICKUP_Y_CENTER = 507

GROUP_LOCATIONS = {}

# ROW 1: 6 MYCARDS Cards (Exact coordinates from image)
GROUP_LOCATIONS["MYCARDS_1"] = (65, 215)
GROUP_LOCATIONS["MYCARDS_2"] = (181, 215)
GROUP_LOCATIONS["MYCARDS_3"] = (555, 215)
GROUP_LOCATIONS["MYCARDS_4"] = (661, 215)
GROUP_LOCATIONS["MYCARDS_5"] = (782, 215)
GROUP_LOCATIONS["MYCARDS_6"] = (892, 215)

# ROW 2 (PUBPILEs & MYDECK): 6 slots + MYDECK at the right
GROUP_LOCATIONS["PUBPILE_1"] = (194, 360)
GROUP_LOCATIONS["PUBPILE_2"] = (311, 360)
GROUP_LOCATIONS["PUBPILE_3"] = (423, 360)
GROUP_LOCATIONS["PUBPILE_4"] = (538, 360)
GROUP_LOCATIONS["PUBPILE_5"] = (645, 360)
GROUP_LOCATIONS["PUBPILE_6"] = (761, 360)
GROUP_LOCATIONS["MYDECK"] = (880, 360)

# ROW 3 (DECKs & PICKUP): DECKPLAYER_1, PUBLIC_DECK, and PICKUP
GROUP_LOCATIONS["DECKPLAYER_1"] = (64, 507)
GROUP_LOCATIONS["PUBLIC_DECK"] = (289, 507)

# ROW 4+ (Y > 650): OPENPLAYER (Opponent cards) and DECKPLAYER_2
# Placed lower down out of physical reach, but visible to the camera
GROUP_LOCATIONS["DECKPLAYER_2"] = (750, 650) # Adjusted left to avoid overlap with OPENPLAYER_2_1
for i in range(1, 6):
    y_offset = 650 + (i - 1) * 110
    GROUP_LOCATIONS[f"OPENPLAYER_1_{i}"] = (100, int(y_offset))
    GROUP_LOCATIONS[f"OPENPLAYER_2_{i}"] = (900, int(y_offset))

groups = list(GROUP_LOCATIONS.keys()) + ["BOTTOM_OBJECT", "TOP_OBJECT", "PICKUP"]
def get_group(p: Point2D) -> str:
    # 1. Check Fixed Objects
    if p.y >= BOTTOM_OBJ_Y_START:
        return "BOTTOM_OBJECT"
    if 0 <= p.y <= TOP_OBJ_Y_END and TOP_OBJ_X_START <= p.x <= TOP_OBJ_X_END:
        return "TOP_OBJECT"
    if PICKUP_X_START <= p.x <= PICKUP_X_END and (PICKUP_Y_CENTER - BOX_H // 2) <= p.y <= (PICKUP_Y_CENTER + BOX_H // 2):
        return "PICKUP"

    # 2. Check Card Slots
    for group_name, (cx, cy) in GROUP_LOCATIONS.items():
        is_rotated = "PLAYER_1" in group_name or "PLAYER_2" in group_name or "DECKPLAYER" in group_name or "OPENPLAYER" in group_name
        w = BOX_H if is_rotated else BOX_W
        h = BOX_W if is_rotated else BOX_H
        
        if (cx - w // 2 <= p.x <= cx + w // 2) and \
           (cy - h // 2 <= p.y <= cy + h // 2):
            return group_name
    return "UNKNOWN"

def get_center_cord(group_name: str):
    """
    Returns the (x, y) coordinates of the center of a given group/slot.
    Supports both exact names (MYCARDS_1) and shorthand (MYCARDS1).
    """
    if group_name in GROUP_LOCATIONS:
        return GROUP_LOCATIONS[group_name]
    
    # Handle shorthand like MYCARDS1 -> MYCARDS_1
    import re
    match = re.search(r'([A-Za-z_]+)(\d+)$', group_name)
    if match:
        prefix, idx = match.groups()
        if not prefix.endswith('_'):
            prefix += '_'
        normalized = f"{prefix}{idx}"
        if normalized in GROUP_LOCATIONS:
            return GROUP_LOCATIONS[normalized]
            
    # Handle special objects not in the dict but in the groups list
    if group_name == "BOTTOM_OBJECT":
        return (TABLE_WIDTH // 2, (BOTTOM_OBJ_Y_START + TABLE_HEIGHT) // 2)
    if group_name == "TOP_OBJECT":
        return ((TOP_OBJ_X_START + TOP_OBJ_X_END) // 2, TOP_OBJ_Y_END // 2)
    if group_name == "PICKUP":
        return ((PICKUP_X_START + PICKUP_X_END) // 2, PICKUP_Y_CENTER)

    raise ValueError(f"Group name '{group_name}' not found in layout definitions.")

def visualize_groups():
    vis_img = np.zeros((TABLE_HEIGHT, TABLE_WIDTH, 3), dtype=np.uint8)
    all_possible_groups = groups + ["UNKNOWN"]
    np.random.seed(42)
    group_colors = {g: np.random.randint(50, 255, 3).tolist() for g in all_possible_groups}
    group_colors["UNKNOWN"] = [15, 15, 15] 
    vis_img[:] = group_colors["UNKNOWN"]

    for group_name, (cx, cy) in GROUP_LOCATIONS.items():
        color = group_colors[group_name]
        is_rotated = "PLAYER_1" in group_name or "PLAYER_2" in group_name or "DECKPLAYER" in group_name or "OPENPLAYER" in group_name
        # Use BOX size for visualization of hitboxes
        w = BOX_H if is_rotated else BOX_W
        h = BOX_W if is_rotated else BOX_H
        
        tl = (cx - w // 2, cy - h // 2)
        br = (cx + w // 2, cy + h // 2)
        
        cv2.rectangle(vis_img, tl, br, color, -1)
        cv2.rectangle(vis_img, tl, br, (255, 255, 255), 1)
        
        # Draw Center Point and Coordinates
        cv2.circle(vis_img, (cx, cy), 3, (0, 0, 255), -1)
        cv2.putText(vis_img, f"({cx},{cy})", (cx - 40, cy + 15), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 255), 1)
        
        lbl = group_name.replace("PLAYER", "P")
        cv2.putText(vis_img, lbl, (cx - 40, cy - 5), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)

    # Draw Fixed Objects and their centers
    for obj_name in ["BOTTOM_OBJECT", "TOP_OBJECT", "PICKUP"]:
        ocx, ocy = get_center_cord(obj_name)
        
        if obj_name == "BOTTOM_OBJECT":
            cv2.rectangle(vis_img, (0, BOTTOM_OBJ_Y_START), (TABLE_WIDTH, TABLE_HEIGHT), group_colors[obj_name], -1)
        elif obj_name == "TOP_OBJECT":
            cv2.rectangle(vis_img, (TOP_OBJ_X_START, 0), (TOP_OBJ_X_END, TOP_OBJ_Y_END), group_colors[obj_name], -1)
        elif obj_name == "PICKUP":
            cv2.rectangle(vis_img, (PICKUP_X_START, PICKUP_Y_CENTER - BOX_H // 2), (PICKUP_X_END, PICKUP_Y_CENTER + BOX_H // 2), group_colors[obj_name], -1)
            # Add a white border so it's visibly distinct
            cv2.rectangle(vis_img, (PICKUP_X_START, PICKUP_Y_CENTER - BOX_H // 2), (PICKUP_X_END, PICKUP_Y_CENTER + BOX_H // 2), (255, 255, 255), 2)
            
        # Draw Center Dot and Label for Objects
        cv2.circle(vis_img, (ocx, ocy), 5, (0, 0, 255), -1)
        cv2.putText(vis_img, f"{obj_name} ({ocx},{ocy})", (ocx - 80, ocy), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

        # --- Replace the old saving code with this ---
    output_filename = "board_layout_shafir_02.jpg"

    # This forces the path to be in the exact same folder as your python script
    output_path = str(Path(__file__).parent / output_filename)

    cv2.imwrite(output_path, vis_img)

    # This will print the exact folder path to your terminal so you can click or copy it!
    print(f"SUCCESS! Visualization saved exactly here:\n{output_path}")

if __name__ == "__main__":
    visualize_groups()
