import os
import numpy as np
import cv2
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk

from analizador_imagenes import AnalizadorApp, BLANCO, NEGRO, GRIS


class PreprocesamientoApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Preprocesamiento: quitar fondo")
        self.configure(bg=BLANCO)
        self.geometry("960x560")
        self.resizable(False, False)

        self.ruta_imagen = None
        self.img_rgb = None
        self.mascara = None
        self.img_sin_fondo = None
        self.metodo = "grabcut"
        self._fotos = {}

        self._construir()

    def _construir(self):
        controles = tk.Frame(self, bg=BLANCO)
        controles.pack(pady=12)

        boton_seleccion = tk.Button(
            controles, text="Seleccionar imagen", font=("Segoe UI", 12),
            fg=NEGRO, bg=GRIS, relief="flat", width=15, command=self.seleccionar_imagen,
        )
        boton_seleccion.grid(row=0, column=0, padx=6)

        self.boton_quitar = tk.Button(
            controles, text="Quitar fondo", font=("Segoe UI", 12),
            fg=NEGRO, bg=GRIS, relief="flat", width=15, state="disabled", command=self.quitar_fondo,
        )
        self.boton_quitar.grid(row=0, column=1, padx=6)

        self.boton_metodo = tk.Button(
            controles, text="Metodo: GrabCut", font=("Segoe UI", 12),
            fg=NEGRO, bg=GRIS, relief="flat", width=15, state="disabled", command=self.alternar_metodo,
        )
        self.boton_metodo.grid(row=0, column=2, padx=6)

        self.boton_guardar = tk.Button(
            controles, text="Guardar sin fondo", font=("Segoe UI", 12),
            fg=NEGRO, bg=GRIS, relief="flat", width=15, state="disabled", command=self.guardar,
        )
        self.boton_guardar.grid(row=0, column=3, padx=6)

        self.boton_psd = tk.Button(
            controles, text="Guardar PSD (mascara)", font=("Segoe UI", 12),
            fg=NEGRO, bg=GRIS, relief="flat", width=16, state="disabled", command=self.guardar_psd,
        )
        self.boton_psd.grid(row=0, column=4, padx=6)

        self.boton_restaurar = tk.Button(
            controles, text="Restaurar original", font=("Segoe UI", 12),
            fg=NEGRO, bg=GRIS, relief="flat", width=15, state="disabled", command=self.restaurar,
        )
        self.boton_restaurar.grid(row=0, column=5, padx=6)

        paneles = tk.Frame(self, bg=BLANCO)
        paneles.pack(fill="both", expand=True)

        for col, (titulo, clave) in enumerate([("Original", "original"), ("Sin fondo", "resultado")]):
            marco = tk.Frame(paneles, bg=BLANCO)
            marco.grid(row=0, column=col, padx=15, pady=6)
            tk.Label(marco, text=titulo, font=("Segoe UI", 14, "bold"), fg=NEGRO, bg=BLANCO).pack()
            lienzo = tk.Canvas(marco, width=440, height=360, bg=GRIS, highlightthickness=0)
            lienzo.pack(pady=8)
            lienzo.create_text(220, 180, text="sin imagen", font=("Segoe UI", 16), fill=NEGRO)
            self.__dict__["lienzo_" + clave] = lienzo

        self.estado = tk.Label(
            self, text="", font=("Segoe UI", 12), fg=NEGRO, bg=BLANCO,
        )
        self.estado.pack(pady=8)

    def _foto_en(self, lienzo, array):
        imagen = Image.fromarray(array)
        proporcion = min(440 / imagen.width, 360 / imagen.height)
        nuevo = (max(1, round(imagen.width * proporcion)), max(1, round(imagen.height * proporcion)))
        foto = ImageTk.PhotoImage(imagen.resize(nuevo))
        self._fotos[lienzo] = foto
        lienzo.delete("all")
        lienzo.create_image(220, 180, image=foto)

    def seleccionar_imagen(self):
        ruta = filedialog.askopenfilename(
            title="Seleccionar imagen",
            filetypes=[("Imagenes", "*.png *.jpg *.jpeg *.bmp"), ("Todos los archivos", "*.*")],
        )
        if not ruta:
            return
        try:
            self.img_rgb = np.array(Image.open(ruta).convert("RGB"))
        except Exception as error:
            messagebox.showerror("Error", f"No se pudo cargar la imagen:\n{error}")
            return
        self.ruta_imagen = ruta
        self.mascara = None
        self.img_sin_fondo = None
        self._foto_en(self.lienzo_original, self.img_rgb)
        self._foto_en(self.lienzo_resultado, self.img_rgb * 0)
        self.estado.configure(text=f"Cargada: {os.path.basename(ruta)}  ({self.img_rgb.shape[1]}x{self.img_rgb.shape[0]})")
        self.boton_quitar.configure(state="normal")
        self.boton_metodo.configure(state="normal")
        self.boton_guardar.configure(state="disabled")
        self.boton_psd.configure(state="disabled")
        self.boton_restaurar.configure(state="normal")

    def _mascara_global(self):
        if self.metodo == "grabcut":
            mascara = AnalizadorApp._grabcut(self.img_rgb)
        else:
            rojo = self.img_rgb[:, :, 0]
            verde = self.img_rgb[:, :, 1]
            azul = self.img_rgb[:, :, 2]
            mascara = np.zeros(self.img_rgb.shape[:2], np.uint8)
            for canal in (rojo, verde, azul):
                mascara = cv2.bitwise_or(mascara, AnalizadorApp._objeto_de(canal))
        kernel = np.ones((3, 3), np.uint8)
        mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, kernel, iterations=2)
        numero, marcada = cv2.connectedComponents(mascara)
        if numero > 1:
            conteo = np.bincount(marcada.ravel())
            mayor = int(np.argmax(conteo[1:]) + 1)
            mascara = np.where(marcada == mayor, 255, 0).astype(np.uint8)
        return mascara

    def quitar_fondo(self):
        if self.img_rgb is None:
            messagebox.showwarning("Aviso", "Primero selecciona una imagen.")
            return
        mascara = self._mascara_global()
        self.mascara = mascara
        resultado = self.img_rgb.copy()
        resultado[mascara == 0] = 0
        rgba = np.dstack([self.img_rgb, mascara])
        self.img_sin_fondo = rgba
        self._foto_en(self.lienzo_resultado, resultado)
        area = float(np.count_nonzero(mascara)) / mascara.size * 100
        self.estado.configure(
            text=f"Fondo quitado con {self.metodo.upper()}  |  objeto: {area:.1f}% del area"
        )
        self.boton_guardar.configure(state="normal")
        self.boton_psd.configure(state="normal")

    def alternar_metodo(self):
        self.metodo = "otsu" if self.metodo == "grabcut" else "grabcut"
        self.boton_metodo.configure(text=f"Metodo: {'GrabCut' if self.metodo == 'grabcut' else 'OTSU'}")
        if self.img_rgb is not None and self.img_sin_fondo is not None:
            self.quitar_fondo()

    def restaurar(self):
        if self.img_rgb is None:
            return
        self.mascara = None
        self.img_sin_fondo = None
        self._foto_en(self.lienzo_resultado, self.img_rgb * 0)
        self.estado.configure(text="Original restaurado.")
        self.boton_guardar.configure(state="disabled")
        self.boton_psd.configure(state="disabled")

    def guardar_psd(self):
        if self.img_sin_fondo is None:
            messagebox.showwarning("Aviso", "Primero quita el fondo.")
            return
        base = os.path.splitext(os.path.basename(self.ruta_imagen or "imagen"))[0]
        ruta = filedialog.asksaveasfilename(
            title="Guardar PSD con mascara",
            initialfile=base + "_mascara",
            defaultextension=".psd",
            filetypes=[("Photoshop", "*.psd")],
        )
        if not ruta:
            return
        try:
            from psd_tools import PSDImage
        except ImportError:
            messagebox.showerror(
                "Error", "Falta el paquete psd-tools:\n  pip install psd-tools"
            )
            return
        try:
            rgb = self.img_rgb
            mascara = self.mascara
            psd = PSDImage.new("RGB", (rgb.shape[1], rgb.shape[0]))
            capa = psd.create_pixel_layer(Image.fromarray(rgb), name="objeto")
            capa.create_mask(Image.fromarray(mascara, mode="L"))
            psd.save(ruta)
            png = os.path.splitext(ruta)[0] + "_mascara.png"
            Image.fromarray(mascara, mode="L").save(png)
        except Exception as error:
            messagebox.showerror("Error", f"No se pudo guardar el PSD:\n{error}")
            return
        self.estado.configure(
            text=f"Guardado: {os.path.basename(ruta)} + mascara PNG"
        )

    def guardar(self):
        if self.img_sin_fondo is None:
            messagebox.showwarning("Aviso", "No hay imagen sin fondo para guardar.")
            return
        sugerencia = os.path.splitext(os.path.basename(self.ruta_imagen or "imagen"))[0] + "_sin_fondo.png"
        ruta = filedialog.asksaveasfilename(
            title="Guardar imagen sin fondo",
            initialfile=sugerencia,
            defaultextension=".png",
            filetypes=[("PNG", "*.png")],
        )
        if not ruta:
            return
        Image.fromarray(self.img_sin_fondo).save(ruta)
        self.estado.configure(text=f"Guardada en: {ruta}")


if __name__ == "__main__":
    PreprocesamientoApp().mainloop()