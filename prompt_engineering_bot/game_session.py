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
        pass


def run_game_session():
    PROC_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))

    print("🚀 --- AI Card Game Session Manager ---")
    if sys.stdin.isatty():
        threading.Thread(target=wait_for_exit, daemon=True).start()

    try:
        LOCK_FILE.touch()
        if CACHE_FILE.exists():
            CACHE_FILE.write_text("")

        print("\n[STEP 1: BAKING]")
        while not (CACHE_FILE.exists() and CACHE_FILE.stat().st_size > 0):
            if not LOCK_FILE.exists():
                return
            time.sleep(1)

        if LOCK_FILE.exists():
            os.remove(LOCK_FILE)
        print("\n✅ Rules Baked Successfully!")

        print("\n[STEP 2: GAME LOOP]")
        from game_engine import analyze_turn

        sys.path.append(str(BASE_DIR / "algorithmic_solvers"))
        try:
            from blackjack_solver import solve as solve_blackjack
            from uno_solver import solve as solve_uno
            from war_solver import solve as solve_war
            ALGO_SOLVERS = {"BLACKJACK": solve_blackjack, "UNO": solve_uno, "WAR": solve_war}
        except ImportError:
            ALGO_SOLVERS = {}

        rules = CACHE_FILE.read_text(encoding="utf-8")
        raw_rules = RAW_RULES_FILE.read_text(encoding="utf-8").strip().upper()
        last_mtime = GAME_STATE_FILE.stat().st_mtime if GAME_STATE_FILE.exists() else 0

        while True:
            if not PID_FILE.exists(): break
            if GAME_STATE_FILE.exists():
                current_mtime = GAME_STATE_FILE.stat().st_mtime
                if current_mtime > last_mtime:
                    print(f"\n🔄 [Session] State Change Detected at {time.ctime()}! Analyzing...")
                    state = GAME_STATE_FILE.read_text(encoding="utf-8")

                    if raw_rules in ALGO_SOLVERS:
                        print(f"🤖 [Session] Using Algorithmic Solver for {raw_rules}...")
                        try:
                            result_list, reasoning = ALGO_SOLVERS[raw_rules](state)
                            final_result = "\n".join(result_list)
                            
                            # FORCE IMMEDIATE FLUSH TO DISK
                            with open(NEXT_MOVE_FILE, "w", encoding="utf-8") as f:
                                f.write(final_result)
                                f.flush()
                                os.fsync(f.fileno())
                            
                            print(f"✅ [Session] Move written and synced.")
                        except Exception as e:
                            print(f"❌ [Session] Algorithmic Error: {e}")
                    else:
                        print(f"🧠 [Session] Sending state to Gemini AI...")
                        try:
                            result = analyze_turn(rules, state)
                            final_result = result['final_result']
                            
                            # FORCE IMMEDIATE FLUSH TO DISK
                            with open(NEXT_MOVE_FILE, "w", encoding="utf-8") as f:
                                f.write(final_result)
                                f.flush()
                                os.fsync(f.fileno())
                                
                            print(f"✅ [Session] AI Move written and synced.")
                        except Exception as e:
                            print(f"❌ [Session] AI Error: {e}")

                    last_mtime = current_mtime
            time.sleep(0.5)

    except KeyboardInterrupt:
        pass
    finally:
        if LOCK_FILE.exists(): os.remove(LOCK_FILE)
        if PID_FILE.exists(): os.remove(PID_FILE)
        
        # Clear temporary data files
        for f in [CACHE_FILE, RAW_RULES_FILE, GAME_STATE_FILE]:
            if f.exists():
                f.write_text("", encoding="utf-8")
                
        print("✅ Session Closed and Data Cleared.")


if __name__ == "__main__":
    run_game_session()
