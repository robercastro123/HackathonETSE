"""Castigos e inspección del sistema para el quiz.

Dos zonas distintas:

- ``DIRECTORIO_CASTIGO``: aquí SÍ se mueve, modifica y borra. Por defecto es
  ``zona_castigo``, una carpeta de pruebas que se crea sola. Para que actúe
  sobre archivos reales, cámbiala (por ejemplo ``Path.home() / "Escritorio"``).
- ``DIRECTORIO_MAPA``: aquí solo se LEE, para dibujar el mapa de archivos.
  Se elige solo según el sistema: la unidad del sistema (``C:``) en Windows
  y ``/`` en Linux/macOS.

Los puertos, la IP y la geolocalización se consultan de verdad en el equipo.
"""

from __future__ import annotations

import getpass
import json
import os
import platform
import random
import shutil
import socket
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# ---------------------------------------------------------------- ajustes

DIRECTORIO_CASTIGO = Path(__file__).resolve().parent / "zona_castigo"

# Solo lectura: raíz que se recorre para el "mapa de archivos".
# Se elige sola según el sistema operativo:
#   Windows -> C:\   |   Linux / macOS -> /
# Se puede forzar otra cosa, por ejemplo Path.home().
def raiz_del_sistema() -> Path:
    if platform.system() == "Windows":
        unidad = os.environ.get("SystemDrive") or "C:"
        return Path(unidad + "\\")
    return Path("/")


DIRECTORIO_MAPA = raiz_del_sistema()

# Sin conexión, la geolocalización se omite y solo se muestra la IP local.
PERMITIR_RED = True

# Nombres que nunca se tocan aunque el directorio configurado sea el del
# proyecto (evita autodestruirse durante la demo).
PROTEGIDOS = {
    "main.py", "minijuegos.py", "castigos.py", "estilo.py",
    "csv_a_json.py", "preguntas.json", "preguntas.csv", "README.md",
    ".git", "__pycache__", "zona_castigo",
}

# Carpetas que no aportan nada al mapa y lo harían eterno.
RUIDO = {
    ".git", "__pycache__", "node_modules", ".cache", ".venv", "venv",
    ".mypy_cache", ".pytest_cache", "site-packages",
}

# Solo se omiten en el primer nivel (raíz del sistema), para no saltarse
# una carpeta "dev" o "run" que el usuario tenga dentro de su casa.
RUIDO_RAIZ = {
    "proc", "sys", "dev", "run", "snap",
    "Windows", "$Recycle.Bin", "System Volume Information", "Recovery",
    "PerfLogs",
}

SERVICIOS = {
    21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
    80: "HTTP", 110: "POP3", 111: "rpcbind", 135: "MSRPC", 139: "NetBIOS",
    143: "IMAP", 443: "HTTPS", 445: "SMB", 515: "LPD", 631: "IPP",
    993: "IMAPS", 995: "POP3S", 1521: "Oracle", 2049: "NFS",
    3000: "Node/Grafana", 3306: "MySQL", 3389: "RDP", 5000: "Flask/UPnP",
    5432: "PostgreSQL", 5900: "VNC", 5985: "WinRM", 6379: "Redis",
    8000: "HTTP-alt", 8080: "HTTP-alt", 8081: "HTTP-alt", 8443: "HTTPS-alt",
    9090: "Prometheus", 9200: "Elasticsearch", 11211: "Memcached",
    27017: "MongoDB",
}

