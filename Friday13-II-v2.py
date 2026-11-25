import pygame
import random
import math
import json

from pathlib import Path
from collections import deque
from functools import lru_cache

pygame.init()

WIDTH, HEIGHT = 800, 600
FPS = 60

TILE = 40
CHUNK_SIZE = 8
WORLD_SEED = 19800613

MOVE_INTERVAL = 0.35
FOOD_INTERVAL = 5.0
MAX_FOOD = 10
FOOD_RADIUS = 12

CAMERA_SPEED = 7.0

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
DARK_RED = (139, 0, 0)
RED = (180, 0, 0)
GRAY = (150, 150, 150)

GRASS = (28, 58, 34)
GRASS2 = (34, 68, 40)
TREE_TRUNK = (58, 38, 24)
TREE_TOP = (18, 48, 22)
ROCK = (88, 82, 74)
WATER = (28, 58, 92)
FENCE = (110, 88, 62)

FONT = pygame.font.SysFont("bahnschrift", 25)
SMALL_FONT = pygame.font.SysFont("bahnschrift", 18)
TITLE_FONT = pygame.font.SysFont("bahnschrift", 48)
SCORE_FONT = pygame.font.SysFont("bahnschrift", 30)

SAVE_FILE = (
    Path.home()
    / ".nestims"
    / "friday13-ii"
    / "records.json"
)

def load_record():
    try:
        data = json.loads(
            SAVE_FILE.read_text(encoding="utf-8")
        )
        return max(0, int(data.get("best", 0)))

    except (OSError, ValueError, TypeError, AttributeError):
        return 0


def save_record(score):
    try:
        SAVE_FILE.parent.mkdir(
            parents=True, exist_ok=True
        )

        temp = SAVE_FILE.with_suffix(".tmp")

        temp.write_text(
            json.dumps({"best": score}, indent=4),
            encoding="utf-8"
        )

        temp.replace(SAVE_FILE)
        return True

    except OSError:
        return False

class DecoKind:
    EMPTY = 0
    TREE = 1
    ROCK = 2
    LAKE = 3
    FENCE = 5


@lru_cache(maxsize=512)
def generate_chunk(cx, cy):

    seed = (
        (cx * 73856093)
        ^ (cy * 19349663)
        ^ WORLD_SEED
    )

    rng = random.Random(seed & 0xFFFFFFFF)

    tiles = [
        [DecoKind.EMPTY for _ in range(CHUNK_SIZE)]
        for _ in range(CHUNK_SIZE)
    ]

    for ly in range(CHUNK_SIZE):
        for lx in range(CHUNK_SIZE):

            wx = cx * CHUNK_SIZE + lx
            wy = cy * CHUNK_SIZE + ly

            noise = (
                math.sin(wx * 0.11)
                + math.cos(wy * 0.09)
            ) * 0.5

            if noise > 0.7 and rng.random() < 0.2:
                tiles[ly][lx] = DecoKind.LAKE

    deco_pool = [
        (DecoKind.TREE, 0.08),
        (DecoKind.ROCK, 0.04),
        (DecoKind.FENCE, 0.02)
    ]

    for ly in range(CHUNK_SIZE):
        for lx in range(CHUNK_SIZE):

            if tiles[ly][lx] != DecoKind.EMPTY:
                continue

            roll = rng.random()

            for kind, chance in deco_pool:

                if roll < chance:
                    tiles[ly][lx] = kind
                    break

                roll -= chance

    return tuple(tuple(row) for row in tiles)


