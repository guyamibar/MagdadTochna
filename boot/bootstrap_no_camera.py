import os
import sys
import time
import threading
from pathlib import Path

# --- PATH SETUP ---
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))
sys.path.append(str(ROOT_DIR / "boot"))
sys.path.append(str(ROOT_DIR / "prompt_engineering_bot"))

# Import our custom modules
from boot.photo_to_state_pipeline.photo_to_state_translation import translate_photo_to_file
from boot.translations.translate_dealer_start_info_to_physical import deal_cards
from prompt_engineering_bot.game_engine import analyze_turn

# Paths for monitoring communication and triggers
DATA_DIR = ROOT_DIR / "prompt_engineering_bot" / "data"
DEALING_FILE = DATA_DIR / "dealing.txt"
GAME_STATE_FILE = DATA_DIR / "current_game_state_input.txt"
NEXT_MOVE_FILE = DATA_DIR / "next_move.txt"
CACHE_FILE = DATA_DIR / "structured_rules_cache.txt"
RAW_RULES_FILE = DATA_DIR / "raw_rules_input.txt"

# Trigger Files
SNAP_TRIGGER = DATA_DIR / "snap.txt"
EXIT_TRIGGER = DATA_DIR / "exit.txt"
PHOTO_FILE = ROOT_DIR / "boot" / "photo_to_state_pipeline" / "photo.jpg"

def run_bot():
    """Starts the Telegram Bot process."""
    print("🤖 [Bot] Starting Telegram Bot...")
    bot_script = ROOT_DIR / "prompt_engineering_bot" / "run_bot.py"
    import subprocess
    # Run the bot script.
    subprocess.call([sys.executable, "-u", str(bot_script)])

# --- THREAD 1: TELEGRAM BOT WRAPPER ---
def thread_run_bot():
    run_bot()

# --- THREAD 2: NO-CAMERA GAME LOOP ---
def thread_run_no_camera_game_loop():
    """Waits for dealing config once, then watches for snap.txt to trigger analysis."""
    print(f"🎮 [Thread 2] Game Loop active. Waiting for dealer configuration...")
    
    # Wait for dealer configuration ONCE
    while True:
        if DEALING_FILE.exists() and DEALING_FILE.stat().st_size > 0:
            print("\n📤 [Dealer] New dealing instructions detected!")
            content = DEALING_FILE.read_text(encoding="utf-8")
            deal_cards(content)
            DEALING_FILE.write_text("", encoding="utf-8")
            print("✅ [Dealer] Deal complete. Instruction file cleared.")
            
            # Auto-trigger a snap after dealing to update the state
            SNAP_TRIGGER.write_text("deal_done", encoding="utf-8")
            break # Execute only once
        time.sleep(1)

    print(f"🎮 [Thread 2] Dealing done. Watching for {SNAP_TRIGGER.name}...")

    while True:
        # Step 1: Wait for Rules to be "Baked" (System initialized)
        if CACHE_FILE.exists() and CACHE_FILE.stat().st_size > 0:
            
            # Step 2: Monitor snap.txt for trigger
            if SNAP_TRIGGER.exists():
                print(f"\n📸 [Game] Snap trigger detected at {time.ctime()}!")
                
                # 0. ALWAYS remove the trigger first to prevent infinite loops on error
                try:
                    trigger_content = SNAP_TRIGGER.read_text(encoding="utf-8").strip()
                    SNAP_TRIGGER.unlink()
                    print(f"   [Trigger Content: {trigger_content}]")
                except Exception as e:
                    print(f"⚠️ [Game] Could not process snap trigger: {e}")
                
                # 1. Capture Fresh Photo
                from main.take_image import HighResCamera
                import cv2
                image = None
                try:
                    with HighResCamera() as camera:
                        image = camera.take_image()
                        if image is not None:
                            PHOTO_FILE.parent.mkdir(parents=True, exist_ok=True)
                            cv2.imwrite(str(PHOTO_FILE), image)
                            print(f"✅ [Game] Fresh photo saved to {PHOTO_FILE}")
                        else:
                            print("❌ [Game] Failed to capture image (None). Skipping analysis.")
                            continue
                except Exception as e:
                    print(f"❌ [Game] Camera error during snap: {e}")
                    continue

                # 2. Translate Photo -> Game State
                if translate_photo_to_file():
                    print("📝 [Game] Translation complete. Generating AI move...")
                    
                    # 3. Get Rules and State
                    rules = CACHE_FILE.read_text(encoding="utf-8")
                    state = GAME_STATE_FILE.read_text(encoding="utf-8")
                    print("\n" + "="*40)
                    print("📊 [Game] CURRENT GAME STATE:")
                    print(state)
                    print("="*40 + "\n")
                    
                    # 4. Run Game Engine
                    try:
                        result = analyze_turn(rules, state)
                        if result and 'final_result' in result:
                            move_text = result['final_result']
                            print(f"🧠 [Game] AI MOVE GENERATED!")
                            
                            # 5. Save move to next_move.txt
                            NEXT_MOVE_FILE.write_text(move_text, encoding="utf-8")
                            print(f"✅ [Game] Move saved to {NEXT_MOVE_FILE}")
                        else:
                            print("❌ [Game] AI Engine returned empty/invalid result.")
                            
                    except Exception as e:
                        print(f"❌ [Game] AI Engine Error: {e}")
        
        time.sleep(1)

if __name__ == "__main__":
    print("""
    🚀 ==========================================
       MAGDAD NO-CAMERA BOOTSTRAP (TELEGRAM CONTROL)
    ==========================================
    """)
    
    # 📸 Take an initial photo and translate it to sync all JPGs
    import cv2
    from main.take_image import HighResCamera

    print("📸 [Camera] Initializing HighResCamera for initial state capture...")
    try:
        with HighResCamera() as camera:
            image = camera.take_image()
            if image is not None:
                # Ensure parent directory exists
                PHOTO_FILE.parent.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(PHOTO_FILE), image)
                print(f"✅ [Camera] Initial photo saved to {PHOTO_FILE}")
                
                # Sync other JPGs and initial state
                translate_photo_to_file()
            else:
                print("❌ [Camera] Failed to take initial photo (image was None).")
    except Exception as e:
        print(f"❌ [Camera] Camera initialization error: {e}")

    # Clear communication and trigger files for a fresh session
    if DEALING_FILE.exists(): DEALING_FILE.write_text("", encoding="utf-8")
    if GAME_STATE_FILE.exists(): GAME_STATE_FILE.write_text("", encoding="utf-8")
    if SNAP_TRIGGER.exists(): SNAP_TRIGGER.unlink()
    if EXIT_TRIGGER.exists(): EXIT_TRIGGER.unlink()

    t1 = threading.Thread(target=thread_run_bot, name="BotThread", daemon=True)
    t2 = threading.Thread(target=thread_run_no_camera_game_loop, name="GameThread", daemon=True)
    
    t1.start()
    t2.start()
    
    try:
        while True:
            # Check for global exit trigger from Telegram
            if EXIT_TRIGGER.exists():
                print("\n🛑 [Main] Exit trigger detected. Shutting down system...")
                try:
                    EXIT_TRIGGER.unlink()
                except:
                    pass
                os._exit(0) # Force exit all threads and processes
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🧹 Shutting down...")
