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
minijuego -> 3 preguntas -> jefe final (3 preguntas, hacen falta 2)
```

Al empezar se detecta automáticamente el usuario del sistema (no se pregunta
nada). Se usan 6 preguntas al azar de `preguntas.json` (3 de la ronda y 3 del
jefe). Si añades más filas al CSV, se mezclan automáticamente; hacen falta al
menos 6.

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

El minijuego de cada partida se elige al azar entre los seis.

### Comodines

Los comodines del minijuego se usan tanto en las 3 preguntas como en el jefe
final. Al fallar una pregunta, si queda algún comodín,
se gasta uno automáticamente: **te libras del castigo** y puedes volver a
intentar la misma pregunta (la opción fallada queda bloqueada). Sin comodines
se aplica el castigo y se revela la respuesta correcta.

### Fallos

- **Primer fallo de la partida:** se imprime por pantalla el nombre del usuario
  real del sistema y el nombre del equipo, y también en la consola. No hay
  castigo todavía. Si te queda algún comodín, se gasta y vuelves a intentarlo.
- **Resto de fallos de la ronda:** si **no** te queda ningún comodín se
  aplica un castigo aleatorio. Se usa una bolsa barajada: en cinco castigos
  salen los cinco tipos.
  - mover un archivo,
  - modificar un archivo,
  - listar los puertos abiertos de `127.0.0.1` (35 puertos habituales),
  - mostrar IP local, IP pública y geolocalización (si hay red),
  - dibujar el mapa de archivos del sistema.
- **Fallos en el jefe final:** no aplican castigos sueltos; cuentan para el
  veredicto.

### Inspección del sistema

Los puertos, la IP y la geolocalización se consultan de verdad en el equipo.
El mapa de archivos recorre una carpeta **en modo solo lectura**:

```python
DIRECTORIO_MAPA = Path.home()   # castigos.py
```

- Por defecto mapea tu carpeta personal, con 4 niveles de profundidad, un
  máximo de 160 entradas y 14 por carpeta. Oculta las carpetas que empiezan
  por punto y omite `node_modules`, `venv`, etc.
- Con `Path("/")` mapea todo el disco (más lento y con avisos de permisos).
- Si prefieres ver también los archivos ocultos:
  `app.castigos.mapa_archivos(incluir_ocultos=True)`.

Todo esto aparece **en una ventana dentro del quiz** (con barra de desplazamiento
para los informes largos) y además se escribe en la consola.

La geolocalización prueba `ipapi.co`, luego `ipwho.is` y, si falla todo, al
menos saca la IP pública con `ipify`. Se cachea durante la partida. Sin
conexión solo se muestra la IP local. Se puede desactivar con
`PERMITIR_RED = False` en `castigos.py`.

### Jefe final

3 preguntas. Con **2 aciertos o más** se supera. Con **1 o menos** se borra
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
