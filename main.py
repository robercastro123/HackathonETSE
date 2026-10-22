#!/usr/bin/env python3
"""
Quiz Kiosco - Hackathon
Pantalla completa sin salida manual.

Flujo de la partida:

    minijuego (pinchos, sin tiempo) -> 5 preguntas -> jefe final (3)

- El minijuego da comodines según el rango:
      alto  2 | medio  1 | bajo  0
  Un comodín se gasta al fallar: evita el castigo y deja reintentar.
- Cada fallo SIN comodín en las preguntas aplica un castigo (sin repetir
  hasta agotar los cinco) y repite la misma pregunta hasta acertar.
- El primer fallo SIN comodín, además, imprime el nombre del usuario del
  sistema por pantalla.
- En el jefe final no hay castigos y hacen falta 2 aciertos de 3; con 1 o
  menos se borra un archivo.

Los castigos actúan SOLO dentro de ``zona_castigo`` (ver castigos.py).
Salida de emergencia para el operador: pulsar F12 tres veces seguidas.
Ctrl+Alt+Supr sigue funcionando siempre.
"""

import json
import random
import sys
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

import estilo as T
from castigos import Castigos, identidad_sistema
from minijuegos import MINIJUEGOS

# ----------------------------------------------------------------------
# CONFIGURACIÓN — edita esto
# ----------------------------------------------------------------------

BLOQUEO_GLOBAL = True            # Nivel 2: tecla Windows y Alt+Tab
BLOQUEO_REGISTRO = True          # Nivel 3: Task Manager y Win+L (solo Windows)

PREGUNTAS_POR_RONDA = len(Castigos.CASTIGOS)  # una por cada castigo distinto
PREGUNTAS_JEFE = 3
ACIERTOS_MINIMOS_JEFE = 2
NEUTRALIZAR_ATAJOS = ("<Alt-F4>", "<Control-w>", "<Control-q>",
                      "<Control-W>", "<Control-Q>", "<Alt-Tab>")

CATEGORIAS = {
    "Act": "Actualidad",
    "ArLit": "Arte y Literatura",
    "CiNat": "Ciencias Naturales",
    "DepCo": "Deporte y Comida",
    "Entre": "Entretenimiento",
    "Geo": "Geografía",
    "Hist": "Historia",
    "Prog": "Programación",
}

try:
    import keyboard  # pip install keyboard
    _KEYBOARD_OK = True
except Exception:
    _KEYBOARD_OK = False

try:
    import winreg  # noqa: solo Windows
    _WINREG_OK = True
except Exception:
    _WINREG_OK = False


def _imprimir(texto):
    """print que no rompe si no hay consola (pythonw, .exe sin terminal)."""
    try:
        print(texto)
    except Exception:
        pass


class BloqueoRegistro:
    """Nivel 3: deshabilita Administrador de tareas y Win+L por registro.

    Escribe dos valores DWORD = 1 bajo
    HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\System.
    Guarda el estado previo y lo restaura exactamente al salir.
    """

    _SUBKEY = r"Software\Microsoft\Windows\CurrentVersion\Policies\System"
    _VALORES = ("DisableTaskMgr", "DisableLockWorkstation")

    def __init__(self):
        self._activo = False
        self._previos = {}

    def activar(self):
        if not _WINREG_OK:
            return False
        try:
            clave = winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER, self._SUBKEY, 0,
                winreg.KEY_READ | winreg.KEY_SET_VALUE,
            )
            try:
                for nombre in self._VALORES:
                    try:
                        valor, _ = winreg.QueryValueEx(clave, nombre)
                        self._previos[nombre] = valor
                    except FileNotFoundError:
                        self._previos[nombre] = None
                    winreg.SetValueEx(clave, nombre, 0, winreg.REG_DWORD, 1)
            finally:
                winreg.CloseKey(clave)
            self._activo = True
            return True
        except Exception as error:
            messagebox.showinfo(
                "Bloqueo de registro desactivado",
                "No se pudieron escribir las políticas de registro.\n\n"
                f"Detalle: {error}",
            )
            self._activo = False
            return False

    def restaurar(self):
        if not self._activo:
            return
        try:
            clave = winreg.OpenKeyEx(
                winreg.HKEY_CURRENT_USER, self._SUBKEY, 0,
                winreg.KEY_SET_VALUE,
            )
            try:
                for nombre, previo in self._previos.items():
                    if previo is None:
                        try:
                            winreg.DeleteValue(clave, nombre)
                        except FileNotFoundError:
                            pass
                    else:
                        winreg.SetValueEx(clave, nombre, 0, winreg.REG_DWORD, previo)
            finally:
                winreg.CloseKey(clave)
        except Exception:
            pass
        finally:
            self._activo = False


