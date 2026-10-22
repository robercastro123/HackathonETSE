"""Castigos del quiz.

Todo lo que se mueve, se modifica o se borra ocurre dentro de
``DIRECTORIO_CASTIGO``. Por defecto es una carpeta de pruebas llamada
``zona_castigo`` que se crea sola al lado de este archivo.

Si quieres que los castigos actúen sobre archivos de verdad, cambia
``DIRECTORIO_CASTIGO`` por la carpeta que quieras (por ejemplo
``Path.home() / "Escritorio"``). Aun así el módulo se niega a salir de esa
carpeta y protege los archivos del propio proyecto.
"""

from __future__ import annotations

import json
import random
import shutil
import socket
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# ---------------------------------------------------------------- ajustes

DIRECTORIO_CASTIGO = Path(__file__).resolve().parent / "zona_castigo"

# Sin conexión, la geolocalización se omite y solo se muestra la IP local.
PERMITIR_RED = True

# Nombres que nunca se tocan aunque el directorio configurado sea el del
# proyecto (evita autodestruirse durante la demo).
PROTEGIDOS = {
    "main.py", "minijuegos.py", "castigos.py", "estilo.py",
    "csv_a_json.py", "preguntas.json", "preguntas.csv", "README.md",
    ".git", "__pycache__", "zona_castigo",
}

SERVICIOS = {
    21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
    80: "HTTP", 110: "POP3", 143: "IMAP", 443: "HTTPS", 445: "SMB",
    3306: "MySQL", 3389: "RDP", 5432: "PostgreSQL", 5900: "VNC",
    6379: "Redis", 8000: "HTTP-alt", 8080: "HTTP-alt", 8443: "HTTPS-alt",
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


class Castigos:
    def __init__(self, usuario: str, base: Path | str | None = None,
                 log=None, permitir_red: bool | None = None):
        self.usuario = usuario or "anónimo"
        self.base = Path(base) if base else DIRECTORIO_CASTIGO
        self.log = log or print
        self.permitir_red = PERMITIR_RED if permitir_red is None else permitir_red
        self._preparar()

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
        self.log(texto)
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
        if not abiertos:
            return self._publicar(
                "[castigo] PUERTOS ABIERTOS EN 127.0.0.1\n"
                "  (ninguno de los habituales respondió)"
            )
        return self._publicar(
            "[castigo] PUERTOS ABIERTOS EN 127.0.0.1\n" + "\n".join(abiertos)
        )

    def ip_y_geo(self) -> str:
        ip_local = "desconocida"
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect(("8.8.8.8", 80))
                ip_local = sock.getsockname()[0]
        except OSError:
            pass

        lineas = ["[castigo] DIRECCIÓN IP", f"  IP local : {ip_local}"]

        if not self.permitir_red:
            lineas.append("  IP pública / geolocalización: desactivado")
            return self._publicar("\n".join(lineas))

        datos = None
        try:
            with urllib.request.urlopen(
                "https://ipapi.co/json/", timeout=2.5
            ) as respuesta:
                datos = json.load(respuesta)
        except Exception:
            datos = None

        if not datos:
            lineas.append("  IP pública / geolocalización: sin conexión")
            return self._publicar("\n".join(lineas))

        ciudad = datos.get("city") or "?"
        region = datos.get("region") or "?"
        pais = datos.get("country_name") or "?"
        org = datos.get("org") or "?"
        lat = datos.get("latitude")
        lon = datos.get("longitude")

        lineas.append(f"  IP pública: {datos.get('ip', '?')}")
        lineas.append(f"  ubicación : {ciudad}, {region}, {pais}")
        lineas.append(f"  operador  : {org}")
        if lat is not None and lon is not None:
            lineas.append(f"  coordenadas: {lat}, {lon}")
            lineas.append(
                f"  mapa: https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=12/{lat}/{lon}"
            )
        return self._publicar("\n".join(lineas))

    def mapa_archivos(self, maximo: int = 120) -> str:
        lineas = [f"[castigo] MAPA DE {self.base}"]
        contador = 0

        def recorrer(carpeta: Path, prefijo: str):
            nonlocal contador
            try:
                hijos = sorted(carpeta.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
            except OSError:
                return
            for posicion, hijo in enumerate(hijos):
                if contador >= maximo:
                    return
                ultimo = posicion == len(hijos) - 1
                rama = "└── " if ultimo else "├── "
                if hijo.is_dir():
                    lineas.append(f"{prefijo}{rama}{hijo.name}/")
                    contador += 1
                    recorrer(hijo, prefijo + ("    " if ultimo else "│   "))
                else:
                    try:
                        tam = hijo.stat().st_size
                    except OSError:
                        tam = 0
                    lineas.append(f"{prefijo}{rama}{hijo.name}  ({tam} B)")
                    contador += 1
                if contador >= maximo:
                    lineas.append(f"{prefijo}    ... (lista truncada)")
                    return

        recorrer(self.base, "")
        if not lineas[1:]:
            lineas.append("  (vacío)")
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

    CASTIGOS = (
        ("mover", 30),
        ("modificar", 30),
        ("puertos", 15),
        ("ip", 10),
        ("mapa", 15),
    )

    def castigo_aleatorio(self) -> tuple[str, str]:
        """Aplica un castigo al azar de los de ronda (sin borrar)."""
        nombres = [nombre for nombre, _ in self.CASTIGOS]
        pesos = [peso for _, peso in self.CASTIGOS]
        nombre = random.choices(nombres, weights=pesos, k=1)[0]
        acciones = {
            "mover": self.mover_archivos,
            "modificar": self.modificar_archivos,
            "puertos": self.puertos_abiertos,
            "ip": self.ip_y_geo,
            "mapa": self.mapa_archivos,
        }
        return nombre, acciones[nombre]()