# Archivos de ejemplo para que la demo tenga algo que mover y romper.
_SEMILLA = {
    "notas_reunion.txt": (
        "Notas de la reunion del lunes\n"
        "- Repasar el guion del quiz\n"
        "- Comprar cables HDMI\n"
        "- Nadie toca la carpeta de produccion\n"
    ),
    "ideas_proyecto.md": (
        "# Ideas\n\n"
        "1. Un quiz que da miedo.\n"
        "2. Un boton que no hace nada.\n"
        "3. Dormir.\n"
    ),
    "contactos.csv": (
        "nombre,email,telefono\n"
        "Ana,ana@example.com,600111222\n"
        "Luis,luis@example.com,600333444\n"
        "Marta,marta@example.com,600555666\n"
    ),
    "presupuesto.txt": (
        "Presupuesto hackathon\n"
        "Pizza: 40 EUR\n"
        "Refrescos: 15 EUR\n"
        "Total: 55 EUR\n"
    ),
    "config_router.txt": (
        "ssid: AULA-3\n"
        "password: no_es_esta\n"
        "canal: 6\n"
    ),
    "diario.txt": (
        "Querido diario: hoy he aceptado jugar a un quiz muy sospechoso.\n"
        "Ojala no haya borrado nada importante.\n"
    ),
    "secretos.txt": (
        "no_leer.txt\n"
        "la_contrasena_es_1234.txt\n"
    ),
    "trabajo/informe_final.txt": (
        "INFORME FINAL\n\n"
        "Conclusion: el proyecto funciona en local.\n"
        "Pendiente: probarlo en el portatil de la demo.\n"
    ),
    "trabajo/borrador.txt": (
        "Borrador v0.3\n"
        "- Introduccion\n"
        "- Desarrollo\n"
        "- Conclusion (escribir)\n"
    ),
    "fotos/vacaciones.txt": (
        "playa.jpg  (2,3 MB)\n"
        "atardecer.jpg  (1,8 MB)\n"
        "grupo.jpg  (2,9 MB)\n"
    ),
    "musica/lista.txt": (
        "cancion1.mp3\n"
        "cancion2.mp3\n"
        "cancion3.mp3\n"
    ),
    "backup_viejo/viejuno.txt": (
        "No borrar. (Bueno, da igual.)\n"
    ),
}


def _dentro(base: Path, ruta: Path) -> bool:
    """True si ``ruta`` está dentro de ``base`` (sin escapes con ..)."""
    try:
        ruta.resolve().relative_to(base.resolve())
        return True
    except (ValueError, OSError):
        return False


def identidad_sistema() -> tuple[str, str]:
    """Usuario real del sistema y nombre del equipo."""
    try:
        usuario = getpass.getuser()
    except Exception:
        usuario = "desconocido"
    try:
        equipo = platform.node() or "desconocido"
    except Exception:
        equipo = "desconocido"
    return usuario, equipo


