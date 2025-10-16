"""Simulador TACHI concentrado en un único archivo Python.

Este script contiene toda la lógica necesaria para representar el proyecto
``TACHI`` sin depender de paquetes adicionales. Puede abrirse y modificarse
como un solo archivo y, aun así, reutilizarse como módulo importable. Incluye:

* Un mapa estilo *pixel art* renderizado en ASCII que refleja los lugares más
  representativos del campus.
* Clases para personajes (rector, maestros, alumnos y empleados) con paneles
  de control que muestran el estado de sus actividades.
* Estructuras de datos basadas en colas (FIFO) y colas de prioridad que
  permiten planificar y atender tareas de acuerdo con su urgencia.

Todo está escrito exclusivamente en Python.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterator, List, Optional, Tuple


# ---------------------------------------------------------------------------
#  Mapa tipo "pixel art"
# ---------------------------------------------------------------------------

_PIXEL_MAP: Tuple[str, ...] = (
    "#############################",
    "#STA#CAF#FUN#ENT#OXX#BIB#GYM#",
    "# TI# SC#ING#POS#MUS#CAN#CIV#",
    "#CAF#OXO#CAF#LIB#DIR#ADM#PRO#",
    "#RES#ASO#COM#DEP#MUS#LAB#UP #",
    "#############################",
)


def render_pixel_map() -> str:
    """Devuelve una representación multilinea del mapa del campus.

    El mapa utiliza caracteres ASCII para simular un tablero tipo pixel art.
    Cada cuadro de cuatro caracteres representa una zona icónica de la UP.
    """

    return "\n".join(_PIXEL_MAP)


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


__all__ = [
    "Activity",
    "ActivityQueue",
    "ActivityType",
    "Character",
    "CharacterType",
    "PriorityActivityQueue",
    "choose_character",
    "create_character",
    "default_characters",
    "render_pixel_map",
    "simulate_day",
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


if __name__ == "__main__":  # pragma: no cover - bloque interactivo
    _demo()

