import math
import pytest

from calculadora import (
    dividir,
    es_primo,
    factorial,
    multiplicar,
    promedio,
    restar,
    sumar,
)


def test_sumar_valores_enteros():
    assert sumar(1, 2, 3, 4) == 10


def test_sumar_sin_argumentos_error():
    with pytest.raises(ValueError):
        sumar()


def test_restar_resultado_negativo():
    assert restar(5, 8) == -3


def test_multiplicar_valores():
    assert multiplicar(2, 3, 4) == 24


def test_multiplicar_requiere_argumentos():
    with pytest.raises(ValueError):
        multiplicar()


def test_dividir_valores():
    assert dividir(10, 2) == 5


def test_dividir_entre_cero_error():
    with pytest.raises(ZeroDivisionError):
        dividir(1, 0)


def test_promedio_lista_valores():
    assert math.isclose(promedio([2, 4, 6, 8]), 5.0)


def test_promedio_vacio_error():
    with pytest.raises(ValueError):
        promedio([])


def test_factorial_numero_grande():
    assert factorial(6) == 720


def test_factorial_no_enteros_error():
    with pytest.raises(TypeError):
        factorial(3.5)  # type: ignore[arg-type]


def test_es_primo_identifica_primos_y_compuestos():
    assert es_primo(7) is True
    assert es_primo(8) is False


def test_es_primo_rechaza_no_enteros():
    with pytest.raises(TypeError):
        es_primo(5.2)  # type: ignore[arg-type]