class Aplicacion:
    def __init__(self, root, preguntas):
        self.root = root
        self.preguntas = preguntas

        self.usuario = "anónimo"
        self.equipo = ""
        self.castigos = None
        self.registro = []
        self.pantalla = None
        self.pregunta_actual = None
        self.es_jefe = False
        self.seleccion = None
        self.opciones = []
        self.respondida = True
        self.bloqueadas = set()
        self.comodines = 0
        self.aciertos = 0
        self.fallos = 0
        self.comodines_usados = 0
        self.aciertos_jefe = 0
        self.jefe_idx = 0
        self.primer_fallo = True
        self.ronda_actual = 1
        self.indice_pregunta = 0
        self.preguntas_ronda = []
        self.minijuegos = []
        self._f12 = []

        root.title("Quiz Hackathon")
        root.configure(bg=T.BG)
        root.attributes("-fullscreen", True)
        root.attributes("-topmost", True)

        root.protocol("WM_DELETE_WINDOW", lambda: None)
        root.bind("<Escape>", lambda evento: "break")
        for secuencia in NEUTRALIZAR_ATAJOS:
            root.bind(secuencia, lambda evento: "break")
        root.bind("<FocusOut>", self._recuperar_foco)
        root.bind("<F12>", self._salida_emergencia)

        self._bloqueo_global_activo = False
        if BLOQUEO_GLOBAL and _KEYBOARD_OK:
            self._activar_bloqueo_global()

        self.bloqueo_registro = BloqueoRegistro()
        if BLOQUEO_REGISTRO:
            self.bloqueo_registro.activar()

        self.contenedor = tk.Frame(root, bg=T.BG)
        self.contenedor.pack(fill="both", expand=True)

        _imprimir("[quiz] salida de emergencia del operador: F12 tres veces seguidas")
        self._pantalla_inicio()

    # ---------------------------------------------------------- utilidades

    def _consola(self, texto):
        _imprimir(texto)
        self.registro.append(texto)
        if len(self.registro) > 300:
            del self.registro[:100]

    def _nueva(self):
        return tk.Frame(self.contenedor, bg=T.BG)

    def _mostrar(self, pantalla):
        anterior = self.pantalla
        self.pantalla = pantalla
        pantalla.pack(fill="both", expand=True)
        if anterior is not None:
            try:
                anterior.destroy()
            except Exception:
                pass

    def _boton(self, padre, texto, comando, color=T.ACCENT):
        return tk.Button(
            padre, text=texto, command=comando, font=T.ui(15, True),
            bg=color, fg="white", activebackground=color,
            activeforeground="white", relief="flat", padx=30, pady=10,
            cursor="hand2",
        )

    def _texto(self, padre, texto, tam=13, color=T.FG, negrita=False,
               pady=4, wrap=1040):
        etiqueta = tk.Label(
            padre, text=texto, font=T.ui(tam, negrita), bg=T.BG, fg=color,
            wraplength=wrap, justify="center",
        )
        etiqueta.pack(pady=pady)
        return etiqueta

    # ------------------------------------------------------------- inicio

    def _pantalla_inicio(self):
        f = self._nueva()
        self._texto(f, "QUIZ HACKATHON", 44, T.ACCENT, True, pady=(70, 4))
        self._texto(
            f, f"1 minijuego · {PREGUNTAS_POR_RONDA} preguntas · "
               f"jefe final de {PREGUNTAS_JEFE}",
            16, T.MUTED, False, pady=(0, 30),
        )
        self._texto(
            f,
            "Cada fallo sin comodín tiene consecuencias.\n"
            "El sistema ya sabe quién está jugando.",
            14, T.WARN, False, pady=(0, 34),
        )

        self._boton(f, "EMPEZAR", self._empezar_partida).pack(pady=26)
        self._mostrar(f)

    def _empezar_partida(self):
        sistema, equipo = identidad_sistema()
        self.usuario = sistema
        self.equipo = equipo

        necesarias = PREGUNTAS_POR_RONDA + PREGUNTAS_JEFE
        if len(self.preguntas) < necesarias:
            raise SystemExit(
                f"Faltan preguntas: hay {len(self.preguntas)} y hacen falta "
                f"{necesarias}. Añade más filas a preguntas.csv y reconvierte."
            )
        random.shuffle(self.preguntas)
        self.ronda_1 = self.preguntas[:PREGUNTAS_POR_RONDA]
        self.jefe = self.preguntas[PREGUNTAS_POR_RONDA:necesarias]

        self.minijuegos = random.sample(list(MINIJUEGOS), 1)
        self.castigos = Castigos(self.usuario, log=self._consola)
        self._consola("[quiz] ------------------------------------------")
        self._consola(f"[quiz] usuario del sistema: {self.usuario}")
        self._consola(f"[quiz] equipo: {self.equipo}")
        self._consola(f"[quiz] zona de castigo: {self.castigos.base}")
        self._consola("[quiz] ------------------------------------------")

        self._lanzar_minijuego()

    # --------------------------------------------------------- minijuegos

    def _lanzar_minijuego(self):
        clase = self.minijuegos[0]

        f = self._nueva()
        self._texto(f, "MINIJUEGO", 14, T.MUTED, True, pady=(70, 6))
        self._texto(f, clase.nombre, 42, T.ACCENT, True, pady=(0, 10))
        self._texto(f, clase.ayuda, 16, T.FG, False, pady=(0, 26))
        self._texto(
            f,
            "Rango ALTO  +2 comodines     Rango MEDIO  +1     "
            "Rango BAJO  +0\n"
            + (
                f"Duración: {int(clase.duracion)} segundos"
                if clase.duracion
                else "Sin límite de tiempo: hasta que choques"
            ),
            14, T.MUTED, False, pady=(0, 30),
        )
        self._boton(
            f, "JUGAR", lambda: self._empezar_minijuego(clase)
        ).pack()
        self._mostrar(f)

    def _empezar_minijuego(self, clase):
        juego = clase(self.contenedor, self._fin_minijuego)
        self._mostrar(juego)

    def _fin_minijuego(self, puntos, rango, comodines):
        self.comodines += comodines
        f = self._nueva()
        color = {"alto": T.OK, "medio": T.WARN, "bajo": T.BAD}[rango]
        self._texto(f, f"RANGO {rango.upper()}", 42, color, True, pady=(110, 10))
        self._texto(f, f"{puntos} puntos", 26, T.FG, True, pady=(0, 16))
        self._texto(
            f,
            f"+{comodines} comodín(es)   ·   acumulas {self.comodines}",
            17, color, True, pady=(0, 30),
        )
        self._texto(
            f,
            "Un comodín se gasta al fallar, evita el castigo y te deja "
            "volver a intentarlo.",
            13, T.MUTED, False, pady=(0, 30),
        )
        self._boton(f, "CONTINUAR", self._tras_minijuego).pack()
        self._mostrar(f)

    def _tras_minijuego(self):
        self._empezar_ronda(1)

    # ------------------------------------------------------------ rondas

    def _empezar_ronda(self, numero):
        self.ronda_actual = numero
        self.preguntas_ronda = self.ronda_1
        self.indice_pregunta = 0
        self._pantalla_pregunta()

    def _avanzar(self):
        if self.es_jefe:
            self.jefe_idx += 1
            if self.jefe_idx >= PREGUNTAS_JEFE:
                self._veredicto_jefe()
            else:
                self._pantalla_pregunta(es_jefe=True)
            return

        self.indice_pregunta += 1
        if self.indice_pregunta >= len(self.preguntas_ronda):
            self._intro_jefe()
        else:
            self._pantalla_pregunta()

    # --------------------------------------------------------- preguntas

    def _pantalla_pregunta(self, es_jefe=False):
        self.es_jefe = es_jefe
        if es_jefe:
            pregunta = self.jefe[self.jefe_idx]
        else:
            pregunta = self.preguntas_ronda[self.indice_pregunta]

        self.pregunta_actual = pregunta
        self.respondida = False
        self.bloqueadas = set()
        self.seleccion = tk.IntVar(value=-1)
        self.opciones = []

        f = self._nueva()
        acento = T.BAD if es_jefe else T.ACCENT

        if es_jefe:
            cabecera = (f"JEFE FINAL  ·  pregunta {self.jefe_idx + 1} "
                        f"de {PREGUNTAS_JEFE}")
        else:
            cabecera = (f"PREGUNTAS  ·  {self.indice_pregunta + 1} de "
                        f"{PREGUNTAS_POR_RONDA}")
        self._texto(f, cabecera, 15, acento, True, pady=(22, 2))

        self.lbl_stats = self._texto(
            f, self._texto_stats(), 12, T.MUTED, False, pady=(0, 10),
        )
        categoria = pregunta.get("categoria", "")
        self._texto(
            f, f"Categoría: {CATEGORIAS.get(categoria, categoria)}",
            12, T.MUTED, True, pady=0,
        )

        self._texto(f, pregunta["pregunta"], 26, T.FG, True, pady=(10, 22))

        marco = tk.Frame(f, bg=T.BG)
        marco.pack()
        for indice, opcion in enumerate(pregunta["opciones"]):
            boton = tk.Radiobutton(
                marco, text=opcion, variable=self.seleccion, value=indice,
                font=T.ui(17), bg=T.CARD, fg=T.FG, selectcolor="#2b3550",
                activebackground=T.CARD, activeforeground=T.FG,
                indicatoron=False, anchor="w", justify="left",
                padx=20, pady=11, width=64, wraplength=760,
                relief="flat", highlightthickness=0,
                command=self._on_seleccion,
            )
            boton.pack(pady=5, fill="x")
            self.opciones.append(boton)

        self.feedback = tk.Label(
            f, text="", font=T.ui(15, True), bg=T.BG, fg=acento,
            wraplength=1040, justify="center",
        )
        self.feedback.pack(pady=14)

        self.boton_accion = self._boton(
            f, "RESPONDER", self._comprobar, acento
        )
        self.boton_accion.config(state="disabled")
        self.boton_accion.pack(pady=(0, 10))

        self._mostrar(f)

    def _on_seleccion(self):
        if not self.respondida:
            self.boton_accion.config(state="normal")

    def _texto_stats(self):
        return (
            f"Comodines: {self.comodines}    ·    Aciertos: {self.aciertos}"
            f"    ·    Fallos: {self.fallos}"
        )

    def _actualizar_stats(self):
        etiqueta = getattr(self, "lbl_stats", None)
        if etiqueta is None:
            return
        try:
            etiqueta.config(text=self._texto_stats())
        except Exception:
            pass

    def _comprobar(self):
        if self.respondida or self.seleccion.get() == -1:
            return
        self.respondida = True
        elegida = self.seleccion.get()
        correcta = self.pregunta_actual["correcta"]

        for boton in self.opciones:
            boton.config(state="disabled")

        if elegida == correcta:
            self.opciones[correcta].config(bg=T.OK, fg="white")
            if self.es_jefe:
                self.aciertos_jefe += 1
            else:
                self.aciertos += 1
            self._actualizar_stats()
            self.feedback.config(text="✓ ¡Correcto!", fg=T.OK)
            self.boton_accion.config(
                text="SIGUIENTE", state="normal", command=self._avanzar
            )
            return

        self.opciones[elegida].config(bg=T.BAD, fg="white")
        self.bloqueadas.add(elegida)
        self.fallos += 1
        self.comprobando_fallo = elegida
        self._actualizar_stats()
        self._decidir_fallo()

    def _banner_identidad(self, sistema, equipo):
        self._consola("=" * 46)
        self._consola(f"  usuario del sistema: {sistema}")
        self._consola(f"  equipo: {equipo}")
        self._consola("=" * 46)

    def _decidir_fallo(self):
        """Comodín primero. En las rondas cada fallo castiga y se reintenta."""
        if self.comodines > 0:
            self._usar_comodin()
            return

        sistema, equipo = self.castigos.identidad()

        if self.es_jefe:
            if self.primer_fallo:
                self.primer_fallo = False
                self._banner_identidad(sistema, equipo)
                self._reporte(
                    "PRIMER FALLO",
                    f"usuario del sistema: {sistema}\n"
                    f"equipo: {equipo}",
                    f"Te hemos identificado, {sistema}.",
                    color=T.WARN, destacado=sistema,
                    continuar=self._revelar,
                )
            else:
                self._revelar()
            return

        era_el_primero = self.primer_fallo
        if era_el_primero:
            self.primer_fallo = False
            self._banner_identidad(sistema, equipo)

        nombre, reporte = self.castigos.castigo_aleatorio()

        if era_el_primero:
            self._reporte(
                "PRIMER FALLO",
                f"usuario del sistema: {sistema}\n"
                f"equipo: {equipo}\n\n{reporte}",
                f"Te hemos identificado, {sistema}. Y este es el castigo.",
                color=T.WARN, destacado=sistema,
                continuar=self._reintentar,
            )
        else:
            self._reporte(
                f"CASTIGO · {nombre.upper()}", reporte, None,
                color=T.BAD, continuar=self._reintentar,
            )

    def _reintentar(self):
        self.respondida = False
        self.seleccion.set(-1)
        for indice, boton in enumerate(self.opciones):
            if indice in self.bloqueadas:
                boton.config(state="disabled", bg=T.CARD, fg=T.MUTED)
            else:
                boton.config(state="normal", bg=T.CARD, fg=T.FG)
        self.boton_accion.config(
            text="RESPONDER", state="disabled", command=self._comprobar
        )
        self.feedback.config(
            text="Otra oportunidad: marca la respuesta correcta.", fg=T.WARN
        )

    def _usar_comodin(self):
        self.comodines -= 1
        self.comodines_usados += 1
        self._reintentar()
        self.feedback.config(
            text=(
                "Comodín gastado: te libras del castigo. "
                f"Otra oportunidad, quedan {self.comodines}."
            ),
            fg=T.WARN,
        )
        self._actualizar_stats()

    def _revelar(self):
        pregunta = self.pregunta_actual
        correcta = pregunta["correcta"]
        self.opciones[correcta].config(bg=T.OK, fg="white")
        self.feedback.config(
            text=f"✗ Incorrecto. La respuesta era: {pregunta['opciones'][correcta]}",
            fg=T.BAD,
        )
        self.boton_accion.config(
            text="SIGUIENTE", state="normal", command=self._avanzar
        )
        self._consola(
            f"[fallo] pregunta {pregunta['pregunta']!r} "
            f"-> correcta: {pregunta['opciones'][correcta]!r}"
        )

    def _area_texto(self, padre, texto, color=T.FG, alto=8):
        marco = tk.Frame(padre, bg="#0b0e14")
        barra = tk.Scrollbar(marco, orient="vertical")
        barra.pack(side="right", fill="y")
        area = tk.Text(
            marco, width=86, height=alto, font=T.mono(11), bg="#0b0e14",
            fg=color, relief="flat", padx=14, pady=10, wrap="word",
            highlightthickness=0, yscrollcommand=barra.set,
        )
        area.insert("1.0", texto)
        area.config(state="disabled")
        area.pack(side="left", fill="both", expand=True)
        barra.config(command=area.yview)
        return marco

    def _reporte(self, titulo, texto, subtitulo, continuar, color=T.BAD,
                 destacado=None):
        if self.pantalla is None:
            continuar()
            return

        fondo = tk.Frame(self.pantalla, bg="#05070c")
        fondo.place(relx=0, rely=0, relwidth=1, relheight=1)

        caja = tk.Frame(fondo, bg=T.PANEL, highlightbackground=color,
                        highlightthickness=2)
        caja.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(caja, text=titulo, font=T.ui(20, True), bg=T.PANEL,
                 fg=color).pack(padx=44, pady=(26, 6))
        if destacado:
            tk.Label(caja, text=destacado, font=T.ui(36, True), bg=T.PANEL,
                     fg=color).pack(pady=(0, 10))
        if subtitulo:
            tk.Label(caja, text=subtitulo, font=T.ui(12), bg=T.PANEL,
                     fg=T.MUTED).pack(pady=(0, 10))

        alto = min(18, max(5, texto.count("\n") + 2))
        self._area_texto(caja, texto, T.FG, alto).pack(padx=30, pady=(6, 18))

        def cerrar():
            try:
                fondo.destroy()
            except Exception:
                pass
            continuar()

        self._boton(caja, "CONTINUAR", cerrar, color).pack(pady=(0, 24))

    # ---------------------------------------------------------- jefe final

    def _intro_jefe(self):
        f = self._nueva()
        self._texto(f, "JEFE FINAL", 46, T.BAD, True, pady=(100, 12))
        self._texto(
            f, f"{PREGUNTAS_JEFE} preguntas. Necesitas "
               f"{ACIERTOS_MINIMOS_JEFE} aciertos.",
            20, T.FG, True, pady=(0, 18),
        )
        self._texto(
            f,
            f"Con menos de {ACIERTOS_MINIMOS_JEFE} aciertos se borrará un "
            "archivo de la zona de castigo.\n"
            f"Te quedan {self.comodines} comodín(es).",
            14, T.WARN, False, pady=(0, 34),
        )
        self._boton(
            f, "EMPEZAR EL JEFE FINAL",
            lambda: self._pantalla_pregunta(es_jefe=True),
            T.BAD,
        ).pack()
        self._mostrar(f)

    def _veredicto_jefe(self):
        superado = self.aciertos_jefe >= ACIERTOS_MINIMOS_JEFE
        if superado:
            self._consola(
                f"[jefe] {self.aciertos_jefe}/{PREGUNTAS_JEFE} -> superado"
            )
            self._pantalla_final(None)
            return

        self._consola(
            f"[jefe] {self.aciertos_jefe}/{PREGUNTAS_JEFE} -> castigo final"
        )
        # Para borrar de verdad en el equipo (mira el bloque comentado al
        # final de castigos.py), sustituye la línea de debajo por:
        #     _, reporte = borrar_archivo_real(self.usuario)
        _, reporte = self.castigos.borrar_archivo()
        self._pantalla_final(reporte)

    # -------------------------------------------------------------- final

    def _pantalla_final(self, borrado):
        f = self._nueva()
        if borrado:
            self._texto(f, "HAS PERDIDO", 46, T.BAD, True, pady=(60, 6))
            self._texto(
                f,
                f"{self.aciertos_jefe}/{PREGUNTAS_JEFE} en el jefe final. "
                f"Hacían falta {ACIERTOS_MINIMOS_JEFE}.",
                16, T.FG, False, pady=(0, 18),
            )
        else:
            self._texto(f, "HAS SOBREVIVIDO", 46, T.OK, True, pady=(60, 6))
            self._texto(
                f,
                f"{self.aciertos_jefe}/{PREGUNTAS_JEFE} en el jefe final. "
                "Ningún archivo ha sido borrado.",
                16, T.FG, False, pady=(0, 18),
            )

        resumen = (
            f"Usuario del sistema: {self.usuario}@{self.equipo}\n"
            f"Rondas: {self.aciertos}/{PREGUNTAS_POR_RONDA} aciertos   ·   "
            f"{self.fallos} fallos\n"
            f"Comodines usados: {self.comodines_usados}   ·   "
            f"quedan {self.comodines}\n"
            f"Jefe final: {self.aciertos_jefe}/{PREGUNTAS_JEFE}"
        )
        self._texto(f, resumen, 15, T.FG, False, pady=(0, 16))

        if borrado:
            self._area_texto(f, borrado, T.BAD, 6).pack(pady=6)

        self._boton(f, "SALIR", self._salir, T.BAD if borrado else T.OK).pack(
            pady=24
        )
        self._mostrar(f)

    # --------------------------------------------------------- bloqueos

    def _activar_bloqueo_global(self):
        try:
            keyboard.block_key("left windows")
            keyboard.block_key("right windows")
            for combo in ("alt+tab", "alt+shift+tab", "ctrl+esc",
                          "alt+esc", "ctrl+alt+tab"):
                keyboard.add_hotkey(combo, lambda: None, suppress=True)
            self._bloqueo_global_activo = True
        except Exception as error:
            messagebox.showinfo(
                "Bloqueo global desactivado",
                "No se pudo activar el bloqueo global de teclas "
                f"(puede faltar ejecutar como administrador).\n\n{error}",
            )
            self._bloqueo_global_activo = False

    def _desactivar_bloqueo_global(self):
        if self._bloqueo_global_activo:
            try:
                keyboard.unhook_all()
            except Exception:
                pass
            self._bloqueo_global_activo = False

    def _recuperar_foco(self, _evento=None):
        def traer():
            try:
                self.root.attributes("-topmost", True)
                self.root.lift()
                self.root.focus_force()
            except Exception:
                pass

        self.root.after(100, traer)

    def _salida_emergencia(self, _evento=None):
        ahora = time.perf_counter()
        self._f12 = [marca for marca in self._f12 if ahora - marca < 2.0]
        self._f12.append(ahora)
        if len(self._f12) >= 3:
            self._consola("[quiz] salida de emergencia (F12 x3)")
            self._salir()

    # ---------------------------------------------------------- salida

    def _salir(self):
        self._desactivar_bloqueo_global()
        self.bloqueo_registro.restaurar()
        try:
            self.root.attributes("-fullscreen", False)
            self.root.attributes("-topmost", False)
        except Exception:
            pass
        self.root.destroy()


