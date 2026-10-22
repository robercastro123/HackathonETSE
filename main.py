#!/usr/bin/env python3
"""
Quiz Kiosco - Hackathon
Pantalla completa sin salida manual.

- No se cierra con Esc ni con el botón de cerrar la ventana: no hacen nada.
- Avanza solo cuando respondes cada pregunta.
- La ÚNICA forma de salir es terminar el quiz: al responder la última
  pregunta aparece el botón "Salir".

Bloqueo de teclado en tres niveles:
  - Nivel 1 (siempre): neutraliza atajos (Alt+F4, Ctrl+W/Q, Alt+Tab)
    mientras la ventana tiene el foco. No necesita nada extra.
  - Nivel 2 (opcional, BLOQUEO_GLOBAL=True): con la librería 'keyboard'
    suprime la tecla Windows y varios atajos de cambio de ventana a nivel
    de sistema. Requiere 'pip install keyboard' y normalmente permisos de
    administrador.
  - Nivel 3 (opcional, BLOQUEO_REGISTRO=True): deshabilita el Administrador
    de tareas (Ctrl+Shift+Esc) y Win+L vía registro. Solo Windows. Se
    restaura al salir.

Ctrl+Alt+Supr NUNCA se bloquea (es imposible sin un driver de kernel, y
es a propósito: es tu red de seguridad para no dejar el equipo colgado).
Ejecútalo en tu propio ordenador.
"""

import sys
import tkinter as tk
<<<<<<< HEAD
import json
from pathlib import Path
from tkinter import messagebox, simpledialog
=======
from tkinter import messagebox

# El bloqueo global (Nivel 2) es opcional: si no está la librería
# 'keyboard', el programa sigue funcionando solo con el Nivel 1.
try:
    import keyboard  # pip install keyboard
    _KEYBOARD_OK = True
except Exception:
    _KEYBOARD_OK = False

# winreg solo existe en Windows. En otros SO el bloqueo por registro
# (Nivel 3) queda desactivado automáticamente.
try:
    import winreg  # noqa: solo Windows
    _WINREG_OK = True
except Exception:
    _WINREG_OK = False
>>>>>>> c72e2bb (Describe tus cambios)

# ----------------------------------------------------------------------
# CONFIGURACIÓN — edita esto
# ----------------------------------------------------------------------

<<<<<<< HEAD
PALABRA_SALIDA = "abracadabra"   # palabra para salir antes de terminar
#
#PREGUNTAS = [
 #   {
  #      "pregunta": "¿Qué significa HTTP?",
   #     "opciones": [
    #        "HyperText Transfer Protocol",
     #       "High Transfer Text Protocol",
      #      "HyperType Transmission Program",
       #     "Home Tool Transfer Protocol",
#        ],
 #       "correcta": 0,  # índice de la opción correcta (empieza en 0)
  #  },
   # {
    #    "pregunta": "¿Cuál es el puerto por defecto de HTTPS?",
     #   "opciones": ["80", "22", "443", "8080"],
#        "correcta": 2,
#    },
#    {
#        "pregunta": "¿Qué estructura de datos es LIFO?",
#        "opciones": ["Cola (Queue)", "Pila (Stack)", "Árbol", "Grafo"],
#        "correcta": 1,
#    },
#    {
#        "pregunta": "¿Qué comando lista archivos en Linux?",
#        "opciones": ["dir", "ls", "list", "show"],
#        "correcta": 1,
#    },
#]
=======
BLOQUEO_GLOBAL = True            # Nivel 2: suprimir tecla Windows y Alt+Tab
BLOQUEO_REGISTRO = True          # Nivel 3: deshabilitar Administrador de
                                 # tareas (Ctrl+Shift+Esc) y Win+L vía
                                 # registro. Solo Windows. Se restaura al
                                 # salir con la palabra clave.

