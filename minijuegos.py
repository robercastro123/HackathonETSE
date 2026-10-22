"""Seis minijuegos de Tkinter para el quiz.

Cada minijuego dura 20 segundos y devuelve un rango:

    alto  -> 2 comodines
    medio -> 1 comodín
    bajo  -> 0 comodines

Todos comparten la clase base ``Minijuego``: HUD, bucle de juego, teclado,
ratón y pantalla de resultados. Para añadir uno nuevo basta con heredar,
definir ``_construir`` y ``paso`` y apuntarlo en ``MINIJUEGOS``.
"""

from __future__ import annotations

import random
import time
import tkinter as tk

from estilo import ACCENT, BAD, BG, FG, MUTED, MONO, OK, WARN, ui

ANCHO = 900
ALTO = 460
DURACION = 20.0


class Minijuego(tk.Frame):
    nombre = "Minijuego"
    ayuda = ""
    umbral_alto = 10
    umbral_medio = 5
    duracion = DURACION

    def __init__(self, master, al_terminar):
        super().__init__(master, bg=BG)
        self.al_terminar = al_terminar
        self.puntos = 0
        self._activo = False
        self._terminado = False
        self._jobs = []
        self._enlaces = []
        self._teclas = set()
        self._t0 = 0.0
        self._t_ultimo = 0.0

        self.hud = tk.Label(self, text="", font=ui(15, True), bg=BG, fg=ACCENT)
        self.hud.pack(pady=(12, 4))
        self.canvas = tk.Canvas(
            self, width=ANCHO, height=ALTO, bg=MONO, highlightthickness=0
        )
        self.canvas.pack()
        self.pie = tk.Label(self, text=self.ayuda, font=ui(12), bg=BG, fg=MUTED)
        self.pie.pack(pady=6)

        self._construir()
        self._enlazar("<KeyPress>", self._tecla)
        self._enlazar("<KeyRelease>", self._soltar)
        self.canvas.bind("<Button-1>", self._clic)
        self.canvas.focus_set()

        self._t0 = time.perf_counter()
        self._t_ultimo = self._t0
        self._activo = True
        self._loop()

    # -------------------------------------------------------------- base

    def _construir(self):
        raise NotImplementedError

    def paso(self, dt, restante):
        pass

    def on_tecla(self, keysym):
        pass

    def on_clic(self, x, y):
        pass

    def destroy(self):
        self._detener()
        super().destroy()

    def _detener(self):
        self._activo = False
        for job in self._jobs:
            try:
                self.after_cancel(job)
            except Exception:
                pass
        self._jobs.clear()
        for widget, secuencia, fid in self._enlaces:
            try:
                widget.unbind(secuencia, fid)
            except Exception:
                pass
        self._enlaces.clear()

    def _enlazar(self, secuencia, manejador):
        try:
            widget = self.winfo_toplevel()
            fid = widget.bind(secuencia, manejador, add="+")
            self._enlaces.append((widget, secuencia, fid))
        except Exception:
            pass

    def _tecla(self, evento):
        self._teclas.add(evento.keysym)
        self.on_tecla(evento.keysym)

    def _soltar(self, evento):
        self._teclas.discard(evento.keysym)

    def _clic(self, evento):
        if self._activo and not self._terminado:
            self.on_clic(evento.x, evento.y)

    def _temporizar(self, ms, funcion):
        self._jobs.append(self.after(ms, funcion))

    def _loop(self):
        if not self._activo or self._terminado:
            return
        ahora = time.perf_counter()
        dt = min(0.06, max(0.001, ahora - self._t_ultimo))
        self._t_ultimo = ahora
        restante = self.duracion - (ahora - self._t0)

        try:
            self.paso(dt, max(0.0, restante))
        except Exception as error:  # noqa: BLE001 - no romper la demo
            print(f"[minijuego] error en {self.nombre}: {error}")
            self._finalizar()
            return

        if self._terminado:
            return

        self.hud.config(
            text=f"{self.nombre}   ·   {self.puntos} pts   ·   "
                 f"{max(0.0, restante):0.1f}s"
        )
        if restante <= 0:
            self._finalizar()
        else:
            self._jobs.append(self.after(16, self._loop))

    def rango(self):
        if self.puntos >= self.umbral_alto:
            return "alto", 2
        if self.puntos >= self.umbral_medio:
            return "medio", 1
        return "bajo", 0

    def _finalizar(self):
        if self._terminado:
            return
        self._terminado = True
        self._activo = False
        rango, comodines = self.rango()

        self.canvas.create_rectangle(
            0, 0, ANCHO, ALTO, fill="#000000", stipple="gray50", outline=""
        )
        self.canvas.create_text(
            ANCHO / 2, ALTO / 2 - 60, text="FIN", fill=FG,
            font=ui(40, True),
        )
        self.canvas.create_text(
            ANCHO / 2, ALTO / 2, text=f"{self.puntos} puntos", fill=ACCENT,
            font=ui(26, True),
        )
        color = {"alto": OK, "medio": WARN, "bajo": BAD}[rango]
        self.canvas.create_text(
            ANCHO / 2, ALTO / 2 + 55,
            text=f"RANGO {rango.upper()}   ·   +{comodines} comodín(es)",
            fill=color, font=ui(20, True),
        )
        self._jobs.append(
            self.after(1300, lambda: self.al_terminar(self.puntos, rango, comodines))
        )

    # ------------------------------------------------------------- utils

    def _texto(self, x, y, texto, color=FG, tam=16, negrita=True, tag=None):
        return self.canvas.create_text(
            x, y, text=texto, fill=color, font=ui(tam, negrita), tags=tag
        )


