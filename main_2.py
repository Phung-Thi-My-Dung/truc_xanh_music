import pygame
import random
import asyncio
import platform
import os

# Initialize Pygame
pygame.init()

# Screen setup
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Green Bamboo Music")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
HIGHLIGHT = (200, 200, 200)
RED = (255, 0, 0)
PASTEL_GREEN = (204, 255, 204)  # Light pastel green background
LIGHT_BROWN = (160, 110, 60) # Light brown for text

# Game settings
FPS = 60
CARD_WIDTH, CARD_HEIGHT = 60, 60
CARD_MARGIN = 10  # Reduced margin to 10 pixels to prevent overflow in 20-pair mode
ENLARGED_CARD_WIDTH, ENLARGED_CARD_HEIGHT = 90, 90  # Enlarged size for all cards

# Notes from the image
NOTES = [
    'A2', 'A3', 'A4', 'A5', 'B2', 'B3', 'B4', 'B5', 'C2', 'C3', 'C4', 'C5', 'C6',
    'D2', 'D3', 'D4', 'D5', 'E2', 'E3', 'E4', 'E5', 'F2', 'F3', 'F4', 'F5',
    'G2', 'G3', 'G4', 'G5'
]

# Load note images from the "images" directory
NOTE_IMAGES = {}
ENLARGED_NOTE_IMAGES = {}
for note in NOTES:
    image = pygame.image.load(f"images/{note}.png")
    NOTE_IMAGES[note] = pygame.transform.scale(image, (CARD_WIDTH, CARD_HEIGHT))
    ENLARGED_NOTE_IMAGES[note] = pygame.transform.scale(image, (ENLARGED_CARD_WIDTH, ENLARGED_CARD_HEIGHT))

# Font
font = pygame.font.SysFont('arial', 36)
small_font = pygame.font.SysFont('arial', 24)  # Smaller font for copyright and sound note

# Load MP3 sounds from the piano-mp3 directory
NOTE_SOUNDS = {}
for note in NOTES:
    sound_path = os.path.join("piano-mp3", f"{note}.mp3")
    try:
        NOTE_SOUNDS[note] = pygame.mixer.Sound(sound_path)
    except pygame.error as e:
        print(f"Error loading {sound_path}: {e}")
        NOTE_SOUNDS[note] = pygame.mixer.Sound(os.path.join("piano-mp3", "C4.mp3"))  # Fallback to C4.mp3

class Card:
    def __init__(self, note, x, y):
        self.note = note
        self.rect = pygame.Rect(x, y, ENLARGED_CARD_WIDTH, ENLARGED_CARD_HEIGHT)  # Use enlarged size for all
        self.enlarged_rect = self.rect  # No need for separate enlarged rect
        self.is_flipped = False
        self.is_matched = False
        self.is_hint = False

    def draw(self, surface):
        if self.is_matched or self.is_flipped or self.is_hint:
            surface.blit(ENLARGED_NOTE_IMAGES[self.note], self.rect)  # Use enlarged image
        else:
            pygame.draw.rect(surface, GRAY, self.rect)  # Use same rect size, but gray background

