import logging
import os
import sys
import time
import subprocess
import json
import platform
import signal
from pathlib import Path
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler,
)
from game_engine import generate_structured_rules, RAW_RULES_FILE, ALGO_SOLVERS

# Import predefined logics
from algorithmic_solvers.games import blackjack_logic, uno_logic, war_logic

# Enable logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.WARNING)
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
PROC_DIR = BASE_DIR / "processes"
LOCK_FILE = DATA_DIR / "manager_active.lock"
CACHE_FILE = DATA_DIR / "structured_rules_cache.txt"
PID_FILE = PROC_DIR / "session.pid"
DEALING_FILE = DATA_DIR / "dealing.txt"
SNAP_TRIGGER = DATA_DIR / "snap.txt"
EXIT_TRIGGER = DATA_DIR / "exit.txt"

# Conversation states
(MAIN_MENU, SET_PLAYERS, SET_DECK, SET_PILES, SET_PASS, SET_DRAW_PILES, SET_DRAW_DECK, SET_PERSONAL, SET_FREE_RULES, SET_CARDS_PER_PLAYER, SET_PUBLIC_CARDS_COUNT, CONFIRM_RULES, GAME_ONGOING) = range(13)

# Keyboards
MAIN_MENU_KBD = ReplyKeyboardMarkup([['Uno', 'Blackjack'], ['War', 'Custom']], one_time_keyboard=True, resize_keyboard=True)
YES_NO_KBD = ReplyKeyboardMarkup([['YES', 'NO']], one_time_keyboard=True, resize_keyboard=True)
CONFIRM_KBD = ReplyKeyboardMarkup([
    ['Yes, those are the rules'],
    ['No, let me try again'],
    ['No, terminate the session']
], one_time_keyboard=True, resize_keyboard=True)
PLAYERS_KBD = ReplyKeyboardMarkup([['1', '2', '3']], one_time_keyboard=True, resize_keyboard=True)
CARDS_KBD = ReplyKeyboardMarkup([
    ['1', '2', '3', '4', '5'],
    ['6', '7', '8', '9', '10'],
    ['11', '12', '13', '14', '15']
], one_time_keyboard=True, resize_keyboard=True)
PUBLIC_CARDS_KBD = ReplyKeyboardMarkup([
    ['0', '1', '2', '3', '4', '5', '6']
], one_time_keyboard=True, resize_keyboard=True)
PILES_KBD = ReplyKeyboardMarkup([
    ['0', '1', '2', '3'],
    ['4', '5', '6']
], one_time_keyboard=True, resize_keyboard=True)
GAME_KBD = ReplyKeyboardMarkup([["It's the bot's turn"], ["End"]], resize_keyboard=True)

