import pygame
import random
import asyncio
import platform
from math import floor

# Initialize Pygame
pygame.init()

# Screen setup
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Trúc Xanh Music")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
HIGHLIGHT = (200, 200, 200)

# Game settings
FPS = 60
CARD_WIDTH, CARD_HEIGHT = 60, 60
CARD_MARGIN = 10
NOTES = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
NOTE_COLORS = {
    'C': (255, 0, 0), 'D': (255, 165, 0), 'E': (255, 255, 0),
    'F': (0, 128, 0), 'G': (0, 0, 255), 'A': (75, 0, 130), 'B': (238, 130, 238)
}

# Font
font = pygame.font.SysFont('arial', 36)

# Sound generation
def create_note_sound(frequency, duration=0.5, sample_rate=44100):
    import numpy as np
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    wave = 0.5 * np.sin(2 * np.pi * frequency * t)
    sound = (wave * 32767).astype(np.int16)
    return pygame.sndarray.make_sound(np.column_stack((sound, sound)))

NOTE_SOUNDS = {
    'C': create_note_sound(261.63),  # C4
    'D': create_note_sound(293.66),  # D4
    'E': create_note_sound(329.63),  # E4
    'F': create_note_sound(349.23),  # F4
    'G': create_note_sound(392.00),  # G4
    'A': create_note_sound(440.00),  # A4
    'B': create_note_sound(493.88)   # B4
}

class Card:
    def __init__(self, note, x, y):
        self.note = note
        self.rect = pygame.Rect(x, y, CARD_WIDTH, CARD_HEIGHT)
        self.is_flipped = False
        self.is_matched = False

