"""Simulador interactivo del campus UP para el Proyecto TACHI usando Pygame.

Esta versión adapta la experiencia previa para que se muestre sobre un mapa tipo
pixel-art inspirado en el prototipo `game.py` proporcionado. Se conservan las
capacidades originales: selección de personaje, necesidades dinámicas, acciones
por edificio, bitácora y panel lateral; además se integran cámaras, interiores,
narrativa simulada y compositor de acciones del prototipo externo."""
from __future__ import annotations

import json
import os
import random
import sys
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import pygame

# ---------------------------------------------------------------------------
# Parámetros globales (tomados y adaptados del prototipo game.py)
# ---------------------------------------------------------------------------
SCREEN_W, SCREEN_H = 1024, 720
TILE = 32
MAP_W, MAP_H = 220, 150
TARGET_FPS = 60
ANIM_FPS = 6

# Día simulado
START_MIN = 8 * 60
END_MIN = 20 * 60
MIN_PER_SEC = 6
SHOW_CLOCK = True

# Panel lateral para el jugador (mantiene la funcionalidad original)
PANEL_WIDTH = 280
PANEL_PADDING = 16
PANEL_BG = (28, 38, 64)
PANEL_TEXT = (235, 240, 255)
PANEL_MUTED = (165, 176, 196)
PANEL_ACCENT = (142, 202, 230)
PANEL_BORDER = (42, 48, 74)
MAX_LOG_ENTRIES = 8

# Necesidades del jugador
DECAY_RATES = {
    "Hambre": 6.0,
    "Energía": 4.5,
    "Progreso Académico": 2.0,
    "Vida Social": 1.5,
}

# ---------------------------------------------------------------------------
# Índices del tileset (del prototipo original)
# ---------------------------------------------------------------------------
(
    T_GRASS,
    T_ROAD,
    T_PATH,
    T_PARK,
    T_ROOF_DEF,
    T_ENTR,
    T_PARKING,
    T_SPORT,
    T_WALL,
    T_FLOOR,
    T_WOOD,
    T_SHELF,
    T_TABLE,
    T_FLAG,
    T_ROOF_LIB,
    T_ROOF_LAB,
    T_ROOF_CAFE,
    T_ROOF_OXXO,
) = range(18)

# ---------------------------------------------------------------------------
# Utilidades generales
# ---------------------------------------------------------------------------

def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


# ---------------------------------------------------------------------------
# Modelos de datos para acciones del jugador
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Action:
    key: str
    label: str
    handler: Callable[["PlayerState"], str]


@dataclass(frozen=True)
class CharacterDefinition:
    name: str
    role: str
    color: Tuple[int, int, int]


CHARACTER_DEFS: Sequence[CharacterDefinition] = (
    CharacterDefinition("Rector Antonio", "rector", (220, 60, 60)),
    CharacterDefinition("Maestra Martha", "maestro", (255, 179, 71)),
    CharacterDefinition("Profe Tachiquín", "maestro", (255, 111, 145)),
    CharacterDefinition("Maestro Isaac", "maestro", (255, 200, 87)),
    CharacterDefinition("Administradora Fabiola", "empleado", (160, 120, 220)),
    CharacterDefinition("Alumno Fundadores", "alumno", (100, 180, 255)),
    CharacterDefinition("Alumna Música", "alumno", (130, 170, 255)),
)

# ---------------------------------------------------------------------------
# Generación de tiles y sprites
# ---------------------------------------------------------------------------


def _make_tile(color: Tuple[int, int, int]) -> pygame.Surface:
    surf = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
    surf.fill(color)
    return surf


def _grid(surface: pygame.Surface, step: int = 8, color: Tuple[int, int, int] = (200, 200, 205)) -> None:
    for x in range(0, TILE, step):
        pygame.draw.line(surface, color, (x, 0), (x, TILE))
    for y in range(0, TILE, step):
        pygame.draw.line(surface, color, (0, y), (TILE, y))


def gen_tiles() -> List[pygame.Surface]:
    tiles: List[pygame.Surface] = []
    grass = _make_tile((26, 115, 26))
    tiles.append(grass)

    road = _make_tile((60, 60, 60))
    for y in range(2, TILE, 8):
        pygame.draw.rect(road, (245, 230, 80), (15, y, 2, 3))
    tiles.append(road)

    path = _make_tile((170, 170, 170))
    _grid(path, 8, (150, 150, 150))
    tiles.append(path)

    park = _make_tile((40, 140, 40))
    tiles.append(park)

    def roof(color: Tuple[int, int, int]) -> pygame.Surface:
        surf = _make_tile(color)
        pygame.draw.rect(surf, (110, 110, 128), (2, 2, 28, 28), 1)
        return surf

    tiles.append(roof((145, 145, 165)))

    entrance = _make_tile((145, 145, 165))
    pygame.draw.rect(entrance, (240, 200, 80), (6, 6, 20, 20))
    tiles.append(entrance)

    parking = _make_tile((45, 45, 55))
    for x in range(4, 32, 8):
        pygame.draw.line(parking, (220, 220, 220), (x, 2), (x, 30), 2)
    tiles.append(parking)

    sport = _make_tile((40, 60, 160))
    pygame.draw.rect(sport, (230, 110, 50), (2, 2, 28, 28), 2)
    tiles.append(sport)

    wall = _make_tile((55, 55, 75))
    tiles.append(wall)

    floor = _make_tile((218, 218, 220))
    _grid(floor)
    tiles.append(floor)

    wood = _make_tile((196, 160, 120))
    tiles.append(wood)

    shelf = _make_tile((230, 230, 230))
    pygame.draw.rect(shelf, (180, 180, 180), (6, 6, 20, 20))
    tiles.append(shelf)

    table = _make_tile((210, 200, 190))
    pygame.draw.ellipse(table, (200, 190, 180), (6, 6, 20, 20))
    tiles.append(table)

    flag = _make_tile((110, 110, 120))
    pygame.draw.rect(flag, (90, 90, 100), (4, 22, 24, 6))
    tiles.append(flag)

    tiles.append(roof((170, 160, 200)))
    tiles.append(roof((160, 200, 190)))
    tiles.append(roof((150, 110, 90)))
    tiles.append(roof((210, 40, 40)))
    return tiles


def load_tiles(path: str) -> List[pygame.Surface]:
    if os.path.exists(path):
        try:
            tileset = pygame.image.load(path).convert_alpha()
            width = tileset.get_width() // TILE
            return [tileset.subsurface(pygame.Rect(i * TILE, 0, TILE, TILE)) for i in range(width)]
        except Exception as exc:
            print("[WARN] tileset.png falló:", exc)
    print("[INFO] Usando tiles generados.")
    return gen_tiles()


def gen_sprites() -> Dict[str, pygame.Surface]:
    def person(color: Tuple[int, int, int]) -> pygame.Surface:
        surf = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
        pygame.draw.ellipse(surf, (240, 220, 180), (10, 4, 12, 12))
        pygame.draw.rect(surf, color, (11, 16, 10, 12))
        pygame.draw.rect(surf, (80, 80, 80), (11, 28, 4, 4))
        pygame.draw.rect(surf, (80, 80, 80), (17, 28, 4, 4))
        return surf

    return {
        "student": person((100, 180, 255)),
        "teacher": person((255, 180, 80)),
        "staff": person((160, 120, 220)),
        "rector": person((220, 60, 60)),
    }


