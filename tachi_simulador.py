"""Simulador TACHI con lógica y visualización interactiva en pygame.

Este script contiene toda la lógica necesaria para representar el proyecto
``TACHI`` sin depender de módulos adicionales. Puede abrirse y modificarse
como un solo archivo y, aun así, reutilizarse como módulo importable. Incluye:

* Un mapa estilo *pixel art* que puede renderizarse en ASCII o en una ventana
  de `pygame`.
* Clases para personajes (rector, maestros, alumnos y empleados) con paneles
  de control que muestran el estado de sus actividades.
* Estructuras de datos basadas en colas (FIFO) y colas de prioridad que
  permiten planificar y atender tareas de acuerdo con su urgencia.
* Una interfaz `PygameSimulator` que permite elegir personajes, atender
  actividades y mostrar la información al colocar el cursor sobre cada avatar.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterator, List, Optional, Tuple


# ---------------------------------------------------------------------------
#  Mapa tipo "pixel art"
# ---------------------------------------------------------------------------


_MAP_TILES: Tuple[Tuple[str, ...], ...] = (
    ("STA", "CAF", "FUN", "ENT", "OXX", "BIB", "GYM"),
    ("TI ", "SC ", "ING", "POS", "MUS", "CAN", "CIV"),
    ("CAF", "OXO", "CAF", "LIB", "DIR", "ADM", "PRO"),
    ("RES", "ASO", "COM", "DEP", "MUS", "LAB", "UP "),
)


def _normalized_tile_name(tile: str) -> str:
    """Normaliza el identificador para búsquedas posteriores."""

    return tile.strip().upper()


def campus_tiles() -> Tuple[Tuple[str, ...], ...]:
    """Devuelve la matriz de celdas que conforma el mapa del campus."""

    return _MAP_TILES


def render_pixel_map() -> str:
    """Devuelve una representación multilinea del mapa del campus.

    El mapa utiliza caracteres ASCII para simular un tablero tipo pixel art.
    Cada cuadro de cuatro caracteres representa una zona icónica de la UP.
    """

    ancho = len(_MAP_TILES[0])
    borde = "#" * (ancho * 4 + 1)
    filas = [borde]
    for fila in _MAP_TILES:
        contenido = "#".join(tile for tile in fila)
        filas.append(f"#{contenido}#")
    filas.append(borde)
    return "\n".join(filas)


def tile_locations() -> Dict[str, Tuple[int, int]]:
    """Devuelve un diccionario con la primera aparición de cada zona en el mapa."""

    ubicaciones: Dict[str, Tuple[int, int]] = {}
    for y, fila in enumerate(_MAP_TILES):
        for x, tile in enumerate(fila):
            nombre = _normalized_tile_name(tile)
            if nombre and nombre not in ubicaciones:
                ubicaciones[nombre] = (x, y)
    return ubicaciones


# ---------------------------------------------------------------------------
#  Modelos de actividades y colas
# ---------------------------------------------------------------------------


class ActivityType(str, Enum):
    """Clasificación general de las actividades dentro de la simulación."""

    ACADEMICA = "académica"
    SOCIAL = "social"
    SALUD = "salud"
    OPERATIVA = "operativa"
    DESCANSO = "descanso"


@dataclass(order=True)
class Activity:
    """Representa una actividad planificada en el campus."""

    priority: int
    nombre: str = field(compare=False)
    tipo: ActivityType = field(compare=False)
    ubicacion: str = field(compare=False)


class PriorityActivityQueue:
    """Cola de prioridad mínima para administrar actividades urgentes."""

    def __init__(self) -> None:
        self._heap: List[Activity] = []

    def __len__(self) -> int:  # pragma: no cover - trivial wrapper
        return len(self._heap)

    def __iter__(self) -> Iterator[Activity]:
        return iter(sorted(self._heap))

    def schedule(self, activity: Activity) -> None:
        """Inserta una actividad conservando el orden por prioridad."""

        self._heap.append(activity)
        self._heap.sort()

    def pop_next(self) -> Optional[Activity]:
        """Extrae la actividad con mayor prioridad (menor valor numérico)."""

        if not self._heap:
            return None
        return self._heap.pop(0)


class ActivityQueue:
    """Cola FIFO tradicional para actividades rutinarias."""

    def __init__(self) -> None:
        self._items: List[Activity] = []

    def __len__(self) -> int:  # pragma: no cover - trivial wrapper
        return len(self._items)

    def __iter__(self) -> Iterator[Activity]:
        return iter(self._items)

    def schedule(self, activity: Activity) -> None:
        self._items.append(activity)

    def pop_next(self) -> Optional[Activity]:
        if not self._items:
            return None
        return self._items.pop(0)


# ---------------------------------------------------------------------------
#  Personajes y panel de control
# ---------------------------------------------------------------------------


class CharacterType(str, Enum):
    """Tipos de personajes disponibles en la simulación."""

    RECTOR = "rector"
    MAESTRO = "maestro"
    ALUMNO = "alumno"
    EMPLEADO = "empleado"


DEFAULT_NEEDS: Tuple[str, ...] = (
    "ha_comido",
    "ha_hecho_ejercicio",
    "ya_dio_clase",
    "ya_fue_a_clases",
    "ya_se_bano",
    "tuvo_examenes",
    "tiene_examenes",
    "hablo_con_amigos",
    "fue_a_asesorias",
    "ya_se_va_a_casa",
    "ya_estudio",
)


@dataclass
class Character:
    """Modelo genérico para personajes del campus."""

    nombre: str
    tipo: CharacterType
    ubicacion: str
    needs: Dict[str, bool] = field(default_factory=lambda: {n: False for n in DEFAULT_NEEDS})
    prioridades: PriorityActivityQueue = field(default_factory=PriorityActivityQueue)
    pendientes: ActivityQueue = field(default_factory=ActivityQueue)

    def schedule_activity(self, *, nombre: str, prioridad: int, tipo: ActivityType, ubicacion: Optional[str] = None) -> None:
        """Programa una nueva actividad.

        Las prioridades más bajas representan situaciones más urgentes.
        """

        destino = ubicacion or self.ubicacion
        activity = Activity(priority=prioridad, nombre=nombre, tipo=tipo, ubicacion=destino)
        if prioridad <= 2:
            self.prioridades.schedule(activity)
        else:
            self.pendientes.schedule(activity)

    def attend_next_activity(self) -> Optional[Activity]:
        """Atiende la actividad disponible más urgente."""

        next_activity = self.prioridades.pop_next() or self.pendientes.pop_next()
        if next_activity:
            self.ubicacion = next_activity.ubicacion
        return next_activity

    def update_need(self, need: str, value: bool) -> None:
        if need not in self.needs:
            raise KeyError(f"Necesidad desconocida: {need}")
        self.needs[need] = value

    def control_panel(self) -> Dict[str, object]:
        """Devuelve una vista tipo panel de control para interfaces gráficas."""

        urgent = list(self.prioridades)
        routine = list(self.pendientes)
        return {
            "nombre": self.nombre,
            "tipo": self.tipo.value,
            "ubicacion": self.ubicacion,
            "necesidades": self.needs.copy(),
            "actividades_prioritarias": [a.nombre for a in urgent],
            "actividades_rutinarias": [a.nombre for a in routine],
        }


def create_character(nombre: str, tipo: CharacterType, ubicacion: str) -> Character:
    """Fábrica sencilla para crear personajes con necesidades iniciales."""

    personaje = Character(nombre=nombre, tipo=tipo, ubicacion=ubicacion)

    if tipo == CharacterType.RECTOR:
        personaje.schedule_activity(
            nombre="Supervisar facultades",
            prioridad=1,
            tipo=ActivityType.OPERATIVA,
            ubicacion="DIR",
        )
        personaje.schedule_activity(
            nombre="Reunión con contadores",
            prioridad=2,
            tipo=ActivityType.OPERATIVA,
            ubicacion="ADM",
        )
    elif tipo == CharacterType.MAESTRO:
        personaje.schedule_activity(
            nombre="Impartir clase de cálculo",
            prioridad=1,
            tipo=ActivityType.ACADEMICA,
            ubicacion="ING",
        )
        personaje.schedule_activity(
            nombre="Asesoría a alumnos",
            prioridad=3,
            tipo=ActivityType.ACADEMICA,
            ubicacion="SC",
        )
    elif tipo == CharacterType.ALUMNO:
        personaje.schedule_activity(
            nombre="Asistir a clases",
            prioridad=1,
            tipo=ActivityType.ACADEMICA,
            ubicacion="ING",
        )
        personaje.schedule_activity(
            nombre="Practicar deporte",
            prioridad=3,
            tipo=ActivityType.SALUD,
            ubicacion="CAN",
        )
        personaje.schedule_activity(
            nombre="Estudiar en biblioteca",
            prioridad=2,
            tipo=ActivityType.ACADEMICA,
            ubicacion="BIB",
        )
    elif tipo == CharacterType.EMPLEADO:
        personaje.schedule_activity(
            nombre="Abrir el Oxxo",
            prioridad=1,
            tipo=ActivityType.OPERATIVA,
            ubicacion="OXO",
        )
        personaje.schedule_activity(
            nombre="Recibir proveedores",
            prioridad=2,
            tipo=ActivityType.OPERATIVA,
            ubicacion="PRO",
        )

    return personaje


def default_characters() -> Dict[CharacterType, Character]:
    """Crea un catálogo básico de personajes icónicos de la UP."""

    return {
        CharacterType.RECTOR: create_character("Antonio", CharacterType.RECTOR, "ADM"),
        CharacterType.MAESTRO: create_character("Dávalos", CharacterType.MAESTRO, "ING"),
        CharacterType.ALUMNO: create_character("Martha", CharacterType.ALUMNO, "BIB"),
        CharacterType.EMPLEADO: create_character("Fabiola", CharacterType.EMPLEADO, "CAF"),
    }


def choose_character(characters: Dict[CharacterType, Character], tipo: CharacterType) -> Character:
    """Selecciona un personaje del catálogo disponible."""

    try:
        return characters[tipo]
    except KeyError as exc:
        disponibles = ", ".join(sorted(t.value for t in characters))
        raise KeyError(f"Tipo de personaje no disponible. Usa uno de: {disponibles}") from exc


def simulate_day(personaje: Character, *, max_steps: int = 5) -> List[str]:
    """Ejecuta una simulación corta sobre las actividades del personaje."""

    resumen: List[str] = []
    for _ in range(max_steps):
        actividad = personaje.attend_next_activity()
        if not actividad:
            resumen.append(f"{personaje.nombre} no tiene actividades pendientes.")
            break
        resumen.append(
            f"{personaje.nombre} atiende '{actividad.nombre}' en {actividad.ubicacion} (tipo: {actividad.tipo.value})."
        )
    return resumen


class PygameSimulator:
    """Interfaz interactiva del simulador usando pygame."""

    TILE_SIZE = 96
    PADDING = 12
    PANEL_WIDTH = 320

    BACKGROUND_COLOR = (14, 16, 26)
    GRID_COLOR = (36, 40, 60)
    PANEL_BACKGROUND = (22, 24, 38)
    PANEL_TEXT = (240, 240, 240)
    PANEL_SUBTEXT = (190, 200, 210)
    SELECTION_COLOR = (255, 235, 97)

    TILE_COLORS: Dict[str, Tuple[int, int, int]] = {
        "STA": (108, 92, 231),
        "CAF": (214, 162, 232),
        "FUN": (255, 159, 243),
        "ENT": (129, 236, 236),
        "OXX": (250, 177, 160),
        "BIB": (116, 185, 255),
        "GYM": (85, 239, 196),
        "TI": (255, 118, 117),
        "SC": (253, 121, 168),
        "ING": (223, 230, 233),
        "POS": (178, 190, 195),
        "MUS": (253, 203, 110),
        "CAN": (0, 184, 148),
        "CIV": (108, 92, 231),
        "OXO": (250, 177, 160),
        "LIB": (116, 185, 255),
        "DIR": (9, 132, 227),
        "ADM": (0, 184, 148),
        "PRO": (0, 206, 201),
        "RES": (232, 67, 147),
        "ASO": (225, 112, 85),
        "COM": (214, 162, 232),
        "DEP": (85, 239, 196),
        "LAB": (45, 52, 54),
        "UP": (253, 203, 110),
    }

    CHARACTER_COLORS: Dict[CharacterType, Tuple[int, int, int]] = {
        CharacterType.RECTOR: (255, 234, 167),
        CharacterType.MAESTRO: (9, 132, 227),
        CharacterType.ALUMNO: (232, 67, 147),
        CharacterType.EMPLEADO: (0, 184, 148),
    }

    def __init__(self, *, characters: Optional[Dict[CharacterType, Character]] = None) -> None:
        self.characters = characters or default_characters()
        self.selected_type: CharacterType = next(iter(self.characters))
        self._tile_lookup = tile_locations()
        self._log: List[str] = []
        self._font_small = None
        self._font_regular = None

    def _map_dimensions(self) -> Tuple[int, int]:
        ancho = len(_MAP_TILES[0]) * self.TILE_SIZE + self.PADDING * 2
        alto = len(_MAP_TILES) * self.TILE_SIZE + self.PADDING * 2
        return ancho, alto

    def _window_dimensions(self) -> Tuple[int, int]:
        mapa_ancho, mapa_alto = self._map_dimensions()
        return mapa_ancho + self.PANEL_WIDTH, mapa_alto

    def _character_centers(self) -> Dict[CharacterType, Tuple[int, int]]:
        centros: Dict[CharacterType, Tuple[int, int]] = {}
        for tipo, personaje in self.characters.items():
            ubicacion = self._tile_lookup.get(_normalized_tile_name(personaje.ubicacion))
            if not ubicacion:
                continue
            x_idx, y_idx = ubicacion
            cx = self.PADDING + x_idx * self.TILE_SIZE + self.TILE_SIZE // 2
            cy = self.PADDING + y_idx * self.TILE_SIZE + self.TILE_SIZE // 2
            centros[tipo] = (cx, cy)
        return centros

    def run(self) -> None:
        """Inicia una ventana de pygame con el simulador interactivo."""

        import pygame

        pygame.init()
        pygame.font.init()

        ancho, alto = self._window_dimensions()
        ventana = pygame.display.set_mode((ancho, alto))
        pygame.display.set_caption("Simulador TACHI - Campus UP")
        reloj = pygame.time.Clock()

        self._font_small = pygame.font.SysFont("arial", 18)
        self._font_regular = pygame.font.SysFont("arial", 20)

        mapa_ancho, _ = self._map_dimensions()
        ejecutando = True
        while ejecutando:
            hover_character: Optional[Character] = None
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    ejecutando = False
                elif evento.type == pygame.KEYDOWN:
                    self._handle_key(evento.key)

            hover_character = self._character_at(pygame.mouse.get_pos())
            self._draw(ventana, mapa_ancho, hover_character)

            pygame.display.flip()
            reloj.tick(30)

        pygame.quit()

    def _handle_key(self, key: int) -> None:
        import pygame

        mapping = {
            pygame.K_1: CharacterType.RECTOR,
            pygame.K_2: CharacterType.MAESTRO,
            pygame.K_3: CharacterType.ALUMNO,
            pygame.K_4: CharacterType.EMPLEADO,
        }
        if key in mapping and mapping[key] in self.characters:
            self.selected_type = mapping[key]
            return

        if key == pygame.K_SPACE:
            self._advance_selected()

    def _advance_selected(self) -> None:
        personaje = self.characters[self.selected_type]
        actividad = personaje.attend_next_activity()
        if actividad:
            mensaje = (
                f"{personaje.nombre} atiende {actividad.nombre} en {actividad.ubicacion}"
            )
        else:
            mensaje = f"{personaje.nombre} no tiene actividades pendientes"
        self._log.insert(0, mensaje)
        self._log = self._log[:6]

    def _character_at(self, mouse_pos: Tuple[int, int]) -> Optional[Character]:
        centros = self._character_centers()
        radio = self.TILE_SIZE // 3
        for tipo, centro in centros.items():
            dx = mouse_pos[0] - centro[0]
            dy = mouse_pos[1] - centro[1]
            if dx * dx + dy * dy <= radio * radio:
                return self.characters[tipo]
        return None

    def _draw(self, surface, mapa_ancho: int, hover_character: Optional[Character]) -> None:
        import pygame

        surface.fill(self.BACKGROUND_COLOR)
        self._draw_map(surface)
        self._draw_characters(surface)
        self._draw_panel(surface, mapa_ancho, hover_character)

    def _draw_map(self, surface) -> None:
        import pygame

        for y, fila in enumerate(_MAP_TILES):
            for x, tile in enumerate(fila):
                rect = pygame.Rect(
                    self.PADDING + x * self.TILE_SIZE,
                    self.PADDING + y * self.TILE_SIZE,
                    self.TILE_SIZE,
                    self.TILE_SIZE,
                )
                nombre = _normalized_tile_name(tile)
                color = self.TILE_COLORS.get(nombre, (99, 110, 114))
                pygame.draw.rect(surface, color, rect)
                pygame.draw.rect(surface, self.GRID_COLOR, rect, 2)

                if self._font_small:
                    etiqueta = nombre or tile.strip()
                    texto = self._font_small.render(etiqueta, True, self.PANEL_TEXT)
                    texto_rect = texto.get_rect(center=rect.center)
                    surface.blit(texto, texto_rect)

    def _draw_characters(self, surface) -> None:
        import pygame

        centros = self._character_centers()
        radio = self.TILE_SIZE // 3
        for tipo, centro in centros.items():
            color = self.CHARACTER_COLORS.get(tipo, (255, 255, 255))
            pygame.draw.circle(surface, color, centro, radio)
            if tipo == self.selected_type:
                pygame.draw.circle(surface, self.SELECTION_COLOR, centro, radio + 4, 2)

    def _draw_panel(
        self,
        surface,
        mapa_ancho: int,
        hover_character: Optional[Character],
    ) -> None:
        import pygame

        panel_rect = pygame.Rect(mapa_ancho, 0, self.PANEL_WIDTH, surface.get_height())
        pygame.draw.rect(surface, self.PANEL_BACKGROUND, panel_rect)
        pygame.draw.rect(surface, self.GRID_COLOR, panel_rect, 2)

        personaje = hover_character or self.characters[self.selected_type]
        titulo = f"{personaje.nombre} ({personaje.tipo.value})"

        if self._font_regular:
            header = self._font_regular.render(titulo, True, self.PANEL_TEXT)
            surface.blit(header, (panel_rect.x + 16, panel_rect.y + 16))

        y = panel_rect.y + 52
        if self._font_small:
            ubic = self._font_small.render(
                f"Ubicación: {personaje.ubicacion}", True, self.PANEL_SUBTEXT
            )
            surface.blit(ubic, (panel_rect.x + 16, y))
            y += 28

            surface.blit(
                self._font_small.render("Necesidades:", True, self.PANEL_TEXT),
                (panel_rect.x + 16, y),
            )
            y += 24
            for nombre, cumplida in personaje.needs.items():
                estado = "✓" if cumplida else "✗"
                texto = f"{estado} {nombre.replace('_', ' ')}"
                surface.blit(
                    self._font_small.render(texto, True, self.PANEL_SUBTEXT),
                    (panel_rect.x + 20, y),
                )
                y += 22
                if y > panel_rect.bottom - 140:
                    break

            y += 12
            surface.blit(
                self._font_small.render("Actividades prioritarias:", True, self.PANEL_TEXT),
                (panel_rect.x + 16, y),
            )
            y += 24
            for actividad in personaje.prioridades:
                surface.blit(
                    self._font_small.render(f"• {actividad.nombre}", True, self.PANEL_SUBTEXT),
                    (panel_rect.x + 20, y),
                )
                y += 22

            y += 12
            surface.blit(
                self._font_small.render("Actividades rutinarias:", True, self.PANEL_TEXT),
                (panel_rect.x + 16, y),
            )
            y += 24
            for actividad in personaje.pendientes:
                surface.blit(
                    self._font_small.render(f"• {actividad.nombre}", True, self.PANEL_SUBTEXT),
                    (panel_rect.x + 20, y),
                )
                y += 22

            instrucciones = [
                "1-4: elegir personaje",
                "Espacio: atender actividad",
                "Coloca el cursor sobre un personaje",
            ]
            y = surface.get_height() - 96
            for instruccion in instrucciones:
                surface.blit(
                    self._font_small.render(instruccion, True, self.PANEL_SUBTEXT),
                    (panel_rect.x + 16, y),
                )
                y += 24

            if self._log:
                y = surface.get_height() - 180
                surface.blit(
                    self._font_small.render("Bitácora:", True, self.PANEL_TEXT),
                    (panel_rect.x + 16, y),
                )
                y += 24
                for linea in self._log:
                    surface.blit(
                        self._font_small.render(linea, True, self.PANEL_SUBTEXT),
                        (panel_rect.x + 16, y),
                    )
                    y += 22

__all__ = [
    "Activity",
    "ActivityQueue",
    "ActivityType",
    "Character",
    "CharacterType",
    "PygameSimulator",
    "PriorityActivityQueue",
    "campus_tiles",
    "choose_character",
    "create_character",
    "default_characters",
    "render_pixel_map",
    "simulate_day",
    "tile_locations",
]


def _demo() -> None:
    """Demostración sencilla cuando se ejecuta el archivo directamente."""

    print("=== Mapa del campus estilo pixel art ===")
    print(render_pixel_map())
    print()

    personajes = default_characters()
    rector = personajes[CharacterType.RECTOR]
    resumen = simulate_day(rector, max_steps=3)
    print(f"Actividades iniciales de {rector.nombre}:")
    for linea in resumen:
        print("-", linea)

    print()
    print("Para la versión interactiva usa: from tachi_simulador import PygameSimulator")


if __name__ == "__main__":  # pragma: no cover - bloque interactivo
    _demo()

