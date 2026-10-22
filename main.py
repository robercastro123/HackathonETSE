#!/usr/bin/env python3
"""
Quiz Kiosco - Hackathon
Pantalla completa con salida voluntaria por contraseña.

- No se cierra con Esc ni con el botón de cerrar la ventana:
  pide la PALABRA_SALIDA para salir.
- Avanza solo cuando respondes cada pregunta.
- Al terminar muestra la puntuación y permite salir.

NO deshabilita teclas del sistema (Alt+Tab, Ctrl+Alt+Supr, gestor de
tareas siguen funcionando). Es un "lock voluntario", no un bloqueo real
del equipo. Ejecútalo en tu propio ordenador.
"""

import tkinter as tk
from tkinter import messagebox, simpledialog

# ----------------------------------------------------------------------
# CONFIGURACIÓN — edita esto
# ----------------------------------------------------------------------

PALABRA_SALIDA = "abracadabra"   # palabra para salir antes de terminar

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

# ----------------------------------------------------------------------
# APLICACIÓN
# ----------------------------------------------------------------------

BG = "#0f1117"
FG = "#e6e6e6"
ACCENT = "#5b8def"
OK = "#3ecf8e"
BAD = "#ef5b5b"
CARD = "#1a1d27"


class QuizKiosco:
    def __init__(self, root):
        self.root = root
        self.indice = 0
        self.aciertos = 0
        self.seleccion = tk.IntVar(value=-1)
        self.respondida = False

        root.title("Quiz Hackathon")
        root.configure(bg=BG)
        root.attributes("-fullscreen", True)
        root.attributes("-topmost", True)

        # Interceptar cierre de ventana -> pedir contraseña
        root.protocol("WM_DELETE_WINDOW", self.intentar_salir)
        # Esc -> pedir contraseña (no cierra directamente)
        root.bind("<Escape>", lambda e: self.intentar_salir())
        # Si pierde el foco, vuelve a traerse al frente (suave)
        root.bind("<FocusOut>", self._recuperar_foco)

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
            text=f"Para salir antes de terminar: Esc y escribe la palabra clave",
            font=("Segoe UI", 12), bg=BG, fg="#6b7280",
        )
        self.lbl_ayuda.pack(side="bottom", pady=20)

    def _mostrar_pregunta(self):
        p = PREGUNTAS[self.indice]
        self.respondida = False
        self.seleccion.set(-1)
        self.contador.config(
            text=f"Pregunta {self.indice + 1} de {len(PREGUNTAS)}"
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
        p = PREGUNTAS[self.indice]
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

        ultima = self.indice == len(PREGUNTAS) - 1
        self.btn_siguiente.config(
            text="Ver resultado" if ultima else "Siguiente", state="normal"
        )

    def _avanzar(self):
        self.indice += 1
        if self.indice < len(PREGUNTAS):
            self._mostrar_pregunta()
        else:
            self._mostrar_resultado()

    def _mostrar_resultado(self):
        for w in self.frame_opciones.winfo_children():
            w.pack_forget()
        self.contador.config(text="Finalizado")
        total = len(PREGUNTAS)
        self.lbl_pregunta.config(
            text=f"Puntuación: {self.aciertos} / {total}"
        )
        self.lbl_feedback.config(
            text=f"{round(self.aciertos / total * 100)}% de aciertos", fg=ACCENT
        )
        self.btn_siguiente.config(text="Salir", state="normal",
                                  command=self._salir_libre)

    # -- salida ----------------------------------------------------------
    def _recuperar_foco(self, _event=None):
        # Vuelve a traer la ventana al frente sin pelearse con el SO
        self.root.after(100, lambda: self.root.attributes("-topmost", True))

    def intentar_salir(self):
        intento = simpledialog.askstring(
            "Salir", "Escribe la palabra clave para salir:",
            show="*", parent=self.root,
        )
        if intento is None:
            return  # canceló
        if intento.strip().lower() == PALABRA_SALIDA.lower():
            self._salir_libre()
        else:
            messagebox.showwarning("Incorrecto", "Palabra clave incorrecta.",
                                   parent=self.root)

    def _salir_libre(self):
        self.root.attributes("-fullscreen", False)
        self.root.destroy()


def main():
    root = tk.Tk()
    QuizKiosco(root)
    root.mainloop()


if __name__ == "__main__":
    main()