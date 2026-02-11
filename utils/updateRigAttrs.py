import sys
sys.path.insert(0, r"Z:\05Framework\users\aferraz\packages\dev_tk\master_tk_config\install\core\python")
sys.path.insert(0, r"Z:\05Framework\users\aferraz")

import maya.standalone
maya.standalone.initialize(name='python')
import maya.cmds as mc

mc.loadPlugin("AbcImport")

import time
import sgtk
import logging
import pprint
import os   

import wknd_tools
from wknd_tools.core import publish_version
import importlib
importlib.reload(publish_version)

import datetime
now = datetime.datetime.now()

###########################################

#######################
# Conectar a ShotGrid #
#######################

tk = sgtk.sgtk_from_path(r"Z:\05Framework\users\aferraz\packages\dev_tk\master_tk_config")
sg = tk.shotgun

# engine = sgtk.platform.current_engine()
# tk = engine.sgtk
# sg = engine.shotgun
# context = engine.context

###########################################


# def add_attributes(mesh, asset_info):

#     # Create Attributes
#     for key in asset_info:

#         if not mc.attributeQuery(key, node=mesh, exists=True):

#             if isinstance(asset_info[key], str):
#                 mc.addAttr(mesh, longName=key, dataType='string')
#             elif isinstance(asset_info[key], int):
#                 mc.addAttr(mesh, longName=key, at='long')
#             elif isinstance(asset_info[key], float):
#                 mc.addAttr(mesh, longName=key, at='double')
#             elif isinstance(asset_info[key], bool):
#                 mc.addAttr(mesh, longName=key, at='bool')

#         if isinstance(asset_info[key], str):

#             mc.setAttr(f"{mesh}.{key}", lock=False)
#             mc.setAttr(f"{mesh}.{key}", asset_info[key], type='string')
#             mc.setAttr(f"{mesh}.{key}", lock=True)

#         else:

#             mc.setAttr(f"{mesh}.{key}", lock=False)
#             mc.setAttr(f"{mesh}.{key}", asset_info[key])
#             mc.setAttr(f"{mesh}.{key}", lock=True)


_SUFFIXES = ("R", "G", "B", "X", "Y", "Z")


def _is_child_component_attr(node, key):
    # Ej: aiShadowColorR -> padre aiShadowColor si existe
    if len(key) < 2:
        return False
    if key.endswith(_SUFFIXES):
        parent = key[:-1]
        return mc.attributeQuery(parent, node=node, exists=True)
    return False


def _is_triple_value(v):
    # [(x,y,z)] o (x,y,z)
    return (
        isinstance(v, (list, tuple)) and
        (
            (len(v) == 1 and isinstance(v[0], (list, tuple)) and len(v[0]) == 3) or
            (len(v) == 3 and all(isinstance(x, (int, float)) for x in v))
        )
    )


def _normalize_triple(v):
    return tuple(v[0] if (isinstance(v, (list, tuple)) and len(v) == 1) else v)


def add_attributes(mesh, asset_info):

    for key, value in asset_info.items():

        # Si te están llegando hijos tipo aiShadowColorR, intenta apuntar al padre
        target_key = key
        if _is_child_component_attr(mesh, key):
            target_key = key[:-1]  # quita R/G/B/X/Y/Z

        plug = f"{mesh}.{target_key}"

        # -------------------------
        # Crear atributo si no existe
        # (solo para tus custom; los ai* normalmente ya existen)
        # -------------------------
        if not mc.attributeQuery(target_key, node=mesh, exists=True):

            if isinstance(value, str):
                mc.addAttr(mesh, ln=target_key, dt="string")

            elif isinstance(value, bool):
                mc.addAttr(mesh, ln=target_key, at="bool")

            elif isinstance(value, int):
                mc.addAttr(mesh, ln=target_key, at="long")

            elif isinstance(value, float):
                mc.addAttr(mesh, ln=target_key, at="double")

            elif _is_triple_value(value):
                # crear double3 + hijos
                mc.addAttr(mesh, ln=target_key, at="double3")
                mc.addAttr(mesh, ln=f"{target_key}X", at="double", parent=target_key)
                mc.addAttr(mesh, ln=f"{target_key}Y", at="double", parent=target_key)
                mc.addAttr(mesh, ln=f"{target_key}Z", at="double", parent=target_key)

            else:
                continue  # tipo no soportado

        # -------------------------
        # Si está conectado, NO lo tocamos (evita romper shading/rig)
        # -------------------------
        if mc.listConnections(plug, s=True, d=False):
            # si quieres log:
            # print(f"SKIP conectado: {plug}")
            continue

        # -------------------------
        # Set value (con unlock temporal si hace falta)
        # -------------------------
        # was_locked = mc.getAttr(plug, lock=True)
        # if was_locked:
        #     mc.setAttr(plug, lock=False)

        try:
            if isinstance(value, str):
                mc.setAttr(plug, value if value is not None else "", type="string")

            elif _is_triple_value(value):
                x, y, z = _normalize_triple(value)
                # ojo: aunque el atributo sea color, setAttr espera double3/float3
                mc.setAttr(plug, x, y, z, type="double3")

            else:
                # Aplana [val] -> val
                if isinstance(value, (list, tuple)) and len(value) == 1 and not isinstance(value[0], (list, tuple)):
                    value = value[0]
                # print("FAIL", plug, "mayaType=", mc.getAttr(plug, type=True), "value=", value, "pyType=", type(value))
                mc.setAttr(plug, value)

        finally:
            mc.setAttr(plug) #, lock=was_locked)


