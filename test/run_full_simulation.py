import os
import subprocess
import time
from pathlib import Path

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

results_log = []

def simulate(game, scenarios):
    print(f"Simulating {game}...")
    RULES_FILE.write_text(game, encoding="utf-8")
    for i, state in enumerate(scenarios):
        STATE_FILE.write_text(state, encoding="utf-8")
        res = run_engine()
        results_log.append({
            "game": game,
            "scenario": i+1,
            "state": state,
            "result": res
        })

# --- SCENARIO GENERATORS ---

uno_scenarios = [
    f"PUBLIC PILES TOP CARDS:\n1. Top pile Card: {r} of {s}\n\nMY OPEN CARDS: NONE\nMY CLOSED CARDS: [{h}]\nMYDECK: NONE\nPUBLICDECK: TRUE"
    for r, s, h in [
        ("5", "Spades", "5 of Hearts, 2 Clubs"),
        ("K", "Diamonds", "2 Diamonds, A Spades"),
        ("2", "Clubs", "8 hearts, 9 diamonds"), # No match
        ("A", "Hearts", "A Spades, K Hearts"),
        ("10", "Spades", "10 spades"),
        ("7", "Diamonds", "2 diamonds"),
        ("NONE", "NONE", "3 of hearts"), # Empty pile
        ("Q", "Clubs", "Q diamonds, 2 clubs"),
        ("3", "Hearts", "3 spades"),
        ("9", "Spades", "9 hearts, 2 clubs"),
        ("4", "Diamonds", "4 hearts, 4 clubs"),
        ("J", "Clubs", "J spades"),
        ("6", "Hearts", "6 diamonds"),
        ("2", "Spades", "3 clubs, 4 diamonds"), # No match
        ("8", "Hearts", "8 spades, 2 hearts")
    ]
]

bj_scenarios = [
    f"PUBLIC PILES TOP CARDS: NONE\nMY OPEN CARDS: [{h}]\nMY CLOSED CARDS: NONE\nMYDECK: NONE\nPUBLICDECK: TRUE"
    for h in [
        "2 of Spades, 3 of Hearts", # 5
        "10 of Spades, 6 of Hearts", # 16
        "10 of Spades, 7 of Hearts", # 17 (Stand)
        "Ace of Spades, 5 of Hearts", # 16 (Soft)
        "Ace of Spades, 6 of Hearts", # 17 (Soft - Stand)
        "K of Clubs, Q of Diamonds", # 20
        "2 of Hearts, 2 of Clubs, 2 of Spades", # 6
        "9 of Diamonds, 7 of Spades", # 16
        "9 of Diamonds, 8 of Spades", # 17
        "Ace of Hearts, Ace of Clubs, 5 of Spades", # 17
        "10 of Hearts, 5 of Spades", # 15
        "J of Spades, 2 of Diamonds, 4 of Clubs", # 16
        "Q of Hearts, 8 of Diamonds", # 18
        "7 of Clubs, 7 of Spades", # 14
        "A of Diamonds, 9 of Hearts" # 20
    ]
]

trash_scenarios = [
    f"PUBLIC PILES TOP CARDS:\n1. Top pile Card: {p1}\n5. Top pile Card: {p5}\nMY OPEN CARDS: NONE\nMY CLOSED CARDS: [{h}]\nMYDECK: NONE\nPUBLICDECK: TRUE"
    for p1, p5, h in [
        ("NONE", "NONE", ""), # Empty hand
        ("NONE", "NONE", "5 of Spades"), # Valid move to 5
        ("Ace of Hearts", "NONE", "Ace of Spades"), # Slot 1 full
        ("NONE", "NONE", "Jack of Clubs"), # Invalid rank
        ("NONE", "NONE", "Ace of Diamonds"), # Valid move to 1
        ("NONE", "NONE", "10 of Hearts"), # Valid move to 10
        ("NONE", "5 of Clubs", "5 of Hearts"), # Slot 5 full
        ("NONE", "NONE", "2 of Spades"),
        ("NONE", "NONE", "3 of Spades"),
        ("NONE", "NONE", "4 of Spades"),
        ("NONE", "NONE", "6 of Spades"),
        ("NONE", "NONE", "7 of Spades"),
        ("NONE", "NONE", "8 of Spades"),
        ("NONE", "NONE", "9 of Spades"),
        ("NONE", "NONE", "Queen of Spades") # Invalid
    ]
]

war_scenarios = ["PUBLIC PILES TOP CARDS: 10 of Hearts\nMY OPEN CARDS: NONE\nMY CLOSED CARDS: NONE\nMYDECK: [Hidden]\nPUBLICDECK: FALSE"] * 15

# Run all
simulate("UNO", uno_scenarios)
simulate("BLACKJACK", bj_scenarios)
simulate("TRASH", trash_scenarios)
simulate("WAR", war_scenarios)

# Final Print
print("\n" + "#"*50)
print("FINAL SIMULATION REPORT")
print("#"*50 + "\n")

for r in results_log:
    print(f"GAME: {r['game']} | SCENARIO {r['scenario']}")
    print(f"RULES: {r['game']}")
    print(f"STATE:\n{r['state']}")
    print(f"RESULT:\n{r['result']}")
    print("-" * 30)
