import pytest

from tachi import (
    ActivityType,
    CharacterType,
    choose_character,
    create_character,
    default_characters,
    render_pixel_map,
    simulate_day,
)


def test_render_pixel_map_contains_key_locations():
    mapa = render_pixel_map()
    assert "STA" in mapa  # Starbucks
    assert "CAF" in mapa  # Caffenio / cafetería
    assert "OXX" in mapa  # Oxxo
    assert "BIB" in mapa  # Biblioteca
    assert "CAN" in mapa  # Canchas deportivas


def test_create_character_initial_activities():
    rector = create_character("Antonio", CharacterType.RECTOR, "ADM")
    control = rector.control_panel()

    assert control["tipo"] == "rector"
    # La actividad más urgente debe ser la de prioridad 1
    assert control["actividades_prioritarias"][0] == "Supervisar facultades"


def test_simulate_day_attends_priority_tasks_first():
    alumno = create_character("Isaac", CharacterType.ALUMNO, "TI")

    # Se agrega una actividad muy urgente
    alumno.schedule_activity(
        nombre="Entregar proyecto final",
        prioridad=0,
        tipo=ActivityType.ACADEMICA,
        ubicacion="TI",
    )

    resumen = simulate_day(alumno, max_steps=2)
    assert "Entregar proyecto final" in resumen[0]


def test_choose_character_errors_when_missing():
    personajes = {CharacterType.ALUMNO: default_characters()[CharacterType.ALUMNO]}
    with pytest.raises(KeyError):
        choose_character(personajes, CharacterType.RECTOR)
