import os
import subprocess
import sys
import time
import signal
from pathlib import Path

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "7969985495:AAGara8w4HwQXsFx-T97D5lHEfJCZSTA3Sg")
# ---------------------

def cleanup_orphans():
    """Kills any existing bot instances to prevent Telegram Conflict errors."""
    print("🧹 Cleaning up old bot instances...")
    if os.name == "nt": # Windows
        # On Windows, we only kill if we are not in a recursive loop.
        # Taskkill /IM python.exe /F will kill THIS script too.
        # Instead, we rely on the bot_proc.terminate() in signal_handler.
        pass
    else: # Linux (Pi)
        # Use pkill to find and kill the specific script
        os.system("pkill -f telegram_bot.py")
    time.sleep(1)

def start_system():
    os.environ["TELEGRAM_BOT_TOKEN"] = TELEGRAM_TOKEN
    
    # 1. PRE-START CLEANUP
    cleanup_orphans()
    
    print("🚀 --- MAGDAD SYSTEM HOST (BOT MODE) ---")
    BASE_DIR = Path(__file__).parent
    
    bot_proc = None

    def signal_handler(sig, frame):
        print("\n\n🧹 Shutting down system...")
        if bot_proc:
            print("🛑 Stopping Telegram Bot...")
            bot_proc.terminate()
        sys.exit(0)

    # Register signals for clean exit (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # 2. START THE BOT
        print("🤖 Starting Telegram Bot...")
        bot_proc = subprocess.Popen([sys.executable, "-u", str(BASE_DIR / "telegram_bot.py")])
        
        print("\n✅ BOT ONLINE")
        print("🛑 Press Ctrl+C to shut down.")

        # Keep the main script alive and monitor the bot
        while True:
            if bot_proc.poll() is not None:
                print("\n⚠️ Telegram Bot stopped. Restarting in 5 seconds...")
                time.sleep(5)
                cleanup_orphans() # Ensure it's really dead before restart
                bot_proc = subprocess.Popen([sys.executable, "-u", str(BASE_DIR / "telegram_bot.py")])
            time.sleep(2)

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if bot_proc:
            bot_proc.terminate()

if __name__ == "__main__":
    if not TELEGRAM_TOKEN:
        print("❌ ERROR: TELEGRAM_BOT_TOKEN not set.")
    else:
        start_system()
