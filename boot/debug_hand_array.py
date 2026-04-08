import sys
from pathlib import Path

# --- PATH SETUP ---
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

# Import the array and the helper functions
from boot.hand_manager import CLOSED, add_to_hand, get_hand_list

def test_hand_initialization():
    print("--- 1. Initial State (Empty) ---")
    print(CLOSED)
    print(f"List view: {get_hand_list()}")
    print()

    print("--- 2. Adding Test Cards ---")
    # Using the manager function to fill the array
    add_to_hand("MYCLOSED_1", "8 of Hearts")
    add_to_hand("MYCLOSED_2", "Queen of Spades")
    add_to_hand("MYCLOSED_3", "3 of Clubs")
    print()

    print("--- 3. Final State (Populated) ---")
    # Print the raw dictionary
    print(f"Raw Dictionary: {CLOSED}")
    
    # Print just the identified cards
    print(f"Active Hand: {get_hand_list()}")

if __name__ == "__main__":
    test_hand_initialization()
