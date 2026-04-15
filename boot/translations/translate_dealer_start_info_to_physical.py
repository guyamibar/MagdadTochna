import sys
import re
from pathlib import Path

"""
FILE: translate_dealer_start_info_to_physical.py

DESCRIPTION:
    Translates initial dealing instructions from Telegram into a call 
    to the physical dealing black box.
"""

# --- PATH SETUP ---
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

# Import the black box from the physical function folder
from game_structure.phisical_function import deal_cards as physical_deal

def deal_cards(dealing_info: str):
    """
    Parses the dealing string and triggers the physical deal sequence.
    """
    print(f"\n📨 [Dealer] Processing Incoming Instructions:\n{dealing_info}")
    
    lines = dealing_info.strip().split('\n')
    
    num_players = 0
    cards_per_player = 0
    public_cards = 0
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        try:
            match = re.search(r"([^:]+):\s*(\d+)", line)
            if not match:
                continue
                
            label = match.group(1).strip().upper()
            count = int(match.group(2))
            
            if "PLAYER" in label:
                if count > 0:
                    num_players += 1
                    # Assumes symmetric dealing based on the first player encountered
                    if cards_per_player == 0:
                        cards_per_player = count
            elif "PUBLIC" in label:
                public_cards = count
                
        except Exception as e:
            print(f"⚠️ [Dealer] Skip line '{line}': {e}")

    # Trigger the black box
    physical_deal(num_players, cards_per_player)

if __name__ == "__main__":
    # Test case
    test_input = """
    PLAYER 1: 5
    PLAYER 2: 5
    PUBLIC CARDS: 3
    """
    deal_cards(test_input)
