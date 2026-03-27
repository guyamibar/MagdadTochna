import pygame
import sys
import time
import random
import json
from pathlib import Path

# Add project paths for solvers
PROJECT_ROOT = Path(__file__).parent
sys.path.append(str(PROJECT_ROOT / "prompt_engineering_bot" / "algorithmic_solvers"))

try:
    from uno_solver import solve as solve_uno
    from blackjack_solver import solve as solve_blackjack
    from trash_solver import solve as solve_trash
    from war_solver import solve as solve_war
except ImportError as e:
    print(f"Warning: Some solvers could not be imported: {e}")

# --- Configuration ---
SCREEN_WIDTH = 1100
SCREEN_HEIGHT = 1000
CARD_WIDTH = 75
CARD_HEIGHT = 110
BG_COLOR = (20, 30, 20)
TEXT_COLOR = (255, 255, 255)

class Card:
    def __init__(self, rank, suit, x, y):
        self.rank = str(rank)
        self.suit = suit
        self.name = f"{rank} of {suit}"
        self.rect = pygame.Rect(x, y, CARD_WIDTH, CARD_HEIGHT)
        self.is_dragging = False
        self.offset_x = 0
        self.offset_y = 0
        self.start_pos = (x, y)
        self.color = (220, 0, 0) if suit in ['Hearts', 'Diamonds'] else (10, 10, 10)
        self.face_up = True 
        self.owner = "DECK"

    def draw(self, screen, font):
        pygame.draw.rect(screen, (255, 255, 255), self.rect, border_radius=8)
        pygame.draw.rect(screen, (50, 50, 50), self.rect, 2, border_radius=8)
        r_text = font.render(self.rank, True, self.color)
        s_text = font.render(self.suit, True, self.color)
        screen.blit(r_text, (self.rect.x + 8, self.rect.y + 5))
        screen.blit(s_text, (self.rect.x + 8, self.rect.y + 35))

def draw_zone(screen, font, rect, label, color, border=2):
    pygame.draw.rect(screen, color, rect, border, border_radius=15)
    lbl = font.render(label, True, (200, 200, 200))
    screen.blit(lbl, (rect.x + 10, rect.y - 25))

def get_rank_val(rank):
    m = {"A": 14, "K": 13, "Q": 12, "J": 11, "10": 10, "9": 9, "8": 8, "7": 7, "6": 6, "5": 5, "4": 4, "3": 3, "2": 2}
    return m.get(rank, 0)