class Button:
    def __init__(self, text, x, y, width, height):
        self.text = text
        self.rect = pygame.Rect(x, y, width, height)
        self.hovered = False

    def draw(self, surface):
        color = HIGHLIGHT if self.hovered else WHITE
        pygame.draw.rect(surface, color, self.rect)
        pygame.draw.rect(surface, BLACK, self.rect, 2)
        text_surface = font.render(self.text, True, BLACK)
        surface.blit(text_surface, (self.rect.x + (self.rect.width - text_surface.get_width()) // 2,
                                  self.rect.y + (self.rect.height - text_surface.get_height()) // 2))

    def check_hover(self, pos):
        self.hovered = self.rect.collidepoint(pos)

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
        self.wait_duration = 1000  # 1 second wait
        self.message = ""
        self.message_timer = 0
        self.buttons = [
            Button("1 Player", WIDTH // 2 - 100, 200, 200, 50),
            Button("2 Players", WIDTH // 2 - 100, 260, 200, 50),
            Button("25 Pairs", WIDTH // 2 - 100, 320, 200, 50),
            Button("15 Pairs", WIDTH // 2 - 100, 380, 200, 50)
        ]

    def setup_game(self, mode, grid_size):
        self.mode = mode
        self.grid_size = grid_size
        self.cards = []
        self.flipped_cards = []
        self.scores = {1: 0, 2: 0}
        self.current_player = 1
        self.state = 'playing'

        # Create card pairs
        pairs = grid_size // 2
        selected_notes = random.sample(NOTES, min(pairs, len(NOTES)))
        card_notes = selected_notes * 2
        random.shuffle(card_notes)

        # Calculate grid dimensions
        rows = 5
        cols = grid_size // 5
        start_x = (WIDTH - (cols * (CARD_WIDTH + CARD_MARGIN) - CARD_MARGIN)) // 2
        start_y = (HEIGHT - (rows * (CARD_HEIGHT + CARD_MARGIN) - CARD_MARGIN)) // 2

        # Create cards
        for i in range(rows):
            for j in range(cols):
                idx = i * cols + j
                if idx < len(card_notes):
                    x = start_x + j * (CARD_WIDTH + CARD_MARGIN)
                    y = start_y + i * (CARD_HEIGHT + CARD_MARGIN)
                    self.cards.append(Card(card_notes[idx], x, y))

    def draw(self):
        screen.fill(WHITE)
        if self.state == 'menu':
            title = font.render("Trúc Xanh Music", True, BLACK)
            screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 100))
            instruction = font.render("Select mode and grid size", True, BLACK)
            screen.blit(instruction, (WIDTH // 2 - instruction.get_width() // 2, 150))
            for button in self.buttons:
                button.draw(screen)
            if self.mode:
                mode_text = font.render(f"Mode: {'1 Player' if self.mode == 'single' else '2 Players'}", True, BLACK)
                screen.blit(mode_text, (WIDTH // 2 - mode_text.get_width() // 2, 450))
            if self.grid_size:
                grid_text = font.render(f"Grid: {self.grid_size // 2} Pairs", True, BLACK)
                screen.blit(grid_text, (WIDTH // 2 - grid_text.get_width() // 2, 500))
        elif self.state == 'playing':
            for card in self.cards:
                if card.is_matched or card.is_flipped:
                    pygame.draw.rect(screen, NOTE_COLORS[card.note], card.rect)
                    text = font.render(card.note, True, BLACK)
                    screen.blit(text, (card.rect.x + 20, card.rect.y + 20))
                else:
                    pygame.draw.rect(screen, GRAY, card.rect)
            score_text = font.render(f"Player 1: {self.scores[1]}", True, BLUE)
            screen.blit(score_text, (10, 10))
            if self.mode == 'multi':
                score_text2 = font.render(f"Player 2: {self.scores[2]}", True, GREEN)
                screen.blit(score_text2, (WIDTH - score_text2.get_width() - 10, 10))
                player_text = font.render(f"Turn: Player {self.current_player}", True, BLACK)
                screen.blit(player_text, (WIDTH // 2 - player_text.get_width() // 2, 10))
            if self.message:
                msg_surface = font.render(self.message, True, BLACK)
                screen.blit(msg_surface, (WIDTH // 2 - msg_surface.get_width() // 2, HEIGHT - 50))
        elif self.state == 'game_over':
            winner = 1 if self.scores[1] > self.scores[2] else 2 if self.scores[2] > self.scores[1] else 0
            if self.mode == 'single':
                text = font.render(f"Game Over! Score: {self.scores[1]}", True, BLACK)
            else:
                text = font.render(f"Game Over! Player {winner} Wins!" if winner else "Game Over! Tie!", True, BLACK)
            screen.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT // 2))
            restart = font.render("Press [R] to Restart", True, BLACK)
            screen.blit(restart, (WIDTH // 2 - restart.get_width() // 2, HEIGHT // 2 + 50))

    def handle_click(self, pos):
        if self.state == 'menu':
            for button in self.buttons:
                if button.rect.collidepoint(pos):
                    if button.text == "1 Player":
                        self.mode = 'single'
                    elif button.text == "2 Players":
                        self.mode = 'multi'
                    elif button.text == "25 Pairs":
                        self.grid_size = 50
                    elif button.text == "15 Pairs":
                        self.grid_size = 30
                    if self.mode and self.grid_size:
                        self.setup_game(self.mode, self.grid_size)
        elif self.state == 'playing' and not self.waiting:
            for card in self.cards:
                if card.rect.collidepoint(pos) and not card.is_flipped and not card.is_matched:
                    card.is_flipped = True
                    NOTE_SOUNDS[card.note].play()
                    self.flipped_cards.append(card)
                    if len(self.flipped_cards) == 2:
                        self.check_match()

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

game = Game()

async def main():
    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type == pygame.MOUSEMOTION:
                if game.state == 'menu':
                    for button in game.buttons:
                        button.check_hover(event.pos)
            if event.type == pygame.MOUSEBUTTONDOWN:
                game.handle_click(event.pos)
            if event.type == pygame.KEYDOWN:
                if game.state == 'menu':
                    if event.key == pygame.K_1:
                        game.mode = 'single'
                    elif event.key == pygame.K_2:
                        game.mode = 'multi'
                    elif event.key == pygame.K_3:
                        game.grid_size = 50
                    elif event.key == pygame.K_4:
                        game.grid_size = 30
                    if game.mode and game.grid_size:
                        game.setup_game(game.mode, game.grid_size)
                elif game.state == 'game_over' and event.key == pygame.K_r:
                    game.state = 'menu'
                    game.mode = None
                    game.grid_size = None

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