PREGUNTAS = [
    {
        "pregunta": "¿Qué significa HTTP?",
        "opciones": [
            "HyperText Transfer Protocol",
            "High Transfer Text Protocol",
            "HyperType Transmission Program",
            "Home Tool Transfer Protocol",
        ],
        "correcta": 0,  # índice de la opción correcta (empieza en 0)
    },
    {
        "pregunta": "¿Cuál es el puerto por defecto de HTTPS?",
        "opciones": ["80", "22", "443", "8080"],
        "correcta": 2,
    },
    {
        "pregunta": "¿Qué estructura de datos es LIFO?",
        "opciones": ["Cola (Queue)", "Pila (Stack)", "Árbol", "Grafo"],
        "correcta": 1,
    },
    {
        "pregunta": "¿Qué comando lista archivos en Linux?",
        "opciones": ["dir", "ls", "list", "show"],
        "correcta": 1,
    },
]
>>>>>>> c72e2bb (Describe tus cambios)

# ----------------------------------------------------------------------
# APLICACIÓN
# ----------------------------------------------------------------------

BG = "#0f1117"
FG = "#e6e6e6"
ACCENT = "#5b8def"
OK = "#3ecf8e"
BAD = "#ef5b5b"
CARD = "#1a1d27"


class BloqueoRegistro:
    """Nivel 3: deshabilita Administrador de tareas y Win+L por registro.

    Escribe dos valores DWORD = 1 bajo
    HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\System:
      - DisableTaskMgr       -> tapa Ctrl+Shift+Esc y el botón del
                                 Administrador de tareas en Ctrl+Alt+Supr.
      - DisableLockWorkstation -> tapa Win+L y el botón "Bloquear".

    Usa HKCU (no HKLM), así que afecta solo a este usuario y no necesita
    permisos de administrador. Guarda el estado previo de cada valor y lo
    restaura EXACTAMENTE al salir: si no existía, lo borra; si existía con
    otro valor, lo repone.
    """

    _SUBKEY = r"Software\Microsoft\Windows\CurrentVersion\Policies\System"
    _VALORES = ("DisableTaskMgr", "DisableLockWorkstation")

    def __init__(self):
        self._activo = False
        self._previos = {}  # nombre -> valor original, o None si no existía

    def activar(self):
        if not _WINREG_OK:
            return False
        try:
            # Abre o crea la clave con permiso de escritura y lectura.
            clave = winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER, self._SUBKEY, 0,
                winreg.KEY_READ | winreg.KEY_SET_VALUE,
            )
            try:
                for nombre in self._VALORES:
                    # Guarda el valor actual (o None si no está).
                    try:
                        valor, _ = winreg.QueryValueEx(clave, nombre)
                        self._previos[nombre] = valor
                    except FileNotFoundError:
                        self._previos[nombre] = None
                    # Lo pone a 1.
                    winreg.SetValueEx(
                        clave, nombre, 0, winreg.REG_DWORD, 1
                    )
            finally:
                winreg.CloseKey(clave)
            self._activo = True
            return True
        except Exception as e:
            messagebox.showinfo(
                "Bloqueo de registro desactivado",
                "No se pudieron escribir las políticas de registro.\n\n"
                "El quiz sigue funcionando con los demás bloqueos.\n\n"
                f"Detalle: {e}",
            )
            self._activo = False
            return False

    def restaurar(self):
        # Se llama SIEMPRE al salir para no dejar el equipo capado.
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
                        # No existía: borrarlo (si ya no está, da igual).
                        try:
                            winreg.DeleteValue(clave, nombre)
                        except FileNotFoundError:
                            pass
                    else:
                        # Existía: reponer su valor original.
                        winreg.SetValueEx(
                            clave, nombre, 0, winreg.REG_DWORD, previo
                        )
            finally:
                winreg.CloseKey(clave)
        except Exception:
            pass
        finally:
            self._activo = False


