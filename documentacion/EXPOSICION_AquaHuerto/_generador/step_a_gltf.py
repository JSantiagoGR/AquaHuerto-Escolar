"""Convierte un STEP (con colores, p. ej. exportado de KiCad) a glTF binario (.glb) para importarlo en Blender.
Ejecutar con el Python que tiene CadQuery/OCP:  python step_a_gltf.py <entrada.step> <salida.glb>"""
import sys

from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.IFSelect import IFSelect_RetDone
from OCP.RWGltf import RWGltf_CafWriter
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TCollection import TCollection_AsciiString, TCollection_ExtendedString
from OCP.TColStd import TColStd_IndexedDataMapOfStringString
from OCP.TDF import TDF_LabelSequence
from OCP.TDocStd import TDocStd_Document
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.Message import Message_ProgressRange

ent, sal = sys.argv[1], sys.argv[2]
doc = TDocStd_Document(TCollection_ExtendedString('XmlOcaf'))
r = STEPCAFControl_Reader()
r.SetColorMode(True)
r.SetNameMode(True)
assert r.ReadFile(ent) == IFSelect_RetDone, 'no se pudo leer el STEP'
r.Transfer(doc)

st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
etiquetas = TDF_LabelSequence()
st.GetFreeShapes(etiquetas)
for i in range(1, etiquetas.Length() + 1):
    BRepMesh_IncrementalMesh(st.GetShape_s(etiquetas.Value(i)), 0.05, False, 0.3, True)

w = RWGltf_CafWriter(TCollection_AsciiString(sal), True)
w.Perform(doc, TColStd_IndexedDataMapOfStringString(), Message_ProgressRange())
print('GLB_OK', sal)
