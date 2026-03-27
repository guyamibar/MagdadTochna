import os
import subprocess
import random
from pathlib import Path
import json

# Paths
BASE_DIR = Path(r"C:\Users\TLP-001\Documents\GitHub\MagdadTochna\prompt_engineering_bot")
DATA_DIR = BASE_DIR / "data"
RULES_FILE = DATA_DIR / "raw_rules_input.txt"
STATE_FILE = DATA_DIR / "current_game_state_input.txt"
MOVE_FILE = DATA_DIR / "next_move.txt"
PYTHON_EXE = Path(r"C:\Users\TLP-001\Documents\GitHub\MagdadTochna\.venv\Scripts\python.exe")
ENGINE_PY = BASE_DIR / "game_engine.py"

def run_engine():
    try:
        subprocess.run([str(PYTHON_EXE), str(ENGINE_PY)], check=True, capture_output=True)
        return MOVE_FILE.read_text(encoding="utf-8").strip()
    except Exception as e:
        return f"ERROR: {e}"

def generate_deck():
    ranks = ['2','3','4','5','6','7','8','9','10','Jack','Queen','King','Ace']
    suits = ['Spades','Hearts','Diamonds','Clubs']
    deck = [f"{r} of {s}" for s in suits for r in ranks]
    random.shuffle(deck)
    return deck

def make_uno_state():
    deck = generate_deck()
    pile = deck.pop()
    hand = [deck.pop() for _ in range(random.randint(1, 7))]
    return f"PUBLIC PILES TOP CARDS:\n1. Top pile Card: {pile}\n\nMY OPEN CARDS: NONE\nMY CLOSED CARDS: [{', '.join(hand)}]\nMYDECK: NONE\nPUBLICDECK: TRUE"

def make_bj_state():
    deck = generate_deck()
    hand = [deck.pop() for _ in range(random.randint(2, 4))]
    return f"PUBLIC PILES TOP CARDS: NONE\nMY OPEN CARDS: [{', '.join(hand)}]\nMY CLOSED CARDS: NONE\nMYDECK: NONE\nPUBLICDECK: TRUE"

def make_trash_state():
    deck = generate_deck()
    hand = [deck.pop()]
    piles = ""
    for i in range(1, 11):
        c = deck.pop() if random.random() > 0.5 else "NONE"
        piles += f"{i}. Top pile Card: {c}\n"
    return f"PUBLIC PILES TOP CARDS:\n{piles}\nMY OPEN CARDS: NONE\nMY CLOSED CARDS: [{', '.join(hand)}]\nMYDECK: NONE\nPUBLICDECK: TRUE"

def make_war_state():
    deck = generate_deck()
    pile = deck.pop()
    return f"PUBLIC PILES TOP CARDS:\n1. Top pile Card: {pile}\nMY OPEN CARDS: NONE\nMY CLOSED CARDS: NONE\nMYDECK: [Hidden]\nPUBLICDECK: FALSE"

def make_custom_state():
    # Simple custom game: Highest card wins. Player must play a card.
    deck = generate_deck()
    pile = deck.pop() if random.random() > 0.5 else "NONE"
    hand = [deck.pop() for _ in range(random.randint(3, 5))]
    return f"PUBLIC PILES TOP CARDS:\n1. Top pile Card: {pile}\n\nMY OPEN CARDS: NONE\nMY CLOSED CARDS: [{', '.join(hand)}]\nMYDECK: NONE\nPUBLICDECK: TRUE"

custom_rules = """Must Have Rules:
1. NUMBER OF PLAYERS: 2
2. NUMBER OF PUBLIC DECKS: 1
3. NUMBER OF PUBLIC PILES: 1
4. CAN A PLAYER PASS WITHOUT PLAYING: NO
5. CAN DRAW FROM PUBLIC PILES: NO
6. CAN DRAW FROM PUBLIC DECKS: YES
7. DO PLAYERS HAVE PERSONAL DECKS: NO

Free Write Rules:
Game: Highest Card
1. Play any card from MY CLOSED CARDS to PUBPILE_1.
2. If no cards, draw from PUBDECK_1 to MY CLOSED CARDS.
"""

scenarios = []
for _ in range(20): scenarios.append(("UNO", make_uno_state()))
for _ in range(20): scenarios.append(("BLACKJACK", make_bj_state()))
for _ in range(20): scenarios.append(("TRASH", make_trash_state()))
for _ in range(20): scenarios.append(("WAR", make_war_state()))
for _ in range(20): scenarios.append((custom_rules, make_custom_state(), "CUSTOM"))

# Save to JSON to be driven by the CLI
with open("eval_scenarios.json", "w") as f:
    json.dump(scenarios, f)

print("Scenarios generated.")
