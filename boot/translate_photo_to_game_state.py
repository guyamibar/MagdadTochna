import sys
import os
import io
from pathlib import Path

# --- PATH SETUP ---
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))
sys.path.append(str(ROOT_DIR / "game_structure"))

from main.board_layout import get_group
from game_structure.game_state import Card as GCard, Player as GPlayer
from game_structure.card_classification import TemplateCardClassifier
from game_structure.models import CardDetectionResult
import boot.hand_manager as hm

"""
FILE: translate_photo_to_game_state.py
...
"""

def get_current_game_state(res: CardDetectionResult) -> str:
    if res is None:
        return "ERROR: No detection data provided."

    tpl_classifier = TemplateCardClassifier()
    print("🗂️ Translating physical card positions to logical game state...")
    
    piles_mapping = {f"PUBPILE_{i}": None for i in range(1, 7)}
    public_deck = False
    my_open_cards = []
    my_deck_exists = False
    players_data = {
        "1": {"open": [], "hand": 0, "deck": False},
        "2": {"open": [], "hand": 0, "deck": False}
    }
    
    for card in res.open_cards:
        group_name = get_group(card.center)
        if card.classification and card.classification.label not in [None, "NO_TFLITE", "Unknown"]:
            rank, suit = card.classification.rank, card.classification.suit
        elif card.warped_image is not None:
            tpl_res = tpl_classifier.classify_image(card.warped_image)
            rank, suit = tpl_res.rank, tpl_res.suit
        else:
            rank, suit = "Unknown", "Unknown"
            
        gcard = GCard(rank=rank, suit=suit)
        if group_name in piles_mapping:
            piles_mapping[group_name] = gcard
        elif group_name.startswith("MYOPEN"):
            my_open_cards.append(gcard)
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
    
    for card in res.face_down_cards:
        group_name = get_group(card.center)
        if group_name == "PICKUP":
            public_deck = True
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

    my_open_list = [f'"{c.rank} of {c.suit}"' for c in my_open_cards]
    output.append(f"MYOPEN: [{', '.join(my_open_list)}]")
    
    # MYCLOSED: Use the actual identified cards from hand_manager.py
    # Instead of counting anonymous backsides, we provide the full identity.
    actual_hand = hm.get_hand_list()
    my_closed_list = [f'"{val}"' for val in actual_hand]
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