# =====================================================================
# 1. Ball Drop
# =====================================================================

class Balldrop(Minijuego):
    nombre = "BALL DROP"
    ayuda = "← →  mueve la cesta. Atrapa las bolas que caen."
    umbral_alto = 14
    umbral_medio = 7

    def _construir(self):
        self._cesta = ANCHO / 2
        self._bolas = []
        self._espera = 0.4
        self.canvas.create_line(0, 412, ANCHO, 412, fill="#232838")
        self._id_cesta = self.canvas.create_rectangle(
            0, 0, 0, 0, fill=ACCENT, outline=""
        )
        self.canvas.create_text(
            ANCHO / 2, 26, text="BALL DROP", fill="#2a3145", font=ui(34, True)
        )

    def on_tecla(self, keysym):
        pass  # el movimiento se calcula en paso() con las teclas pulsadas

    def paso(self, dt, restante):
        velocidad = 620
        if "Left" in self._teclas:
            self._cesta -= velocidad * dt
        if "Right" in self._teclas:
            self._cesta += velocidad * dt
        self._cesta = max(62, min(ANCHO - 62, self._cesta))

        self._espera -= dt
        if self._espera <= 0:
            self._espera = max(0.34, 0.62 - (self.duracion - restante) * 0.014)
            x = random.randint(50, ANCHO - 50)
            bola = self.canvas.create_oval(
                x - 12, -12, x + 12, 12, fill=WARN, outline=""
            )
            self._bolas.append({
                "id": bola, "x": x, "y": 0.0,
                "vy": random.uniform(170, 260) + (self.duracion - restante) * 6,
            })

        for bola in list(self._bolas):
            bola["y"] += bola["vy"] * dt
            self.canvas.coords(
                bola["id"], bola["x"] - 12, bola["y"] - 12,
                bola["x"] + 12, bola["y"] + 12,
            )
            if bola["y"] >= 416:
                if abs(bola["x"] - self._cesta) <= 58:
                    self.puntos += 1
                    destello = self.canvas.create_oval(
                        bola["x"] - 26, 396, bola["x"] + 26, 448,
                        outline=OK, width=3,
                    )
                    self._temporizar(
                        180, lambda i=destello: self.canvas.delete(i)
                    )
                self.canvas.delete(bola["id"])
                self._bolas.remove(bola)

        self.canvas.coords(
            self._id_cesta, self._cesta - 58, 420, self._cesta + 58, 444
        )


# =====================================================================
# 2. Parcel Panic
# =====================================================================

