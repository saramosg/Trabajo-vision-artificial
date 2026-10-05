import pymupdf
doc=pymupdf.open(r"C:\Users\santiago\Downloads\ecuaciones\pdf\Notas de Clase 5.pdf")
doc[8].get_pixmap(dpi=200).save(r"C:\Users\santiago\AppData\Local\Temp\opencode\c5-p9b.png")
doc[9].get_pixmap(dpi=200).save(r"C:\Users\santiago\AppData\Local\Temp\opencode\c5-p10b.png")
print("ok2")
