# HackathonETSE

Quiz kiosco en pantalla completa con un minijuego, comodines y castigos.

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
minijuego (pinchos, sin tiempo) -> 5 preguntas -> jefe final (3, hacen falta 2)
```

Al empezar se detecta automáticamente el usuario del sistema (no se pregunta
nada). Se usan 8 preguntas al azar de `preguntas.json` (5 de la ronda y 3 del
jefe). Si añades más filas al CSV, se mezclan automáticamente; hacen falta al
menos 8.

Cada pregunta muestra su **categoría con el nombre completo**:

| Código | Nombre |
|--------|--------|
| `Geo` | Geografía |
| `CiNat` | Ciencias Naturales |
| `Hist` | Historia |
| `Entre` | Entretenimiento |
| `ArLit` | Arte y Literatura |
| `DepCo` | Deporte y Comida |
| `Prog` | Programación |
| `Act` | Actualidad |

### Minijuego

Solo hay uno: **Don't Touch the Spikes**, y ya **no tiene límite de tiempo**.
Pulsa `espacio` para aletear y pasa por los huecos; termina cuando chocas.
Da comodines según el rango:

| Rango | Comodines | Puntos |
|-------|-----------|--------|
| alto  | 2 | 6 o más huecos |
| medio | 1 | 3 a 5 |
| bajo  | 0 | 0 a 2 |

Los otros cinco minijuegos siguen en `minijuegos.py` (`MINIJUEGOS_ANTIGUOS`)
por si quieres recuperarlos, pero no entran en la partida.

### Comodines

Los comodines del minijuego se usan en las 5 preguntas y en el jefe final.
Al fallar, si queda alguno, se gasta automáticamente: **ni castigo ni nombre**,
y repites la misma pregunta con la opción fallada bloqueada.

### Fallos

- **Cada fallo sin comodín en las 5 preguntas aplica un castigo**, también el
  primero. En el primer fallo, además, se imprime el nombre del usuario real
  del sistema y el equipo (por pantalla y en la consola).
- La pregunta **no avanza hasta que aciertas**: la opción fallada se queda
  bloqueada y las demás siguen disponibles.
- Los castigos no se repiten hasta que han salido los cinco. Si se agotan,
  la bolsa se vuelve a barajar.
  - mover un archivo,
  - modificar un archivo,
  - listar los puertos abiertos de `127.0.0.1`,
  - mostrar IP local, IP pública y geolocalización (si hay red),
  - dibujar el mapa de archivos del sistema.
- **Jefe final:** no hay castigos. Cada pregunta se resuelve al fallar (se
  revela la correcta y se pasa a la siguiente), para que el veredicto 2/3
  tenga sentido.

### Jefe final

3 preguntas. Con **2 aciertos o más** se supera. Con **1 o menos** se borra
un archivo de la zona de castigo.

## Inspección del sistema

Los puertos, la IP y la geolocalización se consultan de verdad en el equipo.

### Puertos

Se comprueba una lista **fija de 43 puertos TCP habituales** en `127.0.0.1` y
`::1` (loopback), y se indica en cuál aceptó la conexión. Solo se listan los
que están realmente abiertos; los cerrados no aparecen. El escaneo es real y
rápido (~0,02 s). La lista está en `SERVICIOS`, al principio de
`castigos.py`. Si no hay **ninguno** abierto, el castigo de puertos se salta
automáticamente y se aplica otro distinto.

Aquí, por ejemplo, aparecen `22/tcp SSH` y `631/tcp IPP`.

### IP y geolocalización

Se consultan **5 proveedores en paralelo** (`ipapi.co`, `ipwho.is`,
`ip-api.com`, `freeipapi`, `ipinfo.io`), se agrupan las respuestas que coinciden
y se descartan las que se van a otra provincia (más de 40 km). Muestra ciudad,
código postal, coordenadas, la dispersión entre fuentes (`±X km`) y un enlace
al mapa. La primera consulta tarda ~1 s y se cachea durante la partida.

Es geolocalización **por IP**: la precisión real es de ciudad, no de GPS. Sin
conexión solo se muestra la IP local. Se puede desactivar con
`PERMITIR_RED = False` en `castigos.py`.

### Mapa de archivos

Recorre una carpeta **en modo solo lectura** y **detecta el sistema operativo
automáticamente**:

```python
DIRECTORIO_MAPA = raiz_del_sistema()
# Windows -> C:\      Linux / macOS -> /
```

- La cabecera muestra el sistema detectado (p. ej. `Linux 7.0…`).
- Se puede forzar otra raíz, por ejemplo tu carpeta personal:
  `DIRECTORIO_MAPA = Path.home()`.
- 8 niveles de profundidad, máximo 240 entradas y 16 por carpeta. El
  presupuesto se reparte entre las ramas para que `/boot` o `/etc` no se coman
  el mapa y siempre salgan `/home`, `/etc`, `/var`, `/usr`, etc. Se puede
  ajustar con `MAPA_PROFUNDIDAD`, `MAPA_MAXIMO` y `MAPA_POR_CARPETA` al
  principio de `castigos.py`.
- Muestra siempre los directorios primero: aunque una carpeta tenga miles de
  archivos, sus subcarpetas no se pierden. Oculta las carpetas que empiezan por
  punto y omite `node_modules`, `venv`, `/proc`, `/sys`, `Windows`, etc.
- Si prefieres ver también los archivos ocultos:
  `app.castigos.mapa_archivos(incluir_ocultos=True)`.

Todo esto aparece **en una ventana dentro del quiz** (con barra de
desplazamiento para los informes largos) y además se escribe en la consola.

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

### Borrado real en el ordenador (opcional y comentado)

Al final de `castigos.py` hay un bloque **comentado** con
`borrar_archivo_real()`. Está desactivado a propósito: por defecto el jefe
final solo borra en `zona_castigo/`. Para activarlo:

1. Descomenta el bloque entero.
2. En `main.py`, dentro de `_veredicto_jefe()`, cambia
   `self.castigos.borrar_archivo()` por `borrar_archivo_real(self.usuario)`
   y añade `borrar_archivo_real` al import.
3. Ajusta `DIRECTORIO_BORRADO_REAL` (por defecto `Path.home()`).

Qué hace y qué evita:

- Elige **un archivo al azar** entre hasta 4000 candidatos y lo borra con
  `unlink()` (sin papelera).
- No sigue enlaces simbólicos.
- No entra en carpetas de sistema (`Windows`, `System32`, `/usr`, `/etc`…),
  ocultas (`.ssh`, `.config`…), de desarrollo (`node_modules`, `venv`) ni en
  `zona_castigo`.
- Protege los archivos del propio quiz.
- **No lo apuntes a `/` ni a `C:\`**: podrías dejar el sistema sin arrancar.

## Salir

- El botón **Salir** de la pantalla final.
- **Salida de emergencia del operador:** pulsa `F12` tres veces seguidas.
- `Ctrl+Alt+Supr` sigue funcionando siempre (no se bloquea a propósito).

## Archivos

| Archivo | Contenido |
|---------|-----------|
| `main.py` | flujo del quiz, pantallas, comodines, jefe final y bloqueos |
| `minijuegos.py` | los minijuegos y el sistema de rangos |
| `castigos.py` | mover/modificar/borrar, puertos, IP, mapa y geolocalización |
| `estilo.py` | colores y fuentes |
| `csv_a_json.py` | conversor de `preguntas.csv` a `preguntas.json` |

El conversor admite el formato del CSV incluido: `Categoría`, `Pregunta`,
`Correcta`, `Incorr1`, `Incorr2` e `Incorr3`. También admite CSV con cuatro
columnas de opciones (`opcion_a` a `opcion_d`) y `respuesta_correcta`.
Las filas sin pregunta se ignoran. Las opciones se mezclan de forma estable
para cada pregunta, y el índice de la respuesta correcta se guarda en el JSON.

`main.py` carga `preguntas.json` desde la misma carpeta. Si se modifica el CSV,
vuelve a ejecutar el conversor antes de iniciar el quiz.
