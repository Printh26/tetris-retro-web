import pygame
import random
import sys
from collections import deque
import os
import math

# ---------- Configuration ----------
ASSET_DIR = os.path.dirname(os.path.abspath(__file__))
BLOCKS_DIR = os.path.join(ASSET_DIR, "blocks")
BG_PATH = os.path.join(ASSET_DIR, "background.png")
CLEAR_SOUND_PATH = os.path.join(ASSET_DIR, "clear.wav")
GAMEOVER_SOUND_PATH = os.path.join(ASSET_DIR, "gameover.wav")
MUSIC_PATH = os.path.join(ASSET_DIR, "music.ogg")

CELL_SIZE = 30
COLUMNS = 10
ROWS = 20
SIDE_PANEL = 200
WIDTH = CELL_SIZE * COLUMNS + SIDE_PANEL
HEIGHT = CELL_SIZE * ROWS
FPS = 60
GAME_TITLE = "Tetris"
SIGNATURE = "Jeux Tetris 2D de Harry — Isabelle Edition"

# Scoring rules
SCORE_SINGLE = 100
SCORE_DOUBLE = 300
SCORE_TRIPLE = 500
SCORE_TETRIS = 800
SCORE_SOFT_DROP = 1
SCORE_HARD_DROP = 2

# Level speed
LEVEL_SPEEDS = [0.8, 0.72, 0.63, 0.55, 0.47, 0.38, 0.3, 0.22, 0.13, 0.1]

def get_drop_interval(level: int) -> float:
    if level - 1 < len(LEVEL_SPEEDS):
        return LEVEL_SPEEDS[level - 1]
    return max(0.03, LEVEL_SPEEDS[-1] * (0.9 ** (level - len(LEVEL_SPEEDS))))

# ---------- Tetrominos ----------
TETROMINOS = {
    'I': [[(0,1),(1,1),(2,1),(3,1)], [(2,0),(2,1),(2,2),(2,3)], [(0,2),(1,2),(2,2),(3,2)], [(1,0),(1,1),(1,2),(1,3)]],
    'J': [[(0,0),(0,1),(1,1),(2,1)], [(1,0),(2,0),(1,1),(1,2)], [(0,1),(1,1),(2,1),(2,2)], [(1,0),(1,1),(0,2),(1,2)]],
    'L': [[(2,0),(0,1),(1,1),(2,1)], [(1,0),(1,1),(1,2),(2,2)], [(0,1),(1,1),(2,1),(0,2)], [(0,0),(1,0),(1,1),(1,2)]],
    'O': [[(1,0),(2,0),(1,1),(2,1)]]*4,
    'S': [[(1,0),(2,0),(0,1),(1,1)], [(1,0),(1,1),(2,1),(2,2)], [(1,1),(2,1),(0,2),(1,2)], [(0,0),(0,1),(1,1),(1,2)]],
    'T': [[(1,0),(0,1),(1,1),(2,1)], [(1,0),(1,1),(2,1),(1,2)], [(0,1),(1,1),(2,1),(1,2)], [(1,0),(0,1),(1,1),(1,2)]],
    'Z': [[(0,0),(1,0),(1,1),(2,1)], [(2,0),(1,1),(2,1),(1,2)], [(0,1),(1,1),(1,2),(2,2)], [(1,0),(0,1),(1,1),(0,2)]]
}

COLORS = {
    'I': (80, 200, 255), 'J': (50, 120, 255), 'L': (255, 140, 50),
    'O': (255, 215, 60), 'S': (80, 255, 120), 'T': (170, 80, 255),
    'Z': (255, 80, 120), 'GRID_BG': (16,16,20), 'GRID_LINE': (40,40,48),
    'GHOST': (200,200,200), 'TEXT': (235,235,245), 'PANEL_BG': (14,14,18),
    'NEON': (0,255,200)
}

# ---------- Utilities ----------
def clamp(value, low=0, high=255):
    return max(low, min(high, int(value)))

def adjust_color(color, amount):
    return tuple(clamp(c + amount) for c in color)

