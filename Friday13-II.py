import pygame
import random
import math
from collections import deque

pygame.init()

tile = 40
ch = 8
world_seed = 19800613

scr_w, scr_h = 800, 600
view_tiles_w = scr_w // tile + 2
view_tiles_h = scr_h // tile + 2

camera_margin = 3

black = (0, 0, 0)
white = (255, 255, 255)
dark_red = (139, 0, 0)
blood_red = (180, 0, 0)
grid_gray = (30, 30, 30)
grass = (28, 58, 34)
grass2 = (34, 68, 40)
tree_trunk = (58, 38, 24)
tree_top = (18, 48, 22)
rock = (88, 82, 74)
water = (28, 58, 92)
dirt = (72, 52, 36)
fence = (110, 88, 62)

move_ms = 350
food_spawn_interval = 5.0

class DecoKind:
    EMPTY = 0
    TREE = 1
    ROCK = 2
    LAKE = 3
    DIRT = 4
    FENCE = 5

font_style = pygame.font.SysFont("bahnschrift", 25)
menu_font = pygame.font.SysFont("bahnschrift", 35)
score_font = pygame.font.SysFont("comicsansm", 35)

def chunk_key(cx, cy):
    return (cx, cy)

def chunk_rng(cx, cy):
    h = (cx * 73856093) ^ (cy * 19349663) ^ world_seed
    return random.Random(h & 0xFFFFFFFF)

def generate_chunk(cx, cy):
    rng = chunk_rng(cx, cy)
    tiles = [[DecoKind.EMPTY for _ in range(ch)] for _ in range(ch)]

    for ly in range(ch):
        for lx in range(ch):
            wx, wy = cx * ch + lx, cy * ch + ly
            n = (math.sin(wx * 0.11) + math.cos(wy * 0.09)) * 0.5
            if n > 0.7 and rng.random() < 0.2:
                tiles[ly][lx] = DecoKind.LAKE

    deco_pool = [
        (DecoKind.TREE, 0.08),
        (DecoKind.ROCK, 0.04),
        (DecoKind.FENCE, 0.02),
    ]

    for ly in range(ch):
        for lx in range(ch):
            if tiles[ly][lx] != DecoKind.EMPTY:
                continue
            roll = rng.random()
            for kind, chance in deco_pool:
                if roll < chance:
                    tiles[ly][lx] = kind
                    break
                roll -= chance

    return tiles