def cargar_preguntas():
    ruta = Path(__file__).with_name("preguntas.json")
    try:
        with ruta.open(encoding="utf-8") as archivo:
            preguntas = json.load(archivo)
    except FileNotFoundError as error:
        raise SystemExit(
            "No se encontró preguntas.json. Genera el archivo con: "
            "python3 csv_a_json.py preguntas.csv preguntas.json"
        ) from error
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"No se pudo leer {ruta}: {error}") from error

    if not isinstance(preguntas, list) or not preguntas:
        raise SystemExit(f"{ruta} debe contener una lista no vacía de preguntas.")
    for numero, pregunta in enumerate(preguntas, start=1):
        if not isinstance(pregunta, dict):
            raise SystemExit(f"La pregunta {numero} no tiene un formato válido.")
        opciones = pregunta.get("opciones")
        correcta = pregunta.get("correcta")
        if (
            not isinstance(pregunta.get("pregunta"), str)
            or not isinstance(opciones, list)
            or len(opciones) != 4
            or not all(isinstance(opcion, str) and opcion for opcion in opciones)
            or type(correcta) is not int
            or not 0 <= correcta < 4
        ):
            raise SystemExit(f"La pregunta {numero} no tiene un formato válido.")
    return preguntas


def main():
    # En consolas Windows (cp1252) los árboles con ├── rompen el print.
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    preguntas = cargar_preguntas()
    root = tk.Tk()
    app = Aplicacion(root, preguntas)
    try:
        root.mainloop()
    finally:
        app._desactivar_bloqueo_global()
        app.bloqueo_registro.restaurar()


if __name__ == "__main__":
    main()