class World:

    def deco_at(self, gx, gy):

        cx, lx = divmod(gx, CHUNK_SIZE)
        cy, ly = divmod(gy, CHUNK_SIZE)

        return generate_chunk(cx, cy)[ly][lx]

    def is_blocked(self, gx, gy):
        return self.deco_at(gx, gy) != DecoKind.EMPTY

    def find_start(self):

        for radius in range(1, 65):

            for x in range(-radius, radius + 1):
                for y in range(-radius, radius + 1):

                    if max(abs(x), abs(y)) != radius:
                        continue

                    empty = all(
                        not self.is_blocked(x + dx, y + dy)
                        for dx in range(-2, 3)
                        for dy in range(-2, 3)
                    )

                    if empty:
                        return x, y

        raise RuntimeError("Unable to find starting area")

    def reachable_cells(self, start, radius, occupied):

        queue = deque([start])
        visited = {start}
        result = []

        sx, sy = start

        while queue:

            x, y = queue.popleft()

            for dx, dy in (
                (1, 0), (-1, 0),
                (0, 1), (0, -1)
            ):

                nx, ny = x + dx, y + dy
                pos = (nx, ny)

                if pos in visited:
                    continue

                if max(
                    abs(nx - sx),
                    abs(ny - sy)
                ) > radius:
                    continue

                if pos in occupied:
                    continue

                if self.is_blocked(nx, ny):
                    continue

                visited.add(pos)
                queue.append(pos)
                result.append(pos)

        return result

@lru_cache(maxsize=16)
def ground_surface(kind, parity):

    surface = pygame.Surface((TILE, TILE))

    if kind == DecoKind.LAKE:
        surface.fill(WATER)
    else:
        surface.fill(GRASS if parity == 0 else GRASS2)

    if kind == DecoKind.TREE:

        pygame.draw.rect(
            surface, TREE_TRUNK,
            (13, 18, 6, 14)
        )

        pygame.draw.circle(
            surface, TREE_TOP,
            (16, 12), 13
        )

    elif kind == DecoKind.ROCK:

        pygame.draw.ellipse(
            surface, ROCK,
            (6, 14, 22, 14)
        )

    elif kind == DecoKind.FENCE:

        for x in (6, 14, 22):

            pygame.draw.rect(
                surface, FENCE,
                (x, 10, 3, 18)
            )

        pygame.draw.rect(
            surface, FENCE,
            (5, 14, 22, 2)
        )

    return surface.convert()