class GameApp:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Magdad Card Game Simulator")
        self.clock = pygame.time.Clock()
        self.font_ui = pygame.font.SysFont("Consolas", 22, bold=True)
        self.font_sm = pygame.font.SysFont("Consolas", 16, bold=True)
        self.card_font = pygame.font.SysFont("Arial", 16, bold=True)
        self.state = "MENU"
        self.game_type = None
        self.reset_game()

    def reset_game(self):
        self.deck_stack = []
        self.bot_hand = []
        self.user_hand = []
        self.pile = []
        self.turn = "USER"
        self.selected_card = None
        self.bot_timer = 0
        self.has_drawn = False
        self.game_msg = ""
        
        ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
        suits = ['Spades', 'Hearts', 'Diamonds', 'Clubs']
        raw = [(r, s) for s in suits for r in ranks]
        random.shuffle(raw)
        for r, s in raw:
            c = Card(r, s, 50, 450)
            self.deck_stack.append(c)

    def start_game(self, gtype):
        self.game_type = gtype
        self.state = "PLAYING"
        count = 7 if gtype in ["UNO", "TRASH"] else 2
        if gtype == "WAR": count = 26
        
        for _ in range(count):
            if self.deck_stack:
                c = self.deck_stack.pop(); c.owner = "BOT"; self.bot_hand.append(c)
            if self.deck_stack:
                c = self.deck_stack.pop(); c.owner = "USER"; self.user_hand.append(c)
        
        if gtype == "UNO":
            c = self.deck_stack.pop(); c.owner = "PILE"; c.rect.center = (550, 450); self.pile.append(c)

    def generate_state_text(self):
        piles_str = ""
        for i in range(1, 7):
            val = self.pile[-1].name if (i == 1 and self.pile) else "FALSE"
            piles_str += f"P{i}: {val}\n"
            
        bot_hand_json = json.dumps([c.name for c in self.bot_hand])
        user_hand_json = json.dumps([c.name for c in self.user_hand])
        
        text = f"{piles_str}\n"
        text += f"MYOPEN: []\n"
        text += f"MYCLOSED: {bot_hand_json}\n"
        text += f"MYDECK: {'TRUE' if self.game_type == 'WAR' else 'FALSE'}\n\n"
        text += f"PLAYER2_OPEN: {user_hand_json}\n"
        text += f"PLAYER2_DECK: FALSE\n\n"
        text += f"PLAYER3_OPEN: []\n"
        text += f"PLAYER3_DECK: FALSE\n\n"
        text += f"PUBLIC_DECK: {'TRUE' if self.deck_stack else 'FALSE'}"
        return text

    def run(self):
        while True:
            if self.state == "MENU": self.menu_loop()
            else: self.game_loop()

    def menu_loop(self):
        self.screen.fill((30, 30, 50))
        title = self.font_ui.render("SELECT GAME MODE", True, (255, 255, 255))
        self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 100))
        modes = ["UNO", "BLACKJACK", "TRASH", "WAR"]
        buttons = []
        for i, m in enumerate(modes):
            r = pygame.Rect(SCREEN_WIDTH//2 - 100, 250 + i*80, 200, 60)
            buttons.append((r, m))
            pygame.draw.rect(self.screen, (100, 100, 150), r, border_radius=10)
            txt = self.font_ui.render(m, True, (255, 255, 255))
            self.screen.blit(txt, (r.centerx - txt.get_width()//2, r.centery - txt.get_height()//2))
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                for r, m in buttons:
                    if r.collidepoint(event.pos): self.start_game(m)
        pygame.display.flip(); self.clock.tick(30)

    def game_loop(self):
        mx, my = pygame.mouse.get_pos()
        if self.turn == "BOT" and not self.selected_card:
            if self.bot_timer == 0: self.bot_timer = time.time()
            if time.time() - self.bot_timer > 1.2:
                st = self.generate_state_text()
                if self.game_type == "UNO": move = solve_uno(st)
                elif self.game_type == "BLACKJACK": move = solve_blackjack(st)
                elif self.game_type == "TRASH": move = solve_trash(st)
                else: move = solve_war(st)
                
                for line in move:
                    if "PLAY:" in line:
                        src, dest, card_name = [x.strip() for x in line.split(":", 1)[1].split(",")]
                        # Handle Draw
                        if src == "PUBLIC_DECK" and self.deck_stack:
                            c = self.deck_stack.pop(); c.owner = "BOT"; self.bot_hand.append(c)
                            print(f"🤖 Bot drew a card.")
                        # Handle Play from hand
                        elif src == "MYCLOSED":
                            target = next((c for c in self.bot_hand if c.name.lower() == card_name.lower()), None)
                            if not target and self.game_type == "WAR" and self.bot_hand: target = self.bot_hand.pop()
                            if target:
                                target.owner = "PILE"; target.rect.center = (550, 450)
                                self.pile.append(target)
                                if target in self.bot_hand: self.bot_hand.remove(target)
                                print(f"🤖 Bot played {target.name}")
                
                self.turn = "USER"; self.has_drawn = False; self.bot_timer = 0

        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: self.state = "MENU"; self.reset_game(); return
            if event.type == pygame.MOUSEBUTTONDOWN and self.turn == "USER":
                if pygame.Rect(350, 400, 150, 180).collidepoint(mx, my) and self.deck_stack:
                    c = self.deck_stack.pop(); c.owner = "USER"; self.user_hand.append(c)
                    self.has_drawn = True
                    if self.game_type in ["BLACKJACK", "WAR"]: self.turn = "BOT"
                if self.has_drawn and pygame.Rect(950, 750, 100, 50).collidepoint(mx, my):
                    self.turn = "BOT"; self.has_drawn = False
                if self.game_type == "WAR" and len(self.pile) >= 2 and pygame.Rect(950, 400, 120, 50).collidepoint(mx, my):
                    v1, v2 = get_rank_val(self.pile[-2].rank), get_rank_val(self.pile[-1].rank)
                    self.game_msg = "BOT WINS" if v1 > v2 else "USER WINS" if v2 > v1 else "WAR!"
                    self.pile = []
                for c in reversed(self.user_hand):
                    if c.rect.collidepoint(mx, my):
                        self.selected_card = c; c.is_dragging = True
                        c.offset_x, c.offset_y = c.rect.x - mx, c.rect.y - my
                        self.user_hand.remove(c); self.user_hand.append(c)
                        break
            elif event.type == pygame.MOUSEBUTTONUP and self.turn == "USER" and self.selected_card:
                self.selected_card.is_dragging = False
                if pygame.Rect(550, 400, 150, 180).colliderect(self.selected_card.rect):
                    self.selected_card.owner = "PILE"; self.selected_card.rect.center = (550, 450)
                    self.pile.append(self.selected_card); self.user_hand.remove(self.selected_card)
                    self.turn = "BOT"; self.has_drawn = False
                else: self.selected_card.rect.topleft = self.selected_card.start_pos
                self.selected_card = None
            elif event.type == pygame.MOUSEMOTION and self.selected_card:
                self.selected_card.rect.x, self.selected_card.rect.y = mx + self.selected_card.offset_x, my + self.selected_card.offset_y

        self.screen.fill(BG_COLOR)
        draw_zone(self.screen, self.font_sm, pygame.Rect(350, 400, 150, 180), "DECK", (200, 100, 150))
        draw_zone(self.screen, self.font_sm, pygame.Rect(550, 400, 150, 180), "PILE", (100, 200, 150))
        draw_zone(self.screen, self.font_sm, pygame.Rect(100, 100, 900, 150), "BOT", (150, 100, 100), 1)
        draw_zone(self.screen, self.font_sm, pygame.Rect(100, 750, 900, 150), "USER", (100, 150, 100), 3)
        if self.has_drawn:
            pygame.draw.rect(self.screen, (200, 50, 50), (950, 750, 100, 50), border_radius=5)
            self.screen.blit(self.font_sm.render("PASS", True, (255, 255, 255)), (965, 765))
        if self.game_type == "WAR" and len(self.pile) >= 2:
            pygame.draw.rect(self.screen, (50, 150, 255), (950, 400, 120, 50), border_radius=5)
            self.screen.blit(self.font_sm.render("COMPARE", True, (255, 255, 255)), (965, 415))
        for i, c in enumerate(self.bot_hand): 
            if not c.is_dragging: c.rect.topleft = (120 + i*min(35, 800//max(1,len(self.bot_hand))), 120)
        for i, c in enumerate(self.user_hand): 
            if not c.is_dragging: c.rect.topleft = (120 + i*min(45, 800//max(1,len(self.user_hand))), 770)
        for c in self.deck_stack + self.pile + self.bot_hand + self.user_hand: c.draw(self.screen, self.card_font)
        self.screen.blit(self.font_ui.render(f"MODE: {self.game_type} | TURN: {self.turn}", True, (255, 255, 0)), (20, 20))
        if self.game_msg:
            msg_t = self.font_ui.render(self.game_msg, True, (255, 50, 50))
            self.screen.blit(msg_t, (SCREEN_WIDTH//2 - msg_t.get_width()//2, 600))
        pygame.display.flip(); self.clock.tick(60)

if __name__ == "__main__": GameApp().run()