async def bake_rules_final(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Finalizes the setup by writing the dealing sequence."""
    try:
        ud = context.user_data
        num_players_input = int(ud.get('players', 2))
        cards_per_player = int(ud.get('cards_per_player', 0))
        public_cards_total = int(ud.get('public_cards', 0))
        
        lines = []
        for i in range(1, 4):
            count = cards_per_player if i <= num_players_input else 0
            lines.append(f"PLAYER {i}: {count}")
        lines.append("")
        lines.append(f"PUBLIC CARDS: {public_cards_total}")
        DEALING_FILE.write_text("\n".join(lines), encoding="utf-8")
        
        await update.message.reply_text(f"✅ Setup for {ud['choice']} is now BAKED and ready!\n\nYou can now use the menu below to control the bot.", reply_markup=GAME_KBD)
    except Exception as e: 
        await update.message.reply_text(f"❌ Error during finalization: {str(e)}")
    return ConversationHandler.END

async def handle_game_turn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles manual triggers for the bot's turn or ending the program."""
    text = update.message.text
    if text == "It's the bot's turn":
        SNAP_TRIGGER.write_text("telegram_button_snap", encoding="utf-8")
        await update.message.reply_text("📸 Snap triggered! Bot is analyzing...", reply_markup=GAME_KBD)
    elif text == "End":
        await update.message.reply_text("🛑 Shutting down the entire system... Goodbye!", reply_markup=ReplyKeyboardRemove())
        EXIT_TRIGGER.write_text("manual_exit", encoding="utf-8")
        # Small delay to ensure message is sent
        time.sleep(1)
        os._exit(0)
    return ConversationHandler.END

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # 1. Start Session if not running
    is_running = False
    if PID_FILE.exists():
        pid_str = PID_FILE.read_text().strip()
        if pid_str:
            try:
                pid = int(pid_str)
                if os.name == "nt":
                    res = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True)
                    if str(pid) in res.stdout:
                        is_running = True
                else:
                    try:
                        os.kill(pid, 0)
                        is_running = True
                    except (ProcessLookupError, PermissionError):
                        pass
            except (ValueError, subprocess.CalledProcessError):
                PID_FILE.unlink()

    if not is_running:
        try:
            python_exe = sys.executable
            script_path = BASE_DIR / "game_session.py"
            subprocess.Popen([python_exe, "-u", str(script_path)], cwd=str(BASE_DIR))
            await update.message.reply_text("🚀 Game Session Manager started!\nIts output will now appear in your main terminal.")
            # Wait briefly for lock file to be created
            time.sleep(1)
        except Exception as e:
            await update.message.reply_text(f"❌ Failed to start session: {e}")
            return ConversationHandler.END

    if not LOCK_FILE.exists():
        await update.message.reply_text("🛑 The Game Session Manager failed to create the lock file. Please check the logs.")
        return ConversationHandler.END

    # 2. Clean Slate for new setup (allow /start to act as a reset)
    if CACHE_FILE.exists():
        CACHE_FILE.write_text("")
    context.user_data.clear()
    
    # 3. Begin Conversation
    await update.message.reply_text("🍳 AI Card Game Rule Baker\n━━━━━━━━━━━━━━\n👥 1. How many PLAYERS (including the AI bot)?\n(Note: The AI Bot is always Player 1)", reply_markup=PLAYERS_KBD)
    return SET_PLAYERS

