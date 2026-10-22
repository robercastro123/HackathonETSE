"""Paleta y fuentes compartidas por el quiz y los minijuegos."""

BG = "#0f1117"
PANEL = "#151823"
CARD = "#1a1d27"
FG = "#e6e6e6"
MUTED = "#6b7280"
ACCENT = "#5b8def"
OK = "#3ecf8e"
BAD = "#ef5b5b"
WARN = "#f0b429"
MONO = "#0b0e14"

FUENTE = "Segoe UI"
FUENTE_MONO = "DejaVu Sans Mono"


def ui(tam, negrita=False):
    return (FUENTE, tam, "bold") if negrita else (FUENTE, tam)


def mono(tam=11, negrita=False):
    return (FUENTE_MONO, tam, "bold") if negrita else (FUENTE_MONO, tam)
