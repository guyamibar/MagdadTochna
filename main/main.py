import sys
from pathlib import Path
from time import sleep

# Add project root and game_structure to sys.path
root = Path(__file__).parent.parent
sys.path.append(str(root))
sys.path.append(str(root / "game_structure"))
from take_image import HighResCamera
import cv2
import numpy as np

from game_structure.gsd import Gsd, camera_params
from board_layout import get_group, visualize_groups

from main_turn_logic import play_turn

if __name__ == "__main__":
    # 1. Visualize the board layout for debugging
    visualize_groups()

    # 2. Load rules (either from Telegram bot cache or default)
    RULES_CACHE = root / "prompt_engineering_bot" / "data" / "structured_rules_cache.txt"
    if RULES_CACHE.exists():
        rules = RULES_CACHE.read_text(encoding="utf-8")
        print(f"Loaded rules from {RULES_CACHE}")
    else:
        rules = "Standard Blackjack rules."
        print("Using default Blackjack rules.")

    # 3. Play a single turn
    camera = HighResCamera()
    camera.start()
    try:
        play_turn(rules)
    except KeyboardInterrupt:
        print("\nTurn interrupted by user.")
    except Exception as e:
        print(f"\nAn error occurred during the turn: {e}")
    finally:
        camera.stop()