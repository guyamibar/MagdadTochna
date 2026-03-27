import pygame
import sys
import os
import json
import subprocess
import time
import random
from pathlib import Path

# Add project path for the parser
sys.path.append(str(Path(__file__).parent.parent / "prompt_engineering_bot" / "algorithmic_solvers"))
from state_parser import parse_game_state

# Paths
BASE_DIR = Path(__file__).parent.parent
BOT_DIR = BASE_DIR / "prompt_engineering_bot"
DATA_DIR = BOT_DIR / "data"
STATE_FILE = DATA_DIR / "current_game_state_input.txt"
MOVE_FILE = DATA_DIR / "next_move.txt"
RULES_FILE = DATA_DIR / "raw_rules_input.txt"
LOCK_FILE = DATA_DIR / "manager_active.lock"

# Standardize Python path
PYTHON_EXE = Path(sys.executable)
ENGINE_PY = BOT_DIR / "game_engine.py"

# GUI Config
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 750
CARD_WIDTH = 45
CARD_HEIGHT = 65
BG_COLOR = (20, 25, 20)
ZONE_COLOR = (60, 80, 60)
TEXT_COLOR = (255, 255, 255)

class Card:
    def __init__(self, name):
        self.name = name
        self.rect = pygame.Rect(0, 0, CARD_WIDTH, CARD_HEIGHT)
        self.is_dragging = False
        parts = name.lower().split(' of ')
        self.rank = parts[0].capitalize() if len(parts) > 0 else "?"
        self.suit = parts[1].capitalize() if len(parts) > 1 else ""
        self.color = (200, 0, 0) if self.suit in ['Hearts', 'Diamonds'] else (10, 10, 10)

    def draw(self, screen, font):
        pygame.draw.rect(screen, (255, 255, 255), self.rect, border_radius=5)
        pygame.draw.rect(screen, (0, 0, 0), self.rect, 1, border_radius=5)
        r_txt = font.render(self.rank[:2], True, self.color)
        s_txt = font.render(self.suit[0] if self.suit else "?", True, self.color)
        screen.blit(r_txt, (self.rect.x + 3, self.rect.y + 2))
        screen.blit(s_txt, (self.rect.centerx - s_txt.get_width()//2, self.rect.y + 25))

class Simulator:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Smart Simulation - Auto Sync")
        self.clock = pygame.time.Clock()
        self.font_ui = pygame.font.SysFont("Consolas", 11, bold=True)
        self.font_move = pygame.font.SysFont("Consolas", 14, bold=True)
        self.font_card = pygame.font.SysFont("Arial", 10, bold=True)
        
        self.zones = {
            "PLAYER2_DECK": pygame.Rect(10, 60, 60, 80),
            "PLAYER2_OPEN": pygame.Rect(80, 60, 300, 80),
            "PLAYER3_OPEN": pygame.Rect(450, 60, 300, 80),
            "PLAYER3_DECK": pygame.Rect(760, 60, 60, 80),
            "PUBLIC_DECK": pygame.Rect(10, 250, 60, 80),
            "P1": pygame.Rect(150, 250, 60, 80), "P2": pygame.Rect(220, 250, 60, 80), "P3": pygame.Rect(290, 250, 60, 80),
            "P4": pygame.Rect(150, 340, 60, 80), "P5": pygame.Rect(220, 340, 60, 80), "P6": pygame.Rect(290, 340, 60, 80),
            "MYOPEN": pygame.Rect(80, 480, 700, 80),
            "MYCLOSED": pygame.Rect(80, 580, 700, 80),
            "MYDECK": pygame.Rect(790, 580, 60, 80)
        }
        self.last_state_mtime = 0
        self.last_move_mtime = MOVE_FILE.stat().st_mtime if MOVE_FILE.exists() else 0
        self.zone_contents = {z: [] for z in self.zones}
        self.selected_card = None
        self.original_zone = None
        self.next_move_text = "Best Move: ..."
        self.engine_display = "AI"
        self.is_loading = False

    def get_unused_cards(self, count, current_cards):
        ranks = ['2','3','4','5','6','7','8','9','10','Jack','Queen','King','Ace']
        suits = ['Spades','Hearts','Diamonds','Clubs']
        deck = [f"{r} of {s}" for s in suits for r in ranks]
        used = [c.name.lower() for c in current_cards]
        available = [c for c in deck if c.lower() not in used]
        random.shuffle(available)
        return available[:count]

    def load_state_from_file(self):
        try:
            if not STATE_FILE.exists(): return
            mtime = STATE_FILE.stat().st_mtime
            if mtime <= self.last_state_mtime: return
            self.last_state_mtime = mtime
            text = STATE_FILE.read_text(encoding="utf-8")
            state = parse_game_state(text)
            self.zone_contents = {z: [] for z in self.zones}
            flat_cards = []
            for idx, name in state['PUBPILE'].items():
                if name and name != "FALSE":
                    c = Card(name); self.zone_contents[f"P{idx}"].append(c); flat_cards.append(c)
            for name in state['MYCLOSED']:
                c = Card(name); self.zone_contents["MYCLOSED"].append(c); flat_cards.append(c)
            for name in state['MYOPEN']:
                c = Card(name); self.zone_contents["MYOPEN"].append(c); flat_cards.append(c)
            for name in state['PLAYER2_OPEN']:
                c = Card(name); self.zone_contents["PLAYER2_OPEN"].append(c); flat_cards.append(c)
            for name in state['PLAYER3_OPEN']:
                c = Card(name); self.zone_contents["PLAYER3_OPEN"].append(c); flat_cards.append(c)
            
            def fill_deck(zname, is_true):
                if is_true:
                    new_names = self.get_unused_cards(10, flat_cards)
                    for n in new_names:
                        c = Card(n); self.zone_contents[zname].append(c); flat_cards.append(c)
            fill_deck("MYDECK", state['MYDECK'])
            fill_deck("PLAYER2_DECK", state['PLAYER2_DECK'])
            fill_deck("PLAYER3_DECK", state['PLAYER3_DECK'])
            fill_deck("PUBLIC_DECK", state['PUBDECK'])
            self.layout_cards()
            self.trigger_logic_if_needed()
        except: pass

    def update_engine_type(self):
        if RULES_FILE.exists():
            raw = RULES_FILE.read_text(encoding="utf-8").strip().upper()
            if raw in ["UNO", "BLACKJACK", "TRASH", "WAR"]:
                self.engine_display = f"ALGO ({raw})"
            else: self.engine_display = "AI (Custom)"

    def trigger_logic_if_needed(self):
        self.is_loading = True
        self.next_move_text = "Best Move: LOADING..."
        # If game_session.py isn't running (indicated by lack of lock), trigger manually
        if not LOCK_FILE.exists():
            subprocess.Popen([str(PYTHON_EXE), str(ENGINE_PY)])

    def write_state_to_file(self):
        state = {
            'PUBPILE': {i: self.zone_contents[f"P{i}"][-1].name if self.zone_contents[f"P{i}"] else "FALSE" for i in range(1,7)},
            'MYCLOSED': [c.name for c in self.zone_contents["MYCLOSED"]],
            'MYOPEN': [c.name for c in self.zone_contents["MYOPEN"]],
            'MYDECK': len(self.zone_contents["MYDECK"]) > 0,
            'PLAYER2_OPEN': [c.name for c in self.zone_contents["PLAYER2_OPEN"]],
            'PLAYER2_DECK': len(self.zone_contents["PLAYER2_DECK"]) > 0,
            'PLAYER3_OPEN': [c.name for c in self.zone_contents["PLAYER3_OPEN"]],
            'PLAYER3_DECK': len(self.zone_contents["PLAYER3_DECK"]) > 0,
            'PUBDECK': len(self.zone_contents["PUBLIC_DECK"]) > 0
        }
        lines = []
        for i in range(1, 7): lines.append(f"P{i}: {state['PUBPILE'].get(i, 'FALSE')}")
        lines.append(f"\nMYOPEN: {json.dumps(state['MYOPEN'])}\nMYCLOSED: {json.dumps(state['MYCLOSED'])}\nMYDECK: {'TRUE' if state['MYDECK'] else 'FALSE'}")
        lines.append(f"\nPLAYER2_OPEN: {json.dumps(state['PLAYER2_OPEN'])}\nPLAYER2_DECK: {'TRUE' if state['PLAYER2_DECK'] else 'FALSE'}")
        lines.append(f"\nPLAYER3_OPEN: {json.dumps(state['PLAYER3_OPEN'])}\nPLAYER3_DECK: {'TRUE' if state['PLAYER3_DECK'] else 'FALSE'}")
        lines.append(f"\nPUBLIC_DECK: {'TRUE' if state['PUBDECK'] else 'FALSE'}")
        
        STATE_FILE.write_text("\n".join(lines), encoding="utf-8")
        self.last_state_mtime = STATE_FILE.stat().st_mtime
        self.trigger_logic_if_needed()

    def layout_cards(self):
        for z_name, rect in self.zones.items():
            for i, card in enumerate(self.zone_contents[z_name]):
                if not card.is_dragging:
                    if rect.width > 100: card.rect.topleft = (rect.x + 5 + i*30, rect.y + 5)
                    else: card.rect.topleft = (rect.x + 5, rect.y + 5 - i*2)

    def run(self):
        running = True
        while running:
            mx, my = pygame.mouse.get_pos()
            self.load_state_from_file()
            self.update_engine_type()
            
            if MOVE_FILE.exists():
                mtime = MOVE_FILE.stat().st_mtime
                if mtime > self.last_move_mtime:
                    self.last_move_mtime = mtime
                    self.is_loading = False
                    try:
                        move = MOVE_FILE.read_text(encoding="utf-8").replace('\n', ' | ')
                        self.next_move_text = "Move: " + move
                    except: pass

            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for zn in reversed(list(self.zone_contents.keys())):
                        for c in reversed(self.zone_contents[zn]):
                            if c.rect.collidepoint(mx, my):
                                self.selected_card = c; self.original_zone = zn
                                c.is_dragging = True; c.offset_x, c.offset_y = c.rect.x-mx, c.rect.y-my
                                break
                        if self.selected_card: break
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.selected_card:
                    self.selected_card.is_dragging = False
                    nz = next((n for n, r in self.zones.items() if r.colliderect(self.selected_card.rect)), None)
                    if nz and nz != self.original_zone:
                        self.zone_contents[self.original_zone].remove(self.selected_card)
                        self.zone_contents[nz].append(self.selected_card)
                        self.write_state_to_file()
                    else: self.layout_cards()
                    self.selected_card = None
                elif event.type == pygame.MOUSEMOTION and self.selected_card:
                    self.selected_card.rect.x, self.selected_card.rect.y = mx + self.selected_card.offset_x, my + self.selected_card.offset_y

            self.screen.fill(BG_COLOR)
            for name, rect in self.zones.items():
                pygame.draw.rect(self.screen, ZONE_COLOR, rect, 1, border_radius=5)
                self.screen.blit(self.font_ui.render(name, True, (150, 180, 150)), (rect.x, rect.y - 15))
            for zn in self.zone_contents:
                for c in self.zone_contents[zn]: c.draw(self.screen, self.font_card)
            
            pygame.draw.rect(self.screen, (30, 30, 50), (0, 0, SCREEN_WIDTH, 40))
            etype_txt = self.font_move.render(f"[{self.engine_display}]", True, (0, 255, 255))
            self.screen.blit(etype_txt, (10, 10))
            
            # Show Move or LOADING
            move_color = (255, 255, 0) if not self.is_loading else (255, 50, 50)
            self.screen.blit(self.font_move.render(self.next_move_text, True, move_color), (etype_txt.get_width() + 20, 10))
            
            pygame.display.flip(); self.clock.tick(60)
        pygame.quit()

if __name__ == "__main__": Simulator().run()
