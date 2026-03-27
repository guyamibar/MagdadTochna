import sys
from pathlib import Path

# Add the current folder to sys.path
sys.path.append(str(Path(__file__).parent))

from blackjack_solver import solve as solve_blackjack
from trash_solver import solve as solve_trash
from uno_solver import solve as solve_uno
from war_solver import solve as solve_war

def run_test(name, solver, scenarios):
    print(f"\n{'='*20}\nTESTING {name.upper()}\n{'='*20}")
    for i, state in enumerate(scenarios):
        print(f"\nScenario {i+1}:")
        print(f"INPUT STATE:\n{state}")
        result = solver(state)
        print(f"SOLVER MOVE: {result}")

# --- SCENARIOS ---

blackjack_scenarios = [
    # 1. Low total
    "PUBLIC PILES TOP CARDS: NONE\nMY OPEN CARDS: NONE\nMY CLOSED CARDS: [2 of Spades, 3 of Hearts]\nMYDECK: NONE\nPUBLICDECK: TRUE",
    # 2. Edge 17
    "PUBLIC PILES TOP CARDS: NONE\nMY OPEN CARDS: NONE\nMY CLOSED CARDS: [10 of Spades, 7 of Hearts]\nMYDECK: NONE\nPUBLICDECK: TRUE",
    # 3. Soft 16 (Ace + 5)
    "PUBLIC PILES TOP CARDS: NONE\nMY OPEN CARDS: NONE\nMY CLOSED CARDS: [Ace of Spades, 5 of Hearts]\nMYDECK: NONE\nPUBLICDECK: TRUE"
]

trash_scenarios = [
    # 1. Empty hand
    "PUBLIC PILES TOP CARDS: NONE\nMY OPEN CARDS: NONE\nMY CLOSED CARDS: NONE\nMYDECK: NONE\nPUBLICDECK: TRUE",
    # 2. Valid slot 5
    "PUBLIC PILES TOP CARDS:\n1. Top pile Card: NONE\n5. Top pile Card: NONE\nMY OPEN CARDS: NONE\nMY CLOSED CARDS: [5 of Spades]\nMYDECK: NONE\nPUBLICDECK: TRUE",
    # 3. Invalid card (Jack)
    "PUBLIC PILES TOP CARDS:\n1. Top pile Card: NONE\nMY OPEN CARDS: NONE\nMY CLOSED CARDS: [Jack of Spades]\nMYDECK: NONE\nPUBLICDECK: TRUE"
]

uno_scenarios = [
    # 1. Rank match
    "PUBLIC PILES TOP CARDS:\n1. Top pile Card: 5 of Spades\nMY OPEN CARDS: NONE\nMY CLOSED CARDS: [5 of Hearts]\nMYDECK: NONE\nPUBLICDECK: TRUE",
    # 2. Suit match
    "PUBLIC PILES TOP CARDS:\n1. Top pile Card: 5 of Spades\nMY OPEN CARDS: NONE\nMY CLOSED CARDS: [8 of Spades]\nMYDECK: NONE\nPUBLICDECK: TRUE",
    # 3. No match
    "PUBLIC PILES TOP CARDS:\n1. Top pile Card: 5 of Spades\nMY OPEN CARDS: NONE\nMY CLOSED CARDS: [2 of Clubs]\nMYDECK: NONE\nPUBLICDECK: TRUE"
]

war_scenarios = [
    # Always same action
    "PUBLIC PILES TOP CARDS:\n1. Top pile Card: 10 of Hearts\nMY OPEN CARDS: NONE\nMY CLOSED CARDS: NONE\nMYDECK: [Hidden Card]\nPUBLICDECK: FALSE"
]

if __name__ == "__main__":
    run_test("Blackjack", solve_blackjack, blackjack_scenarios)
    run_test("Trash", solve_trash, trash_scenarios)
    run_test("Uno", solve_uno, uno_scenarios)
    run_test("War", solve_war, war_scenarios)
