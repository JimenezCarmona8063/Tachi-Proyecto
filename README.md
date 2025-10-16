# Tachi-Proyecto

Simulador en Python de la vida diaria dentro de la Universidad Panamericana.
Todo el código vive en un único archivo (`tachi_simulador.py`) para facilitar su
edición o revisión sin navegar por múltiples módulos. Permite elegir distintos
tipos de personajes (rector, maestros, alumnos y empleados) y gestionar sus
actividades mediante colas clásicas y de prioridad. El mapa del campus se
representa como arte ASCII tipo *pixel art* para mantener la experiencia
completamente en Python.

## Características

- Mapa estilo pixel art que incluye Starbucks, Caffenio, Oxxo, Biblioteca,
  gimnasio, canchas y más ubicaciones emblemáticas de la UP.
- Panel de control por personaje que muestra el estado de sus necesidades y
  actividades pendientes.
- Colas FIFO y de prioridad para organizar tareas urgentes y rutinarias.
- Utilidades para simular las jornadas de cada personaje y verificar que la
  universidad se mantenga en operación.

## Uso rápido

1. Abrir el archivo `tachi_simulador.py` para explorar o modificar el
   simulador.
2. Ejecutarlo directamente para ver una demostración rápida:

   ```bash
   python tachi_simulador.py
   ```

3. También puede importarse desde otros scripts (el paquete `tachi` se mantiene
   por compatibilidad):

   ```python
   from tachi_simulador import (
       CharacterType,
       default_characters,
       render_pixel_map,
       simulate_day,
   )

   print(render_pixel_map())
   antonio = default_characters()[CharacterType.RECTOR]
   for evento in simulate_day(antonio):
       print(evento)
   ```

## Ejecutar las pruebas

```bash
pytest
```
