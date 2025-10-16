"""Funciones utilitarias para operaciones matemáticas básicas.

Todas las funciones están implementadas exclusivamente en Python tal como
indica la especificación del proyecto. Se incluyen validaciones que permiten
detectar entradas no válidas y proporcionar mensajes de error descriptivos.
"""

from __future__ import annotations

from math import prod, sqrt
from typing import Iterable, Sequence

Number = float | int


def _asegurar_argumentos_numericos(numeros: Sequence[Number]) -> None:
    """Verifica que todos los elementos de ``numeros`` sean numéricos."""

    for indice, valor in enumerate(numeros):
        if not isinstance(valor, (int, float)):
            raise TypeError(
                f"El valor en la posición {indice} no es numérico: {valor!r}"
            )


def sumar(*numeros: Number) -> Number:
    """Devuelve la suma de todos los números proporcionados."""

    if not numeros:
        raise ValueError("Se requiere al menos un número para sumar.")
    _asegurar_argumentos_numericos(numeros)
    return sum(numeros)


def restar(minuendo: Number, sustraendo: Number) -> Number:
    """Calcula la resta ``minuendo - sustraendo``."""

    _asegurar_argumentos_numericos((minuendo, sustraendo))
    return minuendo - sustraendo


def multiplicar(*numeros: Number) -> Number:
    """Devuelve el producto de los números proporcionados."""

    if not numeros:
        raise ValueError("Se requiere al menos un número para multiplicar.")
    _asegurar_argumentos_numericos(numeros)
    return prod(numeros)


def dividir(dividendo: Number, divisor: Number) -> float:
    """Calcula la división ``dividendo / divisor``."""

    _asegurar_argumentos_numericos((dividendo, divisor))
    if divisor == 0:
        raise ZeroDivisionError("No se puede dividir entre cero.")
    return dividendo / divisor


def promedio(valores: Iterable[Number]) -> float:
    """Calcula el promedio aritmético de ``valores``."""

    valores_lista = list(valores)
    if not valores_lista:
        raise ValueError("No se puede calcular el promedio de una colección vacía.")
    _asegurar_argumentos_numericos(valores_lista)
    return sum(valores_lista) / len(valores_lista)


def factorial(numero: int) -> int:
    """Calcula el factorial de un número natural."""

    if not isinstance(numero, int):
        raise TypeError("El factorial solo está definido para números enteros.")
    if numero < 0:
        raise ValueError("El factorial no está definido para números negativos.")

    resultado = 1
    for factor in range(2, numero + 1):
        resultado *= factor
    return resultado


def es_primo(numero: int) -> bool:
    """Determina si ``numero`` es un número primo."""

    if not isinstance(numero, int):
        raise TypeError("La primalidad solo se puede evaluar para enteros.")

    if numero < 2:
        return False
    if numero in (2, 3):
        return True
    if numero % 2 == 0:
        return False

    limite = int(sqrt(numero)) + 1
    for posible_divisor in range(3, limite, 2):
        if numero % posible_divisor == 0:
            return False
    return True


__all__ = [
    "dividir",
    "es_primo",
    "factorial",
    "multiplicar",
    "promedio",
    "restar",
    "sumar",
]