def mix_color(a, b, factor):
    return tuple(clamp(a[i] + (b[i] - a[i]) * factor) for i in range(3))

class Piece:
    def __init__(self, shape: str):
        self.shape = shape
        self.rot = 0
        self.x = COLUMNS // 2 - 2
        self.y = -1

    def cells(self, rot=None, x_off=0, y_off=0):
        if rot is None:
            rot = self.rot
        return [(self.x+x_off+x, self.y+y_off+y) for x,y in TETROMINOS[self.shape][rot]]

    def rotate(self, direction=1):
        self.rot = (self.rot + direction) % 4

def create_grid():
    return [[None for _ in range(COLUMNS)] for _ in range(ROWS)]

def inside(x,y):
    return 0<=x<COLUMNS and 0<=y<ROWS

def valid_position(grid, piece, rot=None, x_off=0, y_off=0):
    for x,y in piece.cells(rot, x_off, y_off):
        if y<0: continue
        if not inside(x,y) or grid[y][x] is not None:
            return False
    return True

def lock_piece(grid, piece):
    for x,y in piece.cells():
        if y>=0:
            grid[y][x] = piece.shape

def get_full_rows(grid):
    return [index for index, row in enumerate(grid) if all(cell is not None for cell in row)]

def clear_rows(grid, row_indices):
    cleared = len(row_indices)
    rows_to_clear = set(row_indices)
    new_grid = [row for index, row in enumerate(grid) if index not in rows_to_clear]
    for _ in range(cleared):
        new_grid.insert(0, [None] * COLUMNS)
    return new_grid, cleared

def draw_text(surface, text, size, x, y, align="topleft", bold=False):
    font = pygame.font.SysFont(None,size,bold=bold)
    surf = font.render(text,True,COLORS['TEXT'])
    rect = surf.get_rect()
    setattr(rect, align,(x,y))
    surface.blit(surf,rect)

def draw_panel(surface, rect, border_color, fill=(10, 13, 20), alpha=185, radius=20):
    panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(panel, (*fill, alpha), panel.get_rect(), border_radius=radius)
    pygame.draw.rect(panel, (*border_color, min(255, alpha + 40)), panel.get_rect(), 2, border_radius=radius)
    pygame.draw.line(panel, (255, 255, 255, 28), (16, 12), (rect.width - 16, 12), 2)
    surface.blit(panel, rect.topleft)