def load_sprites(path: str) -> Dict[str, pygame.Surface]:
    if os.path.exists(path):
        try:
            image = pygame.image.load(path).convert_alpha()
            frames = [image.subsurface(pygame.Rect(i * TILE, 0, TILE, TILE)) for i in range(image.get_width() // TILE)]
            data = {"student": frames[0], "teacher": frames[1], "staff": frames[2]}
            data["rector"] = frames[3] if len(frames) > 3 else gen_sprites()["rector"]
            return data
        except Exception as exc:
            print("[WARN] sprites.png falló:", exc)
    print("[INFO] Usando sprites generados.")
    return gen_sprites()


TILES = load_tiles("tileset.png")
SPRITES = load_sprites("sprites.png")

# ---------------------------------------------------------------------------
# Cámara del mapa
# ---------------------------------------------------------------------------


class Camera:
    def __init__(self, width: int, height: int, tile: int) -> None:
        self.width = width
        self.height = height
        self.tile = tile
        self.x = MAP_W // 2 - (width // tile) // 2
        self.y = MAP_H // 2 - (height // tile) // 2

    def clamp(self, max_w: int, max_h: int) -> None:
        tiles_x = self.width // self.tile
        tiles_y = self.height // self.tile
        self.x = max(0, min(max_w - tiles_x, self.x))
        self.y = max(0, min(max_h - tiles_y, self.y))

    def world_to_screen(self, wx: float, wy: float) -> Tuple[int, int]:
        return int((wx - self.x) * self.tile), int((wy - self.y) * self.tile)


cam = Camera(SCREEN_W - PANEL_WIDTH, SCREEN_H, TILE)

# ---------------------------------------------------------------------------
# Mapa exterior
# ---------------------------------------------------------------------------


C_GRASS, C_ROAD, C_BUILD, C_ENTR, C_PARK, C_PATH, C_PARKING, C_SPORT, C_FLAG = range(9)

world: List[List[int]] = [[C_GRASS for _ in range(MAP_W)] for _ in range(MAP_H)]


def fill(x: int, y: int, w: int, h: int, tile_id: int) -> None:
    for yy in range(y, y + h):
        if 0 <= yy < MAP_H:
            for xx in range(x, x + w):
                if 0 <= xx < MAP_W:
                    world[yy][xx] = tile_id


def label(surface: pygame.Surface, font: pygame.font.Font, tile_x: int, tile_y: int, text: str) -> None:
    sx = (tile_x - cam.x) * TILE
    sy = (tile_y - cam.y) * TILE
    if -120 <= sx <= surface.get_width() + 120 and -40 <= sy <= surface.get_height() + 40:
        surface.blit(font.render(text, True, (20, 20, 20)), (sx - 50, sy - 10))


fill(0, MAP_H // 2 - 3, MAP_W, 6, C_ROAD)
fill(MAP_W // 3 - 2, 0, 4, MAP_H, C_ROAD)
fill(2 * MAP_W // 3 - 2, 0, 4, MAP_H, C_ROAD)

fill(40, 18, 48, 14, C_PARKING)
fill(150, 18, 48, 14, C_PARKING)
fill(165, 110, 45, 28, C_PARKING)
fill(6, 108, 40, 30, C_SPORT)
fill(50, 108, 40, 30, C_SPORT)

fill(6, 74, 70, 28, C_PARK)
fill(130, 72, 70, 30, C_PARK)
fill(104, 38, 12, 8, C_PATH)
world[40][110] = C_FLAG
for x in range(12, MAP_W - 12, 2):
    fill(x, 48, 1, 3, C_PATH)
fill(18, 60, 70, 3, C_PATH)
fill(120, 60, 70, 3, C_PATH)

# ---------------------------------------------------------------------------
# Edificios e interiores
# ---------------------------------------------------------------------------


BUILDINGS = [
    ("F", "Edificio Fundadores", (24, 54, 18, 12), [(33, 66)], "aulas"),
    ("B", "Biblioteca", (46, 52, 18, 12), [(55, 64)], "biblioteca"),
    ("C", "Edificio C (Ingenierías)", (88, 50, 24, 14), [(100, 64)], "aulas"),
    ("D", "Edificio D (Laboratorios)", (68, 40, 16, 12), [(76, 52)], "laboratorios"),
    ("E", "Edificio E", (30, 34, 14, 10), [(37, 46)], "oficinas"),
    ("G", "Edificio G", (58, 28, 12, 10), [(64, 38)], "oficinas"),
    ("H", "Edificio H", (118, 48, 14, 12), [(125, 60)], "aulas"),
    ("DP", "Edificio de Posgrados", (78, 66, 12, 10), [(84, 76)], "oficinas"),
    ("CCU", "Centro de Convivencia Universitaria", (132, 50, 16, 12), [(140, 62)], "cafeteria"),
    ("ADM", "Administración / Rectoría", (152, 52, 16, 12), [(160, 64)], "oficinas"),
    ("OXO", "OXXO", (172, 58, 10, 8), [(177, 66)], "oxxo"),
]

BUILD_RECTS: Dict[str, pygame.Rect] = {}
ENTRANCES: Dict[Tuple[int, int], str] = {}
KIND_BY: Dict[str, str] = {}
ROOF_BY_KIND = {
    "aulas": T_ROOF_DEF,
    "oficinas": T_ROOF_DEF,
    "cafeteria": T_ROOF_CAFE,
    "biblioteca": T_ROOF_LIB,
    "laboratorios": T_ROOF_LAB,
    "oxxo": T_ROOF_OXXO,
}

for code, full, (x, y, w, h), entries, kind in BUILDINGS:
    fill(x, y, w, h, C_BUILD)
    for ex, ey in entries:
        world[ey][ex] = C_ENTR
        ENTRANCES[(ex, ey)] = code
    BUILD_RECTS[code] = pygame.Rect(x, y, w, h)
    KIND_BY[code] = kind


class Interior:
    def __init__(self, code: str, kind: str, full_name: str) -> None:
        self.code = code
        self.kind = kind
        self.full_name = full_name
        if kind == "oxxo":
            self.w, self.h = 24, 16
            self.floor = T_FLOOR
        elif kind == "cafeteria":
            self.w, self.h = 34, 22
            self.floor = T_FLOOR
        else:
            self.w, self.h = 32, 20
            self.floor = T_WOOD
        self.grid: List[List[int]] = [[0 for _ in range(self.w)] for _ in range(self.h)]
        for x in range(self.w):
            self.grid[0][x] = 1
            self.grid[self.h - 1][x] = 1
        for y in range(self.h):
            self.grid[y][0] = 1
            self.grid[y][self.w - 1] = 1
        self.exit_pos = (self.w // 2, self.h - 2)
        self.grid[self.h - 1][self.w // 2] = 2
        self.points: List[Tuple[int, int]] = []
        if kind in {"aulas", "laboratorios", "biblioteca"}:
            for y in range(1, self.h - 1):
                self.grid[y][self.w // 2] = 0
            for y0 in (3, 9, 15):
                for rx, ry, rw, rh in (
                    (2, y0, self.w // 2 - 3, 4),
                    (self.w // 2 + 2, y0, self.w // 2 - 4, 4),
                ):
                    for yy in range(ry, ry + rh):
                        for xx in range(rx, rx + rw):
                            self.grid[yy][xx] = 3
                    self.points.append((rx + rw // 2, ry + rh // 2))
        elif kind == "cafeteria":
            for cx in (8, 16, 24, 30):
                for cy in (6, 12, 16):
                    self.points.append((cx, cy))
            for x in range(3, self.w - 3):
                self.grid[3][x] = 1
            self.grid[3][self.w // 2] = 0
        elif kind == "oxxo":
            for x in range(4, self.w - 4, 4):
                for y in range(3, self.h - 3):
                    self.grid[y][x] = 6
            self.points = [(self.w // 2, self.h // 2)]
        else:
            self.points = [(self.w // 2, 3), (self.w // 2, self.h // 2)]


INTERIORS: Dict[str, Interior] = {code: Interior(code, KIND_BY[code], full) for code, full, *_ in BUILDINGS}

# ---------------------------------------------------------------------------
# Control horario
# ---------------------------------------------------------------------------


class DayClock:
    def __init__(self, start_min: int = START_MIN, end_min: int = END_MIN, min_per_sec: int = MIN_PER_SEC) -> None:
        self.start = start_min
        self.end = end_min
        self.current = start_min
        self.rate = min_per_sec

    def tick(self, dt_seconds: float) -> None:
        self.current += int(self.rate * dt_seconds)
        if self.current > self.end:
            self.current = self.start

    def hhmm(self) -> str:
        hour = self.current // 60
        minute = self.current % 60
        return f"{hour:02d}:{minute:02d}"


CLOCK = DayClock()

# ---------------------------------------------------------------------------
# Action board y compositor (heredado del prototipo)
# ---------------------------------------------------------------------------


DEFAULT_ACTIONS = [
    {"rol": "teacher", "dest": "F", "prio": 80, "nota": "Clase matutina"},
    {"rol": "student", "dest": "B", "prio": 60, "nota": "Estudiar"},
    {"rol": "staff", "dest": "ADM", "prio": 60, "nota": "Trámite"},
    {"rol": "rector", "dest": "ADM", "prio": 90, "nota": "Dirección"},
]


class ActionBoard:
    def __init__(self, path: str = "acciones.json") -> None:
        self.path = path
        self.actions: List[Dict[str, object]] = []
        self.load_or_create()

    def load_or_create(self) -> None:
        if not os.path.exists(self.path):
            with open(self.path, "w", encoding="utf-8") as handler:
                json.dump(DEFAULT_ACTIONS, handler, ensure_ascii=False, indent=2)
            self.actions = list(DEFAULT_ACTIONS)
            return
        try:
            with open(self.path, "r", encoding="utf-8") as handler:
                data = json.load(handler)
            if isinstance(data, dict):
                data = data.get("items", [])
            if not isinstance(data, list):
                data = []
            self.actions = list(data)
        except Exception as exc:
            print("[WARN] acciones.json inválido, usando por defecto:", exc)
            self.actions = list(DEFAULT_ACTIONS)

    def reload(self) -> None:
        self.load_or_create()

    def append_and_save(self, item: Dict[str, object]) -> None:
        self.actions.append(item)
        try:
            data: List[Dict[str, object]] = []
            if os.path.exists(self.path):
                with open(self.path, "r", encoding="utf-8") as handler:
                    try:
                        existing = json.load(handler)
                        if isinstance(existing, list):
                            data = list(existing)
                        elif isinstance(existing, dict) and isinstance(existing.get("items"), list):
                            data = list(existing["items"])
                    except Exception:
                        data = []
            data.append(item)
            with open(self.path, "w", encoding="utf-8") as handler:
                json.dump(data, handler, ensure_ascii=False, indent=2)
        except Exception as exc:
            print("[WARN] No pude guardar acciones.json:", exc)


BOARD = ActionBoard()

# ---------------------------------------------------------------------------
# Control del aula (para interiores académicos)
# ---------------------------------------------------------------------------


class ClassroomController:
    def __init__(self, interior: Interior) -> None:
        self.interior = interior
        self.enabled = interior.kind in {"aulas", "laboratorios"}
        self.state = "idle"
        self.index = 0
        self.next_tick = 0
        self.roster: List[Entity] = []
        self.teacher: Optional[Entity] = None
        self.banner_text = ""
        self.banner_until = 0

    def ensure_population(self, code: str, locals_cache: Dict[str, List[Entity]]) -> None:
        if code not in locals_cache:
            local_entities: List[Entity] = []
            local_entities.append(
                Entity(
                    self.interior.w // 2,
                    random.randint(3, self.interior.h - 4),
                    "teacher",
                    name="Profe " + random.choice(["García", "López", "Martínez", "Hernández"]),
                )
            )
            for _ in range(random.randint(10, 16)):
                local_entities.append(
                    Entity(
                        self.interior.w // 2,
                        random.randint(3, self.interior.h - 4),
                        "student",
                    )
                )
            locals_cache[code] = local_entities
        local = locals_cache[code]
        self.teacher = next((entity for entity in local if entity.role == "teacher"), None)
        self.roster = [entity for entity in local if entity.role == "student"]

    def start_roll_if_possible(self, locals_cache: Dict[str, List[Entity]], code: str) -> None:
        if not self.enabled:
            return
        self.ensure_population(code, locals_cache)
        if self.teacher and self.roster and self.state == "idle":
            self.state = "roll"
            self.index = 0
            self.next_tick = pygame.time.get_ticks() + 600
            self.banner("Pase de lista iniciado")

    def update(self, locals_cache: Dict[str, List[Entity]], code: str) -> None:
        if not self.enabled:
            return
        now = pygame.time.get_ticks()
        if self.state == "roll":
            if now >= self.next_tick and self.index < len(self.roster):
                student = self.roster[self.index]
                if self.teacher:
                    self.teacher.say(f"{student.name.split()[0]}?", 600)
                student.say("¡Presente!", 900)
                self.index += 1
                self.next_tick = now + 800
            if self.index >= len(self.roster):
                self.state = "teaching"
                self.banner("Clase en curso")

    def banner(self, text: str, duration_ms: int = 1500) -> None:
        self.banner_text = text
        self.banner_until = pygame.time.get_ticks() + duration_ms

    def draw_banner(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        if self.enabled and self.banner_until > pygame.time.get_ticks():
            rendered = font.render(self.banner_text, True, (255, 255, 120))
            surface.blit(rendered, (surface.get_width() // 2 - rendered.get_width() // 2, 40))


# ---------------------------------------------------------------------------
# Utilidades para la simulación de NPCs
# ---------------------------------------------------------------------------


class PriorityQueue:
    def __init__(self) -> None:
        self._data: List[Tuple[float, Tuple[int, int], Dict[str, object], float, int, int]] = []

    def __len__(self) -> int:
        return len(self._data)

    def push(self, item: Tuple[float, Tuple[int, int], Dict[str, object], float, int, int]) -> None:
        self._data.append(item)
        index = len(self._data) - 1
        while index > 0:
            parent = (index - 1) // 2
            if self._data[parent][0] <= self._data[index][0]:
                break
            self._data[parent], self._data[index] = self._data[index], self._data[parent]
            index = parent

    def pop(self) -> Optional[Tuple[float, Tuple[int, int], Dict[str, object], float, int, int]]:
        if not self._data:
            return None
        top = self._data[0]
        last = self._data.pop()
        if self._data:
            self._data[0] = last
            index = 0
            size = len(self._data)
            while True:
                left = 2 * index + 1
                right = left + 1
                smallest = index
                if left < size and self._data[left][0] < self._data[smallest][0]:
                    smallest = left
                if right < size and self._data[right][0] < self._data[smallest][0]:
                    smallest = right
                if smallest == index:
                    break
                self._data[index], self._data[smallest] = self._data[smallest], self._data[index]
                index = smallest
        return top


def nearest_entry_of(code: str) -> Tuple[int, int]:
    for (tx, ty), building_code in ENTRANCES.items():
        if building_code == code:
            return (tx, ty)
    rect = BUILD_RECTS[code]
    return (rect.centerx, rect.centery)


def sport_random_target() -> Tuple[int, int]:
    rects = [pygame.Rect(6, 108, 40, 30), pygame.Rect(50, 108, 40, 30)]
    chosen = random.choice(rects)
    return (
        random.randint(chosen.left + 2, chosen.right - 3),
        random.randint(chosen.top + 2, chosen.bottom - 3),
    )

ROLES = ["student", "teacher", "staff", "rector"]
FIRST_NAMES = [
    "Ana",
    "Luis",
    "María",
    "Carlos",
    "Sofía",
    "Diego",
    "Paola",
    "Jorge",
    "Valeria",
    "Andrés",
    "Daniel",
    "Fernanda",
    "Miguel",
    "Elena",
    "Ricardo",
    "Lucía",
    "Iván",
    "Camila",
    "Raúl",
    "Jimena",
]


def rand_name() -> str:
    return random.choice(FIRST_NAMES) + " " + random.choice(["P.", "R.", "G.", "S.", "L.", "H."])


class Entity:
    _autoid = 0

    def __init__(self, tx: int, ty: int, role: str = "student", name: Optional[str] = None) -> None:
        Entity._autoid += 1
        self.id = Entity._autoid
        self.tx = tx
        self.ty = ty
        self.role = role
        self.name = name or rand_name()
        self.tick = 0
        self.speed_tick = random.randint(6, 10)
        self.last_anim = 0
        self.current_frame = 0
        self.target: Optional[Tuple[int, int]] = None
        self.motivation = random.uniform(0.45, 0.9)
        self.tasks = random.randint(0, 5) if role in {"student", "teacher"} else 0
        self.exams = random.randint(0, 1) if role == "student" else 0
        self.projects = random.randint(0, 2) if role == "student" else 0
        self.say_text: Optional[str] = None
        self.say_until = 0
        self.plan = self._make_plan()
        self.plan_index = 0

    def say(self, text: str, duration_ms: int = 900) -> None:
        self.say_text = text
        self.say_until = pygame.time.get_ticks() + duration_ms

    def _make_plan(self) -> List[Tuple[int, str]]:
        t = START_MIN
        if self.role == "student":
            return [
                (t, "F"),
                (t + 120, "B"),
                (t + 300, "CCU"),
                (t + 420, "C"),
                (t + 600, "DEP"),
                (END_MIN - 20, "SALIDA"),
            ]
        if self.role == "teacher":
            return [
                (t, "D"),
                (t + 90, "C"),
                (t + 240, "CCU"),
                (t + 360, "B"),
                (END_MIN - 30, "SALIDA"),
            ]
        if self.role == "staff":
            return [
                (t, "ADM"),
                (t + 240, "CCU"),
                (t + 320, "ADM"),
                (END_MIN - 30, "SALIDA"),
            ]
        return [
            (t, "ADM"),
            (t + 150, "E"),
            (t + 300, "ADM"),
            (t + 420, "B"),
            (END_MIN - 30, "SALIDA"),
        ]

    def sprite(self) -> pygame.Surface:
        return SPRITES.get(self.role, SPRITES["student"])

    def _anim(self, now: int) -> None:
        if now - self.last_anim >= 1000 // ANIM_FPS:
            self.current_frame = (self.current_frame + 1) % 4
            self.last_anim = now

    def _campus_can(self, x: int, y: int) -> bool:
        return 0 <= x < MAP_W and 0 <= y < MAP_H and world[y][x] in {
            C_GRASS,
            C_PATH,
            C_ROAD,
            C_PARK,
            C_PARKING,
            C_SPORT,
            C_ENTR,
            C_FLAG,
        }

    def _step(self, tx: int, ty: int) -> None:
        if (self.tx, self.ty) == (tx, ty):
            return
        dx = 1 if tx > self.tx else -1 if tx < self.tx else 0
        dy = 1 if ty > self.ty else -1 if ty < self.ty else 0
        for ox, oy in ((dx, 0), (0, dy), (dx, dy)):
            nx, ny = self.tx + ox, self.ty + oy
            if self._campus_can(nx, ny):
                self.tx, self.ty = nx, ny
                return

    def _set_target_for_destination(self, dest_code: str) -> None:
        if dest_code == "DEP":
            self.target = sport_random_target()
            return
        if dest_code == "SALIDA":
            self.target = (MAP_W // 3 + 2, MAP_H // 2 + 10)
            return
        tx, ty = nearest_entry_of(dest_code)
        self.target = (tx, ty)

    def _matches_targeting(self, action: Dict[str, object]) -> float:
        to_name = action.get("to_name")
        to_id = action.get("to_id")
        if to_id is not None and to_id == self.id:
            return 1.3
        if to_name and str(to_name).strip() == self.name.strip():
            return 1.25
        role = action.get("rol")
        if not role:
            return 1.0
        role = str(role)
        if role == self.role:
            return 1.1
        if self.role in {"teacher", "rector"} and role in {"teacher", "rector", "staff"}:
            return 0.6
        if self.role == "student" and role in {"student", "teacher"}:
            return 0.5
        return 0.4

    def _accept_prob(self, affinity: float, distance_tiles: int, priority: int) -> float:
        dist_penalty = max(0.85 - 0.01 * min(distance_tiles, 30), 0.6)
        priority_boost = 0.8 + 0.004 * max(0, min(100, priority))
        noise = random.uniform(0.95, 1.05)
        probability = self.motivation * (0.6 + 0.4 * affinity) * dist_penalty * priority_boost * noise
        return max(0.05, min(0.98, probability))

    def _apply_task_effect(self, action: Dict[str, object]) -> None:
        if action.get("tipo", "accion") != "tarea":
            return
        category = str(action.get("categoria", "tarea")).lower()
        if category == "tarea":
            self.tasks += 1
        elif category == "examen" and self.role == "student":
            self.exams += 1
        elif category == "proyecto" and self.role == "student":
            self.projects += 1

    def _choose_from_board(self) -> None:
        if not BOARD.actions:
            return
        queue = PriorityQueue()
        for action in BOARD.actions:
            priority = int(action.get("prio", 50))
            destination = action.get("dest")
            affinity = self._matches_targeting(action)
            if destination == "DEP":
                tx, ty = sport_random_target()
            elif destination in BUILD_RECTS or destination in {"SALIDA", None}:
                if destination is None:
                    tx, ty = self.tx, self.ty
                elif destination == "SALIDA":
                    tx, ty = (MAP_W // 3 + 2, MAP_H // 2 + 10)
                else:
                    tx, ty = nearest_entry_of(destination)
            else:
                continue
            distance = abs(tx - self.tx) + abs(ty - self.ty)
            utility = (100 - priority) + 0.35 * distance - 25 * affinity + random.uniform(-2, 2)
            queue.push((utility, (tx, ty), action, affinity, distance, priority))
        if len(queue) == 0:
            return
        result = queue.pop()
        if result is None:
            return
        _, (tx, ty), action, affinity, distance, priority = result
        if random.random() < self._accept_prob(affinity, distance, priority):
            if action.get("tipo", "accion") == "tarea":
                self._apply_task_effect(action)
                self.say("Tomé tarea", 850)
            self.target = (tx, ty)

    def update(self, now: int, scene: "BaseScene") -> None:
        self._anim(now)
        self.tick += 1
        if self.tick < self.speed_tick:
            return
        self.tick = 0
        if isinstance(scene, CampusScene):
            self.motivation = clamp(self.motivation + random.uniform(-0.02, 0.02), 0.3, 0.98)
            current = CLOCK.current
            while self.plan_index < len(self.plan) and current >= self.plan[self.plan_index][0]:
                _, dest = self.plan[self.plan_index]
                if random.random() < self.motivation:
                    self._set_target_for_destination(dest)
                else:
                    self.target = (random.randint(10, 200), random.randint(30, 90))
                self.plan_index += 1
            if self.target is None or random.random() < 0.25:
                self._choose_from_board()
            if self.target is None:
                self._set_target_for_destination(random.choice(["F", "C", "H", "B", "CCU", "ADM"]))
            if self.target:
                self._step(self.target[0], self.target[1])
        else:
            interior = scene.interior
            width, height = interior.w, interior.h
            if self.target is None:
                self.target = random.choice(interior.points) if interior.points else (width // 2, height // 2)
            tx, ty = self.target
            dx = 1 if tx > self.tx else -1 if tx < self.tx else 0
            dy = 1 if ty > self.ty else -1 if ty < self.ty else 0
            for ox, oy in ((dx, 0), (0, dy), (dx, dy)):
                nx, ny = self.tx + ox, self.ty + oy
                if 0 <= nx < width and 0 <= ny < height and interior.grid[ny][nx] in {0, 2, 3, 6}:
                    self.tx, self.ty = nx, ny
                    break


class BaseScene:
    pass


class CampusScene(BaseScene):
    pass


class InteriorScene(BaseScene):
    def __init__(self, code: str) -> None:
        self.code = code
        self.interior = INTERIORS[code]
        self.class_ctrl = ClassroomController(self.interior)

# ---------------------------------------------------------------------------
# Población del campus y cachés por interior
# ---------------------------------------------------------------------------


NPCS: List[Entity] = []
for _ in range(50):
    x, y = random.randint(6, MAP_W - 6), random.randint(20, MAP_H - 6)
    while world[y][x] == C_BUILD:
        x, y = random.randint(6, MAP_W - 6), random.randint(20, MAP_H - 6)
    NPCS.append(Entity(x, y, "student"))
for _ in range(8):
    x, y = random.randint(6, MAP_W - 6), random.randint(20, MAP_H - 6)
    while world[y][x] == C_BUILD:
        x, y = random.randint(6, MAP_W - 6), random.randint(20, MAP_H - 6)
    NPCS.append(Entity(x, y, "teacher"))
for _ in range(8):
    x, y = random.randint(6, MAP_W - 6), random.randint(20, MAP_H - 6)
    while world[y][x] == C_BUILD:
        x, y = random.randint(6, MAP_W - 6), random.randint(20, MAP_H - 6)
    NPCS.append(Entity(x, y, "staff"))
for _ in range(2):
    ex, ey = nearest_entry_of("ADM")
    NPCS.append(Entity(ex, ey, "rector"))

locals_cache: Dict[str, List[Entity]] = {}

# ---------------------------------------------------------------------------
# Estado del jugador controlable y acciones personalizadas
# ---------------------------------------------------------------------------


PLAYER_CHECKLIST = [
    "Comió",
    "Hizo ejercicio",
    "Impartió clase",
    "Asistió a clases",
    "Se bañó",
    "Atendió asesorías",
    "Atendió proveedores",
    "Habló con amigos",
    "Estudió",
]


def default_needs() -> Dict[str, float]:
    return {
        "Hambre": 68.0,
        "Energía": 70.0,
        "Progreso Académico": 52.0,
        "Vida Social": 45.0,
    }


def default_checklist() -> Dict[str, bool]:
    return {item: False for item in PLAYER_CHECKLIST}


@dataclass
class PlayerState:
    definition: CharacterDefinition
    campus_pos: pygame.Vector2
    needs: Dict[str, float] = field(default_factory=default_needs)
    checklist: Dict[str, bool] = field(default_factory=default_checklist)
    log: List[str] = field(default_factory=list)
    interior_code: Optional[str] = None
    interior_pos: pygame.Vector2 = field(default_factory=lambda: pygame.Vector2())

    def reset(self) -> None:
        self.needs = default_needs()
        self.checklist = default_checklist()
        self.campus_pos.update(*nearest_entry_of("F"))
        self.log.clear()
        append_log(self.log, f"{self.definition.name} comienza un nuevo día en la UP.")
        self.interior_code = None
        self.interior_pos.update(0, 0)


# Mapa de roles del simulador previo a roles del prototipo para sprites
ROLE_TO_SPRITE = {
    "alumno": "student",
    "maestro": "teacher",
    "empleado": "staff",
    "rector": "rector",
}


def append_log(log: List[str], entry: str) -> None:
    log.append(entry)
    if len(log) > MAX_LOG_ENTRIES:
        del log[0]


def apply_decay(player: PlayerState, dt: float) -> None:
    for need, rate in DECAY_RATES.items():
        player.needs[need] = clamp(player.needs[need] - rate * dt)


def adjust_needs(
    player: PlayerState,
    *,
    hambre: float = 0.0,
    energia: float = 0.0,
    progreso: float = 0.0,
    social: float = 0.0,
) -> None:
    player.needs["Hambre"] = clamp(player.needs["Hambre"] + hambre)
    player.needs["Energía"] = clamp(player.needs["Energía"] + energia)
    player.needs["Progreso Académico"] = clamp(player.needs["Progreso Académico"] + progreso)
    player.needs["Vida Social"] = clamp(player.needs["Vida Social"] + social)


def make_action(
    key: str,
    label: str,
    *,
    hunger: float = 0.0,
    energy: float = 0.0,
    progress: float = 0.0,
    social: float = 0.0,
    checklist: Iterable[str] = (),
    message: Optional[str] = None,
) -> Action:
    def handler(player: PlayerState) -> str:
        adjust_needs(
            player,
            hambre=hunger,
            energia=energy,
            progreso=progress,
            social=social,
        )
        for item in checklist:
            if item in player.checklist:
                player.checklist[item] = True
        text = message or label
        append_log(player.log, text)
        return text

    return Action(key.upper(), label, handler)


def role_sensitive(
    default: Sequence[Action],
    *,
    maestro: Sequence[Action] = (),
    alumno: Sequence[Action] = (),
    empleado: Sequence[Action] = (),
    rector: Sequence[Action] = (),
) -> Callable[[PlayerState], Sequence[Action]]:
    def factory(player: PlayerState) -> Sequence[Action]:
        role = player.definition.role
        specific: Sequence[Action]
        if role == "maestro":
            specific = maestro
        elif role == "alumno":
            specific = alumno
        elif role == "empleado":
            specific = empleado
        elif role == "rector":
            specific = rector
        else:
            specific = ()
        return tuple(default) + tuple(specific)

    return factory


# Acciones por edificio (adaptadas de la versión previa)
BUILDING_ACTIONS: Dict[str, Callable[[PlayerState], Sequence[Action]]] = {
    "F": role_sensitive(
        (
            make_action(
                "L",
                "Tomar clase magistral",
                progress=18,
                checklist=["Asistió a clases"],
                message="Participó en una clase clave en Fundadores.",
            ),
        ),
        maestro=(
            make_action(
                "D",
                "Dar clase de Fundamentos",
                progress=15,
                checklist=["Impartió clase"],
                message="Impartió una clase memorable en Fundadores.",
            ),
        ),
    ),
    "B": role_sensitive(
        (
            make_action(
                "E",
                "Estudiar en silencio",
                progress=24,
                checklist=["Estudió"],
                message="Aprovechó el silencio de la biblioteca.",
            ),
        ),
        rector=(
            make_action(
                "R",
                "Revisar proyectos de investigación",
                progress=14,
                message="Supervisó proyectos estratégicos de investigación.",
            ),
        ),
    ),
    "C": role_sensitive(
        (
            make_action(
                "P",
                "Prototipar proyecto",
                progress=16,
                checklist=["Estudió"],
                message="Construyó prototipos en los laboratorios de ingenierías.",
            ),
        ),
        alumno=(
            make_action(
                "L",
                "Laboratorio de electrónica",
                progress=14,
                checklist=["Estudió"],
                message="Realizó prácticas en el laboratorio.",
            ),
        ),
        maestro=(
            make_action(
                "C",
                "Clase de circuitos",
                progress=12,
                checklist=["Impartió clase"],
                message="Dirigió un laboratorio de circuitos.",
            ),
        ),
    ),
    "D": role_sensitive(
        (
            make_action(
                "I",
                "Investigar en laboratorio",
                progress=20,
                checklist=["Estudió"],
                message="Experimentó con nuevos prototipos en el laboratorio D.",
            ),
        ),
        maestro=(
            make_action(
                "A",
                "Asesoría técnica",
                progress=10,
                checklist=["Atendió asesorías"],
                message="Orientó a estudiantes durante la práctica.",
            ),
        ),
    ),
    "CCU": role_sensitive(
        (
            make_action(
                "C",
                "Comer en la cafetería",
                hunger=28,
                energy=8,
                checklist=["Comió"],
                message="Compartió comida en el CCU.",
            ),
            make_action(
                "S",
                "Socializar",
                social=16,
                checklist=["Habló con amigos"],
                message="Platicó con amigos en el CCU.",
            ),
        ),
        empleado=(
            make_action(
                "P",
                "Revisar proveedores",
                progress=10,
                checklist=["Atendió proveedores"],
                message="Coordinó entregas con los proveedores del CCU.",
            ),
        ),
    ),
    "ADM": role_sensitive(
        (
            make_action(
                "T",
                "Trámite administrativo",
                progress=12,
                checklist=["Atendió asesorías"],
                message="Completó trámites y ayudó a estudiantes.",
            ),
        ),
        empleado=(
            make_action(
                "G",
                "Gestionar agenda",
                progress=14,
                message="Organizó agenda de citas en administración.",
            ),
        ),
        rector=(
            make_action(
                "R",
                "Reunión estratégica",
                progress=16,
                social=8,
                message="Supervisó el funcionamiento general de la UP.",
            ),
        ),
    ),
    "OXO": role_sensitive(
        (
            make_action(
                "B",
                "Comprar snacks",
                hunger=16,
                energy=6,
                checklist=["Comió"],
                message="Compró snacks en el OXXO del campus.",
            ),
        ),
        empleado=(
            make_action(
                "I",
                "Inventario rápido",
                progress=12,
                checklist=["Atendió proveedores"],
                message="Verificó existencias y proveedores en el OXXO.",
            ),
        ),
    ),
}

# Actividades contextuales del exterior
SPORT_ACTION = make_action(
    "J",
    "Entrenar en canchas",
    hunger=-8,
    energy=-18,
    social=15,
    checklist=["Hizo ejercicio", "Habló con amigos"],
    message="Participó en un juego intenso en la zona deportiva.",
)

MUSIC_ACTION = make_action(
    "M",
    "Practicar con la rondalla",
    progress=12,
    social=14,
    checklist=["Habló con amigos"],
    message="Compartió melodías en el área de música.",
)
# ---------------------------------------------------------------------------
# Renderizado del campus y HUD
# ---------------------------------------------------------------------------


def draw_campus(surface: pygame.Surface, font: pygame.font.Font) -> None:
    tiles_x = (surface.get_width() // TILE) + 2
    tiles_y = (surface.get_height() // TILE) + 2
    for y in range(cam.y, cam.y + tiles_y):
        if not (0 <= y < MAP_H):
            continue
        for x in range(cam.x, cam.x + tiles_x):
            if not (0 <= x < MAP_W):
                continue
            sx, sy = cam.world_to_screen(x, y)
            cell = world[y][x]
            idx = {
                C_GRASS: T_GRASS,
                C_ROAD: T_ROAD,
                C_PATH: T_PATH,
                C_PARK: T_PARK,
                C_PARKING: T_PARKING,
                C_SPORT: T_SPORT,
                C_FLAG: T_FLAG,
                C_ENTR: T_ENTR,
            }.get(cell)
            if cell == C_BUILD:
                idx = T_ROOF_DEF
                for code, rect in BUILD_RECTS.items():
                    if rect.collidepoint(x, y):
                        idx = ROOF_BY_KIND[KIND_BY[code]]
                        break
            if idx is not None and idx < len(TILES):
                surface.blit(TILES[idx], (sx, sy))

    for code, rect in BUILD_RECTS.items():
        if (cam.x - 5) < rect.right and rect.left < (cam.x + surface.get_width() // TILE + 5) and (
            cam.y - 5
        ) < rect.bottom and rect.top < (cam.y + surface.get_height() // TILE + 5):
            full = next(full for c, full, *_ in BUILDINGS if c == code)
            label(surface, font, rect.centerx, rect.top - 1, full)
    label(surface, font, 110, 36, "Plaza de Banderas")
    label(surface, font, BUILD_RECTS["OXO"].centerx, BUILD_RECTS["OXO"].top - 1, "OXXO")
    label(surface, font, 26, 122, "Zona Deportiva")


def draw_interior(surface: pygame.Surface, intr: Interior) -> None:
    tiles_x = (surface.get_width() // TILE) + 2
    tiles_y = (surface.get_height() // TILE) + 2
    for y in range(cam.y, cam.y + tiles_y):
        for x in range(cam.x, cam.x + tiles_x):
            sx, sy = cam.world_to_screen(x, y)
            if 0 <= y < intr.h and 0 <= x < intr.w:
                value = intr.grid[y][x]
                idx = intr.floor if value == 0 else T_WALL if value == 1 else T_ENTR if value == 2 else T_WOOD if value == 3 else T_SHELF
                surface.blit(TILES[idx], (sx, sy))
            else:
                surface.fill((25, 25, 25), pygame.Rect(sx, sy, TILE, TILE))


def draw_entity(surface: pygame.Surface, entity: Entity) -> None:
    sx, sy = cam.world_to_screen(entity.tx, entity.ty)
    surface.blit(entity.sprite(), (sx, sy))


def draw_nameplate(surface: pygame.Surface, entity: Entity, font: pygame.font.Font) -> None:
    sx, sy = cam.world_to_screen(entity.tx, entity.ty)
    name = entity.name
    info = None
    if entity.role in {"student", "teacher"}:
        if entity.role == "student":
            info = f"T:{entity.tasks} Ex:{entity.exams} Proy:{entity.projects}"
        else:
            info = f"Tareas:{entity.tasks}"
    if name:
        rendered = font.render(name, True, (255, 255, 255))
        bg = pygame.Surface((rendered.get_width() + 6, rendered.get_height() + 4), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 160))
        surface.blit(bg, (sx - (bg.get_width() // 2) + 16, sy - 18))
        surface.blit(rendered, (sx - (bg.get_width() // 2) + 19, sy - 16))
    if info:
        rendered = font.render(info, True, (200, 255, 200))
        bg = pygame.Surface((rendered.get_width() + 6, rendered.get_height() + 4), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 140))
        surface.blit(bg, (sx - (bg.get_width() // 2) + 16, sy - 2))
        surface.blit(rendered, (sx - (bg.get_width() // 2) + 19, sy))


def draw_say(surface: pygame.Surface, entity: Entity, font: pygame.font.Font) -> None:
    if entity.say_text and pygame.time.get_ticks() < entity.say_until:
        sx, sy = cam.world_to_screen(entity.tx, entity.ty)
        rendered = font.render(entity.say_text, True, (20, 20, 20))
        bubble = pygame.Surface((rendered.get_width() + 10, rendered.get_height() + 8), pygame.SRCALPHA)
        bubble.fill((255, 255, 255, 220))
        surface.blit(bubble, (sx - (bubble.get_width() // 2) + 16, sy - 34))
        surface.blit(rendered, (sx - (bubble.get_width() // 2) + 21, sy - 32))
    elif entity.say_text and pygame.time.get_ticks() >= entity.say_until:
        entity.say_text = None


def draw_player_avatar(surface: pygame.Surface, player: PlayerState) -> None:
    sprite_key = ROLE_TO_SPRITE.get(player.definition.role, "student")
    sprite = SPRITES[sprite_key]
    if player.interior_code:
        sx, sy = cam.world_to_screen(player.interior_pos.x, player.interior_pos.y)
    else:
        sx, sy = cam.world_to_screen(player.campus_pos.x, player.campus_pos.y)
    surface.blit(sprite, (sx, sy))


def draw_player_panel(surface: pygame.Surface, player: PlayerState, font: pygame.font.Font, small: pygame.font.Font) -> None:
    panel_rect = pygame.Rect(surface.get_width() - PANEL_WIDTH, 0, PANEL_WIDTH, surface.get_height())
    pygame.draw.rect(surface, PANEL_BG, panel_rect)
    pygame.draw.rect(surface, PANEL_BORDER, panel_rect, width=2)

    draw_text = lambda txt, pos, color: surface.blit(font.render(txt, True, color), pos)
    draw_small = lambda txt, pos, color: surface.blit(small.render(txt, True, color), pos)

    draw_text(player.definition.name, (panel_rect.x + PANEL_PADDING, PANEL_PADDING), PANEL_TEXT)
    draw_small(player.definition.role.capitalize(), (panel_rect.x + PANEL_PADDING, PANEL_PADDING + 34), PANEL_MUTED)

    bar_x = panel_rect.x + PANEL_PADDING
    bar_y = PANEL_PADDING + 80
    bar_width = PANEL_WIDTH - PANEL_PADDING * 2
    bar_height = 18

    for label_text, value in player.needs.items():
        pygame.draw.rect(
            surface,
            PANEL_BORDER,
            (bar_x - 2, bar_y - 2, bar_width + 4, bar_height + 4),
            border_radius=6,
        )
        fill_width = int(bar_width * (value / 100))
        pygame.draw.rect(surface, PANEL_ACCENT, (bar_x, bar_y, fill_width, bar_height), border_radius=6)
        draw_small(f"{label_text}: {int(value)}%", (bar_x, bar_y - 22), PANEL_TEXT)
        bar_y += 48

    draw_text("Pendientes", (panel_rect.x + PANEL_PADDING, bar_y + 6), PANEL_TEXT)
    checklist_y = bar_y + 38
    for item, done in player.checklist.items():
        color = (122, 210, 120) if done else PANEL_MUTED
        status = "✔" if done else "•"
        draw_small(f"{status} {item}", (panel_rect.x + PANEL_PADDING + 4, checklist_y), color)
        checklist_y += 22

    draw_text("Bitácora", (panel_rect.x + PANEL_PADDING, surface.get_height() - 220), PANEL_TEXT)
    log_y = surface.get_height() - 186
    for entry in player.log[-MAX_LOG_ENTRIES:]:
        draw_small(f"• {entry}", (panel_rect.x + PANEL_PADDING + 4, log_y), PANEL_MUTED)
        log_y += 22

    draw_small("WASD/Flechas: mover", (panel_rect.x + PANEL_PADDING, surface.get_height() - 60), PANEL_MUTED)
    draw_small("E: entrar/salir | F2: tareas", (panel_rect.x + PANEL_PADDING, surface.get_height() - 32), PANEL_MUTED)


# ---------------------------------------------------------------------------
# Ayudas adicionales de UI
# ---------------------------------------------------------------------------


def wrap_text(text: str, max_chars: int) -> List[str]:
    words = text.split()
    lines: List[str] = []
    current: List[str] = []
    count = 0
    for word in words:
        extra = 1 if current else 0
        if count + len(word) + extra > max_chars:
            lines.append(" ".join(current))
            current = [word]
            count = len(word)
        else:
            current.append(word)
            count += len(word) + extra
    if current:
        lines.append(" ".join(current))
    return lines


def draw_action_overlay(
    surface: pygame.Surface,
    title: str,
    description: str,
    actions: Sequence[Action],
    font: pygame.font.Font,
    small: pygame.font.Font,
) -> None:
    if not actions:
        return
    overlay_rect = pygame.Rect(40, surface.get_height() - 200, surface.get_width() - PANEL_WIDTH - 80, 150)
    pygame.draw.rect(surface, (27, 38, 59, 230), overlay_rect, border_radius=16)
    pygame.draw.rect(surface, (255, 255, 255, 40), overlay_rect, width=2, border_radius=16)
    surface.blit(font.render(title, True, (230, 235, 255)), (overlay_rect.x + 20, overlay_rect.y + 16))
    surface.blit(small.render(description, True, (200, 210, 240)), (overlay_rect.x + 20, overlay_rect.y + 54))
    action_y = overlay_rect.y + 86
    for action in actions:
        surface.blit(small.render(f"[{action.key}] {action.label}", True, (173, 209, 255)), (overlay_rect.x + 20, action_y))
        action_y += 24


def draw_hover_tooltip(surface: pygame.Surface, building_code: str, font: pygame.font.Font) -> None:
    building = next((b for b in BUILDINGS if b[0] == building_code), None)
    if not building:
        return
    _, name, *_rest = building
    tooltip_rect = pygame.Rect(pygame.mouse.get_pos(), (0, 0))
    tooltip_rect.inflate_ip(220, 90)
    tooltip_rect.x += 18
    tooltip_rect.y += 18
    pygame.draw.rect(surface, (42, 56, 82), tooltip_rect, border_radius=12)
    pygame.draw.rect(surface, (220, 230, 255), tooltip_rect, width=2, border_radius=12)
    surface.blit(font.render(name, True, (255, 255, 255)), (tooltip_rect.x + 12, tooltip_rect.y + 8))
    description = BUILDING_DESCRIPTIONS.get(building_code, "")
    for i, line in enumerate(wrap_text(description, 28)):
        surface.blit(pygame.font.Font(None, 22).render(line, True, (206, 216, 244)), (tooltip_rect.x + 12, tooltip_rect.y + 44 + i * 22))


BUILDING_DESCRIPTIONS = {
    "F": "Aulas principales para clases y asesorías.",
    "B": "Centro de estudio, investigación y consulta.",
    "C": "Laboratorios y talleres de ingeniería.",
    "D": "Laboratorios especializados para proyectos.",
    "E": "Oficinas administrativas y académicas.",
    "G": "Oficinas de coordinación y servicios.",
    "H": "Más aulas para cursos y asesorías.",
    "DP": "Edificio dedicado a posgrados y reuniones.",
    "CCU": "Cafetería y zona social del campus.",
    "ADM": "Rectoría y gestiones administrativas.",
    "OXO": "Tienda rápida dentro del campus.",
}
# ---------------------------------------------------------------------------
# Lógica del jugador
# ---------------------------------------------------------------------------


PLAYER_SPEED_TILES = 4.2
INTERIOR_SPEED = 3.5


def campus_passable(x: float, y: float) -> bool:
    ix, iy = int(round(x)), int(round(y))
    if not (0 <= ix < MAP_W and 0 <= iy < MAP_H):
        return False
    return world[iy][ix] in {C_GRASS, C_PATH, C_ROAD, C_PARK, C_PARKING, C_SPORT, C_ENTR, C_FLAG}


def move_on_campus(player: PlayerState, dt: float, pressed: Sequence[bool]) -> None:
    direction = pygame.Vector2(0, 0)
    if pressed[pygame.K_w] or pressed[pygame.K_UP]:
        direction.y -= 1
    if pressed[pygame.K_s] or pressed[pygame.K_DOWN]:
        direction.y += 1
    if pressed[pygame.K_a] or pressed[pygame.K_LEFT]:
        direction.x -= 1
    if pressed[pygame.K_d] or pressed[pygame.K_RIGHT]:
        direction.x += 1
    if direction.length_squared() == 0:
        return
    direction = direction.normalize() * PLAYER_SPEED_TILES * dt
    new_x = player.campus_pos.x + direction.x
    new_y = player.campus_pos.y + direction.y
    if campus_passable(new_x, player.campus_pos.y):
        player.campus_pos.x = new_x
    if campus_passable(player.campus_pos.x, new_y):
        player.campus_pos.y = new_y


def move_in_interior(player: PlayerState, interior: Interior, dt: float, pressed: Sequence[bool]) -> None:
    direction = pygame.Vector2(0, 0)
    if pressed[pygame.K_w] or pressed[pygame.K_UP]:
        direction.y -= 1
    if pressed[pygame.K_s] or pressed[pygame.K_DOWN]:
        direction.y += 1
    if pressed[pygame.K_a] or pressed[pygame.K_LEFT]:
        direction.x -= 1
    if pressed[pygame.K_d] or pressed[pygame.K_RIGHT]:
        direction.x += 1
    if direction.length_squared() == 0:
        return
    direction = direction.normalize() * INTERIOR_SPEED * dt
    new_x = player.interior_pos.x + direction.x
    new_y = player.interior_pos.y + direction.y

    def can_walk(px: float, py: float) -> bool:
        ix, iy = int(round(px)), int(round(py))
        if not (0 <= ix < interior.w and 0 <= iy < interior.h):
            return False
        return interior.grid[iy][ix] in {0, 2, 3, 6}

    if can_walk(new_x, player.interior_pos.y):
        player.interior_pos.x = new_x
    if can_walk(player.interior_pos.x, new_y):
        player.interior_pos.y = new_y


def actions_for_building(player: PlayerState, code: str) -> Sequence[Action]:
    factory = BUILDING_ACTIONS.get(code)
    return factory(player) if factory else ()


def exterior_actions(player: PlayerState) -> Sequence[Action]:
    ix, iy = int(round(player.campus_pos.x)), int(round(player.campus_pos.y))
    cell = world[iy][ix] if 0 <= ix < MAP_W and 0 <= iy < MAP_H else None
    actions: List[Action] = []
    if cell == C_SPORT:
        actions.append(SPORT_ACTION)
    if 100 <= ix <= 132 and 230 <= iy <= 260:
        actions.append(MUSIC_ACTION)
    return actions


def execute_action(player: PlayerState, action: Action) -> None:
    text = action.handler(player)
    append_log(player.log, text)


def enter_building(player: PlayerState, code: str) -> None:
    player.interior_code = code
    interior = INTERIORS[code]
    player.interior_pos.update(interior.w // 2, interior.h - 4)
    append_log(player.log, f"Entró a {INTERIORS[code].full_name}.")


def leave_building(player: PlayerState) -> None:
    if player.interior_code is None:
        return
    code = player.interior_code
    player.interior_code = None
    entrance = nearest_entry_of(code)
    player.campus_pos.update(*entrance)
    append_log(player.log, f"Salió de {INTERIORS[code].full_name}.")


# ---------------------------------------------------------------------------
# Interfaz de selección de personaje
# ---------------------------------------------------------------------------


def character_selection(screen: pygame.Surface, clock: pygame.time.Clock, font: pygame.font.Font, small: pygame.font.Font) -> Optional[PlayerState]:
    index = 0
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    return None
                if event.key in (pygame.K_DOWN, pygame.K_s):
                    index = (index + 1) % len(CHARACTER_DEFS)
                if event.key in (pygame.K_UP, pygame.K_w):
                    index = (index - 1) % len(CHARACTER_DEFS)
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    definition = CHARACTER_DEFS[index]
                    player = PlayerState(definition, pygame.Vector2(*nearest_entry_of("F")))
                    player.reset()
                    return player

        screen.fill((22, 30, 46))
        title = font.render("Proyecto TACHI", True, (242, 246, 255))
        screen.blit(title, (screen.get_width() // 2 - title.get_width() // 2, 120))
        subtitle = small.render("Selecciona un personaje", True, (188, 198, 220))
        screen.blit(subtitle, (screen.get_width() // 2 - subtitle.get_width() // 2, 170))

        base_y = 240
        for idx, character in enumerate(CHARACTER_DEFS):
            color = (240, 244, 255) if idx == index else (150, 160, 190)
            marker = "→" if idx == index else "  "
            entry = small.render(f"{marker} {character.name} ({character.role})", True, color)
            screen.blit(entry, (screen.get_width() // 2 - 220, base_y + idx * 40))

        footer = small.render("ENTER: iniciar   ESC: salir", True, (140, 150, 180))
        screen.blit(footer, (screen.get_width() // 2 - footer.get_width() // 2, 520))
        pygame.display.flip()
        clock.tick(TARGET_FPS)


# ---------------------------------------------------------------------------
# Compositor de acciones (UI F2) - se reutiliza del prototipo
# ---------------------------------------------------------------------------


class TextField:
    def __init__(self, rect: pygame.Rect) -> None:
        self.rect = pygame.Rect(rect)
        self.text = ""
        self.active = False
        self.caret_visible = True
        self.last_caret = 0

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.active = self.rect.collidepoint(event.pos)
        if not self.active:
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_TAB):
                pass
            else:
                ch = event.unicode
                if ch and ch.isprintable() and len(self.text) < 64:
                    self.text += ch

    def update(self) -> None:
        now = pygame.time.get_ticks()
        if now - self.last_caret > 500:
            self.caret_visible = not self.caret_visible
            self.last_caret = now

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        pygame.draw.rect(surface, (255, 255, 255), self.rect, border_radius=8)
        pygame.draw.rect(surface, (40, 40, 60) if self.active else (120, 120, 140), self.rect, 2, border_radius=8)
        padding = 10
        rendered = font.render(self.text, True, (20, 20, 25))
        surface.blit(rendered, (self.rect.x + padding, self.rect.y + (self.rect.height - rendered.get_height()) // 2))
        if self.active and self.caret_visible:
            caret_x = self.rect.x + padding + rendered.get_width() + 2
            pygame.draw.line(surface, (20, 20, 25), (caret_x, self.rect.y + 8), (caret_x, self.rect.bottom - 8), 2)


class ActionComposer:
    def __init__(self, font: pygame.font.Font, small: pygame.font.Font) -> None:
        w, h = 520, 460
        self.panel = pygame.Rect((SCREEN_W - PANEL_WIDTH) // 2 - w // 2, SCREEN_H // 2 - h // 2, w, h)
        x0 = self.panel.x + 22
        y0 = self.panel.y + 64
        fw, fh, gap = 220, 34, 56
        self.font = font
        self.small = small
        self.fields = [
            {"key": "rol", "label": "Rol", "hint": "student | teacher | staff | rector", "tf": TextField(pygame.Rect(x0, y0 + 0 * gap, fw, fh))},
            {
                "key": "dest",
                "label": "Destino",
                "hint": "F,B,C,D,E,G,H,DP,CCU,ADM,OXO,DEP,SALIDA",
                "tf": TextField(pygame.Rect(x0 + fw + 30, y0 + 0 * gap, fw, fh)),
            },
            {
                "key": "prio",
                "label": "Prioridad",
                "hint": "0..100 (mayor = más importante)",
                "tf": TextField(pygame.Rect(x0, y0 + 1 * gap, fw, fh)),
            },
            {
                "key": "tipo",
                "label": "Tipo",
                "hint": "accion | tarea",
                "tf": TextField(pygame.Rect(x0 + fw + 30, y0 + 1 * gap, fw, fh)),
            },
            {
                "key": "categoria",
                "label": "Categoría",
                "hint": "(si tipo=tarea) tarea | examen | proyecto",
                "tf": TextField(pygame.Rect(x0, y0 + 2 * gap, fw, fh)),
            },
            {
                "key": "to_name",
                "label": "Para (nombre exacto)",
                "hint": "p.ej. Ana P.",
                "tf": TextField(pygame.Rect(x0 + fw + 30, y0 + 2 * gap, fw, fh)),
            },
            {
                "key": "to_id",
                "label": "Para (ID)",
                "hint": "número interno del agente (opcional)",
                "tf": TextField(pygame.Rect(x0, y0 + 3 * gap, fw, fh)),
            },
            {"key": "nota", "label": "Nota", "hint": "descripción breve", "tf": TextField(pygame.Rect(x0 + fw + 30, y0 + 3 * gap, fw, fh))},
        ]
        self.index = 0
        self.fields[self.index]["tf"].active = True
        self.btn_save = pygame.Rect(self.panel.right - 150, self.panel.bottom - 56, 130, 36)
        self.btn_close = pygame.Rect(self.panel.right - 300, self.panel.bottom - 56, 130, 36)
        self.message = ""
        self.request_close = False

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for field in self.fields:
                field["tf"].handle_event(event)
            if self.btn_save.collidepoint(event.pos):
                self.save_action()
                return "saved"
            if self.btn_close.collidepoint(event.pos):
                self.request_close = True
                return "close"
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:
                self.fields[self.index]["tf"].active = False
                self.index = (self.index + 1) % len(self.fields)
                self.fields[self.index]["tf"].active = True
                return None
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.save_action()
                return "saved"
            for field in self.fields:
                field["tf"].handle_event(event)
        return None

    def update(self) -> None:
        for field in self.fields:
            field["tf"].update()

    def parse_item(self) -> Dict[str, object]:
        data: Dict[str, object] = {}
        for field in self.fields:
            key = field["key"]
            value = field["tf"].text.strip()
            if value:
                data[key] = value
        if "prio" in data:
            try:
                data["prio"] = int(data["prio"])  # type: ignore[assignment]
            except Exception:
                data["prio"] = 50
        if "to_id" in data:
            try:
                data["to_id"] = int(data["to_id"])  # type: ignore[assignment]
            except Exception:
                data.pop("to_id", None)
        data.setdefault("tipo", "accion")
        if data["tipo"] == "tarea":
            data.setdefault("categoria", "tarea")
        data.setdefault("dest", "B")
        data.setdefault("nota", "(sin nota)")
        return data

    def save_action(self) -> None:
        item = self.parse_item()
        BOARD.append_and_save(item)
        self.message = f"Guardada ✔ (Total: {len(BOARD.actions)})"

    def clear(self) -> None:
        for field in self.fields:
            field["tf"].text = ""
        self.message = ""

    def draw(self, surface: pygame.Surface) -> None:
        dim = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 150))
        surface.blit(dim, (0, 0))
        pygame.draw.rect(surface, (245, 246, 250), self.panel, border_radius=14)
        pygame.draw.rect(surface, (40, 40, 60), self.panel, 2, border_radius=14)
        surface.blit(self.font.render("Agregar acción / tarea", True, (35, 35, 45)), (self.panel.x + 20, self.panel.y + 16))
        for field in self.fields:
            tf = field["tf"]
            surface.blit(self.small.render(field["label"], True, (70, 70, 90)), (tf.rect.x, tf.rect.y - 18))
            tf.draw(surface, self.small)
            surface.blit(self.small.render(field["hint"], True, (125, 125, 145)), (tf.rect.x, tf.rect.bottom + 4))
        pygame.draw.rect(surface, (60, 140, 80), self.btn_save, border_radius=8)
        pygame.draw.rect(surface, (30, 80, 50), self.btn_save, 2, border_radius=8)
        surface.blit(self.font.render("Guardar", True, (255, 255, 255)), (self.btn_save.x + 28, self.btn_save.y + 6))
        pygame.draw.rect(surface, (180, 70, 70), self.btn_close, border_radius=8)
        pygame.draw.rect(surface, (120, 40, 40), self.btn_close, 2, border_radius=8)
        surface.blit(self.font.render("Cerrar (F2)", True, (255, 255, 255)), (self.btn_close.x + 20, self.btn_close.y + 6))
        if self.message:
            surface.blit(self.small.render(self.message, True, (25, 120, 55)), (self.panel.x + 20, self.panel.bottom - 92))
# ---------------------------------------------------------------------------
# Bucle principal
# ---------------------------------------------------------------------------


def update_camera(player: PlayerState, scene: BaseScene) -> None:
    half_w = (SCREEN_W - PANEL_WIDTH) // TILE // 2
    half_h = SCREEN_H // TILE // 2
    if isinstance(scene, InteriorScene):
        cam.x = int(player.interior_pos.x) - half_w
        cam.y = int(player.interior_pos.y) - half_h
        cam.clamp(scene.interior.w, scene.interior.h)
    else:
        cam.x = int(player.campus_pos.x) - half_w
        cam.y = int(player.campus_pos.y) - half_h
        cam.clamp(MAP_W, MAP_H)


def available_building_code_at(player: PlayerState) -> Optional[str]:
    if player.interior_code:
        return player.interior_code
    ix, iy = int(round(player.campus_pos.x)), int(round(player.campus_pos.y))
    for code, rect in BUILD_RECTS.items():
        if rect.collidepoint(ix, iy):
            return code
    for (ex, ey), code in ENTRANCES.items():
        if abs(ex - ix) <= 1 and abs(ey - iy) <= 1:
            return code
    return None


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Proyecto TACHI - Campus Simulator")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 32)
    small = pygame.font.Font(None, 24)
    big = pygame.font.Font(None, 28)

    player: Optional[PlayerState] = None
    scene: BaseScene = CampusScene()
    composer: Optional[ActionComposer] = None
    show_help = False

    while True:
        if player is None:
            selection = character_selection(screen, clock, font, small)
            if selection is None:
                break
            player = selection
            scene = CampusScene()
            continue

        dt = clock.tick(TARGET_FPS) / 1000.0
        CLOCK.tick(dt)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if composer:
                result = composer.handle_event(event)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_F2:
                    composer = None
                    continue
                if event.type == pygame.KEYDOWN and event.key == pygame.K_F6:
                    composer.clear()
                    continue
                if result == "close":
                    composer = None
                    continue
                if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    continue

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if isinstance(scene, InteriorScene):
                        leave_building(player)
                        scene = CampusScene()
                    else:
                        player = None
                    break
                if event.key == pygame.K_F5:
                    BOARD.reload()
                if event.key == pygame.K_F1:
                    show_help = not show_help
                if event.key == pygame.K_F2:
                    composer = ActionComposer(big, small)
                if event.key == pygame.K_e:
                    if isinstance(scene, InteriorScene):
                        leave_building(player)
                        scene = CampusScene()
                    else:
                        ix, iy = int(round(player.campus_pos.x)), int(round(player.campus_pos.y))
                        best: Optional[Tuple[int, int, str]] = None
                        best_dist = 3
                        for (ex, ey), code in ENTRANCES.items():
                            dist = abs(ex - ix) + abs(ey - iy)
                            if dist < best_dist:
                                best = (ex, ey, code)
                                best_dist = dist
                        if best:
                            enter_building(player, best[2])
                            scene = InteriorScene(best[2])
                            scene.class_ctrl.start_roll_if_possible(locals_cache, scene.code)
                            update_camera(player, scene)
                if event.key not in (pygame.K_ESCAPE, pygame.K_F1, pygame.K_F2, pygame.K_F5, pygame.K_F6, pygame.K_e):
                    code = available_building_code_at(player)
                    actions: Sequence[Action] = ()
                    description = ""
                    title = ""
                    if player.interior_code and isinstance(scene, InteriorScene):
                        actions = actions_for_building(player, scene.code)
                        title = INTERIORS[scene.code].full_name
                        description = BUILDING_DESCRIPTIONS.get(scene.code, "")
                    elif not player.interior_code:
                        exterior = exterior_actions(player)
                        actions = exterior
                        title = "Actividades al aire libre"
                        description = "Zonas deportivas y artísticas del campus."
                    pressed_key = pygame.key.name(event.key).upper()
                    for action in actions:
                        if action.key == pressed_key:
                            execute_action(player, action)
                            break

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not isinstance(scene, InteriorScene):
                mx, my = event.pos
                if mx < SCREEN_W - PANEL_WIDTH:
                    tx = cam.x + mx // TILE
                    ty = cam.y + my // TILE
                    if (tx, ty) in ENTRANCES:
                        enter_building(player, ENTRANCES[(tx, ty)])
                        scene = InteriorScene(ENTRANCES[(tx, ty)])
                        scene.class_ctrl.start_roll_if_possible(locals_cache, scene.code)
                        update_camera(player, scene)

        if player is None:
            continue

        pressed = pygame.key.get_pressed()
        if isinstance(scene, InteriorScene):
            move_in_interior(player, scene.interior, dt, pressed)
            scene.class_ctrl.ensure_population(scene.code, locals_cache)
            scene.class_ctrl.update(locals_cache, scene.code)
            if scene.code in locals_cache:
                for entity in locals_cache[scene.code]:
                    entity.update(pygame.time.get_ticks(), scene)
        else:
            move_on_campus(player, dt, pressed)
            for entity in NPCS:
                entity.update(pygame.time.get_ticks(), scene)

        apply_decay(player, dt)
        update_camera(player, scene)

        map_surface = pygame.Surface((SCREEN_W - PANEL_WIDTH, SCREEN_H))
        map_surface.fill((0, 0, 0))
        if isinstance(scene, InteriorScene):
            draw_interior(map_surface, scene.interior)
            code = scene.code
            if code in locals_cache:
                for entity in locals_cache[code]:
                    draw_entity(map_surface, entity)
                    draw_nameplate(map_surface, entity, small)
                    draw_say(map_surface, entity, small)
            scene.class_ctrl.draw_banner(map_surface, font)
            surface_title = small.render(f"{scene.interior.full_name} — E para salir", True, (255, 255, 255))
            map_surface.blit(surface_title, (10, 10))
        else:
            draw_campus(map_surface, small)
            for entity in NPCS:
                draw_entity(map_surface, entity)
            for entity in NPCS:
                draw_nameplate(map_surface, entity, small)
                draw_say(map_surface, entity, small)
            hud_text = small.render(
                "WASD/Flechas: mover | E: entrar/salir | Click: entrar | F2: compositor | F5: recargar JSON | F1: ayuda",
                True,
                (255, 255, 255),
            )
            map_surface.blit(hud_text, (10, 10))
            if show_help:
                help_lines = [
                    "F2 abre el compositor de acciones/tareas en vivo.",
                    "Los agentes aceptan tareas según motivación, afinidad y distancia.",
                    "F5 recarga acciones.json, F6 limpia el formulario del compositor.",
                ]
                y = SCREEN_H - 24 * len(help_lines) - 12
                for line in help_lines:
                    map_surface.blit(small.render(line, True, (235, 235, 235)), (10, y))
                    y += 24

        draw_player_avatar(map_surface, player)

        screen.blit(map_surface, (0, 0))
        draw_player_panel(screen, player, font, small)

        if SHOW_CLOCK:
            clock_text = font.render(f"Hora: {CLOCK.hhmm()}", True, (255, 255, 120))
            screen.blit(clock_text, (SCREEN_W - PANEL_WIDTH - clock_text.get_width() - 20, 16))

        overlay_actions: Sequence[Action] = ()
        overlay_title = ""
        overlay_description = ""
        if isinstance(scene, InteriorScene):
            overlay_actions = actions_for_building(player, scene.code)
            overlay_title = scene.interior.full_name
            overlay_description = BUILDING_DESCRIPTIONS.get(scene.code, "")
        else:
            ext_actions = exterior_actions(player)
            if ext_actions:
                overlay_actions = ext_actions
                overlay_title = "Actividades al aire libre"
                overlay_description = "Canchas deportivas y espacio de música."
        if overlay_actions:
            draw_action_overlay(screen, overlay_title, overlay_description, overlay_actions, big, small)

        if not player.interior_code:
            hover_code = available_building_code_at(player)
            if hover_code:
                draw_hover_tooltip(screen, hover_code, small)

        if composer:
            composer.update()
            composer.draw(screen)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pygame.quit()
        print("Simulador cerrado por el usuario.")
