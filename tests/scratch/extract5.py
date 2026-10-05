import pymupdf
doc=pymupdf.open(r"C:\Users\santiago\Downloads\ecuaciones\pdf\Notas de Clase 5.pdf")
print("pages:", len(doc))
out=[]
for i in range(len(doc)):
    t=doc[i].get_text() or ""
    out.append(f"--- PAGE {i+1} chars={len(t)} ---\n"+t)
open(r"C:\Users\santiago\AppData\Local\Temp\opencode\clase5.txt","w",encoding="utf-8").write("\n".join(out))
