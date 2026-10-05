import os
import tkinter as tk
from tkinter import filedialog, messagebox

import cv2
import numpy as np
from PIL import Image, ImageTk

BLANCO = "#ffffff"
GRIS = "#d9d9d9"
NEGRO = "#000000"


class AnalizadorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Analizador de imagenes")
        self.geometry("1280x720")
        self.resizable(False, False)
        self.configure(bg=BLANCO)
        self.ruta_imagen = None
        self.img_rgb = None
        self.img_proc = None
        self.metodo_fondo = "grabcut"
        self._imagenes_tk = {}
        self._canvas_canales = {}
        self._info_filtros = {}
        self._botones_modo = {}
        self._metrica = {}
        self.modo_canal = {"rgb": "color", "ycm": "color"}
        self._paginas = {}
        self._crear_paginas()
        self.mostrar("menu")

    def _crear_paginas(self):
        self._paginas["menu"] = self._crear_menu()
        self._paginas["rgb"] = self._crear_filtros("rgb", "RGB", ["R", "G", "B"])
        self._paginas["ycm"] = self._crear_filtros("ycm", "YCM", ["Y", "C", "M"])

    def mostrar(self, nombre):
        if nombre in ("rgb", "ycm"):
            self._renderar_canales(nombre)
        self._paginas[nombre].tkraise()

    def _crear_menu(self):
        frame = tk.Frame(self, bg=BLANCO, width=1280, height=720)
        frame.place(x=0, y=0)
        frame.grid_propagate(False)

        titulo = tk.Label(frame, text="Analizador de imagenes", font=("Segoe UI", 28, "bold"), fg=NEGRO, bg=BLANCO)
        titulo.place(x=413, y=61)

        self.zona_imagen = tk.Frame(frame, bg=GRIS, width=305, height=144, cursor="hand2")
        self.zona_imagen.place(x=487, y=185)
        self.zona_imagen.grid_propagate(False)

        self.vista_previa = tk.Canvas(self.zona_imagen, width=305, height=96, bg=GRIS, highlightthickness=0, cursor="hand2")
        self.vista_previa.place(x=0, y=0)
        self.vista_previa.create_text(152, 48, text="seleccionar imagen", font=("Segoe UI", 16), fill=NEGRO)

        self.nombre_imagen = tk.Label(self.zona_imagen, text="", font=("Segoe UI", 11), fg=NEGRO, bg=GRIS, cursor="hand2", wraplength=295)
        self.nombre_imagen.place(x=0, y=96, width=305, height=48)

        for widget in (self.zona_imagen, self.vista_previa, self.nombre_imagen):
            widget.bind("<Button-1>", lambda evento: self.seleccionar_imagen())

        self.boton_fondo_menu = tk.Button(
            frame, text="Quitar fondo (preprocesado)", font=("Segoe UI", 12), fg=NEGRO, bg=GRIS,
            width=22, relief="flat", state="disabled", command=self.alternar_fondo,
        )
        self.boton_fondo_menu.place(x=487, y=345)
        self.boton_metodo = tk.Button(
            frame, text="Metodo: GRABCUT", font=("Segoe UI", 12), fg=NEGRO, bg=GRIS,
            width=10, relief="flat", state="disabled", command=self.alternar_metodo,
        )
        self.boton_metodo.place(x=700, y=345)

        self.boton_rgb = tk.Button(
            frame, text="Filtros RGB", font=("Segoe UI", 14), fg=NEGRO, bg=GRIS,
            width=14, relief="flat", state="disabled", command=lambda: self.mostrar("rgb"),
        )
        self.boton_rgb.place(x=487, y=380)

        self.boton_ycm = tk.Button(
            frame, text="Filtros YCM", font=("Segoe UI", 14), fg=NEGRO, bg=GRIS,
            width=14, relief="flat", state="disabled", command=lambda: self.mostrar("ycm"),
        )
        self.boton_ycm.place(x=792, y=380)

        return frame

    def _crear_filtros(self, clave, titulo, canales):
        frame = tk.Frame(self, bg=BLANCO, width=1280, height=720)
        frame.place(x=0, y=0)
        frame.grid_propagate(False)

        etiqueta_ima = tk.Label(frame, text="Imagen:", font=("Segoe UI", 16), fg=NEGRO, bg=BLANCO)
        etiqueta_ima.place(x=58, y=15)
        valor_ima = tk.Label(frame, text="-", font=("Segoe UI", 16), fg=NEGRO, bg=BLANCO)
        valor_ima.place(x=198, y=15)

        etiqueta_dir = tk.Label(frame, text="Directorio de imagen:", font=("Segoe UI", 16), fg=NEGRO, bg=BLANCO)
        etiqueta_dir.place(x=59, y=95)
        valor_dir = tk.Label(frame, text="-", font=("Segoe UI", 16), fg=NEGRO, bg=BLANCO)
        valor_dir.place(x=419, y=95)

        ancho_titulo = 82 if clave == "rgb" else 90
        titulo_label = tk.Label(frame, text=titulo, font=("Segoe UI", 28, "bold"), fg=NEGRO, bg=BLANCO)
        titulo_label.place(x=(1280 - ancho_titulo) // 2, y=157)

        regresar = tk.Button(
            frame, text="REGRESAR", font=("Segoe UI", 16), fg=NEGRO, bg=GRIS,
            width=10, relief="flat", command=lambda: self.mostrar("menu"),
        )
        regresar.place(x=976, y=29)

        boton_modo = tk.Button(
            frame, text="Modo: color", font=("Segoe UI", 12), fg=NEGRO, bg=GRIS,
            width=12, relief="flat", command=lambda: self.alternar_modo(clave),
        )
        boton_modo.place(x=470, y=29)
        self._botones_modo[clave] = boton_modo

        boton_fondo = tk.Button(
            frame, text="Quitar fondo", font=("Segoe UI", 12), fg=NEGRO, bg=GRIS,
            width=12, relief="flat", command=self.alternar_fondo,
        )
        boton_fondo.place(x=640, y=29)

        self._canvas_canales[clave] = {}
        self._metrica[clave] = {}
        for i, letra in enumerate(canales):
            x_lienzo = 58 + 432 * i
            etiqueta = tk.Label(frame, text=letra, font=("Segoe UI", 28, "bold"), fg=NEGRO, bg=BLANCO)
            etiqueta.place(x=x_lienzo + 150, y=259, anchor="center")
            lienzo = tk.Canvas(frame, width=300, height=300, bg=GRIS, highlightthickness=0, cursor="hand2")
            lienzo.place(x=x_lienzo, y=306)
            lienzo.bind("<Button-1>", lambda evento, c=clave, l=letra: self.aplicar_canal(c, l))
            self._canvas_canales[clave][letra] = lienzo
            metrica = tk.Label(frame, text="", font=("Segoe UI", 12, "bold"), fg=NEGRO, bg=BLANCO)
            metrica.place(x=x_lienzo + 150, y=620, anchor="center")
            self._metrica[clave][letra] = metrica

        self._info_filtros[clave] = {"ima": valor_ima, "dir": valor_dir}
        return frame

    def seleccionar_imagen(self):
        ruta = filedialog.askopenfilename(
            title="Seleccionar imagen",
            filetypes=[("Imagenes", "*.png *.jpg *.jpeg *.bmp *.gif"), ("Todos los archivos", "*.*")],
        )
        if not ruta:
            return
        try:
            self.img_rgb = np.array(Image.open(ruta).convert("RGB"))
        except Exception as error:
            messagebox.showerror("Error", f"No se pudo cargar la imagen:\n{error}")
            return
        self.ruta_imagen = ruta
        self.img_proc = None
        self.boton_fondo_menu.configure(state="normal", text="Quitar fondo (preprocesado)")
        self.boton_metodo.configure(state="normal", text="Metodo: GRABCUT")
        self.nombre_imagen.configure(text=os.path.basename(ruta))
        self._mostrar_vista_previa()
        self.boton_rgb.configure(state="normal")
        self.boton_ycm.configure(state="normal")
        for valores in self._info_filtros.values():
            valores["ima"].configure(text=os.path.basename(ruta))
            valores["dir"].configure(text=self.directorio_desde_src(ruta))
        self._renderar_canales("rgb")
        self._renderar_canales("ycm")

    def _mostrar_vista_previa(self):
        lienzo = self.vista_previa
        lienzo.delete("all")
        if "preview" in self._imagenes_tk:
            del self._imagenes_tk["preview"]
        if self.img_rgb is None:
            lienzo.create_text(152, 48, text="seleccionar imagen", font=("Segoe UI", 16), fill=NEGRO)
            return
        imagen = Image.fromarray(self.img_proc if self.img_proc is not None else self.img_rgb)
        proporcion = min(285 / imagen.width, 92 / imagen.height)
        nuevo = (max(1, round(imagen.width * proporcion)), max(1, round(imagen.height * proporcion)))
        imagen = imagen.resize(nuevo)
        foto = ImageTk.PhotoImage(imagen)
        self._imagenes_tk["preview"] = foto
        lienzo.create_image(152, 48, image=foto)

    @staticmethod
    def directorio_desde_src(ruta):
        directorio = os.path.dirname(ruta)
        indice = directorio.lower().find("src")
        if indice == -1:
            return directorio
        return directorio[indice:]

    def _renderar_canales(self, clave):
        if self.img_rgb is None:
            return
        for letra in self._canvas_canales[clave]:
            self.aplicar_canal(clave, letra)

    def alternar_modo(self, clave):
        orden = ("color", "gris", "objeto")
        actual = self.modo_canal[clave]
        self.modo_canal[clave] = orden[(orden.index(actual) + 1) % len(orden)]
        self._botones_modo[clave].configure(text=f"Modo: {self.modo_canal[clave]}")
        self._renderar_canales(clave)

    def aplicar_canal(self, clave, letra):
        if self.img_rgb is None:
            messagebox.showwarning("Aviso", "Primero selecciona una imagen.")
            return
        canal = self.canal_segun(clave, letra)
        lienzo = self._canvas_canales[clave][letra]
        if canal.ndim == 3:
            imagen = Image.fromarray(canal)
        else:
            imagen = Image.fromarray(canal, mode="L")
        maximo = 292
        proporcion = min(maximo / imagen.width, maximo / imagen.height)
        nuevo = (max(1, round(imagen.width * proporcion)), max(1, round(imagen.height * proporcion)))
        imagen = imagen.resize(nuevo)
        foto = ImageTk.PhotoImage(imagen)
        self._imagenes_tk[(clave, letra)] = foto
        lienzo.delete("all")
        lienzo.create_image(150, 150, image=foto)
        metrica = self._metrica[clave][letra]
        if self.modo_canal.get(clave) == "objeto":
            area = float(np.count_nonzero(canal)) / canal.size * 100
            metrica.configure(text=f"area {area:.0f}%")
        else:
            metrica.configure(text="")

    def canal_segun(self, clave, letra):
        imagen = self.img_proc if self.img_proc is not None else self.img_rgb
        rojos = imagen[:, :, 0]
        verdes = imagen[:, :, 1]
        azules = imagen[:, :, 2]
        modo = self.modo_canal.get(clave)
        objeto = modo == "objeto"
        gris = modo == "gris"
        cero = np.zeros_like(rojos)
        if clave == "rgb":
            if letra == "R":
                canal = rojos
            elif letra == "G":
                canal = verdes
            else:
                canal = azules
            if objeto:
                return self._objeto_de(canal)
            if gris:
                return canal
            if letra == "R":
                return np.dstack([canal, cero, cero])
            if letra == "G":
                return np.dstack([cero, canal, cero])
            return np.dstack([cero, cero, canal])
        if letra == "Y":
            componente = ((rojos.astype(np.float32) + verdes.astype(np.float32)) / 2).astype(np.uint8)
            if objeto:
                return self._objeto_de(componente)
            if gris:
                return componente
            return np.dstack([rojos, verdes, cero])
        if letra == "C":
            componente = ((verdes.astype(np.float32) + azules.astype(np.float32)) / 2).astype(np.uint8)
            if objeto:
                return self._objeto_de(componente)
            if gris:
                return componente
            return np.dstack([cero, verdes, azules])
        componente = ((rojos.astype(np.float32) + azules.astype(np.float32)) / 2).astype(np.uint8)
        if objeto:
            return self._objeto_de(componente)
        if gris:
            return componente
        return np.dstack([rojos, cero, azules])

    @staticmethod
    def _objeto_de(canal):
        suave = cv2.GaussianBlur(canal, (5, 5), 1.2)
        _, binaria = cv2.threshold(suave, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        if cv2.countNonZero(binaria) > binaria.size // 2:
            binaria = cv2.bitwise_not(binaria)
        kernel = np.ones((3, 3), np.uint8)
        binaria = cv2.morphologyEx(binaria, cv2.MORPH_CLOSE, kernel, iterations=2)
        contornos, _ = cv2.findContours(binaria, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        mascara = np.zeros_like(canal)
        if contornos:
            mayor = max(contornos, key=cv2.contourArea)
            cv2.drawContours(mascara, [mayor], -1, 255, -1)
        return mascara

    @staticmethod
    def _grabcut(imagen):
        alto, ancho = imagen.shape[:2]
        escala = 500.0 / max(alto, ancho)
        if escala < 1:
            pequena = cv2.resize(imagen, (round(ancho * escala), round(alto * escala)), interpolation=cv2.INTER_AREA)
        else:
            pequena = imagen
        peq_alto, peq_ancho = pequena.shape[:2]
        mascara = np.zeros((peq_alto, peq_ancho), np.uint8)
        fondo = np.zeros((1, 65), np.float64)
        objeto = np.zeros((1, 65), np.float64)
        rectangulo = (
            max(1, int(peq_ancho * 0.10)),
            max(1, int(peq_alto * 0.10)),
            int(peq_ancho * 0.80),
            int(peq_alto * 0.80),
        )
        cv2.grabCut(pequena, mascara, rectangulo, fondo, objeto, 5, cv2.GC_INIT_WITH_RECT)
        pequena_mask = np.where(
            (mascara == cv2.GC_FGD) | (mascara == cv2.GC_PR_FGD), 255, 0
        ).astype(np.uint8)
        return cv2.resize(pequena_mask, (ancho, alto), interpolation=cv2.INTER_NEAREST)

    def _mascara_global(self, clave):
        imagen = self.img_rgb
        if self.metodo_fondo == "grabcut":
            mascara = self._grabcut(imagen)
        else:
            if clave == "rgb":
                canales = [imagen[:, :, 0], imagen[:, :, 1], imagen[:, :, 2]]
            else:
                rojos = imagen[:, :, 0].astype(np.float32)
                verdes = imagen[:, :, 1].astype(np.float32)
                azules = imagen[:, :, 2].astype(np.float32)
                canales = [
                    ((rojos + verdes) / 2).astype(np.uint8),
                    ((verdes + azules) / 2).astype(np.uint8),
                    ((rojos + azules) / 2).astype(np.uint8),
                ]
            mascara = np.zeros(imagen.shape[:2], np.uint8)
            for canal in canales:
                mascara = cv2.bitwise_or(mascara, self._objeto_de(canal))
        kernel = np.ones((3, 3), np.uint8)
        mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, kernel, iterations=2)
        numero, marcada = cv2.connectedComponents(mascara)
        if numero > 1:
            conteo = np.bincount(marcada.ravel())
            mayor = int(np.argmax(conteo[1:]) + 1)
            mascara = np.where(marcada == mayor, 255, 0).astype(np.uint8)
        return mascara

    def alternar_fondo(self):
        if self.img_rgb is None:
            messagebox.showwarning("Aviso", "Primero selecciona una imagen.")
            return
        if self.img_proc is None:
            mascara = self._mascara_global("rgb")
            self.img_proc = self.img_rgb.copy()
            self.img_proc[mascara == 0] = 0
        else:
            self.img_proc = None
        etiqueta = "Quitar fondo (preprocesado)" if self.img_proc is None else "Restaurar original"
        self.boton_fondo_menu.configure(text=etiqueta)
        self._mostrar_vista_previa()
        self._renderar_canales("rgb")
        self._renderar_canales("ycm")

    def alternar_metodo(self):
        self.metodo_fondo = "grabcut" if self.metodo_fondo == "otsu" else "otsu"
        self.boton_metodo.configure(text="Metodo: GRABCUT" if self.metodo_fondo == "grabcut" else "Metodo: OTSU")
        if self.img_proc is not None:
            self.alternar_fondo()
            self.alternar_fondo()

    @staticmethod
    def _foto_para(imagen, maximo):
        proporcion = min(maximo / imagen.width, maximo / imagen.height)
        nuevo = (max(1, round(imagen.width * proporcion)), max(1, round(imagen.height * proporcion)))
        return ImageTk.PhotoImage(imagen.resize(nuevo))
        proporcion = min(maximo / imagen.width, maximo / imagen.height)
        nuevo = (max(1, round(imagen.width * proporcion)), max(1, round(imagen.height * proporcion)))
        return ImageTk.PhotoImage(imagen.resize(nuevo))


if __name__ == "__main__":
    AnalizadorApp().mainloop()