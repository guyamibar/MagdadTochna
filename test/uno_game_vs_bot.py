import pygame
import sys
import time
import random
from pathlib import Path

# Add project paths for solvers
PROJECT_ROOT = Path(__file__).parent
sys.path.append(str(PROJECT_ROOT / "prompt_engineering_bot" / "algorithmic_solvers"))

try:
    from uno_solver import solve as solve_uno
except ImportError:
    # Minimal fallback solver if import fails
    def solve_uno(state_text):
        return ["* PLAY: PUBDECK_1,MYCLOSED,None", "* PASS"]

# --- Configuration ---
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 1000
CARD_WIDTH = 75
CARD_HEIGHT = 110
BG_COLOR = (20, 25, 20)
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
        if self.face_up:
            pygame.draw.rect(screen, (255, 255, 255), self.rect, border_radius=8)
            pygame.draw.rect(screen, (50, 50, 50), self.rect, 2, border_radius=8)
            r_text = font.render(self.rank, True, self.color)
            s_text = font.render(self.suit[:1], True, self.color) # Just initial
            screen.blit(r_text, (self.rect.x + 8, self.rect.y + 5))
            # Draw suit symbol/text lower
            s_full = font.render(self.suit, True, self.color)
            screen.blit(s_full, (self.rect.x + 8, self.rect.y + 30))
        else:
            pygame.draw.rect(screen, (40, 40, 120), self.rect, border_radius=8)
            pygame.draw.rect(screen, (200, 200, 200), self.rect, 2, border_radius=8)
            pattern = font.render("UNO", True, (255, 255, 255))
            screen.blit(pattern, (self.rect.centerx - pattern.get_width()//2, self.rect.centery - pattern.get_height()//2))

def draw_zone(screen, font, rect, label, color, border=2):
    pygame.draw.rect(screen, color, rect, border, border_radius=15)
    lbl = font.render(label, True, (200, 200, 200))
    screen.blit(lbl, (rect.x + 10, rect.y - 25))

def generate_state_text(cards, cards_on_pile, has_deck):
    top_card = cards_on_pile[-1].name if cards_on_pile else "NONE"
    bot_cards = [c.name for c in cards if c.owner == "BOT"]
    user_cards = [c.name for c in cards if c.owner == "USER"]
    
    text = f"PUBLIC PILES TOP CARDS:\n1. Top pile Card: {top_card}\n\n"
    text += f"MY OPEN CARDS: NONE\n"
    text += f"MY CLOSED CARDS: [{', '.join(bot_cards)}]\n\n"
    text += f"OPENPLAYER_2: [{', '.join(user_cards)}]\n"
    text += f"MYDECK: NONE\n"
    text += f"PUBLICDECK: {'TRUE' if has_deck else 'FALSE'}"
    return text

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Uno vs Bot - Balanced Rules")
    clock = pygame.time.Clock()
    font_ui = pygame.font.SysFont("Consolas", 22, bold=True)
    card_font = pygame.font.SysFont("Arial", 18, bold=True)

    # --- Layout ---
    deck_zone = pygame.Rect(250, 350, 150, 180)
    pile_zone = pygame.Rect(450, 350, 150, 180)
    bot_zone = pygame.Rect(100, 100, 800, 150)
    user_zone = pygame.Rect(100, 750, 800, 150)
    pass_btn_rect = pygame.Rect(820, 650, 120, 50)

    # --- Setup Deck ---
    ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
    suits = ['Spades', 'Hearts', 'Diamonds', 'Clubs']
    raw_deck = [(r, s) for s in suits for r in ranks]
    random.shuffle(raw_deck)

    deck_stack = []
    for r, s in raw_deck:
        c = Card(r, s, deck_zone.x + 20, deck_zone.y + 20)
        c.face_up = False
        deck_stack.append(c)

    bot_hand = []
    user_hand = []
    pile = []

    # Deal 7
    for i in range(7):
        # Bot
        c = deck_stack.pop(); c.owner = "BOT"; c.face_up = False; bot_hand.append(c)
        # User
        c = deck_stack.pop(); c.owner = "USER"; c.face_up = True; user_hand.append(c)

    # Start pile
    c = deck_stack.pop(); c.owner = "PILE"; c.face_up = True; c.rect.center = pile_zone.center; pile.append(c)

    turn = "USER"
    has_drawn = False # Track if user drew this turn
    selected_card = None
    running = True
    bot_timer = 0

    while running:
        mx, my = pygame.mouse.get_pos()
        
        # Organize hands
        for i, c in enumerate(bot_hand):
            if not c.is_dragging: c.rect.topleft = (bot_zone.x + 20 + i*40, bot_zone.y + 20)
        for i, c in enumerate(user_hand):
            if not c.is_dragging: c.rect.topleft = (user_zone.x + 20 + i*45, user_zone.y + 20)

        # --- Bot Logic ---
        if turn == "BOT" and not selected_card:
            if bot_timer == 0: bot_timer = time.time()
            if time.time() - bot_timer > 1.2:
                state_text = generate_state_text(bot_hand + user_hand, pile, len(deck_stack) > 0)
                move = solve_uno(state_text)
                action = move[0]
                
                if "PUBDECK_1,MYCLOSED" in action and deck_stack:
                    c = deck_stack.pop(); c.owner = "BOT"; c.face_up = False; bot_hand.append(c)
                    print("🤖 Bot drew a card.")
                else:
                    card_name = action.split(',')[-1].strip().lower()
                    target = next((c for c in bot_hand if c.name.lower() == card_name), None)
                    if target:
                        target.owner = "PILE"; target.face_up = True; target.rect.center = pile_zone.center
                        pile.append(target); bot_hand.remove(target)
                        print(f"🤖 Bot played {target.name}")
                
                turn = "USER"; has_drawn = False; bot_timer = 0

        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            
            elif event.type == pygame.MOUSEBUTTONDOWN and turn == "USER":
                if event.button == 1:
                    # Click Pass
                    if has_drawn and pass_btn_rect.collidepoint(mx, my):
                        turn = "BOT"; has_drawn = False; continue

                    # Click deck to draw
                    if deck_zone.collidepoint(mx, my) and deck_stack:
                        c = deck_stack.pop(); c.owner = "USER"; c.face_up = True; user_hand.append(c)
                        has_drawn = True; continue

                    # Pick up card
                    for c in reversed(user_hand):
                        if c.rect.collidepoint(mx, my):
                            selected_card = c; c.is_dragging = True
                            c.offset_x, c.offset_y = c.rect.x - mx, c.rect.y - my
                            user_hand.remove(c); user_hand.append(c)
                            break
            
            elif event.type == pygame.MOUSEBUTTONUP and turn == "USER":
                if event.button == 1 and selected_card:
                    selected_card.is_dragging = False
                    if pile_zone.colliderect(selected_card.rect):
                        top = pile[-1]
                        if selected_card.rank == top.rank or selected_card.suit == top.suit:
                            selected_card.owner = "PILE"; selected_card.rect.center = pile_zone.center
                            pile.append(selected_card); user_hand.remove(selected_card)
                            turn = "BOT"; has_drawn = False
                    selected_card = None

            elif event.type == pygame.MOUSEMOTION and selected_card:
                selected_card.rect.x, selected_card.rect.y = mx + selected_card.offset_x, my + selected_card.offset_y

        # --- Draw ---
        screen.fill(BG_COLOR)
        draw_zone(screen, font_ui, deck_zone, "DECK (Click to Draw)", (200, 100, 150))
        draw_zone(screen, font_ui, pile_zone, "PILE", (100, 200, 150))
        draw_zone(screen, font_ui, bot_zone, "BOT (PLAYER 1)", (150, 150, 150), 1)
        draw_zone(screen, font_ui, user_zone, "USER (PLAYER 2)", (150, 200, 150), 3)
        
        # Pass Button
        if has_drawn:
            pygame.draw.rect(screen, (200, 50, 50), pass_btn_rect, border_radius=5)
            ptxt = font_ui.render("PASS", True, (255, 255, 255))
            screen.blit(ptxt, (pass_btn_rect.centerx - ptxt.get_width()//2, pass_btn_rect.centery - ptxt.get_height()//2))

        # Status Hints
        msg = "YOUR TURN: DRAG MATCHING CARD" if not has_drawn else "DRAWN! PLAY CARD OR PASS"
        if any((c.rank == pile[-1].rank or c.suit == pile[-1].suit) for c in user_hand):
            hint_color = (100, 255, 100)
        else:
            hint_color = (255, 100, 100)
            if not has_drawn: msg = "NO MATCH! CLICK DECK TO DRAW"
        
        if turn == "USER":
            screen.blit(font_ui.render(msg, True, hint_color), (SCREEN_WIDTH//2 - 200, 680))
        else:
            screen.blit(font_ui.render("BOT IS THINKING...", True, (255, 255, 0)), (SCREEN_WIDTH//2 - 100, 680))

        # Draw Cards
        for c in deck_stack: c.draw(screen, card_font)
        for c in pile: c.draw(screen, card_font)
        for c in bot_hand: c.draw(screen, card_font)
        for c in user_hand: c.draw(screen, card_font)
        
        pygame.display.flip()
        clock.tick(60)
    pygame.quit()

if __name__ == "__main__":
    main()