class Button:
    def __init__(self, text, x, y, width, height, action=None):
        self.text = text
        self.rect = pygame.Rect(x, y, width, height)
        self.hovered = False
        self.action = action

    def draw(self, surface):
        color = HIGHLIGHT if self.hovered else WHITE
        pygame.draw.rect(surface, color, self.rect)
        pygame.draw.rect(surface, BLACK, self.rect, 2)
        text_surface = font.render(self.text, True, LIGHT_BROWN)  # Use light brown for button text
        surface.blit(text_surface, (self.rect.x + (self.rect.width - text_surface.get_width()) // 2,
                                  self.rect.y + (self.rect.height - text_surface.get_height()) // 2))

    def check_hover(self, pos):
        self.hovered = self.rect.collidepoint(pos)

    def on_click(self):
        if self.action:
            self.action()

class Game:
    def __init__(self):
        self.state = 'menu'
        self.mode = None
        self.grid_size = None
        self.cards = []
        self.flipped_cards = []
        self.current_player = 1
        self.scores = {1: 0, 2: 0}
        self.waiting = False
        self.wait_start_time = 0
        self.wait_duration = 1000
        self.message = ""
        self.message_timer = 0
        self.hints_remaining = 5
        self.hint_timer = 0
        self.hint_duration = 3000  # 3 seconds
        self.hint_card = None
        self.buttons = {
            'menu': [
                Button("Single Player", WIDTH // 2 - 100, 200, 200, 50, lambda: self.set_mode('single')),
                Button("Multiplayer", WIDTH // 2 - 100, 260, 200, 50, lambda: self.set_mode('multi')),
                Button("10 Pairs", WIDTH // 2 - 100, 320, 200, 50, lambda: self.set_grid_size(20)),
                Button("20 Pairs", WIDTH // 2 - 100, 380, 200, 50, lambda: self.set_grid_size(40)),
                Button("Exit", WIDTH // 2 - 100, 440, 200, 50, pygame.quit)
            ],
            'playing': [
                Button("Hint", WIDTH - 150, HEIGHT - 50, 100, 40, self.use_hint),
                Button("Back", 20, HEIGHT - 50, 100, 40, self.back_to_menu),
                Button("Exit", 140, HEIGHT - 50, 100, 40, pygame.quit)  # Moved to top-right corner
            ],
            'game_over': [
                Button("Play Again", WIDTH // 2 - 100, HEIGHT // 2 + 100, 200, 50, self.restart_game),
                Button("Exit", WIDTH // 2 - 100, HEIGHT // 2 + 160, 200, 50, pygame.quit)
            ]
        }

    def set_mode(self, mode):
        self.mode = mode
        if self.mode and self.grid_size:
            self.setup_game(self.mode, self.grid_size)

    def set_grid_size(self, size):
        self.grid_size = size
        if self.mode and self.grid_size:
            self.setup_game(self.mode, self.grid_size)

    def setup_game(self, mode, grid_size):
        self.mode = mode
        self.grid_size = grid_size
        self.cards = []
        self.flipped_cards = []
        self.scores = {1: 0, 2: 0}
        self.current_player = 1
        self.hints_remaining = 5
        self.state = 'playing'

        pairs = grid_size // 2
        selected_notes = random.sample(NOTES, pairs)
        card_notes = selected_notes * 2
        random.shuffle(card_notes)

        # Adjusted grid to use enlarged card size (90x90 pixels) with reduced margin
        rows = 4 if grid_size == 20 else 5
        cols = grid_size // rows
        card_spacing = ENLARGED_CARD_WIDTH + CARD_MARGIN  # Use 90 + 10 = 100 pixels spacing
        start_x = (WIDTH - (cols * card_spacing - CARD_MARGIN)) // 2
        start_y = (HEIGHT - (rows * card_spacing - CARD_MARGIN)) // 2

        for i in range(rows):
            for j in range(cols):
                idx = i * cols + j
                if idx < len(card_notes):
                    x = start_x + j * card_spacing
                    y = start_y + i * card_spacing
                    self.cards.append(Card(card_notes[idx], x, y))

    def draw(self):
        screen.fill(PASTEL_GREEN)  # Use pastel green background
        if self.state == 'menu':
            title = font.render("Green Bamboo Music", True, LIGHT_BROWN)  # Use light brown text
            screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 100))
            instruction = font.render("Select mode and grid size", True, LIGHT_BROWN)
            screen.blit(instruction, (WIDTH // 2 - instruction.get_width() // 2, 150))
            copyright = small_font.render("Game idea, design and development: Nhat Le and Dung T.M Phung", True, LIGHT_BROWN)
            screen.blit(copyright, (WIDTH // 2 - copyright.get_width() // 2, HEIGHT - 50))
            for button in self.buttons['menu']:
                button.draw(screen)
            if self.mode:
                mode_text = font.render(f"Mode: {'Single' if self.mode == 'single' else 'Multi'}", True, LIGHT_BROWN)
                screen.blit(mode_text, (WIDTH // 2 - mode_text.get_width() // 2, 450))
            if self.grid_size:
                grid_text = font.render(f"Grid: {self.grid_size // 2} Pairs", True, LIGHT_BROWN)
                screen.blit(grid_text, (WIDTH // 2 - grid_text.get_width() // 2, 500))
        elif self.state == 'playing':
            for card in self.cards:
                card.draw(screen)
            score_text = font.render(f"Player 1: {self.scores[1]}", True, LIGHT_BROWN)
            screen.blit(score_text, (10, 10))
            if self.mode == 'multi':
                score_text2 = font.render(f"Player 2: {self.scores[2]}", True, LIGHT_BROWN)
                screen.blit(score_text2, (WIDTH - score_text2.get_width() - 10, 10))
                player_text = font.render(f"Turn: Player {self.current_player}", True, LIGHT_BROWN)
                screen.blit(player_text, (WIDTH // 2 - player_text.get_width() // 2, 10))
            if self.message:
                msg_surface = small_font.render(self.message, True, LIGHT_BROWN)
                screen.blit(msg_surface, (WIDTH // 2 - msg_surface.get_width() // 2, HEIGHT - 60))


            sound_note = small_font.render("Turn on sound for the best experience", True, LIGHT_BROWN)
            screen.blit(sound_note, (WIDTH // 2 - sound_note.get_width() // 2, HEIGHT - 30))  # At the bottom
            for button in self.buttons['playing']:
                button.draw(screen)
            # hints_text = font.render(f"Hints: {self.hints_remaining}", True, LIGHT_BROWN)
            # screen.blit(hints_text, (WIDTH - 150, HEIGHT - 90))
        elif self.state == 'game_over':
            winner = 1 if self.scores[1] > self.scores[2] else 2 if self.scores[2] > self.scores[1] else 0
            if self.mode == 'single':
                text = font.render(f"Congratulations! Score: {self.scores[1]}", True, LIGHT_BROWN)
            else:
                text = font.render(f"Congratulations! Player {winner} Wins!" if winner else "Congratulations! Tie!", True, LIGHT_BROWN)
            screen.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT // 2))
            for button in self.buttons['game_over']:
                button.draw(screen)

    def handle_click(self, pos):
        if self.state == 'menu':
            for button in self.buttons['menu']:
                if button.rect.collidepoint(pos):
                    button.on_click()
        elif self.state == 'playing':
            for button in self.buttons['playing']:
                if button.rect.collidepoint(pos):
                    button.on_click()
            if not self.waiting and len(self.flipped_cards) < 2:
                for card in self.cards:
                    if card.rect.collidepoint(pos) and not card.is_flipped and not card.is_matched:
                        card.is_flipped = True
                        NOTE_SOUNDS[card.note].play()
                        self.flipped_cards.append(card)
                        if len(self.flipped_cards) == 2:
                            self.check_match()
        elif self.state == 'game_over':
            for button in self.buttons['game_over']:
                if button.rect.collidepoint(pos):
                    button.on_click()

    def check_match(self):
        card1, card2 = self.flipped_cards
        if card1.note == card2.note:
            card1.is_matched = card2.is_matched = True
            self.scores[self.current_player] += 1
            self.flipped_cards = []
            self.message = "Match!"
            self.message_timer = pygame.time.get_ticks()
            if all(card.is_matched for card in self.cards):
                self.state = 'game_over'
        else:
            self.waiting = True
            self.wait_start_time = pygame.time.get_ticks()
            self.message = "No Match!"
            self.message_timer = pygame.time.get_ticks()

    def use_hint(self):
        if self.hints_remaining > 0 and len(self.flipped_cards) == 1:
            selected_card = self.flipped_cards[0]
            for card in self.cards:
                if card.note == selected_card.note and card != selected_card and not card.is_matched:
                    card.is_hint = True
                    self.hint_card = card
                    self.hint_timer = pygame.time.get_ticks()
                    self.hints_remaining -= 1
                    break

    def back_to_menu(self):
        self.state = 'menu'
        self.mode = None
        self.grid_size = None

    def restart_game(self):
        self.setup_game(self.mode, self.grid_size)

    def update(self):
        if self.waiting and pygame.time.get_ticks() - self.wait_start_time > self.wait_duration:
            for card in self.flipped_cards:
                card.is_flipped = False
            self.flipped_cards = []
            self.waiting = False
            if self.mode == 'multi':
                self.current_player = 2 if self.current_player == 1 else 1
        if self.message and pygame.time.get_ticks() - self.message_timer > 1000:
            self.message = ""
        if self.hint_card and pygame.time.get_ticks() - self.hint_timer > self.hint_duration:
            self.hint_card.is_hint = False
            self.hint_card = None

game = Game()

async def main():
    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type == pygame.MOUSEMOTION:
                if game.state == 'menu':
                    for button in game.buttons['menu']:
                        button.check_hover(event.pos)
                elif game.state == 'playing':
                    for button in game.buttons['playing']:
                        button.check_hover(event.pos)
                elif game.state == 'game_over':
                    for button in game.buttons['game_over']:
                        button.check_hover(event.pos)
            if event.type == pygame.MOUSEBUTTONDOWN:
                game.handle_click(event.pos)
            if event.type == pygame.KEYDOWN:
                if game.state == 'menu':
                    if event.key == pygame.K_1:
                        game.set_mode('single')
                    elif event.key == pygame.K_2:
                        game.set_mode('multi')
                    elif event.key == pygame.K_3:
                        game.set_grid_size(20)
                    elif event.key == pygame.K_4:
                        game.set_grid_size(40)
                elif game.state == 'game_over' and event.key == pygame.K_r:
                    game.restart_game()

        game.update()
        game.draw()
        pygame.display.flip()
        clock.tick(FPS)
        await asyncio.sleep(1.0 / FPS)

if platform.system() == "Emscripten":
    asyncio.ensure_future(main())
else:
    if __name__ == "__main__":
        asyncio.run(main())