import sys, os
import maya.standalone
maya.standalone.initialize(name='python')
import maya.cmds as cmds

path_to_file = sys.argv[1]

cmds.file(path_to_file, open=True, force=True)

# Importar todas las referencias
for rn in cmds.ls(type='reference') or []:
    if rn == 'sharedReferenceNode':
        continue
    try:
        if not cmds.referenceQuery(rn, isLoaded=True):
            cmds.file(loadReference=rn)
        # Importa la referencia
        cmds.file(importReference=True, referenceNode=rn)
    except Exception as e:
        print("WARN: no se pudo importar referencia %s: %s" % (rn, e))

cmds.file(save=True)
maya.standalone.uninitialize()