async def terminate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if PID_FILE.exists():
            pid_str = PID_FILE.read_text().strip()
            if pid_str:
                pid = int(pid_str)
                if os.name == "nt":
                    subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
                else:
                    try:
                        os.kill(pid, signal.SIGTERM)
                        # Give it a moment to die, then force if needed
                        time.sleep(0.5)
                        try:
                            os.kill(pid, 0)
                            os.kill(pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                    except ProcessLookupError:
                        pass
            PID_FILE.unlink()
        if LOCK_FILE.exists(): LOCK_FILE.unlink()
        if CACHE_FILE.exists(): CACHE_FILE.write_text("") 
        await update.message.reply_text("✅ Session terminated and cache cleared.")
    except Exception as e: await update.message.reply_text(f"❌ Error: {e}")

async def menu_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text
    context.user_data['choice'] = choice
    players = context.user_data.get('players', '2')
    if choice == "Custom":
        await update.message.reply_text("🃏 2. Is there a PUBLIC DECK?", reply_markup=YES_NO_KBD)
        return SET_DECK
    game_data = None
    if choice == "Blackjack": game_data = blackjack_logic.get_rules()
    elif choice == "Uno": game_data = uno_logic.get_rules()
    elif choice == "War": game_data = war_logic.get_rules()
    if game_data:
        if isinstance(game_data, str) and game_data.isupper(): raw_rules = game_data
        elif isinstance(game_data, dict):
            raw_rules = f"Must Have Rules:\n1. NUMBER OF PLAYERS: {players}\n2. IS THERE A PUBLIC DECK: YES\n3. NUMBER OF PUBLIC PILES: {game_data['piles']}\n4. CAN A PLAYER PASS WITHOUT PLAYING: {game_data['can_pass']}\n5. CAN DRAW FROM PUBLIC PILES: {game_data['draw_piles']}\n6. CAN DRAW FROM PUBLIC DECK: {game_data['draw_decks']}\n7. DO PLAYERS HAVE PERSONAL DECK: NO\n\nFree Write Rules:\n{game_data['free_rules']}"
        else: raw_rules = str(game_data)
        context.user_data['raw_rules'] = raw_rules
        await update.message.reply_text("🎴 8. How many cards to deal each player (overall)?", reply_markup=CARDS_KBD)
        return SET_CARDS_PER_PLAYER
    return MAIN_MENU

async def set_public_cards_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['public_cards'] = update.message.text
    ud = context.user_data
    
    try:
        # 1. Generate the structured rules first (Stage 1 of the game engine)
        structured = generate_structured_rules(ud['raw_rules'])
        
        # Check if it's an algorithmic solver - if so, skip confirmation
        if ud['raw_rules'].strip().upper() in ALGO_SOLVERS:
            await update.message.reply_text(f"✅ {ud['choice']} (Algorithmic) rules applied. Finalizing setup...")
            await bake_rules_final(update, context)
            return ConversationHandler.END

        await update.message.reply_text("🧠 AI is processing the rules and preparing a summary...")
        
        # 2. Ask the AI to create a human-friendly explanation of those structured rules
        from rotate_key_model import rotator
        explanation_prompt = f"""
        Below are the structured, machine-readable rules for a card game. 
        Your task is to rewrite these rules into a clear, concise, and human-friendly explanation.
        The goal is for a person to read this and confirm that the game logic is correct as they intended.

        STRUCTURED RULES:
        {structured}

        Provide the explanation in a simple, bulleted format. Do not use Markdown symbols like '*' or '_' that might break the Telegram parser.
        """
        response = rotator.call_with_retry(explanation_prompt)
        explanation = response.text.strip()
        
        ud['structured_rules'] = structured # Store for later use
        
        summary = f"📋 AI's Understanding of the Rules\n━━━━━━━━━━━━━━\n" \
                  f"🎮 Game: {ud['choice']}\n" \
                  f"👥 Players: {ud['players']}\n\n" \
                  f"{explanation}\n\n" \
                  f"Is this how you want the AI to play the game?"
        
        await update.message.reply_text(summary, reply_markup=CONFIRM_KBD)
        return CONFIRM_RULES
    except Exception as e:
        await update.message.reply_text(f"❌ Error during rule processing: {e}")
        return ConversationHandler.END

async def confirm_rules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text
    if choice == "Yes, those are the rules":
        # Rules are already baked into CACHE_FILE by generate_structured_rules()
        await update.message.reply_text("✅ Rules confirmed! Finalizing the setup...")
        await bake_rules_final(update, context)
        return ConversationHandler.END
    elif choice == "No, let me try again":
        if CACHE_FILE.exists():
            CACHE_FILE.write_text("") # Erase the structured rules cache
        context.user_data.clear()
        await update.message.reply_text("🔄 Rules discarded. Let's start over.\n👥 1. How many PLAYERS (including the AI bot)?", reply_markup=PLAYERS_KBD)
        return SET_PLAYERS
    elif choice == "No, terminate the session":
        if CACHE_FILE.exists():
            CACHE_FILE.write_text("") # Erase the structured rules cache
        await terminate(update, context)
        return ConversationHandler.END
    return CONFIRM_RULES



async def set_players(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['players'] = update.message.text
    await update.message.reply_text("Choose a game or build custom:", reply_markup=MAIN_MENU_KBD)
    return MAIN_MENU

async def set_deck(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['deck'] = update.message.text.upper()
    await update.message.reply_text("📍 3. Number of PUBLIC PILES?", reply_markup=PILES_KBD); return SET_PILES
async def set_piles(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['piles'] = update.message.text
    await update.message.reply_text("⏭ 4. Can a player PASS?", reply_markup=YES_NO_KBD); return SET_PASS
async def set_pass(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['can_pass'] = update.message.text.upper()
    await update.message.reply_text("📥 5. Draw from PILES?", reply_markup=YES_NO_KBD); return SET_DRAW_PILES
async def set_draw_piles(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['draw_piles'] = update.message.text.upper()
    await update.message.reply_text("🎃 6. Draw from DECK?", reply_markup=YES_NO_KBD); return SET_DRAW_DECK
async def set_draw_deck(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['draw_deck'] = update.message.text.upper()
    await update.message.reply_text("🎒 7. PERSONAL DECK?", reply_markup=YES_NO_KBD); return SET_PERSONAL
async def set_personal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['personal_deck'] = update.message.text.upper()
    await update.message.reply_text("📝 8. FREE WRITE RULES:", reply_markup=ReplyKeyboardRemove()); return SET_FREE_RULES
async def finish_custom(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ud = context.user_data
    raw = f"Must Have Rules:\n1. NUMBER OF PLAYERS: {ud['players']}\n2. IS THERE A PUBLIC DECK: {ud['deck']}\n3. NUMBER OF PUBLIC PILES: {ud['piles']}\n4. CAN A PLAYER PASS WITHOUT PLAYING: {ud['can_pass']}\n5. CAN DRAW FROM PUBLIC PILES: {ud['draw_piles']}\n6. CAN DRAW FROM PUBLIC DECK: {ud['draw_deck']}\n7. DO PLAYERS HAVE PERSONAL DECK: {ud['personal_deck']}\n\nFree Write Rules:\n{update.message.text}"
    context.user_data['raw_rules'] = raw
    await update.message.reply_text("🎴 9. How many cards to deal each player (overall)?", reply_markup=CARDS_KBD)
    return SET_CARDS_PER_PLAYER

async def set_cards_per_player(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['cards_per_player'] = update.message.text
    await update.message.reply_text("🃏 10. How many public cards are overall (open and closed)?", reply_markup=PUBLIC_CARDS_KBD)
    return SET_PUBLIC_CARDS_COUNT

async def confirm_rules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text
    if choice == "Yes, those are the rules":
        # Rules are already baked into CACHE_FILE by generate_structured_rules()
        await update.message.reply_text("✅ Rules confirmed! Finalizing the setup...")
        await bake_rules_final(update, context)
        return ConversationHandler.END
    elif choice == "No, let me try again":
        if CACHE_FILE.exists():
            CACHE_FILE.write_text("") # Erase the structured rules cache
        context.user_data.clear()
        await update.message.reply_text("🔄 Rules discarded. Let's start over.\n👥 1. How many PLAYERS (including the AI bot)?", reply_markup=PLAYERS_KBD)
        return SET_PLAYERS
    elif choice == "No, terminate the session":
        if CACHE_FILE.exists():
            CACHE_FILE.write_text("") # Erase the structured rules cache
        await terminate(update, context)
        return ConversationHandler.END
    return CONFIRM_RULES

if __name__ == "__main__":
    TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not TOKEN: exit(1)
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("terminate", terminate))
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SET_PLAYERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_players)],
            MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, menu_choice)],
            SET_DECK: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_deck)],
            SET_PILES: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_piles)],
            SET_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_pass)],
            SET_DRAW_PILES: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_draw_piles)],
            SET_DRAW_DECK: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_draw_deck)],
            SET_PERSONAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_personal)],
            SET_FREE_RULES: [MessageHandler(filters.TEXT & ~filters.COMMAND, finish_custom)],
            SET_CARDS_PER_PLAYER: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_cards_per_player)],
            SET_PUBLIC_CARDS_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_public_cards_count)],
            CONFIRM_RULES: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_rules)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END), CommandHandler("start", start)],
    ))
    
    # Add a global handler for the Game Menu after the rules are baked
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^(It's the bot's turn|End)$"), handle_game_turn))
    
    app.run_polling()