class ParcelPanic(Minijuego):
    nombre = "PARCEL PANIC"
    ayuda = "Clic en los paquetes antes de que desaparezcan. Rojo = bomba."
    umbral_alto = 12
    umbral_medio = 6

    _COLS, _FILAS = 5, 3
    _ANCHO_CAJA = 92
    _VIDA = 1.55

    def _construir(self):
        self._paquetes = []
        self._espera = 0.2
        self._hueco_x = ANCHO / self._COLS
        self._hueco_y = (ALTO - 80) / self._FILAS
        self.canvas.create_text(
            ANCHO / 2, 26, text="PARCEL PANIC", fill="#2a3145", font=ui(34, True)
        )

    def _centro(self, col, fila):
        return (
            20 + self._hueco_x * (col + 0.5),
            50 + self._hueco_y * (fila + 0.5),
        )

    def paso(self, dt, restante):
        self._espera -= dt
        ocupados = {(p["col"], p["fila"]) for p in self._paquetes}
        if self._espera <= 0 and len(self._paquetes) < 6:
            libres = [
                (c, f)
                for c in range(self._COLS)
                for f in range(self._FILAS)
                if (c, f) not in ocupados
            ]
            if libres:
                col, fila = random.choice(libres)
                x, y = self._centro(col, fila)
                tipo = random.choices(
                    ("normal", "fragil", "bomba"), weights=(70, 20, 10)
                )[0]
                color = {"normal": "#3b5bdb", "fragil": WARN, "bomba": BAD}[tipo]
                etiqueta = {"normal": "CAJA", "fragil": "FRÁGIL", "bomba": "BOMBA"}[tipo]
                rect = self.canvas.create_rectangle(
                    x - 42, y - 42, x + 42, y + 42,
                    fill="#1b2030", outline=color, width=3,
                )
                texto = self.canvas.create_text(
                    x, y, text=etiqueta, fill=color, font=ui(13, True)
                )
                self._paquetes.append({
                    "col": col, "fila": fila, "x": x, "y": y,
                    "vida": self._VIDA, "tipo": tipo,
                    "rect": rect, "texto": texto,
                })
            self._espera = random.uniform(0.45, 0.7)

        for paquete in list(self._paquetes):
            paquete["vida"] -= dt
            if paquete["vida"] <= 0:
                self._quitar(paquete)
            elif paquete["vida"] < 0.5:
                self.canvas.itemconfig(paquete["rect"], width=5)

    def _quitar(self, paquete):
        self.canvas.delete(paquete["rect"])
        self.canvas.delete(paquete["texto"])
        if paquete in self._paquetes:
            self._paquetes.remove(paquete)

    def on_clic(self, x, y):
        for paquete in list(self._paquetes):
            if abs(x - paquete["x"]) <= 46 and abs(y - paquete["y"]) <= 46:
                if paquete["tipo"] == "bomba":
                    self.puntos = max(0, self.puntos - 2)
                    self.canvas.create_text(
                        paquete["x"], paquete["y"] - 58, text="-2",
                        fill=BAD, font=ui(20, True),
                    )
                else:
                    ganancia = 2 if paquete["tipo"] == "fragil" else 1
                    self.puntos += ganancia
                    self.canvas.create_text(
                        paquete["x"], paquete["y"] - 58, text=f"+{ganancia}",
                        fill=OK, font=ui(20, True),
                    )
                self._quitar(paquete)
                return


# =====================================================================
# 3. Fruit Ninja
# =====================================================================

class FruitNinja(Minijuego):
    nombre = "FRUIT NINJA"
    ayuda = "Clic en las frutas. No toques las bombas."
    umbral_alto = 12
    umbral_medio = 6

    _COLORES = ("#e74c3c", "#f39c12", "#2ecc71", "#9b59b6", "#3498db")

    def _construir(self):
        self._frutas = []
        self._espera = 0.2
        self.canvas.create_text(
            ANCHO / 2, 26, text="FRUIT NINJA", fill="#2a3145", font=ui(34, True)
        )

    def paso(self, dt, restante):
        self._espera -= dt
        if self._espera <= 0:
            self._espera = random.uniform(0.35, 0.55)
            x = random.randint(120, ANCHO - 120)
            bomba = random.random() < 0.14
            color = BAD if bomba else random.choice(self._COLORES)
            radio = 24
            cuerpo = self.canvas.create_oval(
                x - radio, ALTO, x + radio, ALTO + radio * 2,
                fill=color, outline="",
            )
            marca = self.canvas.create_text(
                x, ALTO + radio, text="✖" if bomba else "",
                fill=FG, font=ui(18, True),
            )
            self._frutas.append({
                "x": x, "y": float(ALTO), "vy": random.uniform(-780, -620),
                "vx": random.uniform(-130, 130), "bomba": bomba,
                "id": cuerpo, "marca": marca, "radio": radio,
            })

        for fruta in list(self._frutas):
            fruta["vy"] += 1100 * dt
            fruta["x"] += fruta["vx"] * dt
            fruta["y"] += fruta["vy"] * dt
            r = fruta["radio"]
            self.canvas.coords(
                fruta["id"], fruta["x"] - r, fruta["y"] - r,
                fruta["x"] + r, fruta["y"] + r,
            )
            self.canvas.coords(fruta["marca"], fruta["x"], fruta["y"])
            if fruta["y"] > ALTO + 70:
                self.canvas.delete(fruta["id"])
                self.canvas.delete(fruta["marca"])
                self._frutas.remove(fruta)

    def on_clic(self, x, y):
        for fruta in list(self._frutas):
            if (fruta["x"] - x) ** 2 + (fruta["y"] - y) ** 2 <= 32 ** 2:
                if fruta["bomba"]:
                    self.puntos = max(0, self.puntos - 3)
                    aviso, color = "-3", BAD
                else:
                    self.puntos += 1
                    aviso, color = "+1", OK
                self.canvas.create_text(
                    fruta["x"], fruta["y"] - 34, text=aviso,
                    fill=color, font=ui(20, True),
                )
                self.canvas.delete(fruta["id"])
                self.canvas.delete(fruta["marca"])
                self._frutas.remove(fruta)
                return


