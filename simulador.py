"""Simulador interactivo del campus UP para el Proyecto TACHI usando Pygame."""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Sequence, Tuple

import pygame

# --- Constantes de configuración ---
WIDTH, HEIGHT = 1280, 720
PANEL_WIDTH = 320
MAP_WIDTH = WIDTH - PANEL_WIDTH
FPS = 60
BACKGROUND_COLOR = (236, 240, 243)
PANEL_COLOR = (28, 38, 64)
PANEL_TEXT = (235, 240, 255)
PANEL_MUTED = (180, 190, 210)
ACCENT_COLOR = (142, 202, 230)
BORDER_COLOR = (42, 48, 74)
PLAYER_RADIUS = 16
PLAYER_SPEED = 220.0  # pixeles por segundo
DECAY_RATES = {
    "Hambre": 6.0,
    "Energía": 4.5,
    "Progreso Académico": 2.0,
    "Vida Social": 1.5,
}
MAX_LOG_ENTRIES = 8


# --- Utilidades ---
def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def append_log(log: List[str], entry: str) -> None:
    log.append(entry)
    if len(log) > MAX_LOG_ENTRIES:
        del log[0]


# --- Modelos de dominio ---
@dataclass
class Character:
    name: str
    role: str
    color: Tuple[int, int, int]
    needs: Dict[str, float] = field(default_factory=lambda: {
        "Hambre": 68.0,
        "Energía": 70.0,
        "Progreso Académico": 52.0,
        "Vida Social": 45.0,
    })
    checklist: Dict[str, bool] = field(default_factory=lambda: {
        "Comió": False,
        "Hizo ejercicio": False,
        "Impartió clase": False,
        "Asistió a clases": False,
        "Se bañó": False,
        "Atendió asesorías": False,
        "Atendió proveedores": False,
        "Habló con amigos": False,
        "Estudió": False,
    })
    position: pygame.Vector2 = field(default_factory=lambda: pygame.Vector2(MAP_WIDTH / 2, HEIGHT / 2))
    log: List[str] = field(default_factory=list)

    def reset(self) -> None:
        self.needs = {k: 70.0 for k in self.needs}
        self.checklist = {k: False for k in self.checklist}
        self.position.update(MAP_WIDTH / 2, HEIGHT / 2)
        self.log.clear()
        append_log(self.log, f"{self.name} está listo para un día productivo en la UP.")


@dataclass
class Action:
    key: str
    label: str
    handler: Callable[[Character], str]


@dataclass
class Building:
    name: str
    rect: pygame.Rect
    color: Tuple[int, int, int]
    highlight: Tuple[int, int, int]
    action_factory: Callable[[Character], Sequence[Action]]
    description: str

    def actions_for(self, character: Character) -> Sequence[Action]:
        return self.action_factory(character)


# --- Definición de personajes ---
CHARACTERS: Sequence[Character] = (
    Character("Rector Antonio", "rector", (255, 89, 94)),
    Character("Maestra Martha", "maestro", (255, 179, 71)),
    Character("Profe Tachiquín", "maestro", (255, 111, 145)),
    Character("Maestro Isaac", "maestro", (255, 200, 87)),
    Character("Administradora Fabiola", "empleado", (163, 196, 243)),
    Character("Alumno Fundadores", "alumno", (96, 189, 104)),
    Character("Alumna Música", "alumno", (130, 170, 255)),
)


# --- Definición de edificios y acciones ---
def adjust_needs(
    character: Character,
    *,
    hambre: float = 0.0,
    energia: float = 0.0,
    progreso: float = 0.0,
    social: float = 0.0,
) -> None:
    character.needs["Hambre"] = clamp(character.needs["Hambre"] + hambre)
    character.needs["Energía"] = clamp(character.needs["Energía"] + energia)
    character.needs["Progreso Académico"] = clamp(character.needs["Progreso Académico"] + progreso)
    character.needs["Vida Social"] = clamp(character.needs["Vida Social"] + social)


