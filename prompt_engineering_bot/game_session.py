import os
import time
import subprocess
import threading
import sys
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
PROC_DIR = BASE_DIR / "processes"
LOCK_FILE = DATA_DIR / "manager_active.lock"
CACHE_FILE = DATA_DIR / "structured_rules_cache.txt"
GAME_STATE_FILE = DATA_DIR / "current_game_state_input.txt"
NEXT_MOVE_FILE = DATA_DIR / "next_move.txt"
RAW_RULES_FILE = DATA_DIR / "raw_rules_input.txt"
PID_FILE = PROC_DIR / "session.pid"


def wait_for_exit():
    try:
        input("\n🛑 PRESS ENTER AT ANY TIME TO END THE SESSION 🛑\n")
        os._exit(0)
    except EOFError:
        # Silently exit thread if stdin is closed/not available
        pass


def run_game_session():
    # Write session PID
    PID_FILE.write_text(str(os.getpid()))

    print("🚀 --- AI Card Game Session Manager ---")
    print("📢 NOTE: The Telegram Bot should already be running in the background.")

    # Start exit listener thread only if running in an interactive terminal
    if sys.stdin.isatty():
        threading.Thread(target=wait_for_exit, daemon=True).start()

    try:
        # 1. Open the gate for Rule Baking
        LOCK_FILE.touch()
        if CACHE_FILE.exists():
            CACHE_FILE.write_text("")  # Reset cache for new rules

        print("\n[STEP 1: BAKING]")
        print("👉 GO TO TELEGRAM and use /start to set the rules.")
        print("⌛ Waiting for rules to be baked...")

        # Wait until cache is populated by the bot
        while not (CACHE_FILE.exists() and CACHE_FILE.stat().st_size > 0):
            if not LOCK_FILE.exists():
                print("\nℹ️ Session interrupted via Telegram.")
                return
            time.sleep(1)

        # 2. Rules are baked, close the gate
        if LOCK_FILE.exists():
            os.remove(LOCK_FILE)
        print("\n✅ Rules Baked Successfully!")

        # 3. Enter the Turn Analysis Loop
        print("\n[STEP 2: GAME LOOP]")
        print("The system is now monitoring 'current_game_state_input.txt'.")

        from game_engine import analyze_turn

        # --- Import Algorithmic Solvers for Fallback ---
        sys.path.append(str(BASE_DIR / "algorithmic_solvers"))
        try:
            from blackjack_solver import solve as solve_blackjack
            from uno_solver import solve as solve_uno
            from war_solver import solve as solve_war
            ALGO_SOLVERS = {
                "BLACKJACK": solve_blackjack,
                "UNO": solve_uno,
                "WAR": solve_war
            }
        except ImportError as e:
            print(f"Warning: Algorithmic solvers not available: {e}")
            ALGO_SOLVERS = {}

        rules = CACHE_FILE.read_text(encoding="utf-8")
        raw_rules = RAW_RULES_FILE.read_text(encoding="utf-8").strip()
        last_mtime = GAME_STATE_FILE.stat().st_mtime if GAME_STATE_FILE.exists() else 0

        while True:
            if not PID_FILE.exists(): break  # Terminated via /terminate
            if GAME_STATE_FILE.exists():
                current_mtime = GAME_STATE_FILE.stat().st_mtime
                if current_mtime > last_mtime:
                    print("\n🔄 State Change Detected! Analyzing...")
                    state = GAME_STATE_FILE.read_text(encoding="utf-8")

                    # --- Algorithmic Override Check ---
                    if raw_rules in ALGO_SOLVERS:
                        print(f"🤖 Game identified as {raw_rules}. Using Algorithmic Solver.")
                        try:
                            result_list, reasoning = ALGO_SOLVERS[raw_rules](state)
                            final_result = "\n".join(result_list)
                            print(f"🧠 REASONING: {reasoning}")
                            print(f"ALGORITHMIC RESULT:\n{final_result}\n")
                            NEXT_MOVE_FILE.write_text(final_result, encoding="utf-8")
                        except Exception as e:
                            print(f"❌ Algorithmic Error: {e}")
                    else:
                        # Standard AI Analysis
                        try:
                            result = analyze_turn(rules, state)
                            final_result = result['final_result']
                            print(f"🧠 REASONING: {result['strategy']}")
                            print(f"AI RESULT:\n{final_result}\n")
                            NEXT_MOVE_FILE.write_text(final_result, encoding="utf-8")
                        except Exception as e:
                            print(f"❌ AI Error during analysis: {e}")

                    last_mtime = current_mtime
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n👋 Game session ended by user.")
    finally:
        # CLEANUP (Only local files, don't kill the bot)
        print("\n🧹 Cleaning up session...")
        if LOCK_FILE.exists(): os.remove(LOCK_FILE)
        if PID_FILE.exists(): os.remove(PID_FILE)
        print("✅ Session Closed. The Bot remains alive.")


if __name__ == "__main__":
    run_game_session()