# =====================================================================
# 4. Crossy Road
# =====================================================================

class CrossyRoad(Minijuego):
    nombre = "CROSSY ROAD"
    ayuda = "Flechas para moverte. Cruza las carreteras sin que te atropellen."
    umbral_alto = 10
    umbral_medio = 5
    duracion = 22.0

    _CELDA = 56
    _COLS = 16
    _FILAS = 8
    _OX = (ANCHO - 16 * 56) // 2
    _OY = 6
    _INICIO = (7, 7)

    def _construir(self):
        self.col, self.fila = self._INICIO
        self._bonus = 0
        self._golpes = 0
        self._ultimo_mov = 0.0
        self._coches = []

        c = self._CELDA
        for fila in range(self._FILAS):
            color = "#1d2a1f" if fila in (0, self._FILAS - 1) else "#232733"
            self.canvas.create_rectangle(
                self._OX, self._OY + fila * c,
                self._OX + self._COLS * c, self._OY + (fila + 1) * c,
                fill=color, outline="",
            )
        for fila in range(1, self._FILAS - 1):
            y = self._OY + fila * c + c / 2
            for x in range(0, ANCHO, 60):
                self.canvas.create_line(
                    self._OX + x, y, self._OX + x + 26, y,
                    fill="#3b4050", width=2,
                )

        colores = ("#e74c3c", "#3498db", "#9b59b6", "#f39c12", "#1abc9c")
        for fila in range(1, self._FILAS - 1):
            direccion = 1 if fila % 2 else -1
            velocidad = random.uniform(90, 165) * direccion
            ancho = random.choice((42, 52, 62))
            for i in range(2):
                x = random.uniform(0, ANCHO) + i * (ANCHO / 2)
                rect = self.canvas.create_rectangle(
                    0, 0, 0, 0, fill=random.choice(colores), outline=""
                )
                self._coches.append({
                    "id": rect, "x": x, "fila": fila,
                    "ancho": ancho, "vel": velocidad,
                })

        self._jugador = self.canvas.create_rectangle(
            0, 0, 0, 0, fill="#ffd166", outline="#b8860b", width=2
        )
        self._dibujar_jugador()

    def _dibujar_jugador(self):
        c = self._CELDA
        x = self._OX + self.col * c
        y = self._OY + self.fila * c
        self.canvas.coords(self._jugador, x + 9, y + 8, x + c - 9, y + c - 6)

    def _choca(self):
        c = self._CELDA
        x0 = self._OX + self.col * c + 9
        y0 = self._OY + self.fila * c + 8
        x1 = x0 + c - 18
        y1 = y0 + c - 14
        for coche in self._coches:
            cy = self._OY + coche["fila"] * c + c / 2
            cx0 = coche["x"] - coche["ancho"] / 2
            cx1 = coche["x"] + coche["ancho"] / 2
            if x0 < cx1 and x1 > cx0 and y0 < cy + 16 and y1 > cy - 16:
                return True
        return False

    def _reaparecer(self):
        self.col, self.fila = self._INICIO
        self._golpes += 1
        self._dibujar_jugador()

    def on_tecla(self, keysym):
        ahora = time.perf_counter()
        if ahora - self._ultimo_mov < 0.09:
            return
        self._ultimo_mov = ahora
        if keysym == "Up":
            self.fila -= 1
        elif keysym == "Down":
            self.fila += 1
        elif keysym == "Left":
            self.col -= 1
        elif keysym == "Right":
            self.col += 1
        else:
            return
        self.col = max(0, min(self._COLS - 1, self.col))
        self.fila = max(0, min(self._FILAS - 1, self.fila))

        if self._choca():
            self._reaparecer()
            return

        logrado = (self._FILAS - 1) - self.fila
        self.puntos = max(self.puntos, self._bonus + logrado)
        if self.fila == 0:
            self._bonus += 10
            self.puntos = max(self.puntos, self._bonus)
            self._reaparecer()
        self._dibujar_jugador()

    def paso(self, dt, restante):
        c = self._CELDA
        for coche in self._coches:
            coche["x"] += coche["vel"] * dt
            if coche["vel"] > 0 and coche["x"] - coche["ancho"] > ANCHO + 40:
                coche["x"] = -40
            elif coche["vel"] < 0 and coche["x"] + coche["ancho"] < -40:
                coche["x"] = ANCHO + 40
            cy = self._OY + coche["fila"] * c + c / 2
            self.canvas.coords(
                coche["id"],
                coche["x"] - coche["ancho"] / 2, cy - 16,
                coche["x"] + coche["ancho"] / 2, cy + 16,
            )
        if self._choca():
            self._reaparecer()