def make_action(
    key: str,
    label: str,
    *,
    hunger: float = 0.0,
    energy: float = 0.0,
    progress: float = 0.0,
    social: float = 0.0,
    checklist: Iterable[str] = (),
    message: str | None = None,
) -> Action:
    def handler(character: Character) -> str:
        adjust_needs(
            character,
            hambre=hunger,
            energia=energy,
            progreso=progress,
            social=social,
        )
        for item in checklist:
            if item in character.checklist:
                character.checklist[item] = True
        return message or label

    return Action(key.upper(), label, handler)


def rector_only(action: Action) -> Callable[[Character], Sequence[Action]]:
    def _factory(character: Character) -> Sequence[Action]:
        if character.role == "rector":
            return (action,)
        return ()

    return _factory


def role_sensitive(default: Sequence[Action], *, maestro: Sequence[Action] = (), alumno: Sequence[Action] = (), empleado: Sequence[Action] = (), rector: Sequence[Action] = ()) -> Callable[[Character], Sequence[Action]]:
    def _factory(character: Character) -> Sequence[Action]:
        role = character.role
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

    return _factory


BUILDINGS: Sequence[Building] = (
    Building(
        "Starbucks",
        pygame.Rect(80, 80, 140, 110),
        (229, 179, 120),
        (255, 203, 160),
        role_sensitive(
            (
                make_action(
                    "E",
                    "Pedir latte",
                    hunger=18,
                    energy=15,
                    checklist=["Comió"],
                    message="Disfrutó un latte cremoso en Starbucks.",
                ),
            ),
            maestro=(
                make_action(
                    "R",
                    "Preparar clase con café",
                    progress=12,
                    checklist=["Impartió clase"],
                    message="Planificó una clase inspiradora con aroma a café.",
                ),
            ),
            alumno=(
                make_action(
                    "T",
                    "Resolver tareas con caffeine",
                    progress=16,
                    checklist=["Estudió"],
                    message="Avanzó en tareas mientras tomaba café.",
                ),
            ),
        ),
        "Refresca tu energía con café y charla casual.",
    ),
    Building(
        "Caffenio",
        pygame.Rect(260, 60, 160, 120),
        (229, 200, 144),
        (252, 224, 180),
        role_sensitive(
            (
                make_action(
                    "E",
                    "Desayunar chilaquiles",
                    hunger=28,
                    energy=10,
                    checklist=["Comió"],
                    message="Repuso fuerzas con chilaquiles en Caffenio.",
                ),
                make_action(
                    "S",
                    "Platicar con compañeros",
                    social=14,
                    checklist=["Habló con amigos"],
                    message="Tuvo una charla animada con compañeros.",
                ),
            ),
        ),
        "El punto favorito para socializar y desayunar.",
    ),
    Building(
        "Fundadores",
        pygame.Rect(460, 50, 220, 150),
        (167, 201, 87),
        (195, 225, 121),
        role_sensitive(
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
        "Edificio central de clases y asesorías.",
    ),
    Building(
        "Smart Center",
        pygame.Rect(740, 70, 210, 130),
        (120, 177, 169),
        (154, 204, 199),
        role_sensitive(
            (
                make_action(
                    "A",
                    "Solicitar asesoría",
                    progress=14,
                    social=6,
                    checklist=["Atendió asesorías"],
                    message="Recibió asesoría en el Smart Center.",
                ),
            ),
            empleado=(
                make_action(
                    "P",
                    "Revisar proveedores",
                    progress=10,
                    checklist=["Atendió proveedores"],
                    message="Atendió a proveedores tecnológicos.",
                ),
            ),
        ),
        "Soluciones tecnológicas y asesorías académicas.",
    ),
    Building(
        "Biblioteca",
        pygame.Rect(980, 60, 180, 150),
        (146, 168, 209),
        (175, 195, 232),
        role_sensitive(
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
        "Centro de estudio, investigación y consulta.",
    ),
    Building(
        "Canchas",
        pygame.Rect(100, 260, 260, 160),
        (92, 153, 124),
        (122, 184, 153),
        role_sensitive(
            (
                make_action(
                    "J",
                    "Jugar partido",
                    hunger=-8,
                    energy=-18,
                    social=15,
                    checklist=["Hizo ejercicio", "Habló con amigos"],
                    message="Participó en un juego intenso en las canchas.",
                ),
            ),
            alumno=(
                make_action(
                    "E",
                    "Entrenar para torneo",
                    energy=-22,
                    social=12,
                    checklist=["Hizo ejercicio"],
                    message="Se preparó para el torneo universitario.",
                ),
            ),
        ),
        "Espacios deportivos al aire libre.",
    ),
    Building(
        "Gimnasio",
        pygame.Rect(400, 250, 190, 150),
        (78, 115, 146),
        (108, 147, 180),
        role_sensitive(
            (
                make_action(
                    "G",
                    "Sesión de gimnasio",
                    hunger=-12,
                    energy=-20,
                    social=6,
                    checklist=["Hizo ejercicio"],
                    message="Cumplió su rutina en el gimnasio.",
                ),
            ),
        ),
        "Entrenamiento físico y bienestar.",
    ),
    Building(
        "Música",
        pygame.Rect(630, 240, 200, 160),
        (222, 120, 138),
        (240, 150, 165),
        role_sensitive(
            (
                make_action(
                    "P",
                    "Practicar instrumento",
                    progress=12,
                    social=10,
                    checklist=["Habló con amigos"],
                    message="Compartió melodías con la rondalla universitaria.",
                ),
            ),
            alumno=(
                make_action(
                    "R",
                    "Rehearsal con la rondalla",
                    progress=10,
                    social=16,
                    checklist=["Habló con amigos"],
                    message="Ensayó con la rondalla universitaria.",
                ),
            ),
        ),
        "Salas de ensayo y presentaciones artísticas.",
    ),
    Building(
        "Capilla",
        pygame.Rect(870, 250, 160, 150),
        (203, 153, 126),
        (225, 178, 155),
        role_sensitive(
            (
                make_action(
                    "M",
                    "Momento de reflexión",
                    progress=8,
                    energy=8,
                    social=2,
                    message="Tomó un momento de paz en la capilla.",
                ),
            ),
        ),
        "Espacio de silencio y contemplación.",
    ),
    Building(
        "Oxxo",
        pygame.Rect(1080, 260, 150, 150),
        (241, 209, 102),
        (252, 225, 150),
        role_sensitive(
            (
                make_action(
                    "B",
                    "Comprar snacks",
                    hunger=16,
                    energy=6,
                    checklist=["Comió"],
                    message="Compró snacks en el Oxxo del campus.",
                ),
            ),
            empleado=(
                make_action(
                    "P",
                    "Revisar inventario",
                    progress=12,
                    checklist=["Atendió proveedores"],
                    message="Verificó el inventario y proveedores del Oxxo.",
                ),
            ),
        ),
        "Tienda de conveniencia dentro del campus.",
    ),
    Building(
        "Administración",
        pygame.Rect(140, 470, 220, 170),
        (183, 132, 167),
        (205, 162, 190),
        role_sensitive(
            (
                make_action(
                    "T",
                    "Trámites estudiantiles",
                    progress=6,
                    social=4,
                    checklist=["Atendió proveedores"],
                    message="Completó trámites administrativos.",
                ),
            ),
            rector=(
                make_action(
                    "I",
                    "Inspeccionar facultades",
                    progress=14,
                    social=8,
                    checklist=["Atendió proveedores"],
                    message="Supervisó que las facultades funcionen correctamente.",
                ),
            ),
            empleado=(
                make_action(
                    "R",
                    "Revisar reportes",
                    progress=16,
                    message="Procesó reportes financieros.",
                ),
            ),
        ),
        "Corazón administrativo del campus.",
    ),
    Building(
        "Posgrados",
        pygame.Rect(390, 470, 200, 170),
        (139, 180, 216),
        (169, 204, 232),
        role_sensitive(
            (
                make_action(
                    "S",
                    "Seminario avanzado",
                    progress=20,
                    checklist=["Estudió"],
                    message="Participó en un seminario de posgrados.",
                ),
            ),
            maestro=(
                make_action(
                    "A",
                    "Asesorar tesis",
                    progress=18,
                    checklist=["Atendió asesorías"],
                    message="Guió a estudiantes de posgrado.",
                ),
            ),
        ),
        "Edificio de investigación y formación avanzada.",
    ),
    Building(
        "Ingenierías",
        pygame.Rect(620, 470, 240, 170),
        (124, 148, 194),
        (156, 180, 220),
        role_sensitive(
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
        "Laboratorios de innovación y tecnología.",
    ),
    Building(
        "Residencias",
        pygame.Rect(900, 470, 220, 170),
        (212, 175, 144),
        (231, 202, 178),
        role_sensitive(
            (
                make_action(
                    "R",
                    "Descansar",
                    hunger=-6,
                    energy=26,
                    message="Tomó un descanso reparador en residencias.",
                ),
                make_action(
                    "B",
                    "Bañarse",
                    energy=6,
                    checklist=["Se bañó"],
                    message="Se refrescó con una ducha rápida.",
                ),
            ),
            alumno=(
                make_action(
                    "T",
                    "Tarea nocturna",
                    progress=12,
                    checklist=["Estudió"],
                    message="Avanzó en tarea nocturna antes de dormir.",
                ),
            ),
        ),
        "Zona de descanso para estudiantes y visitantes.",
    ),
)


# --- Pantallas y UI ---
def draw_text(surface: pygame.Surface, text: str, position: Tuple[int, int], font: pygame.font.Font, color: Tuple[int, int, int]) -> pygame.Rect:
    rendered = font.render(text, True, color)
    rect = rendered.get_rect(topleft=position)
    surface.blit(rendered, rect)
    return rect


def draw_panel(surface: pygame.Surface, character: Character, font: pygame.font.Font, small_font: pygame.font.Font) -> None:
    panel_rect = pygame.Rect(MAP_WIDTH, 0, PANEL_WIDTH, HEIGHT)
    pygame.draw.rect(surface, PANEL_COLOR, panel_rect)

    draw_text(surface, character.name, (MAP_WIDTH + 20, 20), font, PANEL_TEXT)
    draw_text(surface, character.role.capitalize(), (MAP_WIDTH + 20, 60), small_font, PANEL_MUTED)

    bar_x = MAP_WIDTH + 20
    bar_y = 110
    bar_width = PANEL_WIDTH - 40
    bar_height = 18

    for label, value in character.needs.items():
        pygame.draw.rect(surface, BORDER_COLOR, (bar_x - 2, bar_y - 2, bar_width + 4, bar_height + 4), border_radius=6)
        fill_width = int(bar_width * (value / 100))
        pygame.draw.rect(surface, ACCENT_COLOR, (bar_x, bar_y, fill_width, bar_height), border_radius=6)
        draw_text(surface, f"{label}: {int(value)}%", (bar_x, bar_y - 22), small_font, PANEL_TEXT)
        bar_y += 54

    draw_text(surface, "Pendientes", (MAP_WIDTH + 20, bar_y + 4), font, PANEL_TEXT)
    checklist_y = bar_y + 40
    for item, done in character.checklist.items():
        color = (122, 210, 120) if done else PANEL_MUTED
        status = "✔" if done else "•"
        draw_text(surface, f"{status} {item}", (MAP_WIDTH + 24, checklist_y), small_font, color)
        checklist_y += 24

    draw_text(surface, "Bitácora", (MAP_WIDTH + 20, HEIGHT - 220), font, PANEL_TEXT)
    log_y = HEIGHT - 180
    for entry in character.log[-MAX_LOG_ENTRIES:]:
        draw_text(surface, f"• {entry}", (MAP_WIDTH + 24, log_y), small_font, PANEL_MUTED)
        log_y += 22

    instructions_y = HEIGHT - 60
    draw_text(surface, "WASD: mover", (MAP_WIDTH + 20, instructions_y), small_font, PANEL_MUTED)
    draw_text(surface, "E/T/etc: acción", (MAP_WIDTH + 140, instructions_y), small_font, PANEL_MUTED)


def draw_map(surface: pygame.Surface, font: pygame.font.Font, small_font: pygame.font.Font, hovered: Building | None) -> None:
    surface.fill(BACKGROUND_COLOR)
    pygame.draw.rect(surface, (214, 222, 235), pygame.Rect(0, 0, MAP_WIDTH, HEIGHT))
    pygame.draw.rect(surface, (190, 205, 219), pygame.Rect(40, 30, MAP_WIDTH - 80, HEIGHT - 60), border_radius=26)

    for building in BUILDINGS:
        rect = building.rect
        color = building.highlight if building is hovered else building.color
        pygame.draw.rect(surface, color, rect, border_radius=12)
        pygame.draw.rect(surface, BORDER_COLOR, rect, width=2, border_radius=12)
        text_rect = draw_text(surface, building.name, (rect.x + 12, rect.y + 10), small_font, (32, 40, 60))
        underline = pygame.Rect(text_rect.left, text_rect.bottom + 2, text_rect.width, 2)
        pygame.draw.rect(surface, (32, 40, 60), underline)


def draw_player(surface: pygame.Surface, character: Character) -> pygame.Rect:
    position = (int(character.position.x), int(character.position.y))
    pygame.draw.circle(surface, character.color, position, PLAYER_RADIUS)
    pygame.draw.circle(surface, BORDER_COLOR, position, PLAYER_RADIUS, width=2)
    return pygame.Rect(position[0] - PLAYER_RADIUS, position[1] - PLAYER_RADIUS, PLAYER_RADIUS * 2, PLAYER_RADIUS * 2)


def draw_action_overlay(surface: pygame.Surface, building: Building, actions: Sequence[Action], font: pygame.font.Font, small_font: pygame.font.Font) -> None:
    if not building or not actions:
        return

    overlay_rect = pygame.Rect(60, HEIGHT - 200, MAP_WIDTH - 120, 140)
    pygame.draw.rect(surface, (27, 38, 59, 235), overlay_rect, border_radius=16)
    pygame.draw.rect(surface, (255, 255, 255, 40), overlay_rect, width=2, border_radius=16)
    draw_text(surface, building.name, (overlay_rect.x + 20, overlay_rect.y + 16), font, (230, 235, 255))
    draw_text(surface, building.description, (overlay_rect.x + 20, overlay_rect.y + 60), small_font, (200, 210, 240))

    action_x = overlay_rect.x + 20
    action_y = overlay_rect.y + 90
    for action in actions:
        draw_text(surface, f"[{action.key}] {action.label}", (action_x, action_y), small_font, (173, 209, 255))
        action_y += 26


def draw_hover_tooltip(surface: pygame.Surface, building: Building, font: pygame.font.Font) -> None:
    tooltip_rect = pygame.Rect(pygame.mouse.get_pos(), (0, 0))
    tooltip_rect.inflate_ip(220, 90)
    tooltip_rect.x += 18
    tooltip_rect.y += 18
    pygame.draw.rect(surface, (42, 56, 82), tooltip_rect, border_radius=12)
    pygame.draw.rect(surface, (220, 230, 255), tooltip_rect, width=2, border_radius=12)
    draw_text(surface, building.name, (tooltip_rect.x + 10, tooltip_rect.y + 8), font, (255, 255, 255))
    wrapped = wrap_text(building.description, 26)
    y = tooltip_rect.y + 42
    for line in wrapped:
        draw_text(surface, line, (tooltip_rect.x + 10, y), pygame.font.Font(None, 22), (206, 216, 244))
        y += 24


def wrap_text(text: str, max_chars: int) -> List[str]:
    words = text.split()
    lines: List[str] = []
    current: List[str] = []
    count = 0
    for word in words:
        if count + len(word) + (1 if current else 0) > max_chars:
            lines.append(" ".join(current))
            current = [word]
            count = len(word)
        else:
            current.append(word)
            count += len(word) + (1 if current else 0)
    if current:
        lines.append(" ".join(current))
    return lines


# --- Lógica del juego ---
def apply_decay(character: Character, dt: float) -> None:
    for need, rate in DECAY_RATES.items():
        character.needs[need] = clamp(character.needs[need] - rate * dt)


def building_for_position(position: pygame.Vector2) -> Building | None:
    point = (int(position.x), int(position.y))
    for building in BUILDINGS:
        if building.rect.collidepoint(point):
            return building
    return None


def update_position(character: Character, dt: float, keys: Sequence[bool]) -> None:
    direction = pygame.Vector2(0, 0)
    if keys[pygame.K_w] or keys[pygame.K_UP]:
        direction.y -= 1
    if keys[pygame.K_s] or keys[pygame.K_DOWN]:
        direction.y += 1
    if keys[pygame.K_a] or keys[pygame.K_LEFT]:
        direction.x -= 1
    if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
        direction.x += 1

    if direction.length_squared() > 0:
        direction = direction.normalize()
        character.position += direction * PLAYER_SPEED * dt
        character.position.x = clamp(character.position.x, 40 + PLAYER_RADIUS, MAP_WIDTH - 40 - PLAYER_RADIUS)
        character.position.y = clamp(character.position.y, 40 + PLAYER_RADIUS, HEIGHT - 40 - PLAYER_RADIUS)


def execute_action(character: Character, action: Action) -> None:
    result = action.handler(character)
    append_log(character.log, result)


def character_selection(screen: pygame.Surface, clock: pygame.time.Clock, font: pygame.font.Font, small_font: pygame.font.Font) -> Character | None:
    index = 0
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    return None
                if event.key in (pygame.K_DOWN, pygame.K_s):
                    index = (index + 1) % len(CHARACTERS)
                if event.key in (pygame.K_UP, pygame.K_w):
                    index = (index - 1) % len(CHARACTERS)
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    chosen = CHARACTERS[index]
                    chosen.reset()
                    return chosen

        screen.fill((22, 30, 46))
        draw_text(screen, "Proyecto TACHI", (WIDTH // 2 - 160, 120), font, (242, 246, 255))
        draw_text(screen, "Selecciona un personaje", (WIDTH // 2 - 190, 170), small_font, (188, 198, 220))

        base_y = 240
        for idx, character in enumerate(CHARACTERS):
            color = (240, 244, 255) if idx == index else (150, 160, 190)
            marker = "→" if idx == index else "  "
            draw_text(screen, f"{marker} {character.name} ({character.role})", (WIDTH // 2 - 210, base_y + idx * 40), small_font, color)

        draw_text(screen, "ENTER: iniciar   ESC: salir", (WIDTH // 2 - 170, 520), small_font, (140, 150, 180))
        pygame.display.flip()
        clock.tick(FPS)


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Proyecto TACHI - Campus Simulator")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 42)
    small_font = pygame.font.Font(None, 28)

    current_character: Character | None = None

    while True:
        if current_character is None:
            selection = character_selection(screen, clock, font, small_font)
            if selection is None:
                break
            current_character = selection
            continue

        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    current_character = None
                    break

                building = building_for_position(current_character.position)
                if building:
                    actions = building.actions_for(current_character)
                    pressed = pygame.key.name(event.key).upper()
                    for action in actions:
                        if action.key == pressed:
                            execute_action(current_character, action)
                            break

        if current_character is None:
            continue

        keys = pygame.key.get_pressed()
        update_position(current_character, dt, keys)
        apply_decay(current_character, dt)

        hovered_building = None
        mouse_pos = pygame.mouse.get_pos()
        if mouse_pos[0] < MAP_WIDTH:
            for building in BUILDINGS:
                if building.rect.collidepoint(mouse_pos):
                    hovered_building = building
                    break

        active_building = building_for_position(current_character.position)
        available_actions = active_building.actions_for(current_character) if active_building else ()

        draw_map(screen, font, small_font, hovered_building or active_building)
        draw_player(screen, current_character)
        draw_action_overlay(screen, active_building, available_actions, font, small_font)

        if hovered_building and hovered_building is not active_building:
            draw_hover_tooltip(screen, hovered_building, small_font)

        draw_panel(screen, current_character, font, small_font)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pygame.quit()
        print("Simulador cerrado por el usuario.")
