import pymupdf
src=r"C:\Users\santiago\Downloads\ecuaciones\pdf\Notas de Clase 5.pdf"
doc=pymupdf.open(src)
for i in range(len(doc)):
    page=doc[i]
    pix=page.get_pixmap(dpi=150)
    pix.save(rf"C:\Users\santiago\AppData\Local\Temp\opencode\c5-p{i+1}.png")
print("done", len(doc))
