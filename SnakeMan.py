"""
SnakeMan  -  Pac-Man style game  (Rubber 3D edition)
Player : Snake   |   Enemies : Bombs
Upgraded Graphical Engine
"""
import sys, os, math, random, array as _arr
from collections import deque

_missing = []
try:    import pygame
except: _missing.append("pygame")
try:    import yaml; _HAS_YAML = True
except: _HAS_YAML = False

if _missing:
    print("Missing:", ", ".join(_missing)); print("pip install pygame pyyaml"); sys.exit(1)

pygame.mixer.pre_init(22050, -16, 2, 512)
pygame.init()
ROOT = os.path.dirname(os.path.abspath(__file__))

_DEFAULT_CFG = {
    "game": {"time_limit_seconds": 300, "player_speed": 2.8, "bomb_base_move_every": 7,
             "bomb_fright_move_every": 18, "cell_size": 28, "fps": 60, "window_width": 740, "window_height": 580},
    "levels": [
        {"id":1,"file":"levels/level1.txt","speed_multiplier":0.80,"bomb_move_every":9,"bomb_fright_move_every":22},
        {"id":2,"file":"levels/level2.txt","speed_multiplier":1.00,"bomb_move_every":7,"bomb_fright_move_every":18},
        {"id":3,"file":"levels/level3.txt","speed_multiplier":1.25,"bomb_move_every":5,"bomb_fright_move_every":14},
    ],
}

def load_config():
    if not _HAS_YAML: return _DEFAULT_CFG
    try:
        with open(os.path.join(ROOT, "config.yml")) as f: return yaml.safe_load(f)
    except FileNotFoundError: return _DEFAULT_CFG

def load_sounds():
    if not _HAS_YAML: return {}
    try:
        with open(os.path.join(ROOT, "sounds.yml")) as f: return yaml.safe_load(f) or {}
    except Exception as e:
        print(f'[WARN] sounds.yml: {e}'); return {}

CFG  = load_config(); GCFG = CFG["game"]
_SCFG         = load_sounds()

_MENU_STYLE   = str(_SCFG.get('menu_style',    'bright')).lower()
_MENU_VOL     = float(_SCFG.get('menu_volume',  0.08))
_MENU_ATK_MS  = float(_SCFG.get('menu_attack_ms',  18.0))
_MENU_REL_MS  = float(_SCFG.get('menu_release_ms', 45.0))
_GAME_VOL     = float(_SCFG.get('game_volume',  0.09))
_GAME_ATK_MS  = float(_SCFG.get('game_attack_ms',  75.0))
_GAME_REL_MS  = float(_SCFG.get('game_release_ms', 140.0))
_SFX_VOL      = float(_SCFG.get('sfx_volume', 1.0))
_EAT_CFG      = _SCFG.get('eat',   {})
_POWER_CFG    = _SCFG.get('power', {})
_BOOM_CFG     = _SCFG.get('boom',  {})
_CLEAR_CFG    = _SCFG.get('clear', {})

CELL = GCFG.get("cell_size", 28); FPS = GCFG.get("fps", 60)
HUD_H = 58; TIME_LIMIT = GCFG.get("time_limit_seconds", 300)

BLACK=( 0, 0, 0); WHITE=(255,255,255); YELLOW=(255,215, 0); ORANGE=(255,140, 0)
RED=(215, 45, 45); PINK_C=(255,110,175); CYAN_C=( 60,210,215)
DARK_BG=( 7, 7, 20); WALL_FILL=( 15, 15,125); PATH_BG=( 18, 18, 40)
TIMER_WARN=(220, 78, 38); GOLD=(255,200, 48)
SNAKE_GREEN=( 28,135, 28); SNAKE_LIGHT=( 55,175, 55)
SNAKE_EYE=(218,210, 38); TONGUE_RED=(205, 25, 25)
BOMB_COLORS=[RED,PINK_C,ORANGE,CYAN_C]

THEMES = {
    'classic': {'wall':(15,15,125),  'path':(18,18,40),   'bg':(7,7,20),    'hud':(10,10,35)},
    'forest':  {'wall':(18,88,24),   'path':(8,22,8),     'bg':(4,10,4),    'hud':(6,14,6)},
    'ice':     {'wall':(35,95,175),  'path':(12,28,52),   'bg':(6,12,28),   'hud':(8,16,38)},
    'desert':  {'wall':(155,105,28), 'path':(38,26,8),    'bg':(18,10,4),   'hud':(26,14,5)},
    'neon':    {'wall':(18,145,135), 'path':(6,28,26),    'bg':(3,10,10),   'hud':(4,15,14)},
}
_AT = THEMES['classic']

