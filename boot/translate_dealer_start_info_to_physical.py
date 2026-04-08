import sys
import re
import time
from pathlib import Path

"""
FILE: translate_dealer_start_info_to_physical.py

DESCRIPTION:
    Translates initial dealing instructions into physical dealer actions. 
    It parses how many cards each player should receive and how many public 
    cards to dispense, then triggers the shooting mechanism.

INPUT:
    - dealing_info (str): A multi-line string specifying card counts.
      Example:
        PLAYER 1: 3
        PLAYER 2: 3
        PLAYER 3: 0
        PUBLIC CARDS: 2

OUTPUT:
    - None (triggers physical hardware actions via physical_function.py).

LOGIC MEANING:
    - PLAYER 1: The Bot. Deals cards to 'MYDECK'.
    - PLAYER 2: Left Opponent. Deals cards to 'DECKPLAYER_1'.
    - PLAYER 3: Right Opponent. Deals cards to 'DECKPLAYER_2'.
    - PUBLIC CARDS: Shared center cards. Deals cards to 'PUBPILE_1'.
    - FOR EACH CARD:
        1. Identifies the target (x,y) from board_layout.
        2. Calls shoot() to dispense the card to those coordinates.
"""

# --- PATH SETUP ---
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))
sys.path.append(str(ROOT_DIR / "game_structure"))

from main.board_layout import get_center_cord
from game_structure.phisical_function import shoot

def deal_cards(dealing_info: str):
    """
    Parses the dealing string and executes the shooting sequence.
    """
    print(f"\n🃏 Starting Deal Sequence:\n{dealing_info}")
    
    lines = dealing_info.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        try:
            # 1. Parse Player/Public counts using Regex
            # Matches "PLAYER X: N" or "PUBLIC CARDS: N"
            match = re.search(r"([^:]+):\s*(\d+)", line)
            if not match:
                continue
                
            label = match.group(1).strip().upper()
            count = int(match.group(2))
            
            if count <= 0:
                continue
                
            # 2. Map label to slot name in board_layout.py
            target_slot = ""
            if "PLAYER 1" in label:
                target_slot = "MYDECK"
            elif "PLAYER 2" in label:
                target_slot = "DECKPLAYER_1"
            elif "PLAYER 3" in label:
                target_slot = "DECKPLAYER_2"
            elif "PUBLIC" in label:
                target_slot = "PUBPILE_1"
            else:
                print(f"⚠️ Unknown dealing label: {label}")
                continue
                
            # 3. Get Coordinates
            coords = get_center_cord(target_slot)
            print(f"🚀 Dealing {count} cards to {label} ({target_slot}) at {coords}...")
            
            # 4. Perform the action for each card
            for i in range(count):
                print(f"   [Card {i+1}/{count}] Shooting to {coords}...")
                shoot(coords)
                
                # Small pause between cards to allow hardware reset
                time.sleep(0.5)
                
        except Exception as e:
            print(f"❌ Error dealing line '{line}': {e}")

if __name__ == "__main__":
    # Test case
    test_input = """
    PLAYER 1: 3
    PLAYER 2: 3
    PLAYER 3: 0
    PUBLIC CARDS: 2
    """
    deal_cards(test_input)