class QuizKiosco:
    def __init__(self, root, preguntas):
        self.root = root
        self.preguntas = preguntas
        self.indice = 0
        self.aciertos = 0
        self.seleccion = tk.IntVar(value=-1)
        self.respondida = False

        root.title("Quiz Hackathon")
        root.configure(bg=BG)
        root.attributes("-fullscreen", True)
        root.attributes("-topmost", True)

        # Cerrar la ventana (botón X / Alt+F4) no hace nada.
        root.protocol("WM_DELETE_WINDOW", lambda: None)
        # Esc no hace nada.
        root.bind("<Escape>", lambda e: "break")
        # Si pierde el foco, vuelve a traerse al frente (suave)
        root.bind("<FocusOut>", self._recuperar_foco)

        # --- NIVEL 1: neutralizar atajos mientras la ventana tiene foco ---
        # Devolver "break" evita que el atajo llegue a su acción por defecto.
        for seq in ("<Alt-F4>", "<Control-w>", "<Control-q>",
                    "<Control-W>", "<Control-Q>", "<Alt-Tab>"):
            root.bind(seq, lambda e: "break")

        # --- NIVEL 2: bloqueo global (tecla Windows, Alt+Tab) -------------
        self._bloqueo_global_activo = False
        if BLOQUEO_GLOBAL and _KEYBOARD_OK:
            self._activar_bloqueo_global()

        # --- NIVEL 3: bloqueo por registro (Task Manager, Win+L) ----------
        self.bloqueo_registro = BloqueoRegistro()
        if BLOQUEO_REGISTRO:
            self.bloqueo_registro.activar()

        self._construir_ui()
        self._mostrar_pregunta()

    # -- UI --------------------------------------------------------------
    def _construir_ui(self):
        self.contador = tk.Label(
            self.root, text="", font=("Segoe UI", 16),
            bg=BG, fg=ACCENT,
        )
        self.contador.pack(pady=(40, 10))

        self.lbl_pregunta = tk.Label(
            self.root, text="", font=("Segoe UI", 28, "bold"),
            bg=BG, fg=FG, wraplength=1100, justify="center",
        )
        self.lbl_pregunta.pack(pady=(10, 40))

        self.frame_opciones = tk.Frame(self.root, bg=BG)
        self.frame_opciones.pack()

        self.botones = []
        for i in range(4):
            b = tk.Radiobutton(
                self.frame_opciones, text="", variable=self.seleccion,
                value=i, font=("Segoe UI", 20), bg=CARD, fg=FG,
                selectcolor=CARD, activebackground=CARD, activeforeground=FG,
                indicatoron=True, anchor="w", padx=20, pady=16,
                width=50, command=self._on_seleccion,
            )
            b.pack(pady=8, fill="x")
            self.botones.append(b)

        self.lbl_feedback = tk.Label(
            self.root, text="", font=("Segoe UI", 18),
            bg=BG, fg=FG,
        )
        self.lbl_feedback.pack(pady=30)

        self.btn_siguiente = tk.Button(
            self.root, text="Responder", font=("Segoe UI", 18, "bold"),
            bg=ACCENT, fg="white", activebackground=ACCENT,
            relief="flat", padx=40, pady=12, command=self._accion_boton,
            state="disabled",
        )
        self.btn_siguiente.pack(pady=10)

        self.lbl_ayuda = tk.Label(
            self.root,
            text="Responde todas las preguntas para terminar",
            font=("Segoe UI", 12), bg=BG, fg="#6b7280",
        )
        self.lbl_ayuda.pack(side="bottom", pady=20)

    def _mostrar_pregunta(self):
        p = self.preguntas[self.indice]
        self.respondida = False
        self.seleccion.set(-1)
        self.contador.config(
            text=f"Pregunta {self.indice + 1} de {len(self.preguntas)}"
        )
        self.lbl_pregunta.config(text=p["pregunta"])
        for i, b in enumerate(self.botones):
            if i < len(p["opciones"]):
                b.config(text=p["opciones"][i], state="normal", bg=CARD, fg=FG)
                b.pack(pady=8, fill="x")
            else:
                b.pack_forget()
        self.lbl_feedback.config(text="")
        self.btn_siguiente.config(text="Responder", state="disabled")

    # -- lógica ----------------------------------------------------------
    def _on_seleccion(self):
        if not self.respondida:
            self.btn_siguiente.config(state="normal")

    def _accion_boton(self):
        if not self.respondida:
            self._comprobar()
        else:
            self._avanzar()

    def _comprobar(self):
        if self.seleccion.get() == -1:
            return
        self.respondida = True
        p = self.preguntas[self.indice]
        correcta = p["correcta"]
        elegida = self.seleccion.get()

        for b in self.botones:
            b.config(state="disabled")
        self.botones[correcta].config(bg=OK, fg="white")

        if elegida == correcta:
            self.aciertos += 1
            self.lbl_feedback.config(text="✓ ¡Correcto!", fg=OK)
        else:
            self.botones[elegida].config(bg=BAD, fg="white")
            self.lbl_feedback.config(
                text=f"✗ Incorrecto. La respuesta era: {p['opciones'][correcta]}",
                fg=BAD,
            )

        ultima = self.indice == len(self.preguntas) - 1
        self.btn_siguiente.config(
            text="Ver resultado" if ultima else "Siguiente", state="normal"
        )

    def _avanzar(self):
        self.indice += 1
        if self.indice < len(self.preguntas):
            self._mostrar_pregunta()
        else:
            self._mostrar_resultado()

    def _mostrar_resultado(self):
        for w in self.frame_opciones.winfo_children():
            w.pack_forget()
        self.contador.config(text="Finalizado")
        total = len(self.preguntas)
        self.lbl_pregunta.config(
            text=f"Puntuación: {self.aciertos} / {total}"
        )
        self.lbl_feedback.config(
            text=f"{round(self.aciertos / total * 100)}% de aciertos", fg=ACCENT
        )
        self.lbl_ayuda.config(
            text=(
                "Para un control total, podríamos programar un cron (o una "
                "tarea de inicio) que lanzara este programa cada vez que se "
                "enciende el portátil, de modo que no se pudiera usar el "
                "equipo sin pasar por el quiz.\n"
                "No lo hacemos porque no es necesario para la explicación."
            ),
            justify="center",
        )
        self.btn_siguiente.config(text="Salir", state="normal",
                                  command=self._salir_libre)

    # -- bloqueo global (Nivel 2) ----------------------------------------
    def _activar_bloqueo_global(self):
        try:
            keyboard.block_key("left windows")
            keyboard.block_key("right windows")
            # Suprime a nivel global (no solo con foco) los atajos de
            # cambio de ventana y de menú Inicio que la ventana no puede
            # interceptar por sí sola.
            for combo in ("alt+tab", "alt+shift+tab", "ctrl+esc",
                          "alt+esc", "ctrl+alt+tab"):
                keyboard.add_hotkey(combo, lambda: None, suppress=True)
            self._bloqueo_global_activo = True
        except Exception as e:
            # Normalmente por falta de permisos de administrador.
            messagebox.showinfo(
                "Bloqueo global desactivado",
                "No se pudo activar el bloqueo global de teclas "
                f"(probablemente falta ejecutar como administrador).\n\n"
                f"El quiz sigue funcionando con el bloqueo de ventana.\n\n"
                f"Detalle: {e}",
            )
            self._bloqueo_global_activo = False

    def _desactivar_bloqueo_global(self):
        # Se llama SIEMPRE al salir para no dejar teclas colgadas.
        if self._bloqueo_global_activo:
            try:
                keyboard.unhook_all()
            except Exception:
                pass
            self._bloqueo_global_activo = False

    # -- salida ----------------------------------------------------------
    def _recuperar_foco(self, _event=None):
        # Vuelve a traer la ventana al frente Y recupera el teclado.
        # attributes(-topmost) solo la pone delante; para que el foco
        # vuelva hacen falta lift() + focus_force().
        def _traer():
            self.root.attributes("-topmost", True)
            self.root.lift()
            self.root.focus_force()
        self.root.after(100, _traer)

    def _salir_libre(self):
        self._desactivar_bloqueo_global()
        self.bloqueo_registro.restaurar()
        self.root.attributes("-fullscreen", False)
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
    preguntas = cargar_preguntas()
    root = tk.Tk()
<<<<<<< HEAD
    QuizKiosco(root, preguntas)
    root.mainloop()
=======
    app = QuizKiosco(root)
    try:
        root.mainloop()
    finally:
        # Red de seguridad: si el programa peta a mitad, desbloquea igual.
        app._desactivar_bloqueo_global()
        app.bloqueo_registro.restaurar()
>>>>>>> c72e2bb (Describe tus cambios)


if __name__ == "__main__":
    main()