# Tachi-Proyecto

Simulador en Python de la vida diaria dentro de la Universidad Panamericana.
Permite elegir distintos tipos de personajes (rector, maestros, alumnos y
empleados) y gestionar sus actividades mediante colas clásicas y de prioridad.
El mapa del campus se representa como arte ASCII tipo *pixel art* para mantener
la experiencia completamente en Python.

## Características

- Mapa estilo pixel art que incluye Starbucks, Caffenio, Oxxo, Biblioteca,
  gimnasio, canchas y más ubicaciones emblemáticas de la UP.
- Panel de control por personaje que muestra el estado de sus necesidades y
  actividades pendientes.
- Colas FIFO y de prioridad para organizar tareas urgentes y rutinarias.
- Utilidades para simular las jornadas de cada personaje y verificar que la
  universidad se mantenga en operación.

## Uso rápido

```python
from tachi import CharacterType, default_characters, render_pixel_map, simulate_day

print(render_pixel_map())
antonio = default_characters()[CharacterType.RECTOR]
for evento in simulate_day(antonio):
    print(evento)
```

## Ejecutar las pruebas

```bash
pytest
```