@lru_cache(maxsize=1)
def food_surface():

    surface = pygame.Surface(
        (TILE, TILE), pygame.SRCALPHA
    )

    cx = cy = TILE // 2
    radius = TILE // 3

    pygame.draw.circle(
        surface, RED, (cx, cy), radius
    )

    pygame.draw.circle(
        surface, DARK_RED,
        (cx, cy), radius // 2
    )

    for offset in (-1, 1):

        pygame.draw.circle(
            surface, BLACK,
            (
                cx + offset * radius // 2,
                cy - radius // 2
            ),
            max(2, TILE // 10)
        )

    return surface.convert_alpha()


@lru_cache(maxsize=1)
def body_surface():

    surface = pygame.Surface(
        (TILE, TILE), pygame.SRCALPHA
    )

    surface.fill(WHITE)

    mid = TILE // 2
    thickness = max(4, TILE // 6)

    pygame.draw.line(
        surface, BLACK,
        (mid, 0), (mid, TILE),
        thickness
    )

    pygame.draw.line(
        surface, BLACK,
        (0, mid), (TILE, mid),
        thickness
    )

    for dx in (-1, 1):
        for dy in (-1, 1):

            pygame.draw.circle(
                surface, RED,
                (
                    mid + dx * TILE // 3,
                    mid + dy * TILE // 3
                ),
                max(1, TILE // 10)
            )

    return surface.convert_alpha()


@lru_cache(maxsize=4)
def head_surface(direction):

    surface = pygame.Surface(
        (TILE, TILE), pygame.SRCALPHA
    )

    surface.fill(WHITE)

    eye_size = max(3, TILE // 6)

    pygame.draw.circle(
        surface, BLACK,
        (TILE // 3, TILE // 4),
        eye_size
    )

    pygame.draw.circle(
        surface, BLACK,
        (2 * TILE // 3, TILE // 4),
        eye_size
    )

    angles = {
        (1, 0): 270,
        (-1, 0): 90,
        (0, -1): 0,
        (0, 1): 180
    }

    return pygame.transform.rotate(
        surface, angles[direction]
    ).convert_alpha()

class Game:

    def __init__(self):

        self.screen = pygame.display.set_mode(
            (WIDTH, HEIGHT)
        )

        pygame.display.set_caption(
            "Friday 13 - II | NESTIMS"
        )

        self.clock = pygame.time.Clock()

        self.running = True
        self.state = "MENU"

        self.best = load_record()
        self.score = 0
        self.new_record = False
        self.save_error = False

        self.overlay = pygame.Surface(
            (WIDTH, HEIGHT), pygame.SRCALPHA
        )

        self.overlay.fill((0, 0, 0, 200))

        self.hud = pygame.Surface(
            (WIDTH, 65), pygame.SRCALPHA
        )

        self.hud.fill((0, 0, 0, 190))

    def text(self, message, font, color, x, y):

        surface = font.render(message, True, color)
        rect = surface.get_rect(center=(x, y))
        self.screen.blit(surface, rect)



    def start_game(self):

        self.world = World()

        start = self.world.find_start()

        self.segments = deque([start])
        self.occupied = {start}

        self.direction = (1, 0)
        self.next_direction = (1, 0)

        self.score = 0
        self.new_record = False
        self.save_error = False

        self.move_timer = 0.0
        self.food_timer = 0.0
        self.elapsed = 0.0

        self.foods = set()

        self.cam_x = (
            start[0] * TILE
            + TILE / 2
            - WIDTH / 2
        )

        self.cam_y = (
            start[1] * TILE
            + TILE / 2
            - HEIGHT / 2
        )

        self.started = False
        self.state = "PLAYING"

        for _ in range(3):
            self.spawn_food()



    def spawn_food(self):

        if len(self.foods) >= MAX_FOOD:
            return

        head = self.segments[0]
        hx, hy = head

        reachable = self.world.reachable_cells(
            head,
            FOOD_RADIUS,
            self.occupied
        )

        candidates = [
            pos for pos in reachable
            if pos not in self.foods
            and abs(pos[0] - hx) <= 8
            and abs(pos[1] - hy) <= 5
            and abs(pos[0] - hx) + abs(pos[1] - hy) >= 2
        ]

        if not candidates:

            candidates = [
                pos for pos in reachable
                if pos not in self.foods
            ]

        if candidates:
            self.foods.add(random.choice(candidates))

    def update_food(self):

        hx, hy = self.segments[0]

        self.foods = {
            (x, y)
            for x, y in self.foods
            if max(abs(x - hx), abs(y - hy)) <= 24
        }

        if not self.foods:
            self.spawn_food()



    def update_record(self):

        if self.score > self.best:

            self.best = self.score
            self.new_record = True

        self.save_error = not save_record(self.best)

    def finish_game(self):

        self.update_record()
        self.state = "GAME_OVER"



    def move(self):

        self.direction = self.next_direction

        hx, hy = self.segments[0]
        dx, dy = self.direction

        new_head = (hx + dx, hy + dy)

        if self.world.is_blocked(*new_head):

            self.finish_game()
            return

        growing = new_head in self.foods
        tail = self.segments[-1]

        if new_head in self.occupied:

            if growing or new_head != tail:

                self.finish_game()
                return

        if not growing:

            removed = self.segments.pop()
            self.occupied.remove(removed)

        self.segments.appendleft(new_head)
        self.occupied.add(new_head)

        if growing:

            self.foods.remove(new_head)
            self.score += 1

        self.update_food()



    def update_camera(self, dt):

        hx, hy = self.segments[0]

        target_x = (
            hx * TILE
            + TILE / 2
            - WIDTH / 2
        )

        target_y = (
            hy * TILE
            + TILE / 2
            - HEIGHT / 2
        )

        factor = 1.0 - math.exp(
            -CAMERA_SPEED * dt
        )

        self.cam_x += (
            target_x - self.cam_x
        ) * factor

        self.cam_y += (
            target_y - self.cam_y
        ) * factor



    def handle_events(self):

        directions = {
            pygame.K_LEFT: (-1, 0),
            pygame.K_RIGHT: (1, 0),
            pygame.K_UP: (0, -1),
            pygame.K_DOWN: (0, 1),
            pygame.K_a: (-1, 0),
            pygame.K_d: (1, 0),
            pygame.K_w: (0, -1),
            pygame.K_s: (0, 1)
        }

        for event in pygame.event.get():

            if event.type == pygame.QUIT:

                if self.state in ("PLAYING", "PAUSED"):
                    self.update_record()

                self.running = False
                return

            if event.type != pygame.KEYDOWN:
                continue

            key = event.key

            if self.state == "MENU":

                if key in (
                    pygame.K_RETURN,
                    pygame.K_1
                ):
                    self.start_game()

                elif key == pygame.K_ESCAPE:
                    self.running = False

            elif self.state == "PLAYING":

                if key in directions:

                    dx, dy = directions[key]
                    ox, oy = self.direction

                    if not self.started:

                        self.direction = (dx, dy)
                        self.next_direction = (dx, dy)
                        self.started = True

                    elif (dx, dy) != (-ox, -oy):

                        self.next_direction = (dx, dy)

                elif key in (
                    pygame.K_p, pygame.K_SPACE
                ):

                    self.state = "PAUSED"

                elif key == pygame.K_ESCAPE:

                    self.update_record()
                    self.state = "MENU"

            elif self.state == "PAUSED":

                if key in (
                    pygame.K_p, pygame.K_SPACE
                ):

                    self.state = "PLAYING"

                elif key == pygame.K_ESCAPE:

                    self.update_record()
                    self.state = "MENU"

            elif self.state == "GAME_OVER":

                if key == pygame.K_r:
                    self.start_game()

                elif key == pygame.K_m:
                    self.state = "MENU"

                elif key == pygame.K_ESCAPE:
                    self.running = False



    def update(self, dt):

        if self.state != "PLAYING":
            return

        if not self.started:
            return

        self.elapsed += dt

        self.food_timer += dt

        if self.food_timer >= FOOD_INTERVAL:

            self.food_timer -= FOOD_INTERVAL
            self.spawn_food()

        self.move_timer += dt

        while self.move_timer >= MOVE_INTERVAL:

            self.move_timer -= MOVE_INTERVAL
            self.move()

            if self.state != "PLAYING":
                return

        self.update_camera(dt)



    def draw_menu(self):

        self.screen.fill(BLACK)

        self.text(
            "NESTIMS",
            SMALL_FONT, GRAY, 400, 45
        )

        self.text(
            "FRIDAY 13 - II",
            TITLE_FONT, DARK_RED, 400, 120
        )

        self.text(
            "INFINITE",
            SCORE_FONT, RED, 400, 180
        )

        self.text(
            "An endless procedural world",
            FONT, GRAY, 400, 235
        )

        self.text(
            "ENTER - Play",
            SCORE_FONT, WHITE, 400, 325
        )

        self.text(
            f"Personal best: {self.best}",
            FONT, RED, 400, 385
        )

        self.text(
            "WASD / Arrow keys - Movement",
            SMALL_FONT, GRAY, 400, 465
        )

        self.text(
            "ESC - Exit",
            FONT, GRAY, 400, 520
        )

        self.text(
            "Version 1.1 | NS-004",
            SMALL_FONT, GRAY, 400, 575
        )



    def draw_world(self):

        self.screen.fill(BLACK)

        start_x = math.floor(self.cam_x / TILE)
        start_y = math.floor(self.cam_y / TILE)

        end_x = math.floor(
            (self.cam_x + WIDTH) / TILE
        ) + 1

        end_y = math.floor(
            (self.cam_y + HEIGHT) / TILE
        ) + 1

        for gy in range(start_y, end_y):
            for gx in range(start_x, end_x):

                kind = self.world.deco_at(gx, gy)

                surface = ground_surface(
                    kind, (gx + gy) % 2
                )

                px = math.floor(
                    gx * TILE - self.cam_x
                )

                py = math.floor(
                    gy * TILE - self.cam_y
                )

                self.screen.blit(surface, (px, py))

        for gx, gy in self.foods:

            px = math.floor(
                gx * TILE - self.cam_x
            )

            py = math.floor(
                gy * TILE - self.cam_y
            )

            if (
                -TILE < px < WIDTH
                and -TILE < py < HEIGHT
            ):

                self.screen.blit(
                    food_surface(), (px, py)
                )

        for index, (gx, gy) in enumerate(
            reversed(self.segments)
        ):

            px = math.floor(
                gx * TILE - self.cam_x
            )

            py = math.floor(
                gy * TILE - self.cam_y
            )

            if not (
                -TILE < px < WIDTH
                and -TILE < py < HEIGHT
            ):
                continue

            is_head = (
                index == len(self.segments) - 1
            )

            surface = (
                head_surface(self.direction)
                if is_head
                else body_surface()
            )

            self.screen.blit(surface, (px, py))



    def formatted_time(self):

        seconds = int(self.elapsed)
        minutes, seconds = divmod(seconds, 60)

        return f"{minutes:02d}:{seconds:02d}"

    def draw_hud(self):

        self.screen.blit(self.hud, (0, 0))

        score = SCORE_FONT.render(
            f"Score: {self.score}", True, WHITE
        )

        best = SMALL_FONT.render(
            f"Best: {max(self.best, self.score)}",
            True, RED
        )

        timer = FONT.render(
            self.formatted_time(), True, WHITE
        )

        self.screen.blit(score, (15, 5))
        self.screen.blit(best, (15, 38))

        self.screen.blit(
            timer,
            (WIDTH - timer.get_width() - 15, 8)
        )

        hx, hy = self.segments[0]

        coords = SMALL_FONT.render(
            f"X: {hx}  Y: {hy}", True, GRAY
        )

        self.screen.blit(
            coords,
            (WIDTH - coords.get_width() - 15, 38)
        )

    def draw_game(self):

        self.draw_world()
        self.draw_hud()

        if not self.started:

            self.text(
                "Press WASD or arrow keys to start",
                FONT, WHITE, 400, 530
            )

    def draw_pause(self):

        self.draw_game()

        self.screen.blit(self.overlay, (0, 0))

        self.text(
            "PAUSED",
            TITLE_FONT, RED, 400, 230
        )

        self.text(
            "P / SPACE - Continue",
            FONT, WHITE, 400, 320
        )

        self.text(
            "ESC - Main Menu",
            FONT, GRAY, 400, 365
        )

    def draw_game_over(self):

        self.screen.fill(BLACK)

        self.text(
            "NESTIMS | FRIDAY 13 - II",
            SMALL_FONT, GRAY, 400, 50
        )

        self.text(
            "GAME OVER",
            TITLE_FONT, RED, 400, 130
        )

        self.text(
            "FINAL SCORE",
            SMALL_FONT, GRAY, 400, 195
        )

        self.text(
            str(self.score),
            TITLE_FONT, WHITE, 400, 245
        )

        self.text(
            f"Personal best: {self.best}",
            FONT, WHITE, 400, 305
        )

        self.text(
            f"Survival time: {self.formatted_time()}",
            FONT, GRAY, 400, 345
        )

        if self.new_record:

            self.text(
                "NEW RECORD!",
                FONT, RED, 400, 390
            )

        self.text(
            "R - Replay",
            FONT, WHITE, 400, 445
        )

        self.text(
            "M - Main Menu",
            FONT, WHITE, 400, 485
        )

        self.text(
            "ESC - Exit",
            FONT, GRAY, 400, 525
        )

        if self.save_error:

            self.text(
                "Unable to save record",
                SMALL_FONT, RED, 400, 575
            )

    def render(self):

        if self.state == "MENU":
            self.draw_menu()

        elif self.state == "PLAYING":
            self.draw_game()

        elif self.state == "PAUSED":
            self.draw_pause()

        elif self.state == "GAME_OVER":
            self.draw_game_over()

        pygame.display.flip()

    def run(self):

        while self.running:

            dt = min(
                self.clock.tick(FPS) / 1000.0,
                0.25
            )

            self.handle_events()

            if not self.running:
                break

            self.update(dt)
            self.render()

        pygame.quit()


def main():

    game = Game()
    game.run()


if __name__ == "__main__":
    main()