def draw_block(surface, color, rect, glow=False, ghost=False, flash=0.0):
    block = pygame.Rect(rect)
    if ghost:
        ghost_surface = pygame.Surface((block.width, block.height), pygame.SRCALPHA)
        pygame.draw.rect(ghost_surface, (*adjust_color(color, 70), 45), ghost_surface.get_rect(), border_radius=8)
        pygame.draw.rect(ghost_surface, (*adjust_color(color, 120), 135), ghost_surface.get_rect(), 2, border_radius=8)
        surface.blit(ghost_surface, block.topleft)
        return

    if glow:
        glow_rect = block.inflate(10, 10)
        glow_surface = pygame.Surface(glow_rect.size, pygame.SRCALPHA)
        glow_color = adjust_color(color, 90)
        pygame.draw.rect(glow_surface, (*glow_color, 45), glow_surface.get_rect(), border_radius=12)
        surface.blit(glow_surface, glow_rect.topleft)

    shadow_rect = block.move(0, 3)
    pygame.draw.rect(surface, (8, 10, 18), shadow_rect, border_radius=9)

    layers = 5
    base_color = mix_color(color, (255, 255, 255), min(0.55, flash * 0.65))
    for idx in range(layers):
        inset = idx * 2
        layer_rect = block.inflate(-inset * 2, -inset * 2)
        if layer_rect.width <= 0 or layer_rect.height <= 0:
            continue
        shade = 42 - idx * 16
        layer_color = adjust_color(base_color, shade)
        pygame.draw.rect(surface, layer_color, layer_rect, border_radius=max(3, 9 - idx))

    highlight = pygame.Rect(block.x + 3, block.y + 3, max(6, block.width - 10), max(4, block.height // 3))
    highlight_surface = pygame.Surface(highlight.size, pygame.SRCALPHA)
    pygame.draw.rect(highlight_surface, (255, 255, 255, int(95 + flash * 90)), highlight_surface.get_rect(), border_radius=8)
    surface.blit(highlight_surface, highlight.topleft)

    edge = mix_color(base_color, (255, 255, 255), 0.5)
    pygame.draw.rect(surface, edge, block, 2, border_radius=9)

def draw_mini_piece(surface, piece, origin_x, origin_y, size=14):
    min_x = min(x for x, _ in TETROMINOS[piece.shape][0])
    max_x = max(x for x, _ in TETROMINOS[piece.shape][0])
    min_y = min(y for _, y in TETROMINOS[piece.shape][0])
    max_y = max(y for _, y in TETROMINOS[piece.shape][0])
    width = (max_x - min_x + 1) * size
    height = (max_y - min_y + 1) * size
    offset_x = origin_x - width // 2
    offset_y = origin_y - height // 2
    for x, y in TETROMINOS[piece.shape][0]:
        rect = pygame.Rect(offset_x + (x - min_x) * size, offset_y + (y - min_y) * size, size, size)
        draw_block(surface, COLORS[piece.shape], rect, glow=True)

def initialize_audio():
    original_driver = os.environ.get("SDL_AUDIODRIVER")
    attempted = []
    driver_candidates = [None, "directsound", "winmm"]

    for driver in driver_candidates:
        try:
            if pygame.mixer.get_init():
                pygame.mixer.quit()
            if driver is None:
                os.environ.pop("SDL_AUDIODRIVER", None)
            else:
                os.environ["SDL_AUDIODRIVER"] = driver
            pygame.mixer.pre_init(44100, -16, 2, 512)
            pygame.mixer.init()
            return True, driver or "default", attempted
        except pygame.error as err:
            attempted.append(f"{driver or 'default'}: {err}")

    if pygame.mixer.get_init():
        pygame.mixer.quit()
    if original_driver is None:
        os.environ.pop("SDL_AUDIODRIVER", None)
    else:
        os.environ["SDL_AUDIODRIVER"] = original_driver
    return False, None, attempted

def load_audio_assets():
    audio = {
        "enabled": False,
        "driver": None,
        "clear": None,
        "gameover": None,
        "music_loaded": False,
    }
    try:
        audio_ready, driver_name, attempted = initialize_audio()
        if not audio_ready:
    
                raise pygame.error(" | ".join(attempted) if attempted else "initialisation audio impossible")

        if os.path.exists(CLEAR_SOUND_PATH):
            audio["clear"] = pygame.mixer.Sound(CLEAR_SOUND_PATH)
        if os.path.exists(GAMEOVER_SOUND_PATH):
            audio["gameover"] = pygame.mixer.Sound(GAMEOVER_SOUND_PATH)
        if os.path.exists(MUSIC_PATH):
            pygame.mixer.music.load(MUSIC_PATH)
            pygame.mixer.music.set_volume(0.5)
            audio["music_loaded"] = True

        audio["enabled"] = True
        audio["driver"] = driver_name
    except pygame.error as err:
        print(f"Audio desactive: {err}")
    return audio

def start_music(audio_state):
    if not audio_state["enabled"] or not audio_state["music_loaded"]:
        return False
    if pygame.mixer.music.get_busy():
        return True
    pygame.mixer.music.play(-1)
    return True

# ---------- Game Class ----------
class Tetris:
    def __init__(self,screen,bg_image,audio_state):
        self.screen = screen
        self.grid = create_grid()
        self.score = 0
        self.level = 1
        self.lines = 0
        self.bag = deque()
        self.next_queue = deque()
        self._refill_bag()
        while len(self.next_queue)<5:
            self.next_queue.append(self._draw_from_bag())
        self.current = self._draw_from_bag()
        self.hold_piece = None
        self.hold_lock = False
        self.drop_timer = 0
        self.drop_interval = get_drop_interval(self.level)
        self.game_over = False
        self.paused = False
        self.bg_image = bg_image
        self.clearing_rows = []
        self.clear_flash_timer = 0.0
        self.clear_flash_duration = 0.18
        self.audio_enabled = audio_state["enabled"]
        self.audio_driver = audio_state["driver"]
        self.sound_clear = audio_state["clear"]
        self.sound_gameover = audio_state["gameover"]

    def _refill_bag(self):
        shapes=list(TETROMINOS.keys())
        random.shuffle(shapes)
        for s in shapes:
            self.bag.append(s)

    def _draw_from_bag(self):
        if not self.bag: self._refill_bag()
        return Piece(self.bag.popleft())

    def spawn_next(self):
        if not self.next_queue:
            while len(self.next_queue)<5: self.next_queue.append(self._draw_from_bag())
        self.current=self.next_queue.popleft()
        while len(self.next_queue)<5: self.next_queue.append(self._draw_from_bag())
        self.hold_lock=False
        if not valid_position(self.grid,self.current):
            self.game_over=True
            if self.sound_gameover:
                self.sound_gameover.play()

    def hold(self):
        if self.hold_lock: return
        if self.hold_piece is None:
            self.hold_piece = Piece(self.current.shape)
            self.spawn_next()
        else:
            temp=self.current.shape
            self.current=Piece(self.hold_piece.shape)
            self.hold_piece=Piece(temp)
        self.hold_lock=True

    def rotate_current(self,direction=1):
        if self.clear_flash_timer > 0:
            return False
        old=self.current.rot
        new=(self.current.rot+direction)%4
        for dx,dy in [(0,0),(-1,0),(1,0),(-2,0),(2,0),(0,-1)]:
            if valid_position(self.grid,self.current,new,dx,dy):
                self.current.rot=new
                self.current.x+=dx
                self.current.y+=dy
                return True
        self.current.rot=old
        return False

    def soft_drop(self):
        if self.clear_flash_timer > 0:
            return False
        if valid_position(self.grid,self.current,None,0,1):
            self.current.y+=1
            self.score+=SCORE_SOFT_DROP
            return True
        else:
            self.lock_and_check()
            return False

    def hard_drop(self):
        if self.clear_flash_timer > 0:
            return
        dist=0
        while valid_position(self.grid,self.current,None,0,dist+1):
            dist+=1
        self.current.y+=dist
        self.score+=SCORE_HARD_DROP*dist
        self.lock_and_check()

    def lock_and_check(self):
        lock_piece(self.grid,self.current)
        self.hold_lock=False
        self.clearing_rows = get_full_rows(self.grid)
        cleared = len(self.clearing_rows)
        if cleared > 0:
            if cleared==1: self.score+=SCORE_SINGLE*self.level
            elif cleared==2: self.score+=SCORE_DOUBLE*self.level
            elif cleared==3: self.score+=SCORE_TRIPLE*self.level
            elif cleared>=4: self.score+=SCORE_TETRIS*self.level
            self.lines += cleared
            new_level = self.lines // 10 + 1
            if new_level != self.level:
                self.level = new_level
                self.drop_interval = get_drop_interval(self.level)
            self.clear_flash_timer = self.clear_flash_duration
            if self.sound_clear:
                self.sound_clear.play()
            return
        self.spawn_next()

    def update(self,dt):
        if self.game_over or self.paused: return
        if self.clear_flash_timer > 0:
            self.clear_flash_timer = max(0.0, self.clear_flash_timer - dt)
            if self.clear_flash_timer == 0.0:
                self.grid, _ = clear_rows(self.grid, self.clearing_rows)
                self.clearing_rows = []
                self.spawn_next()
            return
        self.drop_timer+=dt
        if self.drop_timer>=self.drop_interval:
            self.drop_timer=0
            if valid_position(self.grid,self.current,None,0,1):
                self.current.y+=1
            else:
                self.lock_and_check()

    def instant_drop_y(self):
        dist=0
        while valid_position(self.grid,self.current,None,0,dist+1):
            dist+=1
        return self.current.y+dist

    # ---------- Drawing ----------
    def draw_grid(self,surface):
        playfield = pygame.Rect(0, 0, CELL_SIZE * COLUMNS, CELL_SIZE * ROWS)
        pygame.draw.rect(surface, COLORS['GRID_BG'], playfield, border_radius=18)
        inner_glow = pygame.Surface(playfield.size, pygame.SRCALPHA)
        pygame.draw.rect(inner_glow, (0, 255, 200, 18), inner_glow.get_rect(), border_radius=18)
        surface.blit(inner_glow, playfield.topleft)

        flash_strength = 0.0
        if self.clear_flash_timer > 0:
            flash_strength = self.clear_flash_timer / self.clear_flash_duration

        for r in range(ROWS):
            for c in range(COLUMNS):
                val=self.grid[r][c]
                cell_rect = pygame.Rect(c * CELL_SIZE + 2, r * CELL_SIZE + 2, CELL_SIZE - 4, CELL_SIZE - 4)
                if val:
                    row_flash = flash_strength if r in self.clearing_rows else 0.0
                    draw_block(surface, COLORS[val], cell_rect, glow=r in self.clearing_rows, flash=row_flash)
                else:
                    pygame.draw.rect(surface, (255, 255, 255, 10), cell_rect, 1, border_radius=6)

        if self.clear_flash_timer <= 0:
            ghost_y=self.instant_drop_y()
            for x,y in self.current.cells():
                gy=ghost_y+(y-self.current.y)
                if gy>=0:
                    ghost_rect = pygame.Rect(x * CELL_SIZE + 4, gy * CELL_SIZE + 4, CELL_SIZE - 8, CELL_SIZE - 8)
                    draw_block(surface, COLORS[self.current.shape], ghost_rect, ghost=True)
            for x,y in self.current.cells():
                if y>=0:
                    rect = pygame.Rect(x * CELL_SIZE + 2, y * CELL_SIZE + 2, CELL_SIZE - 4, CELL_SIZE - 4)
                    draw_block(surface, COLORS[self.current.shape], rect, glow=True)

        for r in range(ROWS+1):
            pygame.draw.line(surface,(50, 56, 70),(0,r*CELL_SIZE),(COLUMNS*CELL_SIZE,r*CELL_SIZE))
        for c in range(COLUMNS+1):
            pygame.draw.line(surface,(50, 56, 70),(c*CELL_SIZE,0),(c*CELL_SIZE,ROWS*CELL_SIZE))
        pygame.draw.rect(surface,COLORS['NEON'],(0,0,CELL_SIZE*COLUMNS,CELL_SIZE*ROWS),3, border_radius=18)
        if flash_strength > 0:
            flash = pygame.Surface(playfield.size, pygame.SRCALPHA)
            pygame.draw.rect(flash, (255, 255, 255, int(55 * flash_strength)), flash.get_rect(), border_radius=18)
            surface.blit(flash, playfield.topleft)

    def draw_side_panel(self,surface,music_on=True):
        panel_x=COLUMNS*CELL_SIZE
        draw_panel(surface, pygame.Rect(panel_x + 8, 10, SIDE_PANEL - 16, HEIGHT - 20), COLORS['NEON'], fill=(8, 12, 20), alpha=205)
        draw_text(surface,"PROCHAINS",24,panel_x+24,28,bold=True)
        start_y=74
        for i in range(4):
            if i<len(self.next_queue):
                piece=self.next_queue[i]
                slot = pygame.Rect(panel_x + 22, start_y + i * 74, SIDE_PANEL - 44, 58)
                draw_panel(surface, slot, COLORS[piece.shape], fill=(15, 20, 30), alpha=170, radius=16)
                draw_mini_piece(surface, piece, slot.centerx, slot.centery, size=12)
        draw_text(surface,"RESERVE",24,panel_x+24,380,bold=True)
        if self.hold_piece:
            hold_slot = pygame.Rect(panel_x + 22, 416, SIDE_PANEL - 44, 72)
            draw_panel(surface, hold_slot, COLORS[self.hold_piece.shape], fill=(15, 20, 30), alpha=170, radius=16)
            draw_mini_piece(surface, self.hold_piece, hold_slot.centerx, hold_slot.centery, size=14)

        draw_text(surface,f"Score  {self.score}",22,panel_x+24,514,bold=True)
        draw_text(surface,f"Lignes  {self.lines}",20,panel_x+24,548)
        draw_text(surface,f"Niveau  {self.level}",20,panel_x+24,576)
        draw_text(surface,"COMMANDES",20,panel_x+24,618,bold=True)
        draw_text(surface,"← →  Deplacer",16,panel_x+24,646)
        draw_text(surface,"↑ / Z  Rotation",16,panel_x+24,668)
        draw_text(surface,"↓  Descente rapide",16,panel_x+24,690)
        draw_text(surface,"Espace  Chute",16,panel_x+24,712)
        if not self.audio_enabled:
            status = "INDISPONIBLE"
        else:
            status = "ON" if music_on else "OFF"
        draw_text(surface,f"Musique  {status}",16,panel_x+24,734)
        if self.audio_enabled and self.audio_driver:
            draw_text(surface,f"Sortie  {self.audio_driver}",14,panel_x+24,756)

    def draw_scanlines(self,surface):
        sl=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        sl.set_alpha(50)
        for y in range(0,HEIGHT,4):
            pygame.draw.line(sl,(0,0,0,60),(0,y),(WIDTH,y))
        surface.blit(sl,(0,0))

    def draw(self,music_on=True):
        self.screen.blit(self.bg_image, (0,0))
        self.draw_grid(self.screen)
        self.draw_side_panel(self.screen,music_on)
        if self.paused:
            draw_panel(self.screen, pygame.Rect(WIDTH // 2 - 150, HEIGHT // 2 - 80, 300, 120), COLORS['NEON'], fill=(8, 10, 18), alpha=220, radius=22)
            draw_text(self.screen,"PAUSE",60,WIDTH//2,HEIGHT//2-20,align="center",bold=True)
        if self.game_over:
            draw_panel(self.screen, pygame.Rect(WIDTH // 2 - 180, HEIGHT // 2 - 90, 360, 150), (255, 90, 120), fill=(20, 8, 14), alpha=225, radius=24)
            draw_text(self.screen,"GAME OVER",60,WIDTH//2,HEIGHT//2-34,align="center",bold=True)
            draw_text(self.screen,"Appuie sur ENTREE pour relancer",24,WIDTH//2,HEIGHT//2+20,align="center")
        self.draw_scanlines(self.screen)

# ---------- Title Screen ----------
def draw_title_screen(screen,bg_image):
    screen.blit(bg_image,(0,0))
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((4, 10, 18, 118))
    screen.blit(overlay, (0, 0))

    hero_rect = pygame.Rect(34, 42, WIDTH - 68, HEIGHT - 84)
    draw_panel(screen, hero_rect, COLORS['NEON'], fill=(8, 12, 20), alpha=210, radius=28)
    pygame.draw.rect(screen, COLORS['NEON'], (0,0,CELL_SIZE*COLUMNS,CELL_SIZE*ROWS),3, border_radius=18)

    ticks = pygame.time.get_ticks() / 1000
    draw_text(screen,GAME_TITLE,90,WIDTH//2,150,align="center",bold=True)
    draw_text(screen,SIGNATURE,26,WIDTH//2,205,align="center")
    draw_text(screen,"Empile, accelere, survive.",30,WIDTH//2,255,align="center")

    demo_shapes=['T','L','I','O','S']
    base_x=86
    base_y=322
    size=18
    for idx,sh in enumerate(demo_shapes):
        bob = int(8 * abs(math.sin(ticks * 1.4 + idx * 0.6)))
        for x,y in TETROMINOS[sh][0]:
            rect=pygame.Rect(base_x+idx*78+x*size,base_y+y*size-bob,size,size)
            draw_block(screen, COLORS[sh], rect, glow=True)

    info_rect = pygame.Rect(WIDTH // 2 - 180, HEIGHT - 170, 360, 92)
    draw_panel(screen, info_rect, (255, 255, 255), fill=(12, 16, 28), alpha=190, radius=22)
    draw_text(screen,"Appuie sur ENTREE pour jouer",28,WIDTH//2,HEIGHT-140,align="center",bold=True)
    draw_text(screen,"Echap pour quitter  •  M pour la musique",18,WIDTH//2,HEIGHT-106,align="center")
    sl=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
    sl.set_alpha(50)
    for y in range(0,HEIGHT,4):
        pygame.draw.line(sl,(0,0,0,60),(0,y),(WIDTH,y))
    screen.blit(sl,(0,0))

# ---------- Main loop ----------
def main():
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    pygame.font.init()
    pygame.display.set_caption("Tetris by Harry - Isabelle Edition")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    audio_state = load_audio_assets()

    # Load background
    if not os.path.exists(BG_PATH):
        print("ERREUR : background.png introuvable !")
        bg_image = pygame.Surface((WIDTH, HEIGHT))
        bg_image.fill((10,10,12))
    else:
        bg_image = pygame.image.load(BG_PATH).convert()
        bg_image = pygame.transform.scale(bg_image,(WIDTH,HEIGHT))

    in_title = True
    game = None
    soft_drop_active = False
    music_on = start_music(audio_state)

    running = True
    while running:
        dt = clock.tick(FPS)/1000.0
        for event in pygame.event.get():
            if event.type==pygame.QUIT:
                running=False; break
            if event.type==pygame.KEYDOWN:
                if event.key==pygame.K_ESCAPE: running=False; break
                if in_title and event.key==pygame.K_RETURN:
                    game=Tetris(screen,bg_image,audio_state)
                    in_title=False
                elif not in_title:
                    busy = game.clear_flash_timer > 0
                    if event.key==pygame.K_p and not game.game_over: game.paused=not game.paused
                    if event.key==pygame.K_r: game=Tetris(screen,bg_image,audio_state); soft_drop_active=False
                    if event.key==pygame.K_c and not game.game_over and not game.paused and not busy: game.hold()
                    if event.key==pygame.K_SPACE and not game.game_over and not game.paused and not busy: game.hard_drop()
                    if event.key==pygame.K_DOWN and not busy: soft_drop_active=True
                    if event.key==pygame.K_LEFT and not game.game_over and not game.paused and not busy and valid_position(game.grid,game.current,None,-1,0): game.current.x-=1
                    if event.key==pygame.K_RIGHT and not game.game_over and not game.paused and not busy and valid_position(game.grid,game.current,None,1,0): game.current.x+=1
                    if event.key==pygame.K_UP and not game.game_over and not game.paused and not busy: game.rotate_current(1)
                    if event.key==pygame.K_z and not game.game_over and not game.paused and not busy: game.rotate_current(-1)
                    if event.key==pygame.K_RETURN and game.game_over: game=Tetris(screen,bg_image,audio_state); soft_drop_active=False
                    if event.key==pygame.K_m and game.audio_enabled:  # Toggle musique
                        if music_on:
                            pygame.mixer.music.pause()
                            music_on = False
                        else:
                            pygame.mixer.music.unpause()
                            music_on = True

            if event.type==pygame.KEYUP and event.key==pygame.K_DOWN: soft_drop_active=False

        if in_title:
            draw_title_screen(screen,bg_image)
        else:
            if soft_drop_active and not game.game_over and not game.paused and game.clear_flash_timer <= 0:
                if valid_position(game.grid,game.current,None,0,1):
                    game.current.y+=1; game.score+=SCORE_SOFT_DROP
                else:
                    game.lock_and_check()
            game.update(dt)
            game.draw(music_on)

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__=="__main__":
    main()

