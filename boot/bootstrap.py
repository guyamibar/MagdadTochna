import os
import sys
import time
import threading
from pathlib import Path

# --- PATH SETUP ---
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))
sys.path.append(str(ROOT_DIR / "boot"))

# Import our custom modules from the 'boot' folder
from boot.shoot_photo import shoot_photo
from boot.photo_to_state_pipeline.photo_to_state_translation import translate_photo_to_file
from boot.translations.translate_from_ai_move_to_physical import translate_and_execute
from boot.translations.translate_dealer_start_info_to_physical import deal_cards

# Paths for monitoring AI communication
DATA_DIR = ROOT_DIR / "prompt_engineering_bot" / "data"
DEALING_FILE = DATA_DIR / "dealing.txt"
GAME_STATE_FILE = DATA_DIR / "current_game_state_input.txt"
NEXT_MOVE_FILE = DATA_DIR / "next_move.txt"
CACHE_FILE = DATA_DIR / "structured_rules_cache.txt"
RESULT_STATE_FILE = ROOT_DIR / "boot" / "photo_to_state_pipeline" / "result_state.txt"

def turn_button_pushed():
    """
    PLACEHOLDER: Implement the logic to check if the physical turn button is pushed.
    """
    return False

# --- THREAD 1: TELEGRAM BOT ---
def thread_run_bot():
    """Starts the Telegram Bot process."""
    print("🤖 [Thread 1] Starting Telegram Bot...")
    bot_script = ROOT_DIR / "prompt_engineering_bot" / "run_bot.py"
    import subprocess
    # Run the bot script. It has its own internal persistence loop.
    subprocess.call([sys.executable, "-u", str(bot_script)])

# --- THREAD 2: DEALER MONITOR ---
def thread_run_dealer_start_loop_check():
    """Monitors dealing.txt for new instructions from Telegram."""
    print("🃏 [Thread 2] Dealer loop active. Monitoring dealing.txt...")
    while True:
        if DEALING_FILE.exists() and DEALING_FILE.stat().st_size > 0:
            print("\n📤 [Dealer] New dealing instructions detected!")
            content = DEALING_FILE.read_text(encoding="utf-8")
            deal_cards(content)
            DEALING_FILE.write_text("", encoding="utf-8")
            print("✅ [Dealer] Deal complete. Instruction file cleared.")
        time.sleep(1)

# --- THREAD 3: MAIN GAME LOOP ---
def thread_run_game_turn_loop():
    """The master loop that coordinates Acquisition, Translation, and AI."""
    print("🎮 [Thread 3] Game Turn loop active.")
    
    while True:
        # Check if rules are baked (session active)
        if CACHE_FILE.exists() and CACHE_FILE.stat().st_size > 0:
            
            if turn_button_pushed():
                print("\n📸 [Game] Button Pushed! Capturing live state...")
                
                # 1. Capture Photo
                if not shoot_photo():
                    continue
                
                # 2. Translate Photo to Game State (updates current_game_state_input.txt)
                if not translate_photo_to_file():
                    continue
                
                # 3. Read the logical state
                if GAME_STATE_FILE.exists():
                    state_text = GAME_STATE_FILE.read_text(encoding="utf-8")
                else:
                    print("❌ Error: current_game_state_input.txt not found after translation.")
                    continue
                
                print("📝 [Game] State updated. AI is now calculating move...")
                last_mtime = NEXT_MOVE_FILE.stat().st_mtime if NEXT_MOVE_FILE.exists() else 0
                
                # IMPORTANT: The file is already updated by translate_photo_to_file. 
                # We don't need to re-write it unless we want to force a change trigger.
                # GAME_STATE_FILE.write_text(state_text, encoding="utf-8")
                
                print("⌛ [Game] Waiting for AI Tactical Response (next_move.txt)...")
                timeout = 45 
                start_wait = time.time()
                move_found = False
                
                while time.time() - start_wait < timeout:
                    if NEXT_MOVE_FILE.exists():
                        current_mtime = NEXT_MOVE_FILE.stat().st_mtime
                        if current_mtime > last_mtime:
                            move_text = NEXT_MOVE_FILE.read_text(encoding="utf-8").strip()
                            print(f"\n🧠 [Game] NEW AI MOVE DETECTED!")
                            translate_and_execute(move_text)
                            move_found = True
                            break
                    time.sleep(0.5)
                
                if not move_found:
                    print("❌ [Game] Timeout: AI failed to generate a new move.")
                
        time.sleep(0.5)

if __name__ == "__main__":
    print("""
    🚀 ==========================================
       MAGDAD AUTOMATED CARD SYSTEM BOOTSTRAP
    ==========================================
    """)
    
    # Reset files
    from boot.hand_manager import save_hand, save_pickup
    save_hand({f"MYCARDS_{i}": [None, None] for i in range(1, 7)})
    save_pickup([None, None])
    if DEALING_FILE.exists(): DEALING_FILE.write_text("", encoding="utf-8")
    if GAME_STATE_FILE.exists(): GAME_STATE_FILE.write_text("", encoding="utf-8")

    t1 = threading.Thread(target=thread_run_bot, name="BotThread", daemon=True)
    t2 = threading.Thread(target=thread_run_dealer_start_loop_check, name="DealerThread", daemon=True)
    t3 = threading.Thread(target=thread_run_game_turn_loop, name="GameThread", daemon=True)
    
    t1.start()
    t2.start()
    t3.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🧹 Shutting down...")
