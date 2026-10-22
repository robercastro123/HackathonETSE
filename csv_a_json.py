#!/usr/bin/env python3
"""Convierte un CSV de preguntas a JSON con el formato de Quiz Kiosco.

El CSV debe tener estas columnas (no importan mayúsculas, tildes ni espacios):

    pregunta
    opcion_a, opcion_b, opcion_c, opcion_d
    respuesta_correcta        (letra A-D o el texto exacto de una opción)

Columnas opcionales:

    categoria                 (si falta, se usa la ronda o "General")
    ronda                     (se usa como "Ronda N" si no hay categoría)

También se admite «respuesta» o «correcta» en lugar de «respuesta_correcta».

Uso:
    python3 csv_a_json.py preguntas.csv preguntas.json
    python3 csv_a_json.py preguntas.csv                  # imprime por pantalla
    python3 csv_a_json.py preguntas.csv salida.json --categoria "Informática"
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import random
import re
import sys
import unicodedata
from pathlib import Path


class ErrorCsv(Exception):
    """Error de formato o de contenido del CSV."""


COLUMNAS_REQUERIDAS = (
    "pregunta",
    "opcion_a",
    "opcion_b",
    "opcion_c",
    "opcion_d",
    "respuesta_correcta",
)

ALIAS_COLUMNAS = {
    "preguntas": "pregunta",
    "respuesta": "respuesta_correcta",
    "correcta": "respuesta_correcta",
    "respuestas": "respuesta_correcta",
    "opcion_1": "opcion_a",
    "opcion_2": "opcion_b",
    "opcion_3": "opcion_c",
    "opcion_4": "opcion_d",
    "incorrecta_1": "incorr1",
    "incorrecta_2": "incorr2",
    "incorrecta_3": "incorr3",
}


def _sin_tildes(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in normalizado if not unicodedata.combining(c))


def _normalizar_cabecera(texto: str) -> str:
    texto = _sin_tildes(texto).strip().lower()
    texto = re.sub(r"[^a-z0-9]+", "_", texto).strip("_")
    return ALIAS_COLUMNAS.get(texto, texto)


def _normalizar_texto(texto: str) -> str:
    return " ".join(_sin_tildes(texto).strip().lower().split())


def _leer_texto(ruta: Path) -> str:
    for codificacion in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return ruta.read_text(encoding=codificacion)
        except UnicodeDecodeError:
            continue
    raise ErrorCsv(f"No se pudo leer {ruta} con una codificación conocida.")


def _indice_correcto(respuesta: str, opciones: list[str]) -> int | None:
    """Devuelve el índice 0-3 de la respuesta correcta, o None si no coincide."""
    buscada = _normalizar_texto(respuesta)

    # 1) Coincidencia exacta con el texto de una opción.
    for indice, opcion in enumerate(opciones):
        if _normalizar_texto(opcion) == buscada:
            return indice

    # 2) Letra: A, B, C, D (también admite "B)", "C.", etc.).
    letra = re.fullmatch(r"([abcd])\s*[\).:\-]?", _sin_tildes(respuesta).strip().lower())
    if letra:
        return "abcd".index(letra.group(1))

    # 3) Número de opción: 1-4.
    if respuesta.strip() in {"1", "2", "3", "4"}:
        return int(respuesta.strip()) - 1

    return None


def convertir_csv(ruta_csv: str | Path, categoria_fija: str | None = None) -> list[dict]:
    """Lee el CSV y devuelve una lista de diccionarios lista para json.dump()."""
    ruta = Path(ruta_csv)
    if not ruta.exists():
        raise ErrorCsv(f"No se encontró el archivo: {ruta}")

    texto = _leer_texto(ruta)
    if not texto.strip():
        raise ErrorCsv("El CSV está vacío.")

    try:
        dialecto = csv.Sniffer().sniff(texto[:4096], delimiters=",;\t")
    except csv.Error:
        dialecto = csv.excel

    lector = csv.DictReader(io.StringIO(texto), dialect=dialecto)
    encabezados: dict[str, str] = {}
    for original in (lector.fieldnames or []):
        clave = _normalizar_cabecera(original)
        if clave and clave not in encabezados:
            encabezados[clave] = original

    formato_actual = all(
        columna in encabezados
        for columna in (
            "pregunta", "respuesta_correcta", "incorr1", "incorr2", "incorr3"
        )
    )
    requeridas = (
        ("pregunta", "respuesta_correcta", "incorr1", "incorr2", "incorr3")
        if formato_actual
        else COLUMNAS_REQUERIDAS
    )
    faltantes = [columna for columna in requeridas if columna not in encabezados]
    if faltantes:
        raise ErrorCsv(
            "Faltan columnas obligatorias: " + ", ".join(faltantes) +
            ".\nColumnas encontradas: " +
            ", ".join(encabezados.values() if encabezados else ["(ninguna)"])
        )

    def valor(fila: dict, columna: str) -> str:
        if columna not in encabezados:
            return ""
        return (fila.get(encabezados[columna]) or "").strip()

    preguntas: list[dict] = []
    errores: list[str] = []

    for numero_fila, fila in enumerate(lector, start=2):
        if not any(valor(fila, columna) for columna in requeridas):
            continue  # línea vacía

        enunciado = valor(fila, "pregunta")
        if formato_actual:
            respuesta = valor(fila, "respuesta_correcta")
            opciones = [respuesta] + [
                valor(fila, f"incorr{numero}") for numero in range(1, 4)
            ]
        else:
            opciones = [valor(fila, f"opcion_{letra}") for letra in "abcd"]
            respuesta = valor(fila, "respuesta_correcta")

        if not enunciado:
            errores.append(f"Fila {numero_fila}: la pregunta está vacía.")
            continue
        if any(not opcion for opcion in opciones):
            errores.append(f"Fila {numero_fila}: faltan opciones (se necesitan 4).")
            continue

        if formato_actual:
            # Use a stable per-question order so repeated conversions produce
            # the same JSON without making the correct option always first.
            random.Random(enunciado).shuffle(opciones)
            indice = next(
                i for i, opcion in enumerate(opciones)
                if opcion == respuesta
            )
        else:
            if not respuesta:
                errores.append(f"Fila {numero_fila}: falta la respuesta correcta.")
                continue

            indice = _indice_correcto(respuesta, opciones)
            if indice is None:
                errores.append(
                    f"Fila {numero_fila}: la respuesta «{respuesta}» no es una letra "
                    "A-D, un número 1-4 ni el texto de una opción."
                )
                continue

        if categoria_fija:
            categoria = categoria_fija
        else:
            categoria = valor(fila, "categoria")
            if not categoria:
                ronda = valor(fila, "ronda")
                categoria = f"Ronda {ronda}" if ronda else "General"

        preguntas.append({
            "categoria": categoria,
            "pregunta": enunciado,
            "opciones": opciones,
            "correcta": indice,
        })

    if errores:
        mensaje_error = f"Se encontraron {len(errores)} error(es):\n" + "\n".join(errores)
        raise ErrorCsv(mensaje_error)
        
    if not preguntas:
        raise ErrorCsv("El CSV no contiene ninguna pregunta válida.")
    return preguntas


def guardar_json(preguntas: list[dict], ruta_salida: str | Path) -> None:
    ruta = Path(ruta_salida)
    if ruta.parent and not ruta.parent.exists():
        ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8") as archivo:
        json.dump(preguntas, archivo, ensure_ascii=False, indent=2)
        archivo.write("\n")


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(
        description="Convierte un CSV de preguntas al JSON de Quiz Kiosco.",
    )
    analizador.add_argument("csv", help="Archivo CSV de entrada.")
    analizador.add_argument(
        "json", nargs="?", help="Archivo JSON de salida (si se omite, usa stdout).",
    )
    analizador.add_argument(
        "-c", "--categoria",
        help="Fuerza esta categoría para todas las preguntas (ignora la del CSV).",
    )
    argumentos = analizador.parse_args(argv)

    try:
        preguntas = convertir_csv(argumentos.csv, argumentos.categoria)
    except (ErrorCsv, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    if argumentos.json:
        guardar_json(preguntas, argumentos.json)
        print(
            f"Convertidas {len(preguntas)} preguntas en {argumentos.json}",
            file=sys.stderr,
        )
    else:
        print(json.dumps(preguntas, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())