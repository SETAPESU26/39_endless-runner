import io
import math
import struct
import wave

import pygame

from .player import Player
from .obstacle import Obstacle


class GameEngine:
    # Starting speed, maximum speed, frames between obstacles.
    LEVELS = {
        pygame.K_1: ("Easy", 6, 10, 90),
        pygame.K_2: ("Medium", 8, 12, 75),
        pygame.K_3: ("Hard", 10, 14, 60),
    }

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.ground_y = height - 40
        self.font = pygame.font.SysFont("Arial", 30)
        self.small_font = pygame.font.SysFont("Arial", 22)
        self.sounds = {}
        self.setup_sounds()
        self.reset(pygame.K_1)
        self.state = "menu"

    def setup_sounds(self):
        # Generate WAV sounds in memory; no audio files are required.
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()

            for name, frequency, duration in (
                ("jump", 650, 0.12),
                ("score", 1000, 0.10),
                ("over", 180, 0.45),
            ):
                rate = 44100
                count = int(rate * duration)
                samples = bytearray()

                for i in range(count):
                    envelope = math.sin(math.pi * i / count)
                    value = int(
                        7000 * envelope
                        * math.sin(2 * math.pi * frequency * i / rate)
                    )
                    samples.extend(struct.pack("<h", value))

                audio = io.BytesIO()
                with wave.open(audio, "wb") as wav:
                    wav.setnchannels(1)
                    wav.setsampwidth(2)
                    wav.setframerate(rate)
                    wav.writeframes(samples)

                audio.seek(0)
                self.sounds[name] = pygame.mixer.Sound(file=audio)

        except pygame.error:
            # Keep the game playable when no audio device is available.
            self.sounds = {}

    def play_sound(self, name):
        sound = self.sounds.get(name)
        if sound is not None:
            sound.play()

    def reset(self, key):
        self.difficulty, self.speed, self.max_speed, self.spawn_interval = (
            self.LEVELS[key]
        )
        self.player = Player(80, self.ground_y)
        self.obstacles = []
        self._spawn_timer = 0
        self.score = 0
        self.distance = 0
        self.game_over = False
        self.state = "playing"

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if event.key in (pygame.K_ESCAPE, pygame.K_q):
            pygame.event.post(pygame.event.Event(pygame.QUIT))
            return

        if self.state != "playing":
            if event.key in self.LEVELS:
                self.reset(event.key)
            return

        if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
            if self.player.on_ground:
                self.player.jump()
                self.play_sound("jump")

    def handle_input(self):
        pass

    def update(self):
        if self.state != "playing":
            return

        # The cap keeps movement below the 25-pixel obstacle width.
        # Obstacles cannot jump across the player's entire hitbox.
        self.speed = min(self.speed + 0.003, self.max_speed)
        self.player.update()

        self._spawn_timer += 1
        if self._spawn_timer >= self.spawn_interval:
            self._spawn_timer = 0
            self.obstacles.append(
                Obstacle(self.width, self.ground_y, self.speed)
            )

        for obstacle in self.obstacles:
            obstacle.speed = self.speed
            obstacle.move()

        # Check collisions before awarding points or removing obstacles.
        for obstacle in self.obstacles:
            if obstacle.rect().colliderect(self.player.rect()):
                self.game_over = True
                self.state = "game_over"
                self.play_sound("over")
                return

        for obstacle in self.obstacles:
            if (
                not obstacle.scored
                and obstacle.x + obstacle.width < self.player.x
            ):
                obstacle.scored = True
                self.score += 1
                self.play_sound("score")

        self.obstacles = [
            obstacle for obstacle in self.obstacles
            if not obstacle.off_screen()
        ]
        self.distance += self.speed

    def centered_text(self, screen, text, y, small=False):
        font = self.small_font if small else self.font
        surface = font.render(text, True, (245, 245, 245))
        screen.blit(
            surface,
            surface.get_rect(center=(self.width // 2, y)),
        )

    def render(self, screen):
        pygame.draw.line(
            screen, (120, 80, 40),
            (0, self.ground_y), (self.width, self.ground_y), 4
        )
        pygame.draw.rect(screen, (45, 85, 190), self.player.rect())

        for obstacle in self.obstacles:
            pygame.draw.rect(screen, (30, 100, 30), obstacle.rect())

        label = self.small_font.render(
            f"Score: {self.score}   Difficulty: {self.difficulty}",
            True, (0, 0, 0)
        )
        screen.blit(label, (10, 10))

        if self.state == "playing":
            controls = self.small_font.render(
                "Jump: Space / Up / W     Exit: Q / Esc",
                True, (0, 0, 0)
            )
            screen.blit(controls, (10, 40))
            return

        overlay = pygame.Surface(
            (self.width, self.height), pygame.SRCALPHA
        )
        overlay.fill((0, 0, 0, 205))
        screen.blit(overlay, (0, 0))

        title = "GAME OVER" if self.game_over else "ENDLESS RUNNER"
        self.centered_text(screen, title, 95)

        if self.game_over:
            self.centered_text(
                screen, f"Final score: {self.score}", 145
            )

        self.centered_text(
            screen, "Choose difficulty to start or replay", 200, True
        )
        self.centered_text(
            screen, "1: Easy     2: Medium     3: Hard", 240, True
        )
        self.centered_text(
            screen, "Q / Esc: Exit", 285, True
        )