#########################

def _collapse_components(attrs, node):
    """Quita aiColorR/G/B si existe aiColor (padre) y es float3/double3."""
    keep = []
    attrset = set(attrs)
    for a in attrs:
        if len(a) > 1 and a.endswith(_SUFFIXES):
            parent = a[:-1]
            if parent in attrset:
                try:
                    t = mc.getAttr(f"{node}.{parent}", type=True)
                    if t in ("float3", "double3"):
                        continue  # skip componente, nos quedamos con el padre
                except:
                    pass
        keep.append(a)
    return keep


def _get_default(node, attr):
    # attributeQuery listDefault suele devolver lista de defaults (a veces None)
    try:
        d = mc.attributeQuery(attr, node=node, listDefault=True)
        if d is None:
            return None
        # float3/double3 suelen venir como [x,y,z]
        return d
    except:
        return None


def _norm_value(v):
    # getAttr para triples suele devolver [(x,y,z)]
    if isinstance(v, (list, tuple)) and len(v) == 1 and isinstance(v[0], (list, tuple)):
        return list(v[0])
    if isinstance(v, (list, tuple)) and len(v) == 1 and not isinstance(v[0], (list, tuple)):
        return v[0]
    return v


def _differs(v, d, eps=1e-6):
    if d is None:
        return False  # si no sabemos el default, no lo marcamos como modificado
    v = _norm_value(v)
    # defaults suelen ser lista
    if isinstance(d, (list, tuple)) and isinstance(v, (list, tuple)):
        if len(d) != len(v):
            return True
        for a, b in zip(v, d):
            if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                if abs(a - b) > eps:
                    return True
            else:
                if a != b:
                    return True
        return False
    # escalares
    if isinstance(v, (int, float)) and isinstance(d, (list, tuple)) and len(d) == 1:
        d = d[0]
    if isinstance(v, (int, float)) and isinstance(d, (int, float)):
        return abs(v - d) > eps
    return v != d


def get_modified_ai_attrs(shape, include_connected=False):
    """
    Devuelve dict {attr: value} con solo los ai* que difieren del default.
    Por defecto excluye los conectados (o puedes incluirlos para log).
    """
    attrs = mc.listAttr(shape, st="ai*") or []
    attrs = _collapse_components(attrs, shape)

    out = {}
    for a in attrs:
        plug = f"{shape}.{a}"

        # si está conectado y no quieres incluirlos, skip
        in_conns = mc.listConnections(plug, s=True, d=False)
        if in_conns and not include_connected:
            continue

        try:
            v = mc.getAttr(plug)
        except:
            continue

        d = _get_default(shape, a)
        if _differs(v, d):
            out[a] = v

    return out

##########################