class World:
    def __init__(self):
        self.chunks = {}

    @staticmethod
    def get_chunk_coord(coord):
        if coord >= 0:
            return coord // ch
        else:
            return -((-coord) // ch) - 1

    def get_chunk(self, cx, cy):
        key = chunk_key(cx, cy)
        if key not in self.chunks:
            self.chunks[key] = generate_chunk(cx, cy)
        return self.chunks[key]

    def deco_at(self, gx, gy):
        cx = gx // ch
        lx = gx % ch
        if lx < 0:
            lx += ch
            cx -= 1
        cy = gy // ch
        ly = gy % ch
        if ly < 0:
            ly += ch
            cy -= 1
        return self.get_chunk(cx, cy)[ly][lx]

    def is_blocked(self, gx, gy):
        d = self.deco_at(gx, gy)
        return d in (DecoKind.TREE, DecoKind.ROCK, DecoKind.LAKE, DecoKind.FENCE)

    def find_empty_area(self, center_x, center_y, radius=5):
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                test_x = center_x + dx
                test_y = center_y + dy

                empty = True
                for check_dx in range(-2, 3):
                    for check_dy in range(-2, 3):
                        if self.is_blocked(test_x + check_dx, test_y + check_dy):
                            empty = False
                            break
                    if not empty:
                        break

                if empty:
                    return (test_x, test_y)
        return None

def draw_ground(surf, gx, gy, deco):
    px, py = 0, 0
    if deco == DecoKind.DIRT:
        pygame.draw.rect(surf, dirt, (px, py, tile, tile))
    elif deco == DecoKind.LAKE:
        pygame.draw.rect(surf, water, (px, py, tile, tile))
    else:
        base = grass if (gx + gy) % 2 == 0 else grass2
        pygame.draw.rect(surf, base, (px, py, tile, tile))

def draw_tree(surf):
    pygame.draw.rect(surf, tree_trunk, (13, 18, 6, 14))
    pygame.draw.circle(surf, tree_top, (16, 12), 13)

def draw_rock(surf):
    pygame.draw.ellipse(surf, rock, (6, 14, 22, 14))

def draw_fence(surf):
    for x in (6, 14, 22):
        pygame.draw.rect(surf, fence, (x, 10, 3, 18))
    pygame.draw.rect(surf, fence, (5, 14, 22, 2))

def draw_deco(surf, kind):
    if kind == DecoKind.TREE:
        draw_tree(surf)
    elif kind == DecoKind.ROCK:
        draw_rock(surf)
    elif kind == DecoKind.FENCE:
        draw_fence(surf)

def draw_tourist(surf):
    center_x = tile // 2
    center_y = tile // 2
    radius = tile // 3
    pygame.draw.circle(surf, blood_red, (center_x, center_y), radius)
    pygame.draw.circle(surf, dark_red, (center_x, center_y), radius // 2)
    eye_size = max(2, tile // 10)
    pygame.draw.circle(surf, black, (center_x - radius // 2, center_y - radius // 2), eye_size)
    pygame.draw.circle(surf, black, (center_x + radius // 2, center_y - radius // 2), eye_size)

def draw_snake_segment(surf, x, y, is_head, direction):
    if is_head:
        pygame.draw.rect(surf, white, [x, y, tile, tile])
        eye_size = max(3, tile // 6)
        if direction == (1, 0):
            pygame.draw.circle(surf, black, (x + tile - tile // 4, y + tile // 3), eye_size)
            pygame.draw.circle(surf, black, (x + tile - tile // 4, y + 2 * tile // 3), eye_size)
        elif direction == (-1, 0):
            pygame.draw.circle(surf, black, (x + tile // 4, y + tile // 3), eye_size)
            pygame.draw.circle(surf, black, (x + tile // 4, y + 2 * tile // 3), eye_size)
        elif direction == (0, -1):
            pygame.draw.circle(surf, black, (x + tile // 3, y + tile // 4), eye_size)
            pygame.draw.circle(surf, black, (x + 2 * tile // 3, y + tile // 4), eye_size)
        else:
            pygame.draw.circle(surf, black, (x + tile // 3, y + 3 * tile // 4), eye_size)
            pygame.draw.circle(surf, black, (x + 2 * tile // 3, y + 3 * tile // 4), eye_size)
    else:
        pygame.draw.rect(surf, white, [x, y, tile, tile])
        line_thickness = max(4, tile // 6)
        mid_x = x + tile // 2
        mid_y = y + tile // 2
        pygame.draw.line(surf, black, (mid_x, y), (mid_x, y + tile), line_thickness)
        pygame.draw.line(surf, black, (x, mid_y), (x + tile, mid_y), line_thickness)
        spot_size = max(1, tile // 10)
        pygame.draw.circle(surf, blood_red, (mid_x - tile // 3, mid_y - tile // 3), spot_size)
        pygame.draw.circle(surf, blood_red, (mid_x + tile // 3, mid_y - tile // 3), spot_size)
        pygame.draw.circle(surf, blood_red, (mid_x - tile // 3, mid_y + tile // 3), spot_size)
        pygame.draw.circle(surf, blood_red, (mid_x + tile // 3, mid_y + tile // 3), spot_size)

def draw_hud(screen, score):
    value = score_font.render("Victims: " + str(score), True, blood_red)
    screen.blit(value, [10, 0])

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((scr_w, scr_h))
        pygame.display.set_caption('Friday 13 - Infinite')
        self.clock = pygame.time.Clock()
        self.world = World()
        self.score = 0
        self.time = 0.0
        self.move_accum = 0.0
        self.direction = (1, 0)
        self.next_direction = (1, 0)
        self.running = True
        self.game_over = False

        self.food_spawn_timer = 0.0
        self.foods = []

        self.cam_x = 0
        self.cam_y = 0
        self.target_cam_x = 0
        self.target_cam_y = 0

        self.cam_offset_x = 0.0
        self.cam_offset_y = 0.0
        self.is_cam_moving = False
        self.cam_move_progress = 0.0
        self.cam_start_x = 0
        self.cam_start_y = 0
        self.cam_end_x = 0
        self.cam_end_y = 0

        start_pos = self.find_start_position()
        self.segments = deque([start_pos])

        hx, hy = self.head()
        self.cam_x = hx - view_tiles_w // 2
        self.cam_y = hy - view_tiles_h // 2
        self.target_cam_x = self.cam_x
        self.target_cam_y = self.cam_y
        self.cam_start_x = self.cam_x
        self.cam_start_y = self.cam_y
        self.cam_end_x = self.cam_x
        self.cam_end_y = self.cam_y

        self.spawn_food()

    def find_start_position(self):
        center_positions = [(0, 0), (5, 5), (-5, -5), (5, -5), (-5, 5)]

        for center in center_positions:
            pos = self.world.find_empty_area(center[0], center[1], 8)
            if pos:
                return pos

        for x in range(-20, 21):
            for y in range(-20, 21):
                if not self.world.is_blocked(x, y):
                    return (x, y)

        return (0, 0)

    def head(self):
        return self.segments[0]

    def spawn_food(self):
        for _ in range(200):
            hx, hy = self.head()
            gx = hx + random.randint(-20, 20)
            gy = hy + random.randint(-20, 20)

            if not self.world.is_blocked(gx, gy):
                if (gx, gy) not in self.segments:
                    food_taken = False
                    for food in self.foods:
                        if food == (gx, gy):
                            food_taken = True
                            break
                    if not food_taken:
                        self.foods.append((gx, gy))
                        return True

        for x in range(-30, 31):
            for y in range(-30, 31):
                if not self.world.is_blocked(x, y):
                    if (x, y) not in self.segments:
                        food_taken = False
                        for food in self.foods:
                            if food == (x, y):
                                food_taken = True
                                break
                        if not food_taken:
                            self.foods.append((x, y))
                            return True
        return False

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                if self.game_over and event.key == pygame.K_r:
                    self.__init__()
                    return
                if event.key == pygame.K_LEFT:
                    self.queue_dir((-1, 0))
                elif event.key == pygame.K_RIGHT:
                    self.queue_dir((1, 0))
                elif event.key == pygame.K_UP:
                    self.queue_dir((0, -1))
                elif event.key == pygame.K_DOWN:
                    self.queue_dir((0, 1))

    def queue_dir(self, d):
        ox, oy = self.direction
        nx, ny = d
        if (ox + nx, oy + ny) == (0, 0):
            return
        self.next_direction = d

    def try_move(self):
        self.direction = self.next_direction
        dx, dy = self.direction
        hx, hy = self.head()
        new_head = (hx + dx, hy + dy)

        if self.world.is_blocked(*new_head):
            self.game_over = True
            return

        if new_head in list(self.segments):
            self.game_over = True
            return

        self.segments.appendleft(new_head)
        self.segments.pop()

        for food in self.foods[:]:
            if new_head == food:
                self.foods.remove(food)
                self.score += 1
                tail = self.segments[-1]
                self.segments.append(tail)
                break

    def update_camera(self):
        hx, hy = self.head()

        cam_w = view_tiles_w
        cam_h = view_tiles_h

        ideal_cam_x = hx - cam_w // 2
        ideal_cam_y = hy - cam_h // 2

        rel_x = hx - self.cam_x
        rel_y = hy - self.cam_y

        need_move_x = False
        need_move_y = False

        if rel_x < camera_margin:
            need_move_x = True
            self.target_cam_x = ideal_cam_x
        elif rel_x > cam_w - camera_margin:
            need_move_x = True
            self.target_cam_x = ideal_cam_x

        if rel_y < camera_margin:
            need_move_y = True
            self.target_cam_y = ideal_cam_y
        elif rel_y > cam_h - camera_margin:
            need_move_y = True
            self.target_cam_y = ideal_cam_y

        if (need_move_x or need_move_y) and not self.is_cam_moving:
            self.cam_start_x = self.cam_x
            self.cam_start_y = self.cam_y
            self.cam_end_x = self.target_cam_x
            self.cam_end_y = self.target_cam_y
            self.is_cam_moving = True
            self.cam_move_progress = 0.0

        if self.is_cam_moving:
            self.cam_move_progress += 1.0 / (move_ms / 16.67)

            if self.cam_move_progress >= 1.0:
                self.cam_move_progress = 1.0
                self.is_cam_moving = False
                self.cam_x = self.cam_end_x
                self.cam_y = self.cam_end_y
                self.cam_offset_x = 0.0
                self.cam_offset_y = 0.0
            else:
                t = self.cam_move_progress
                t = t * t * (3 - 2 * t)

                curr_x = self.cam_start_x + (self.cam_end_x - self.cam_start_x) * t
                curr_y = self.cam_start_y + (self.cam_end_y - self.cam_start_y) * t

                self.cam_offset_x = curr_x - int(curr_x)
                self.cam_offset_y = curr_y - int(curr_y)
                self.cam_x = int(curr_x)
                self.cam_y = int(curr_y)

    def update(self, dt):
        if self.game_over:
            return

        self.time += dt

        self.food_spawn_timer += dt
        if self.food_spawn_timer >= food_spawn_interval:
            self.food_spawn_timer = 0.0
            if len(self.foods) < 10:
                self.spawn_food()

        self.move_accum += dt * 1000
        while self.move_accum >= move_ms:
            self.move_accum -= move_ms
            self.try_move()

            self.update_camera()

            if not self.is_cam_moving:
                self.update_camera()

    def render(self):
        self.screen.fill(black)

        cam_gx = self.cam_x + self.cam_offset_x
        cam_gy = self.cam_y + self.cam_offset_y

        for sy in range(view_tiles_h):
            for sx in range(view_tiles_w):
                gx = self.cam_x + sx
                gy = self.cam_y + sy

                px = int((sx - self.cam_offset_x) * tile)
                py = int((sy - self.cam_offset_y) * tile)

                deco = self.world.deco_at(gx, gy)

                tile_surf = pygame.Surface((tile, tile))
                draw_ground(tile_surf, gx, gy, deco)
                if deco not in (DecoKind.EMPTY, DecoKind.DIRT, DecoKind.LAKE):
                    draw_deco(tile_surf, deco)
                self.screen.blit(tile_surf, (px, py))

        hx, hy = self.head()
        for fx, fy in self.foods:
            if abs(fx - hx) < view_tiles_w // 2 and abs(fy - hy) < view_tiles_h // 2:
                px = int((fx - cam_gx) * tile)
                py = int((fy - cam_gy) * tile)
                food_surf = pygame.Surface((tile, tile), pygame.SRCALPHA)
                draw_tourist(food_surf)
                self.screen.blit(food_surf, (px, py))

        total = len(self.segments)
        for i in range(total - 1, -1, -1):
            gx, gy = self.segments[i]
            px = int((gx - cam_gx) * tile)
            py = int((gy - cam_gy) * tile)
            seg_surf = pygame.Surface((tile, tile), pygame.SRCALPHA)
            draw_snake_segment(seg_surf, 0, 0, i == 0, self.direction)
            self.screen.blit(seg_surf, (px, py))

        victims_text = font_style.render(f"Victims on map: {len(self.foods)}", True, (150, 150, 150))
        self.screen.blit(victims_text, [10, 40])

        draw_hud(self.screen, self.score)

        if self.game_over:
            overlay = pygame.Surface((scr_w, scr_h), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            self.screen.blit(overlay, (0, 0))
            mesg = font_style.render("GAME OVER! R - Restart", True, blood_red)
            text_x = scr_w // 2 - mesg.get_width() // 2
            text_y = scr_h // 2 - mesg.get_height() // 2
            self.screen.blit(mesg, [text_x, text_y])

        pygame.display.flip()

    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self.handle_input()
            self.update(dt)
            self.render()
        pygame.quit()

def main():
    game = Game()
    game.run()

if __name__ == "__main__":
    main()
