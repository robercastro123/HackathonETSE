# HackathonETSE

Quiz kiosco en pantalla completa con minijuegos, comodines y castigos.

## Ejecutar

Con Python 3, desde esta carpeta:

```bash
python3 csv_a_json.py preguntas.csv preguntas.json
python3 main.py
```

En Windows conviene lanzarlo desde una consola (ahí se ven también los
mensajes de los castigos). `keyboard` y `winreg` son opcionales: si no están,
el quiz funciona igual, solo con los bloqueos de ventana.

## Cómo se juega

```
minijuego -> 5 preguntas -> minijuego -> 5 preguntas -> jefe final (6)
```

Al empezar se pide un nombre de usuario. Se usan 16 preguntas al azar de
`preguntas.json` (10 de las rondas y 6 del jefe). Si añades más filas al CSV,
se mezclan automáticamente; hacen falta al menos 16.

### Minijuegos

Cada uno dura entre 20 y 22 segundos y da comodines según el rango:

| Rango | Comodines |
|-------|-----------|
| alto  | 2         |
| medio | 1         |
| bajo  | 0         |

| Minijuego | Controles | Puntos |
|-----------|-----------|--------|
| Ball Drop | `←` `→` | bolas atrapadas |
| Parcel Panic | clic | paquetes recogidos (rojo = bomba, resta) |
| Fruit Ninja | clic | frutas cortadas (bomba = −3) |
| Crossy Road | flechas | filas cruzadas |
| Don't Touch the Spikes | `espacio` | huecos pasados |
| Jungle Run | `espacio` | troncos esquivados |

Los dos minijuegos de cada partida se eligen al azar y no se repiten.

### Comodines

Se acumulan entre minijuegos. Al fallar una pregunta, si queda algún comodín,
se gasta uno y se puede volver a intentar la misma pregunta (la opción fallada
queda bloqueada). Sin comodines se revela la respuesta correcta.

### Fallos

- **Primer fallo de la partida:** se imprime el nombre de usuario por pantalla
  (y en la consola). No hay castigo todavía.
- **Resto de fallos de las rondas:** se aplica un castigo aleatorio:
  - mover un archivo,
  - modificar un archivo,
  - listar los puertos abiertos de `127.0.0.1`,
  - mostrar IP local, IP pública y geolocalización (si hay red),
  - dibujar el mapa de archivos de la zona de castigo.
- **Fallos en el jefe final:** no aplican castigos sueltos; cuentan para el
  veredicto.

### Jefe final

6 preguntas. Con **4 aciertos o más** se supera. Con **3 o menos** se borra
un archivo de la zona de castigo.

## Zona de castigo

Todo lo que se mueve, se modifica o se borra ocurre dentro de `zona_castigo/`,
que se crea sola con archivos de ejemplo (y se vuelve a rellenar al iniciar el
programa, así que una demo se puede repetir sin dejar el equipo roto).

Para que los castigos actúen sobre archivos reales, cambia `DIRECTORIO_CASTIGO`
al principio de `castigos.py`:

```python
DIRECTORIO_CASTIGO = Path.home() / "Escritorio"
```

Aun así el módulo se niega a salir de esa carpeta y protege los archivos del
propio proyecto (`main.py`, `preguntas.json`, `.git`, etc.). Haz una copia de
seguridad antes de apuntar a una carpeta con cosas importantes.

La geolocalización usa `ipapi.co`. Si no hay conexión, solo se muestra la IP
local. Se puede desactivar con `PERMITIR_RED = False` en `castigos.py`.

## Salir

- El botón **Salir** de la pantalla final.
- **Salida de emergencia del operador:** pulsa `F12` tres veces seguidas.
- `Ctrl+Alt+Supr` sigue funcionando siempre (no se bloquea a propósito).

## Archivos

| Archivo | Contenido |
|---------|-----------|
| `main.py` | flujo del quiz, pantallas, comodines, jefe final y bloqueos |
| `minijuegos.py` | los 6 minijuegos y el sistema de rangos |
| `castigos.py` | mover/modificar/borrar, puertos, IP y mapa (sin Tkinter) |
| `estilo.py` | colores y fuentes |
| `csv_a_json.py` | conversor de `preguntas.csv` a `preguntas.json` |

El conversor admite el formato del CSV incluido: `Categoría`, `Pregunta`,
`Correcta`, `Incorr1`, `Incorr2` e `Incorr3`. También admite CSV con cuatro
columnas de opciones (`opcion_a` a `opcion_d`) y `respuesta_correcta`.
Las filas sin pregunta se ignoran. Las opciones se mezclan de forma estable
para cada pregunta, y el índice de la respuesta correcta se guarda en el JSON.

`main.py` carga `preguntas.json` desde la misma carpeta. Si se modifica el CSV,
vuelve a ejecutar el conversor antes de iniciar el quiz.
