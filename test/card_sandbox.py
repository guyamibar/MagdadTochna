import pygame
import sys

# --- Configuration ---
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 1000
CARD_WIDTH = 70
CARD_HEIGHT = 100
BG_COLOR = (20, 20, 20)
TEXT_COLOR = (255, 255, 255)

class Card:
    def __init__(self, rank, suit, x, y):
        self.rank = str(rank)
        self.suit = suit
        self.rect = pygame.Rect(x, y, CARD_WIDTH, CARD_HEIGHT)
        self.is_dragging = False
        self.offset_x = 0
        self.offset_y = 0
        self.start_pos = (x, y) # For snapping back
        self.color = (200, 0, 0) if suit in ['Hearts', 'Diamonds'] else (0, 0, 0)

    def draw(self, screen, font):
        pygame.draw.rect(screen, (255, 255, 255), self.rect, border_radius=5)
        pygame.draw.rect(screen, (0, 0, 0), self.rect, 1, border_radius=5)
        r_text = font.render(self.rank, True, self.color)
        s_text = font.render(self.suit[0], True, self.color)
        screen.blit(r_text, (self.rect.x + 5, self.rect.y + 2))
        screen.blit(s_text, (self.rect.x + 5, self.rect.y + 20))

def draw_zone(screen, font, rect, label, color, fill=True):
    if fill:
        pygame.draw.rect(screen, color, rect)
    else:
        pygame.draw.rect(screen, color, rect, 2)
    lbl = font.render(label, True, TEXT_COLOR)
    screen.blit(lbl, (rect.x + (rect.width - lbl.get_width()) // 2, rect.y + (rect.height - lbl.get_height()) // 2))

def is_valid_uno_move(played_card, top_card):
    if top_card is None: return True
    return played_card.rank == top_card.rank or played_card.suit == top_card.suit

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Uno Simulator - Rule Enforced")
    clock = pygame.time.Clock()
    font_zones = pygame.font.SysFont("Consolas", 18)
    card_font = pygame.font.SysFont("Arial", 16, bold=True)

    # --- Define Zones ---
    gw, gh = 180, 140
    start_x, start_y = 230, 150
    
    # Map zones for lookup
    deck_zone = pygame.Rect(start_x, start_y, gw, gh)
    pile_zone = pygame.Rect(start_x + gw, start_y, gw, gh)
    my_closed_zone = pygame.Rect(170, 770, 600, 130)

    zones = [
        (pygame.Rect(410, 10, 120, 140), "CARD REF", (255, 255, 255), False),
        (deck_zone, "DECK", (255, 105, 180), True),
        (pile_zone, "P1 (PILE)", (230, 255, 180), True),
        (pygame.Rect(start_x + gw*2, start_y, gw, gh), "P2", (255, 204, 51), True),
        (pygame.Rect(start_x, start_y + gh, gw, gh), "P3", (130, 70, 100), True),
        (pygame.Rect(start_x + gw, start_y + gh, gw, gh), "P4", (220, 100, 90), True),
        (pygame.Rect(start_x + gw*2, start_y + gh, gw, gh), "P5", (255, 51, 255), True),
        (pygame.Rect(420, 450, 100, 140), "MYDECK", (153, 51, 255), True),
        (pygame.Rect(170, 620, 600, 130), "MY_OPEN ROW", (144, 238, 144), True),
        (my_closed_zone, "MY_CLOSED ROW", (128, 160, 50), True),
    ]

    # Side bars
    side_bars = [
        (pygame.Rect(0, 0, 160, 130), (240, 230, 240)),
        (pygame.Rect(0, 130, 160, 500), (70, 120, 140)),
        (pygame.Rect(800, 0, 200, 130), (100, 150, 100)),
        (pygame.Rect(800, 130, 200, 500), (110, 140, 50)),
    ]

    # --- Create Deck ---
    ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
    suits = ['Spades', 'Hearts', 'Diamonds', 'Clubs']
    cards = []
    for i, suit in enumerate(suits):
        for j, rank in enumerate(ranks):
            cards.append(Card(rank, suit, deck_zone.x + 5, deck_zone.y + 5))

    # Initial card on pile
    top_pile_card = cards.pop()
    top_pile_card.rect.center = pile_zone.center
    top_pile_card.start_pos = top_pile_card.rect.topleft
    cards_on_pile = [top_pile_card]

    selected_card = None
    running = True

    while running:
        mx, my = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    # Check if clicking deck to draw
                    if not selected_card:
                        # Find top card in deck zone
                        deck_cards = [c for c in cards if deck_zone.colliderect(c.rect)]
                        if deck_cards and deck_zone.collidepoint(event.pos):
                            c = deck_cards[-1]
                            c.rect.topleft = (my_closed_zone.x + 10, my_closed_zone.y + 10)
                            c.start_pos = c.rect.topleft
                            continue

                    for card in reversed(cards + cards_on_pile):
                        if card.rect.collidepoint(event.pos):
                            # Don't allow moving cards already in the pile unless it's the top one
                            if card in cards_on_pile and card != cards_on_pile[-1]: continue
                            
                            selected_card = card
                            card.is_dragging = True
                            card.offset_x, card.offset_y = card.rect.x - mx, card.rect.y - my
                            if card in cards: cards.remove(card); cards.append(card)
                            break
            
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1 and selected_card:
                    selected_card.is_dragging = False
                    
                    # Check drop location
                    if pile_zone.colliderect(selected_card.rect):
                        # Attempting to play Uno move
                        if is_valid_uno_move(selected_card, cards_on_pile[-1]):
                            selected_card.rect.center = pile_zone.center
                            selected_card.start_pos = selected_card.rect.topleft
                            if selected_card in cards: cards.remove(selected_card)
                            cards_on_pile.append(selected_card)
                            print(f"✅ Valid Move: {selected_card.rank} of {selected_card.suit}")
                        else:
                            # Illegal move - snap back
                            selected_card.rect.topleft = selected_card.start_pos
                            print("❌ Illegal Uno Move! Must match rank or suit.")
                    else:
                        # General movement allowed elsewhere
                        selected_card.start_pos = selected_card.rect.topleft
                    
                    selected_card = None
            
            elif event.type == pygame.MOUSEMOTION:
                if selected_card and selected_card.is_dragging:
                    selected_card.rect.x, selected_card.rect.y = mx + selected_card.offset_x, my + selected_card.offset_y

        # --- Draw ---
        screen.fill(BG_COLOR)
        for rect, color in side_bars: pygame.draw.rect(screen, color, rect)
        for z_rect, label, color, fill in zones: draw_zone(screen, font_zones, z_rect, label, color, fill)
        for card in cards: card.draw(screen, card_font)
        for card in cards_on_pile: card.draw(screen, card_font)
        
        pygame.display.flip()
        clock.tick(60)
    pygame.quit()

if __name__ == "__main__":
    main()
