"""Convierte los STEP a archivos nativos de SolidWorks (.SLDPRT / .SLDASM) usando la API COM."""
import glob
import os
import sys
import time

import pythoncom
import win32com.client as w

SRC = sys.argv[1]
DST = sys.argv[2]
os.makedirs(DST, exist_ok=True)
pythoncom.CoInitialize()
sw = w.Dispatch('SldWorks.Application')
sw.Visible = False
time.sleep(3)
for f in sorted(glob.glob(os.path.join(SRC, '*.step'))):
    nombre = os.path.splitext(os.path.basename(f))[0]
    sw.LoadFile2(f, 'r')
    m = sw.ActiveDoc
    if m is None:
        print('NO_ABRIO', f)
        continue
    tipo = m.GetType  # propiedad: 1 pieza, 2 ensamble
    ext = '.SLDASM' if tipo == 2 else '.SLDPRT'
    out = os.path.join(DST, nombre + ext)
    ok = m.SaveAs3(out, 0, 2)
    print('GUARDADO' if ok == 0 else 'ERROR_%s' % ok, out)
    sw.CloseAllDocuments(True)
sw.ExitApp()