def setup_logger():
    logger = logging.getLogger("wknd_autopub")
    logger.setLevel(logging.DEBUG)   # o INFO

    # Evitar añadir handlers duplicados si llamas varias veces
    if not logger.handlers:
        # Handler a consola
        sh = logging.StreamHandler()
        sh.setLevel(logging.DEBUG)
        fmt = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        sh.setFormatter(fmt)
        logger.addHandler(sh)

        # Handler a fichero (opcional pero muy útil)
        log_path = r"Z:\05Framework\logs\auto_publish\autoPublish_Rigs_log.txt"
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        fh = logging.FileHandler(log_path, mode="a", encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    return logger

###############


logger = setup_logger()

logger.info("------------------------------------------ ")
logger.info(f"STARTING ROUTINE ---------------- {now} ---- ")
logger.info("------------------------------------------ ")
###############


def _publish_to_SG(asset, task, fields):

    logger.info(f"Publicando a SG -{asset}-")

    context = tk.context_from_entity_dictionary(task)
    # logger.info(f"CONTEXT --> {context.entity}")

    current_version = fields["version"]
    description = "Auto update - Copiamos attributos de Shading al Rig"
    asset_type = fields["sg_asset_type"]
    use_playblast = False

    publisher = publish_version.Publisher(context, current_version, description, asset_type, use_playblast, log_callback=logger, tk=tk, sg=sg)
    publish_result = publisher.publish()

    logger.info("✅ PUBLISH COMPLETE")

    logger.info(publish_result)
    logger.info("-"*100)
    logger.info("-"*100)

###########################################


def main():

    ############################################
    # Buscamos Props no procesados previamente #
    ############################################

    # assets = sg.find("Asset", [["sg_asset_type", "is", "PRP"], ["sg_uv_on_rig", "is_not", True]], ["code", "sg_asset_type", ])
    filters = [
        # ["entity.Asset.code", "in", ["cajaCartonGrande"]],
        ["entity.Asset.sg_asset_type", "is", "PRP"],
        ["entity.Asset.sg_uv_on_rig", "is_not", True],
        ["step", "is", {"type": "Step", "id": 16}],
        ["sg_status_list", "is", "apr"]
        ]

    assets = sg.find("Task",
                     filters,
                     ["entity.Asset.code", "entity.Asset.sg_asset_type", "entity.Asset.id"]
                     )

    logger.info(f"Assets encontrados para actualizar: {len(assets)}")

    # Templates
    template_abc = tk.templates["asset_alembic_cache"]
    template_work = tk.templates["maya_asset_work"]

    # Custom attributes
    attrs = ['GUS_asset_id', 'GUS_asset_name', 'GUS_shading_grp']

    # Recorremos la lista
    errors = {}
    for asset in assets:

        asset_name = asset["entity.Asset.code"].replace(" ", "")

        logger.info(f"Procesando {asset_name} ------------------------------")

        # GET RIG SCENE ###############################

        fields = {"Task": "RigAnimation"}
        fields["sg_asset_type"] = asset["entity.Asset.sg_asset_type"]
        fields["Asset"] = asset_name

        # Buscamos paths que matcheen el template
        p = tk.paths_from_template(template_work, fields)
        if not p:
            errors[asset_name] = "No hay escena de RigAnimation!"
            continue

        # Ordenamos los paths y cogemos el más nuevo
        p.sort(reverse=True)
        work_path = p[0]
        logger.info(f"\t- Work path: {work_path}")

        # Get fields from scene
        fields_work = template_work.get_fields(work_path)

        # Get RigAnimation task from SG
        task = sg.find_one("Task", 
                           [["content", "is", fields_work["Task"]], ["entity.Asset.id", "is", asset["entity.Asset.id"]]], 
                           ["content", "entity", "step"])

        # GET ABC PATH #################################

        fields["Task"] = "Shading"

        # Buscamos paths que matcheen el template
        p_abc = tk.paths_from_template(template_abc, fields)
        if not p_abc:
            errors[asset_name] = "No hay Abc!"
            continue

        # Ordenamos los paths y cogemos el más nuevo
        p_abc.sort(reverse=True)
        abc_path = p_abc[0]
        logger.info(f"\t- ABC path: {abc_path}")

        # Abrimos la escena #############################

        mc.file(work_path, open=True, f=True)

        logger.info("\t- Escena abierta :)")

        # Referenciamos el abc
        namespace = f"{asset_name}_scene"

        ref_node = mc.file(
            abc_path,
            reference=True,
            loadReferenceDepth="all",
            mergeNamespacesOnClash=False,
            namespace=namespace,
        )

        logger.info(f"\t- Alembic importado :)")

        # Cogemos el frame actual para hacer el refresh
        frame = mc.currentTime(q=True)

        #################################
        # Recorremos las meshes del abc #
        #################################

        logger.info(f"\t- Procesando meshes...")

        ref = mc.ls(f"{namespace}:*", assemblies=True)

        logger.info(f"\t- NAMESPACE = {namespace}")
        logger.info(f"\t- REF = {ref}")

        # Buscamos las mesh del abc y el rig
        meshes_in_ref = mc.listRelatives(f"{ref[0]}|{namespace}:geo", ad=True, type='mesh')  # , f=True)
        meshes_in_rig = mc.listRelatives(f"{asset_name}|geo", ad=True, type='mesh')

        asset_info = {}

        for mesh in meshes_in_ref:

            # Añadimos los atributos de arnold (esto se puede mejorar y hacer solo una vez)
            # attrs = attrs + _list_arnold_attrs(mesh)

            mod_ai_attr = get_modified_ai_attrs(mesh, include_connected=False)
            attrs = attrs + [k for k in mod_ai_attr.keys()]

            asset_info[mesh.split(":")[-1]] = {}

            # # Get Attr Values
            # attrErrors = []
            # for attr in attrs:
            #     try:
            #         value = mc.getAttr(f"{mesh}.{attr}")
            #         asset_info[mesh.split(":")[-1]][attr] = value
            #     except:
            #         attrErrors.append(attr)

            ########
            # Get Attr Values (robusto para float3/double3)
            attrErrors = []
            mesh_key = mesh.split(":")[-1]
            dst = asset_info.setdefault(mesh_key, {})

            # Helpers
            _suffixes = ("R", "G", "B", "X", "Y", "Z")

            def _is_component(a):
                return len(a) > 1 and a.endswith(_suffixes)

            def _parent_attr(a):
                return a[:-1]

            for attr in attrs:
                try:
                    plug = f"{mesh}.{attr}"
                    if mc.listConnections(plug, source=True, destination=False):
                        continue

                    # Si es componente (aiShadowColorR), guardamos el componente
                    # pero además intentaremos colapsar al padre después
                    value = mc.getAttr(plug)
                    dst[attr] = value

                except Exception:
                    attrErrors.append(attr)

            # ---- Collapsar componentes a su padre (R/G/B o X/Y/Z) ----
            # Ej: aiShadowColorR/G/B -> aiShadowColor = [(r,g,b)]
            #     aiSomethingX/Y/Z   -> aiSomething = [(x,y,z)]
            for a in list(dst.keys()):
                if not _is_component(a):
                    continue

                parent = _parent_attr(a)

                # Si el padre existe en el nodo y es float3/double3, lo reconstruimos
                if mc.attributeQuery(parent, node=mesh, exists=True):
                    ptype = mc.getAttr(f"{mesh}.{parent}", type=True)
                    if ptype in ("float3", "double3"):

                        # Coge componentes, si faltan los pone a 0
                        def _get_comp(suf):
                            v = dst.get(parent + suf)
                            # getAttr de un componente suele ser float; si viene [float], aplanamos
                            if isinstance(v, (list, tuple)) and len(v) == 1 and not isinstance(v[0], (list, tuple)):
                                v = v[0]
                            return float(v) if v is not None else 0.0

                        x = _get_comp("R") if (parent + "R") in dst else _get_comp("X")
                        y = _get_comp("G") if (parent + "G") in dst else _get_comp("Y")
                        z = _get_comp("B") if (parent + "B") in dst else _get_comp("Z")

                        dst[parent] = [(x, y, z)]

                        # opcional: quitar los componentes para no intentar setearlos luego
                        for suf in ("R", "G", "B", "X", "Y", "Z"):
                            dst.pop(parent + suf, None)
            ###########

            if attrErrors:
                errors[asset_name] = attrErrors

            ################
            # COPIAMOS UVs #
            ################

            # shapeOrig = mesh.split(":")[-1].replace("Shape", "ShapeOrig")
            for sh in meshes_in_rig:
                if mesh.split(":")[-1].split("_")[0] in sh and "shapeorig" in sh.lower():
                    shapeOrig = sh
                    break
            if not shapeOrig:
                errors[asset_name] = f"Cannot find ShapeOrig for {mesh}"
                continue

            # Conectamos
            mc.connectAttr(f"{mesh}.outMesh", f"{shapeOrig}.inMesh")
            # Refresh
            time.sleep(0.3)
            mc.currentTime(frame+1)
            # Desconectamos
            mc.disconnectAttr(f"{mesh}.outMesh", f"{shapeOrig}.inMesh")
            # Refresh
            mc.currentTime(frame-1)
            mc.refresh(force=True)

            #####################
            # ADD ATTR TO SHAPE #
            #####################

            add_attributes(mesh.split(":")[-1], asset_info[mesh.split(":")[-1]])

        # Eliminamos la ref del ABC
        logger.info(f"\t- Eliminamos la ref del ABC...")
        refFile = mc.referenceQuery(ref_node, filename=True, withoutCopyNumber=True)
        mc.file(refFile, removeReference=True)

        if not attrErrors:

            logger.info(f"\t- Publicando...")

            # PUBLISH TO SHOTGRID
            _publish_to_SG(asset, task, fields_work)

            # Update checkbox on SG
            sg.update("Asset", asset["entity.Asset.id"], {"sg_uv_on_rig": True})

            logger.info(f"\t- ✅ DONE! ^^ ==================================")

        else:
            logger.info(f"\t- ❌❌❌ SKIPPING publish of {asset_name} due to attributte errors!")

    if errors:
        logger.info(f"---------------- ❌ ERRORES ❌ ----------------\n ")
        logger.info(pprint.pprint(errors))


#############################################################################

if __name__ == "__main__":
    main()

## USE ##
# "C:\Program Files\Autodesk\Maya2026\bin\mayapy.exe" Z:\05Framework\users\aferraz\wknd_tools\utils\updateRigAttrs.py