# =====================================================================
# 5. Don't Touch the Spikes
# =====================================================================

class NoToquesLosPinchos(Minijuego):
    nombre = "DON'T TOUCH THE SPIKES"
    ayuda = "Espacio para aletear. Pasa por los huecos sin tocar los pinchos."
    umbral_alto = 6
    umbral_medio = 3
    duracion = 22.0

    _X = 190
    _R = 14
    _GRAVEDAD = 1150
    _ALETEO = -390
    _ANCHO_PUERTA = 58
    _HUECO = 185

    def _construir(self):
        self._y = ALTO / 2
        self._vy = 0.0
        self._puertas = []
        self._espera = 0.7

        for x in range(0, ANCHO + 20, 22):
            self.canvas.create_polygon(
                x, 0, x + 20, 0, x + 10, 16, fill="#4b5563", outline=""
            )
            self.canvas.create_polygon(
                x, ALTO, x + 20, ALTO, x + 10, ALTO - 16, fill="#4b5563", outline=""
            )
        self._pajaro = self.canvas.create_oval(
            self._X - self._R, self._y - self._R,
            self._X + self._R, self._y + self._R,
            fill=WARN, outline="#b8860b", width=2,
        )
        self._pico = self.canvas.create_polygon(
            0, 0, 0, 0, 0, 0, fill="#e67e22", outline=""
        )

    def on_tecla(self, keysym):
        if keysym == "space":
            self._vy = self._ALETEO

    def _puerta(self):
        return self._ANCHO_PUERTA, self._HUECO

    def paso(self, dt, restante):
        self._vy += self._GRAVEDAD * dt
        self._y += self._vy * dt
        ancho, hueco = self._puerta()
        r = self._R

        self.canvas.coords(
            self._pajaro, self._X - r, self._y - r, self._X + r, self._y + r
        )
        self.canvas.coords(
            self._pico, self._X + r - 2, self._y - 4,
            self._X + r + 12, self._y, self._X + r - 2, self._y + 5,
        )

        if self._y - r <= 16 or self._y + r >= ALTO - 16:
            self._finalizar()
            return

        self._espera -= dt
        if self._espera <= 0:
            self._espera = 1.45
            y = random.randint(110, ALTO - 110)
            arriba = self.canvas.create_rectangle(
                0, 0, 0, 0, fill="#2ecc71", outline="#27ae60", width=2
            )
            abajo = self.canvas.create_rectangle(
                0, 0, 0, 0, fill="#2ecc71", outline="#27ae60", width=2
            )
            self._puertas.append({
                "x": float(ANCHO + 40), "y": y,
                "arriba": arriba, "abajo": abajo,
            })

        for puerta in list(self._puertas):
            puerta["x"] -= 215 * dt
            x0 = puerta["x"]
            x1 = x0 + ancho
            tope = puerta["y"] - hueco / 2
            suelo = puerta["y"] + hueco / 2
            self.canvas.coords(puerta["arriba"], x0, 0, x1, tope)
            self.canvas.coords(puerta["abajo"], x0, suelo, x1, ALTO)

            bx0, bx1 = self._X - r, self._X + r
            by0, by1 = self._y - r, self._y + r
            if bx0 < x1 and bx1 > x0 and (by0 < tope or by1 > suelo):
                self._finalizar()
                return

            if x1 < bx0:
                self.puntos += 1
                self.canvas.delete(puerta["arriba"])
                self.canvas.delete(puerta["abajo"])
                self._puertas.remove(puerta)