class Castigos:
    def __init__(self, usuario: str, base: Path | str | None = None,
                 mapa_base: Path | str | None = None,
                 log=None, permitir_red: bool | None = None):
        self.usuario = usuario or "anónimo"
        self.base = Path(base) if base else DIRECTORIO_CASTIGO
        self.mapa_base = Path(mapa_base) if mapa_base else DIRECTORIO_MAPA
        self.log = log or print
        self.permitir_red = PERMITIR_RED if permitir_red is None else permitir_red
        self._cache_geo = None
        self._geo_consultada = False
        self._bolsa = []
        self._preparar()

    def identidad(self) -> tuple[str, str]:
        """Usuario real del sistema y nombre del equipo (para el primer fallo)."""
        return identidad_sistema()

    # ------------------------------------------------------------ base

    def _preparar(self):
        self.base.mkdir(parents=True, exist_ok=True)
        for relativo, contenido in _SEMILLA.items():
            destino = self.base / relativo
            if not destino.exists():
                destino.parent.mkdir(parents=True, exist_ok=True)
                try:
                    destino.write_text(contenido, encoding="utf-8")
                except OSError:
                    pass

    def _archivos(self) -> list[Path]:
        """Archivos tocables, de cualquier subcarpeta, sin protegidos."""
        archivos = []
        for ruta in sorted(self.base.rglob("*")):
            if not ruta.is_file():
                continue
            if any(parte in PROTEGIDOS for parte in ruta.relative_to(self.base).parts):
                continue
            if _dentro(self.base, ruta):
                archivos.append(ruta)
        return archivos

    def _elegir(self) -> Path | None:
        archivos = self._archivos()
        return random.choice(archivos) if archivos else None

    def _rel(self, ruta: Path) -> str:
        try:
            return str(ruta.relative_to(self.base))
        except ValueError:
            return str(ruta)

    def _publicar(self, texto: str) -> str:
        """Muestra el informe sin que una consola rara (cp1252, pythonw) lo tumbe."""
        try:
            self.log(texto)
        except Exception:
            try:
                self.log(texto.encode("ascii", "replace").decode("ascii"))
            except Exception:
                pass
        return texto

    # ------------------------------------------------------- castigos

    def mover_archivos(self) -> str:
        origen = self._elegir()
        if origen is None:
            return self._publicar("[castigo] No queda ningún archivo que mover.")

        destino_dir = self.base / "movidos"
        destino_dir.mkdir(parents=True, exist_ok=True)
        destino = destino_dir / origen.name
        if destino.exists():
            destino = destino_dir / f"{origen.stem}_{random.randint(100, 999)}{origen.suffix}"
        try:
            shutil.move(str(origen), str(destino))
        except OSError as error:
            return self._publicar(f"[castigo] No se pudo mover {self._rel(origen)}: {error}")

        return self._publicar(
            "[castigo] MOVER ARCHIVO\n"
            f"  origen : {self._rel(origen)}\n"
            f"  destino: {self._rel(destino)}"
        )

    def modificar_archivos(self) -> str:
        origen = self._elegir()
        if origen is None:
            return self._publicar("[castigo] No queda ningún archivo que modificar.")

        marca = (
            "\n\n----------------------------------------\n"
            f"archivo modificado por el quiz de {self.usuario}\n"
            "si querías este archivo, deberías haber acertado\n"
            "----------------------------------------\n"
        )
        try:
            with origen.open("a", encoding="utf-8", errors="replace") as archivo:
                archivo.write(marca)
        except OSError as error:
            return self._publicar(f"[castigo] No se pudo modificar {self._rel(origen)}: {error}")

        return self._publicar(
            "[castigo] MODIFICAR ARCHIVO\n"
            f"  archivo: {self._rel(origen)}\n"
            "  añadidas 4 líneas al final"
        )

    def puertos_abiertos(self) -> str:
        def abierto(puerto: int) -> bool:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(0.25)
                    return sock.connect_ex(("127.0.0.1", puerto)) == 0
            except OSError:
                return False

        with ThreadPoolExecutor(max_workers=32) as pool:
            resultados = list(pool.map(abierto, SERVICIOS))

        abiertos = [
            f"  {puerto:>5}/tcp  {servicio}"
            for puerto, servicio, esta in zip(SERVICIOS, SERVICIOS.values(), resultados)
            if esta
        ]
        cabecera = (
            f"[castigo] PUERTOS ABIERTOS EN 127.0.0.1  "
            f"({len(SERVICIOS)} puertos comprobados)"
        )
        if not abiertos:
            return self._publicar(
                cabecera + "\n  (ninguno de los habituales respondió)"
            )
        return self._publicar(cabecera + "\n" + "\n".join(abiertos))

    def _pedir_json(self, url: str, timeout: float):
        with urllib.request.urlopen(url, timeout=timeout) as respuesta:
            return json.load(respuesta)

    def _consultar_geo(self):
        """Intenta varios proveedores; devuelve dict normalizado o None."""
        try:
            datos = self._pedir_json("https://ipapi.co/json/", 2.0)
            if datos.get("ip"):
                return {
                    "ip": datos.get("ip"),
                    "ciudad": datos.get("city"),
                    "region": datos.get("region"),
                    "pais": datos.get("country_name"),
                    "org": datos.get("org"),
                    "lat": datos.get("latitude"),
                    "lon": datos.get("longitude"),
                }
        except Exception:
            pass

        try:
            datos = self._pedir_json("https://ipwho.is/", 2.0)
            if datos.get("success") and datos.get("ip"):
                conexion = datos.get("connection") or {}
                return {
                    "ip": datos.get("ip"),
                    "ciudad": datos.get("city"),
                    "region": datos.get("region"),
                    "pais": datos.get("country"),
                    "org": conexion.get("isp") or conexion.get("org"),
                    "lat": datos.get("latitude"),
                    "lon": datos.get("longitude"),
                }
        except Exception:
            pass

        # Último recurso: al menos la IP pública, sin geolocalización.
        try:
            datos = self._pedir_json("https://api.ipify.org?format=json", 1.5)
            if datos.get("ip"):
                return {"ip": datos.get("ip")}
        except Exception:
            pass
        return None

    def ip_y_geo(self) -> str:
        ip_local = "desconocida"
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect(("8.8.8.8", 80))
                ip_local = sock.getsockname()[0]
        except OSError:
            pass

        try:
            equipo = platform.node() or "desconocido"
        except Exception:
            equipo = "desconocido"

        lineas = [
            "[castigo] DIRECCIÓN IP",
            f"  equipo   : {equipo}",
            f"  IP local : {ip_local}",
        ]

        if not self.permitir_red:
            lineas.append("  IP pública / geolocalización: desactivado")
            return self._publicar("\n".join(lineas))

        datos = self._cache_geo
        if datos is None and not getattr(self, "_geo_consultada", False):
            datos = self._consultar_geo()
            self._cache_geo = datos
            self._geo_consultada = True

        if not datos:
            lineas.append("  IP pública / geolocalización: sin conexión")
            return self._publicar("\n".join(lineas))

        lineas.append(f"  IP pública: {datos.get('ip') or '?'}")
        if datos.get("ciudad") or datos.get("pais"):
            lineas.append(
                "  ubicación : "
                f"{datos.get('ciudad') or '?'}, {datos.get('region') or '?'}, "
                f"{datos.get('pais') or '?'}"
            )
        if datos.get("org"):
            lineas.append(f"  operador  : {datos['org']}")
        lat, lon = datos.get("lat"), datos.get("lon")
        if lat is not None and lon is not None:
            lineas.append(f"  coordenadas: {lat}, {lon}")
            lineas.append(
                f"  mapa: https://www.openstreetmap.org/?mlat={lat}&mlon={lon}"
                f"#map=12/{lat}/{lon}"
            )
        return self._publicar("\n".join(lineas))

    def _listar(self, carpeta: Path, limite: int) -> list[Path]:
        """Lista acotada, pero priorizando directorios.

        Si una carpeta tiene miles de archivos, con un corte ciego se
        perderían sus subcarpetas. Aquí se guardan hasta ``limite`` carpetas
        y hasta ``limite`` archivos, así el mapa nunca se deja los directorios.
        """
        carpetas: list[Path] = []
        archivos: list[Path] = []
        try:
            with os.scandir(carpeta) as entradas:
                for entrada in entradas:
                    ruta = Path(entrada.path)
                    try:
                        es_dir = entrada.is_dir(follow_symlinks=False)
                    except OSError:
                        es_dir = False
                    if es_dir:
                        carpetas.append(ruta)
                    else:
                        archivos.append(ruta)
                    if len(carpetas) >= limite and len(archivos) >= limite:
                        break
        except OSError:
            return []
        return carpetas + archivos

    @staticmethod
    def _clave_orden(ruta: Path):
        prioridad = {
            # carpetas típicas del usuario
            "escritorio": 0, "desktop": 0,
            "documentos": 1, "documents": 1,
            "descargas": 2, "downloads": 2,
            "imágenes": 3, "imagenes": 3, "pictures": 3,
            "música": 4, "musica": 4, "music": 4,
            "vídeos": 5, "videos": 5,
            # raíces importantes: que /bin o /boot no se coman el mapa
            "home": 0, "users": 0, "root": 5, "etc": 6, "var": 7,
            "usr": 8, "opt": 9, "srv": 10, "tmp": 11, "boot": 12,
            "media": 13, "mnt": 14,
            "program files": 5, "program files (x86)": 6, "programdata": 7,
        }
        try:
            es_archivo = ruta.is_file()
        except OSError:
            es_archivo = True
        return (
            1 if es_archivo else 0,
            prioridad.get(ruta.name.lower(), 20),
            ruta.name.lower(),
        )

    def mapa_archivos(self, maximo: int = 160, profundidad: int = 4,
                      por_carpeta: int = 14,
                      incluir_ocultos: bool = False) -> str:
        base = self.mapa_base
        sistema = platform.system() or "?"
        version = platform.release() or "?"
        lineas = [
            f"[castigo] MAPA DE ARCHIVOS · {base}",
            f"  {sistema} {version}  ·  solo lectura",
        ]
        contador = 0

        def recorrer(carpeta: Path, prefijo: str, nivel: int,
                     presupuesto: int) -> int:
            """Añade como mucho ``presupuesto`` líneas y devuelve cuántas usó."""
            nonlocal contador
            if presupuesto <= 0 or contador >= maximo:
                return 0
            if nivel > profundidad:
                lineas.append(f"{prefijo}... (profundidad máxima)")
                return 0

            hijos = self._listar(carpeta, maximo * 2)
            if not incluir_ocultos:
                hijos = [h for h in hijos if not h.name.startswith(".")]
            if not hijos:
                return 0
            hijos.sort(key=self._clave_orden)

            resto = max(0, len(hijos) - por_carpeta)
            visibles = hijos[:por_carpeta]
            usadas = 0

            for posicion, hijo in enumerate(visibles):
                if usadas >= presupuesto or contador >= maximo:
                    break
                ultimo = posicion == len(visibles) - 1 and resto == 0
                rama = "└── " if ultimo else "├── "
                try:
                    es_dir = hijo.is_dir() and not hijo.is_symlink()
                except OSError:
                    es_dir = False

                if es_dir:
                    omitir = hijo.name in RUIDO or (
                        nivel == 0 and hijo.name in RUIDO_RAIZ
                    )
                    if omitir:
                        lineas.append(f"{prefijo}{rama}{hijo.name}/  [omitido]")
                        contador += 1
                        usadas += 1
                        continue

                    lineas.append(f"{prefijo}{rama}{hijo.name}/")
                    contador += 1
                    usadas += 1

                    restante = presupuesto - usadas
                    if restante <= 0:
                        continue
                    # reparto proporcional: ninguna rama se come todo el mapa
                    cuota = max(4, restante // max(1, len(visibles) - posicion))
                    usadas += recorrer(
                        hijo,
                        prefijo + ("    " if ultimo else "│   "),
                        nivel + 1,
                        min(cuota, restante),
                    )
                else:
                    try:
                        tam = hijo.stat().st_size
                    except OSError:
                        tam = 0
                    enlace = " -> enlace" if hijo.is_symlink() else ""
                    lineas.append(
                        f"{prefijo}{rama}{hijo.name}  ({tam} B){enlace}"
                    )
                    contador += 1
                    usadas += 1

            if resto and usadas < presupuesto:
                lineas.append(f"{prefijo}└── ... (+{resto} más)")
            return usadas

        try:
            recorrer(base, "", 0, maximo)
        except Exception as error:  # noqa: BLE001 - un mapa roto no debe tumbar el quiz
            lineas.append(f"  [error al recorrer: {error}]")
        lineas.append(
            f"  {contador} entradas · profundidad {profundidad} · solo lectura"
        )
        return self._publicar("\n".join(lineas))

    def borrar_archivo(self) -> tuple[Path | None, str]:
        """Borra UN archivo. Devuelve (ruta_borrada, reporte)."""
        archivo = self._elegir()
        if archivo is None:
            return None, self._publicar("[castigo] No queda ningún archivo que borrar.")
        if not _dentro(self.base, archivo):
            return None, self._publicar("[castigo] Ruta fuera de la zona permitida. Cancelado.")

        relativo = self._rel(archivo)
        try:
            archivo.unlink()
        except OSError as error:
            return None, self._publicar(f"[castigo] No se pudo borrar {relativo}: {error}")

        return archivo, self._publicar(
            "[castigo] ARCHIVO BORRADO\n"
            f"  {relativo}\n"
            "  no hay copia de seguridad."
        )

    # -------------------------------------------------------- aleatorio

    CASTIGOS = ("mover", "modificar", "puertos", "ip", "mapa")

    def castigo_aleatorio(self) -> tuple[str, str]:
        """Aplica un castigo al azar de los de ronda (sin borrar).

        Se usa una bolsa barajada: en cinco fallos salen los cinco tipos, sin
        repetir hasta haberlos agotado.
        """
        if not self._bolsa:
            self._bolsa = list(self.CASTIGOS)
            random.shuffle(self._bolsa)
        nombre = self._bolsa.pop()
        acciones = {
            "mover": self.mover_archivos,
            "modificar": self.modificar_archivos,
            "puertos": self.puertos_abiertos,
            "ip": self.ip_y_geo,
            "mapa": self.mapa_archivos,
        }
        return nombre, acciones[nombre]()