def apply_theme(name):
    global WALL_FILL, PATH_BG, DARK_BG, _AT
    _AT = THEMES.get(name, THEMES['classic'])
    WALL_FILL = _AT['wall']; PATH_BG = _AT['path']; DARK_BG = _AT['bg']
    _wall_tile_cache.clear()

MENU_W = int(GCFG.get('window_width',  740))
MENU_H = int(GCFG.get('window_height', 580))

UP=( 0,-1); DOWN=( 0,1); LEFT=(-1,0); RIGHT=(1,0); STOP=(0,0)
ALL_DIRS=[UP,DOWN,LEFT,RIGHT]
OPPOSITE={UP:DOWN,DOWN:UP,LEFT:RIGHT,RIGHT:LEFT,STOP:STOP}

_sph_cache={}; _wall_tile_cache={}

def _make_sphere(r, base):
    """Generates high-gloss rubbery toy aesthetic with modern specular maps."""
    d = r * 2 + 4
    s = pygame.Surface((d, d), pygame.SRCALPHA)
    cx = cy = r + 2
    
    rim = tuple(max(0, c - 85) for c in base)
    peak = tuple(min(255, c + 80) for c in base)
    
    for i in range(r, 0, -1):
        t = i / r
        col = tuple(int(rim[j] + (peak[j] - rim[j]) * (1 - t**0.35)) for j in range(3))
        pygame.draw.circle(s, col + (255,), (cx, cy), i)
        
    # High-intensity glossy reflection point
    sr = max(2, r // 3)
    scx, scy = cx - int(r * 0.35), cy - int(r * 0.35)
    for i in range(sr, 0, -1):
        a = int(230 * (1 - (i / sr)**1.5))
        pygame.draw.circle(s, (255, 255, 255, a), (scx, scy), i)
    return s

def blit_sphere(surf, cx, cy, r, color):
    key = (r, color)
    if key not in _sph_cache: _sph_cache[key] = _make_sphere(r, color)
    surf.blit(_sph_cache[key], (cx - r - 2, cy - r - 2))

def drop_shadow(surf, cx, cy, r):
    """Creates a soft, modern alpha-blended ambient occlusion shadow map."""
    w = r * 2 + 8
    h = max(6, r // 2 + 5)
    sh = pygame.Surface((w, h), pygame.SRCALPHA)
    
    # Layered concentric shadow rings for gradient smoothness
    for i in range(4):
        alpha = int(48 * (1 - i / 4))
        pygame.draw.ellipse(sh, (0, 0, 0, alpha), (i, i, w - i*2, h - i*2))
    surf.blit(sh, (cx - r - 4, cy + int(r * 0.4) - 2))

def _make_wall_tile(size):
    """Bakes clean, smooth continuous bevel vectors for modern UI depth."""
    s = pygame.Surface((size, size))
    b = max(4, size // 6)
    face = tuple(min(255, c + 15) for c in WALL_FILL)
    light = tuple(min(255, c + 70) for c in WALL_FILL)
    dark = tuple(max(0, c - 45) for c in WALL_FILL)
    
    s.fill(face)
    pygame.draw.polygon(s, light, [(0, 0), (size, 0), (size - b, b), (b, b)])
    pygame.draw.polygon(s, light, [(0, 0), (b, b), (b, size - b), (0, size)])
    pygame.draw.polygon(s, dark, [(0, size), (size, size), (size - b, size - b), (b, size - b)])
    pygame.draw.polygon(s, dark, [(size, 0), (size, size), (size - b, size - b), (size - b, b)])
    pygame.draw.rect(s, (0, 0, 0, 30), (0, 0, size, size), 1)
    return s

def get_wall_tile():
    if WALL_FILL not in _wall_tile_cache: _wall_tile_cache[WALL_FILL] = _make_wall_tile(CELL)
    return _wall_tile_cache[WALL_FILL]

def draw_pellet(surf, cx, cy): 
    blit_sphere(surf, cx, cy, 5, (235, 235, 240))

def draw_power_pellet(surf, cx, cy, frame):
    pulse = int(7 + 2.5 * math.sin(frame * 0.15))
    gh_r = pulse + 9
    gh = pygame.Surface((gh_r * 2, gh_r * 2), pygame.SRCALPHA)
    for i in range(gh_r, 0, -1):
        a = int(110 * (1 - (i / gh_r)**1.3))
        pygame.draw.circle(gh, (255, 215, 0, a), (gh_r, gh_r), i)
    surf.blit(gh, (cx - gh_r, cy - gh_r))
    blit_sphere(surf, cx, cy, pulse, (255, 200, 15))

def draw_snake(surf, px, py, direction, tongue_out):
    cx = int(px) + CELL // 2; cy = int(py) + CELL // 2; r = CELL // 2 - 1
    drop_shadow(surf, cx, cy, r + 1)
    dx, dy = direction if direction != STOP else RIGHT
    pa_x, pa_y = -dy, dx
    
    blit_sphere(surf, cx, cy, r, SNAKE_GREEN)
    sp = r // 3; sr = max(4, int(r * 0.7))
    blit_sphere(surf, cx + dx * sp, cy + dy * sp, sr, SNAKE_LIGHT)
    
    # Eyes
    ef = r // 5; es = r * 2 // 5; er = max(3, r // 4)
    for sign in (-1, +1):
        ex = cx + dx * ef + pa_x * sign * es
        ey = cy + dy * ef + pa_y * sign * es
        blit_sphere(surf, ex, ey, er, SNAKE_EYE)
        pygame.draw.circle(surf, BLACK, (ex, ey), 2)
        
    if tongue_out and direction != STOP:
        tbx = cx + dx * (r + 1); tby = cy + dy * (r + 1)
        tl = max(5, r // 2 + 2); ttx = tbx + dx * tl; tty = tby + dy * tl
        fl = max(3, r // 4 + 1)
        pygame.draw.line(surf, TONGUE_RED, (tbx, tby), (ttx, tty), 2)
        for sign in (-1, +1):
            fx = ttx + pa_x * sign * fl; fy = tty + pa_y * sign * fl
            pygame.draw.line(surf, TONGUE_RED, (ttx, tty), (fx, fy), 2)

def draw_bomb(surf, px, py, frightened, flash, frame, color):
    cx = int(px) + CELL // 2; cy = int(py) + CELL // 2; r = CELL // 2 - 2
    drop_shadow(surf, cx, cy, r)
    if frightened:
        col = (235, 235, 250) if flash else (35, 35, 215)
        ec = (190, 190, 220) if flash else (70, 70, 220)
        blit_sphere(surf, cx, cy, r, col)
        er = max(2, r // 5)
        for xo in [-r // 3, r // 3]: blit_sphere(surf, cx + xo, cy - r // 4, er, ec)
        pts = [(cx - r // 2, cy + r // 4), (cx - r // 4, cy), (cx, cy + r // 4), (cx + r // 4, cy), (cx + r // 2, cy + r // 4)]
        pygame.draw.lines(surf, WHITE if flash else (75, 75, 225), False, pts, 2)
    else:
        dc = tuple(max(15, c // 3) for c in color)
        blit_sphere(surf, cx, cy, r, dc)
        pygame.draw.circle(surf, color, (cx, cy), r, 3)
        bob = math.sin(frame * 0.25) * 3.0
        fx, fy = cx + r - 5, cy - r + 4; tx, ty = int(fx + 6 + bob), int(fy - 10)
        pygame.draw.line(surf, (150, 115, 35), (fx, fy), (tx, ty), 3)
        
        # Fuse Sparks
        for gr in range(6, 0, -1):
            t = 1 - gr / 6
            gc = (min(255, int(255 * t)), min(255, int(160 * t)), 30)
            pygame.draw.circle(surf, gc, (tx, ty), gr)
        pygame.draw.circle(surf, WHITE, (tx, ty), 2)

# ─── Audio Initialization / Management ─────────────────────────────────────────
_MENU_NOTES_DEFAULT = [
    (523,42),(0,10),(659,40),(0,10),(784,42),(0,12),(1047,58),(0,18),
    (988,40),(0,10),(784,40),(0,10),(659,42),(0,12),(523,58),(0,18)
]
MENU_MUSIC = [(int(hz), max(1, round(ms * 60 / 1000))) for hz, ms in _SCFG.get('menu_notes', _MENU_NOTES_DEFAULT)]

_GM_EASY_DEF = [(392,55),(0,12),(494,52),(0,10),(587,62),(0,15),(784,68)]
_GM_MED_DEF = [(523,55),(0,12),(659,52),(0,10),(784,62),(0,15),(1047,68)]
_GM_HARD_DEF = [(440,55),(0,12),(523,52),(0,10),(659,62),(0,15),(880,68)]

def _notes_ms(key, default):
    raw = _SCFG.get(key)
    if raw: return [(int(hz), max(1, round(ms * 60 / 1000))) for hz, ms in raw]
    return default

GAME_MUSIC   = _notes_ms('game_notes_easy',   _GM_EASY_DEF)
GAME_MUSIC_B = _notes_ms('game_notes_medium', _GM_MED_DEF)
GAME_MUSIC_C = _notes_ms('game_notes_hard',   _GM_HARD_DEF)

_NOTE_CACHE = {}; _OCR_CACHE = {}

def _make_note(freq, dur_frames, vol=None):
    key = (freq, dur_frames)
    if key in _NOTE_CACHE: return _NOTE_CACHE[key]
    if vol is None: vol = _MENU_VOL
    sr = 22050; dur_s = max(0.01, dur_frames / 60.0); n = int(sr * dur_s)
    buf = _arr.array('h', [0] * (n * 2))
    if freq > 0:
        atk_n = max(1, int(sr * _MENU_ATK_MS / 1000))
        rel_n = max(1, int(sr * _MENU_REL_MS / 1000))
        for i in range(n):
            t = i / sr
            atk = min(1.0, i / atk_n)
            rel = min(1.0, (n - i) / rel_n)
            phase = (freq * t) % 1.0
            raw = 2.0 * abs(2.0 * phase - 1.0) - 1.0
            raw = raw * 0.45 + math.sin(2 * math.pi * freq * t) * 0.55
            v = int(raw * vol * atk * rel * 32767)
            buf[2*i] = buf[2*i+1] = max(-32767, min(32767, v))
    snd = pygame.mixer.Sound(buffer=buf)
    _NOTE_CACHE[key] = snd; return snd

def _make_ocarina_note(freq, dur_frames, vol=None):
    key = (freq, dur_frames)
    if key in _OCR_CACHE: return _OCR_CACHE[key]
    if vol is None: vol = _GAME_VOL
    sr = 22050; dur_s = max(0.01, dur_frames / 60.0); n = int(sr * dur_s)
    buf = _arr.array('h', [0] * (n * 2))
    if freq > 0:
        atk_n = max(1, int(sr * _GAME_ATK_MS / 1000))
        rel_n = max(1, int(sr * _GAME_REL_MS / 1000))
        for i in range(n):
            t = i / sr
            atk = min(1.0, i / atk_n)
            rel = min(1.0, (n - i) / rel_n)
            raw = (math.sin(2 * math.pi * freq * t) * 0.90 + math.sin(2 * math.pi * freq * 0.5 * t) * 0.08)
            v = int(raw * vol * atk * rel * 32767)
            buf[2*i] = buf[2*i+1] = max(-32767, min(32767, v))
    snd = pygame.mixer.Sound(buffer=buf)
    _OCR_CACHE[key] = snd; return snd

def _make_boom():
    dur_s = float(_BOOM_CFG.get('duration_ms', 900)) / 1000
    bvol = float(_BOOM_CFG.get('volume', 0.44)) * _SFX_VOL
    f_low = float(_BOOM_CFG.get('freq_low', 36))
    decay = float(_BOOM_CFG.get('decay', 4.2))
    sr = 22050; n = int(sr * dur_s); buf = _arr.array('h', [0] * (n * 2))
    rng = random.Random(7)
    for i in range(n):
        t = i / sr
        env = math.exp(-t * decay)
        noise = rng.uniform(-1, 1)
        f_sweep = f_low * math.exp(-t * 2.5)
        low = math.sin(2 * math.pi * f_sweep * t) * 0.6
        raw = (noise * 0.4 + low) * env
        buf[2*i] = buf[2*i+1] = int(max(-1.0, min(1.0, raw)) * bvol * 32767)
    return pygame.mixer.Sound(buffer=buf)

def _make_eat():
    sr = 22050; n = int(sr * 0.07); buf = _arr.array('h', [0] * (n * 2))
    for i in range(n):
        t = i / sr; env = math.sin(math.pi * i / n) ** 2
        freq = 550 + 280 * (i / n)
        buf[2*i] = buf[2*i+1] = int(math.sin(2 * math.pi * freq * t) * env * 0.12 * 32767)
    return pygame.mixer.Sound(buffer=buf)

_SFX = {}
_MS  = {'seq': [], 'idx': 0, 'timer': 0, 'ch': None, 'ocarina': False}
_SOUND_OK = False

def init_sounds():
    global _SFX, _SOUND_OK
    try:
        _MS['ch'] = pygame.mixer.Channel(0)
        _SFX['boom']  = _make_boom()
        _SFX['eat']   = _make_eat()
        _SFX['power'] = _make_eat() # Reuse envelope for brief safety
        _SFX['clear'] = _make_eat()
        _SOUND_OK = True
    except Exception as e:
        print(f'[WARN] Sound system failure: {e}')

def music_start(seq, ocarina=False):
    if not _SOUND_OK: return
    _MS['seq'] = seq; _MS['idx'] = 0; _MS['timer'] = 0; _MS['ocarina'] = ocarina

def music_stop():
    if _MS['ch']: _MS['ch'].stop()
    _MS['seq'] = []

def music_tick():
    if not _SOUND_OK or not _MS['seq'] or not _MS['ch']: return
    _MS['timer'] -= 1
    if _MS['timer'] <= 0:
        freq, dur = _MS['seq'][_MS['idx'] % len(_MS['seq'])]
        snd = _make_ocarina_note(freq, dur) if _MS['ocarina'] else _make_note(freq, dur)
        if freq > 0: _MS['ch'].play(snd)
        _MS['timer'] = dur
        _MS['idx'] = (_MS['idx'] + 1) % len(_MS['seq'])

def snd_play(name):
    if not _SOUND_OK or name not in _SFX: return
    ch = pygame.mixer.find_channel()
    if ch: ch.play(_SFX[name])

# ─── Explosion Particle Engine ────────────────────────────────────────────────
class Explosion:
    def __init__(self, cx, cy, col1, col2=(255,220,0), n=24):
        self.cx = cx; self.cy = cy; self.done = False; self.frame = 0
        self.particles = []
        for _ in range(n):
            angle = random.uniform(0, math.tau); spd = random.uniform(2.0, 8.0)
            col = col1 if random.random() > 0.35 else col2
            life = random.randint(25, 50)
            self.particles.append({'x': float(cx), 'y': float(cy),
                'vx': math.cos(angle)*spd, 'vy': math.sin(angle)*spd - random.uniform(0,2),
                'r': random.uniform(4,10), 'col': col, 'life': life, 'ml': life})

    def update(self):
        self.frame += 1; alive = False
        for p in self.particles:
            p['life'] -= 1
            if p['life'] <= 0: continue
            alive = True
            p['x'] += p['vx']; p['y'] += p['vy']
            p['vy'] += 0.25; p['vx'] *= 0.95; p['r'] *= 0.96
        self.done = not alive

    def draw(self, surf):
        if self.frame < 10:
            rr = self.frame * 7 + 3
            ring = pygame.Surface((rr*2+4, rr*2+4), pygame.SRCALPHA)
            a = int(220 * (1 - self.frame / 10))
            pygame.draw.circle(ring, (255,215,85,a), (rr+2,rr+2), rr, 4)
            surf.blit(ring, (self.cx - rr - 2, self.cy - rr - 2))
        for p in self.particles:
            if p['life'] <= 0 or p['r'] < 1.0: continue
            alpha = p['life'] / p['ml']
            col = tuple(int(c * alpha) for c in p['col'])
            if any(c > 0 for c in col):
                blit_sphere(surf, int(p['x']), int(p['y']), max(1, int(p['r'])), col)

# ─── Level Processing ─────────────────────────────────────────────────────────
def _flood_fix(maze, rows, cols, start):
    visited = [[False]*cols for _ in range(rows)]
    q = deque([start]); visited[start[1]][start[0]] = True
    while q:
        x, y = q.popleft()
        for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
            nx, ny = (x+dx)%cols, y+dy
            if 0 <= ny < rows and not visited[ny][nx] and maze[ny][nx] != 1:
                visited[ny][nx] = True; q.append((nx, ny))
    for r in range(rows):
        for c in range(cols):
            if maze[r][c] in (2, 3) and not visited[r][c]: maze[r][c] = 0

def load_level(path):
    full = os.path.join(ROOT, path)
    if not os.path.exists(full):
        # Generate clean programmatic fallback grid
        grid = ["#"*21] + ["#"+"."*19+"#"]*21 + ["#"*21]
        grid[11] = "#" + "."*9 + "K" + "."*9 + "#"
        return [[1 if c=='#' else 2 for c in r] for r in grid], 23, 21, (10,11), [], {}, 19*21-1
    with open(full) as f: raw = f.read().splitlines()
    meta = {}; grid_lines = []
    for line in raw:
        if line.startswith('!'):
            k, _, v = line[1:].partition('='); meta[k.strip()] = v.strip()
        else: grid_lines.append(line)
    rows = len(grid_lines); cols = max((len(l) for l in grid_lines), default=21)
    maze = [[0]*cols for _ in range(rows)]
    koala_pos = (cols//2, rows//2); bombs = []
    for r, line in enumerate(grid_lines):
        for c, ch in enumerate(line):
            if ch == '#':  maze[r][c] = 1
            elif ch == '.': maze[r][c] = 2
            elif ch in ('O','o'): maze[r][c] = 3
            elif ch == 'K': koala_pos = (c, r)
            elif ch == 'B': bombs.append((c, r))
    _flood_fix(maze, rows, cols, koala_pos)
    total = sum(1 for r in range(rows) for c in range(cols) if maze[r][c] in (2,3))
    return maze, rows, cols, koala_pos, bombs, meta, total

class Koala:
    def __init__(self, gx, gy, speed):
        self.gx=gx; self.gy=gy; self.speed=speed
        self.px=float(gx*CELL); self.py=float(gy*CELL)
        self.direction=STOP; self.queued=STOP
        self.tgx=gx; self.tgy=gy; self.arrived=True
        self.mouth_open=False; self.lives=3; self.score=0

    def queue_dir(self, d): self.queued = d

    def update(self, maze, rows, cols):
        if self.arrived:
            nd = self.queued
            if nd != STOP:
                nx, ny = (self.gx+nd[0])%cols, (self.gy+nd[1])%rows
                if maze[ny][nx] != 1: self.direction = nd
            if self.direction != STOP:
                dx, dy = self.direction
                nx, ny = (self.gx+dx)%cols, (self.gy+dy)%rows
                if maze[ny][nx] != 1: self.tgx=nx; self.tgy=ny; self.arrived=False
                else: self.direction=STOP
        if not self.arrived:
            tx=self.tgx*CELL; ty=self.tgy*CELL
            if abs(self.tgx-self.gx)>1: self.px=tx
            if abs(self.tgy-self.gy)>1: self.py=ty
            dist=math.hypot(tx-self.px, ty-self.py)
            if dist <= self.speed:
                self.px=float(tx); self.py=float(ty); self.gx=self.tgx; self.gy=self.tgy; self.arrived=True
            else:
                self.px+=(tx-self.px)/dist*self.speed; self.py+=(ty-self.py)/dist*self.speed
        self.mouth_open = not self.arrived

    def draw(self, surf): draw_snake(surf, self.px, self.py+HUD_H, self.direction, self.mouth_open)

class Bomb:
    def __init__(self, gx, gy, bomb_id, move_every, fright_move_every):
        self.gx=gx; self.gy=gy; self.bomb_id=bomb_id
        self.move_every=move_every; self.fright_move_every=fright_move_every
        self.px=float(gx*CELL); self.py=float(gy*CELL)
        self.direction=random.choice(ALL_DIRS)
        self.move_timer=0; self.mode='scatter'; self.mode_timer=0
        self.frightened=False; self.fright_timer=0; self.flash=False
        self.color=BOMB_COLORS[bomb_id%len(BOMB_COLORS)]; self.dead=False

    def frighten(self): self.frightened=True; self.fright_timer=360; self.flash=False

    def update(self, maze, rows, cols, koala, frame):
        if self.dead: return
        if self.frightened:
            self.fright_timer -= 1
            if self.fright_timer <= 0: self.frightened=False
            elif self.fright_timer < 90: self.flash=(frame//15)%2==0
        self.move_timer += 1
        interval = self.fright_move_every if self.frightened else self.move_every
        if self.move_timer < interval: return
        self.move_timer = 0
        opts = [d for d in ALL_DIRS if 0<=(self.gx+d[0])<cols and 0<=(self.gy+d[1])<rows and maze[self.gy+d[1]][self.gx+d[0]]!=1]
        if not opts: return
        self.direction = random.choice(opts)
        self.gx+=self.direction[0]; self.gy+=self.direction[1]
        self.px=float(self.gx*CELL); self.py=float(self.gy*CELL)

    def draw(self, surf, frame):
        if not self.dead: draw_bomb(surf, self.px, self.py+HUD_H, self.frightened, self.flash, frame, self.color)

# ─── Level Selection Reconstruction ───────────────────────────────────────────
class LevelSelect:
    def __init__(self, screen, font_l, font_m, font_s, level_cfgs, scores):
        self.screen=screen; self.font_l=font_l; self.font_m=font_m; self.font_s=font_s
        self.level_cfgs=level_cfgs; self.selected=0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE: return 'menu'
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE): return 'play'
            elif event.key == pygame.K_UP: self.selected = max(0, self.selected - 1)
            elif event.key == pygame.K_DOWN: self.selected = min(len(self.level_cfgs)-1, self.selected + 1)
        return None

    def draw(self):
        self.screen.fill(DARK_BG)
        title = self.font_l.render("SELECT LEVEL", True, YELLOW)
        self.screen.blit(title, (MENU_W//2 - title.get_width()//2, 45))
        for i, cfg in enumerate(self.level_cfgs):
            col = GOLD if i == self.selected else WHITE
            lbl = self.font_m.render(f"Level {cfg['id']} - Speed: {cfg['speed_multiplier']}x", True, col)
            self.screen.blit(lbl, (MENU_W//2 - lbl.get_width()//2, 160 + i*50))
        hint = self.font_s.render("Press SPACE/ENTER to launch | ESC to go back", True, (130,130,160))
        self.screen.blit(hint, (MENU_W//2 - hint.get_width()//2, MENU_H - 60))

# ─── Map Editor Architecture ──────────────────────────────────────────────────
class MapEditor:
    SIDEBAR_W = 140
    TOOLS = [('1:Wall','#',WALL_FILL), ('2:Empty',' ',PATH_BG), ('3:Pellet','.',(170,170,170)), ('4:Power','O',YELLOW), ('5:Snake','K',SNAKE_GREEN), ('6:Bomb','B',RED)]
    def __init__(self, screen, font_m, font_s):
        self.screen=screen; self.font_m=font_m; self.font_s=font_s
        self.rows=18; self.cols=21; self.tool=0; self.grid=[[' ']*21 for _ in range(18)]
    def handle_event(self, event):
        if event.type==pygame.KEYDOWN and event.key==pygame.K_ESCAPE: return 'menu'
        return None
    def draw(self):
        self.screen.fill(DARK_BG)
        pygame.draw.rect(self.screen, (12,12,36), (0,0,self.SIDEBAR_W,MENU_H))
        lbl = self.font_m.render("Editor Active", True, YELLOW)
        self.screen.blit(lbl, (10,20))
        msg = self.font_s.render("Press ESC to Exit", True, WHITE)
        self.screen.blit(msg, (10,60))

# ─── Main Run Control Engine ──────────────────────────────────────────────────
def main():
    screen = pygame.display.set_mode((MENU_W, MENU_H))
    pygame.display.set_caption("SnakeMan: Rubber 3D Edition")
    clock = pygame.time.Clock()
    
    f_large = pygame.font.SysFont("comicsansms", 42)
    f_med = pygame.font.SysFont("comicsansms", 24)
    f_small = pygame.font.SysFont("monospace", 14)
    
    init_sounds()
    apply_theme('classic')
    
    state = 'menu'
    level_cfgs = CFG.get("levels", _DEFAULT_CFG["levels"])
    sel_scene = LevelSelect(screen, f_large, f_med, f_small, level_cfgs, {})
    editor_scene = MapEditor(screen, f_med, f_small)
    
    # Engine Tracking Fields
    maze, r_rows, r_cols, k_start, b_list, koala, bombs = None, 0, 0, (0,0), [], None, []
    pellets_remaining, frame, game_time = 0, 0, 0.0
    explosions = []
    
    music_start(MENU_MUSIC)
    
    while True:
        frame += 1
        music_tick()
        events = pygame.event.get()
        
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
                
            if state == 'menu':
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_1:
                        state = 'select'
                    elif event.key == pygame.K_2:
                        state = 'editor'
                    elif event.key == pygame.K_ESCAPE:
                        pygame.quit(); sys.exit()
                        
            elif state == 'select':
                nxt = sel_scene.handle_event(event)
                if nxt == 'menu': state = 'menu'
                elif nxt == 'play':
                    # Build active state configurations dynamically
                    tgt_lvl = level_cfgs[sel_scene.selected]
                    maze, r_rows, r_cols, k_start, b_list, _, pellets_remaining = load_level(tgt_lvl["file"])
                    koala = Koala(k_start[0], k_start[1], GCFG["player_speed"] * tgt_lvl["speed_multiplier"])
                    bombs = [Bomb(bx, by, i, tgt_lvl["bomb_move_every"], tgt_lvl["bomb_fright_move_every"]) for i,(bx,by) in enumerate(b_list)]
                    game_time = float(TIME_LIMIT)
                    explosions.clear()
                    music_start(GAME_MUSIC, ocarina=True)
                    state = 'game'
                    
            elif state == 'editor':
                if editor_scene.handle_event(event) == 'menu': state = 'menu'
                
            elif state == 'game':
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        music_start(MENU_MUSIC); state = 'menu'
                    elif event.key == pygame.K_UP: koala.queue_dir(UP)
                    elif event.key == pygame.K_DOWN: koala.queue_dir(DOWN)
                    elif event.key == pygame.K_LEFT: koala.queue_dir(LEFT)
                    elif event.key == pygame.K_RIGHT: koala.queue_dir(RIGHT)
                    
        # State Execution Blocks
        if state == 'menu':
            screen.fill(DARK_BG)
            t_lbl = f_large.render("SNAKEMAN", True, YELLOW)
            screen.blit(t_lbl, (MENU_W//2 - t_lbl.get_width()//2, MENU_H//3 - 30))
            sub = f_med.render("1: Play Game  |  2: Map Editor  |  ESC: Quit", True, WHITE)
            screen.blit(sub, (MENU_W//2 - sub.get_width()//2, MENU_H//2 + 20))
            
        elif state == 'select':
            sel_scene.draw()
            
        elif state == 'editor':
            editor_scene.draw()
            
        elif state == 'game':
            # Logic Loop execution
            game_time -= 1.0 / 60.0
            koala.update(maze, r_rows, r_cols)
            
            # Pellet consumption verification loops
            cx, cy = koala.gx, koala.gy
            if maze[cy][cx] == 2: # Clean pellet consumption
                maze[cy][cx] = 0; koala.score += 10; pellets_remaining -= 1
                snd_play('eat')
            elif maze[cy][cx] == 3: # Power Pellets trigger
                maze[cy][cx] = 0; koala.score += 50; pellets_remaining -= 1
                snd_play('power')
                for b in bombs: b.frighten()
                
            for b in bombs:
                b.update(maze, r_rows, r_cols, koala, frame)
                if not b.dead and b.gx == koala.gx and b.gy == koala.gy:
                    if b.frightened:
                        b.dead = True; koala.score += 200
                        explosions.append(Explosion(b.px+CELL//2, b.py+HUD_H+CELL//2, b.color, WHITE))
                        snd_play('boom')
                    else:
                        koala.lives -= 1
                        explosions.append(Explosion(koala.px+CELL//2, koala.py+HUD_H+CELL//2, SNAKE_GREEN, YELLOW))
                        snd_play('boom')
                        if koala.lives <= 0:
                            music_start(MENU_MUSIC); state = 'menu'
                            
            for ex in explosions: ex.update()
            explosions = [e for e in explosions if not e.done]
            
            if pellets_remaining <= 0 or game_time <= 0:
                music_start(MENU_MUSIC); state = 'menu'
                
            # Game Space Vector Blitting Loop
            screen.fill(DARK_BG)
            # Render HUD Panel Layout
            pygame.draw.rect(screen, (15,15,40), (0, 0, MENU_W, HUD_H))
            pygame.draw.line(screen, GOLD, (0, HUD_H), (MENU_W, HUD_H), 2)
            
            sc_lbl = f_med.render(f"SCORE: {koala.score}", True, WHITE)
            lv_lbl = f_med.render(f"LIVES: {koala.lives}", True, RED)
            tm_lbl = f_med.render(f"TIME: {max(0, int(game_time))}", True, YELLOW if game_time > 30 else TIMER_WARN)
            screen.blit(sc_lbl, (25, 12)); screen.blit(lv_lbl, (MENU_W//2 - lv_lbl.get_width()//2, 12))
            screen.blit(tm_lbl, (MENU_W - tm_lbl.get_width() - 25, 12))
            
            # Map elements layout loop execution
            for r in range(r_rows):
                for c in range(r_cols):
                    bx = c * CELL; by = r * CELL + HUD_H
                    val = maze[r][c]
                    if val == 1: screen.blit(get_wall_tile(), (bx, by))
                    elif val == 2: draw_pellet(screen, bx+CELL//2, by+CELL//2)
                    elif val == 3: draw_power_pellet(screen, bx+CELL//2, by+CELL//2, frame)
                    
            koala.draw(screen)
            for b in bombs: b.draw(screen, frame)
            for ex in explosions: ex.draw(screen)
            
        pygame.display.flip()
        clock.tick(FPS)

if __name__ == '__main__': main()