# =====================================================================
# 6. Jungle Run
# =====================================================================

class JungleRun(Minijuego):
    nombre = "JUNGLE RUN"
    ayuda = "Espacio para saltar. Esquiva los troncos."
    umbral_alto = 7
    umbral_medio = 4

    _SUELO = 386
    _X = 170
    _ANCHO_J = 38
    _ALTO_J = 48
    _GRAVEDAD = 2200
    _SALTO = -900

    def _construir(self):
        self._y = self._SUELO - self._ALTO_J
        self._vy = 0.0
        self._suelo = True
        self._obstaculos = []
        self._espera = 0.9
        self._velocidad = 330.0
        self.canvas.create_rectangle(
            0, self._SUELO, ANCHO, ALTO, fill="#2d3b2a", outline=""
        )
        for x in range(0, ANCHO + 60, 60):
            self.canvas.create_rectangle(
                x, self._SUELO + 20, x + 30, self._SUELO + 26,
                fill="#3d4f39", outline=""
            )
        for x, alto in ((40, 90), (260, 60), (520, 110), (760, 70)):
            self.canvas.create_rectangle(
                x, self._SUELO - alto, x + 26, self._SUELO,
                fill="#1f2a1d", outline=""
            )
        self._jugador = self.canvas.create_rectangle(
            0, 0, 0, 0, fill="#f4a261", outline="#b5651d", width=2
        )
        self._dibujar()

    def _dibujar(self):
        self.canvas.coords(
            self._jugador,
            self._X, self._y,
            self._X + self._ANCHO_J, self._y + self._ALTO_J,
        )

    def on_tecla(self, keysym):
        if keysym == "space" and self._suelo:
            self._vy = self._SALTO
            self._suelo = False

    def paso(self, dt, restante):
        self._vy += self._GRAVEDAD * dt
        self._y += self._vy * dt
        if self._y + self._ALTO_J >= self._SUELO:
            self._y = self._SUELO - self._ALTO_J
            self._vy = 0.0
            self._suelo = True
        self._dibujar()

        self._velocidad = 330 + (self.duracion - restante) * 9
        self._espera -= dt
        if self._espera <= 0:
            self._espera = random.uniform(1.05, 1.55)
            alto = random.randint(38, 64)
            ancho = random.randint(28, 46)
            rect = self.canvas.create_rectangle(
                0, 0, 0, 0, fill="#7f5539", outline="#5e3f2a", width=2
            )
            self._obstaculos.append({
                "x": float(ANCHO + 40), "ancho": ancho, "alto": alto,
                "id": rect, "contado": False,
            })

        jx0, jx1 = self._X + 6, self._X + self._ANCHO_J - 6
        jy0, jy1 = self._y + 4, self._y + self._ALTO_J
        for obstaculo in list(self._obstaculos):
            obstaculo["x"] -= self._velocidad * dt
            ox0 = obstaculo["x"]
            ox1 = ox0 + obstaculo["ancho"]
            oy0 = self._SUELO - obstaculo["alto"]
            self.canvas.coords(
                obstaculo["id"], ox0, oy0, ox1, self._SUELO
            )
            if jx0 < ox1 and jx1 > ox0 and jy1 > oy0:
                self._finalizar()
                return
            if not obstaculo["contado"] and ox1 < jx0:
                obstaculo["contado"] = True
                self.puntos += 1
            if ox1 < -50:
                self.canvas.delete(obstaculo["id"])
                self._obstaculos.remove(obstaculo)


MINIJUEGOS = (
    Balldrop,
    ParcelPanic,
    FruitNinja,
    CrossyRoad,
    NoToquesLosPinchos,
    JungleRun,
)
