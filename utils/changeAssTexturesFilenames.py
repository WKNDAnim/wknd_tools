import sys
sys.path.insert(0, r"Z:\05Framework\users\aferraz\packages\dev_tk\master_tk_config\install\core\python")
sys.path.insert(0, r"Z:\05Framework\users\aferraz")

import re
import os
import sgtk
import shutil
import logging
import datetime

#######################
# Conectar a ShotGrid #
#######################

tk = sgtk.sgtk_from_path(r"Z:\05Framework\users\aferraz\packages\dev_tk\master_tk_config")
sg = tk.shotgun

###############################################


def _buscar_files(contenido, asset):

    """ Dado el contenido de un archivo .ass:
            - Busca los filenames de work
            - Busca su path equivalente en publish
            - Devuelve un dict: {work_path: publish_path}
            """

    template_work_painter = tk.templates["substancepainter_asset_textures_path_export"]
    template_work_designer = tk.templates["substancedesigner_asset_textures_path_export"]
    template_publish = tk.templates["texture_folder_publish"]

    # Buscamos la root de publish del asset
    asset_publish_root = _get_asset_text_pub_root(asset)
    if not asset_publish_root or not os.path.exists(asset_publish_root):
        log("❌❌ No se ha podido encontrar ASSET PUBLISH ROOT...")
        return

    # Buscamos los filenames en el archivo
    filenames = re.findall(r'filename "([^"]+)"', contenido)
    if not filenames:
        log("\t\t\t ⚠️⚠️⚠️ No filenames found!")
        return False

    # Recorremos cada uno para hacer replace a publish
    aux = {}
    for path in filenames:

        log(f"\t\t\t - {path}")

        if "publish" in path.lower():
            log("\t\t\t\t 🌞 El path ya está en publish ----------------------")
            # continue

        if "\\naswknd\DataCenter" in path:
            path.replace("\\naswknd\DataCenter", "Z:")

        # Separamos el filename
        _, file = os.path.split(path)

        # Formamos el path de publish
        new_path = os.path.join(asset_publish_root, file)

        log(f"\t\t\t\t --> {new_path}")

        aux[path] = new_path

    return aux


def _search_ass(asset):

    template_publish = tk.templates["asset_ass_root"]

    fields = {
        "Asset": asset["code"],
        "sg_asset_type": asset["sg_asset_type"],
        "Step": "SURF",
        "Task": "Shading"
    }

    ass_root = template_publish.apply_fields(fields)

    if not os.path.exists(ass_root):
        return False

    ass_files = os.listdir(ass_root)
    ass_files.sort(reverse=True)

    return os.path.join(ass_root, ass_files[0])


def _search_assets():

    filter = [
        ["project.Project.id", "is", 91],
        ["sg_asset_type", "in", ["ELEM"]],
        ["sg_status_list", "is_not", "omt"]
    ]
    query = ["code", "sg_asset_type"]

    return sg.find("Asset", filter, query)


def _get_asset_text_pub_root(asset):

    template = tk.templates["texture_folder_publish"]

    fields = {
        "Asset": asset["code"],
        "sg_asset_type": asset["sg_asset_type"],
        "Step": "SURF",
        "Task": "Shading"
    }

    paths = tk.paths_from_template(template, fields)
    paths.sort(reverse=True)

    return paths[0]


###############################################

ERROR = []
DONE = []

LINUX_ROOT = "/nbpt/remote/nbfxpt/jobs/GUS/mirror_weeknd"
WIN_ROOT = "Z:/02Proyectos"

today = datetime.datetime.today().strftime('%Y%m%d')
LOG_FILE = rf"Z:\05Framework\logs\ass\assFixer_{today}.log"

logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")


def log(msg):
    logging.info(msg)
    print(msg)


def main():

    assets = _search_assets()

    # assets = assets[:3]

    for asset in assets:

        log("="*100)
        log(asset)
        log("="*100)

        ass_path = _search_ass(asset)

        if not ass_path:
            ERROR.append(asset["code"])
            log(f"❌ No se ha podido encontrar ASS PATH ...")
            continue

        log(f"⏱️ Procesando: {ass_path}")

        # Hacemos backup del archivo
        ass_folder, ass_file = os.path.split(ass_path)
        log(f"\t - 📂 {ass_folder}\n\t - 📋 {ass_file}")
        publish_root = os.path.dirname(ass_folder)
        ass_bckp_folder = os.path.join(publish_root, "ass_bckp")
        if not os.path.exists(ass_bckp_folder):
            os.makedirs(ass_bckp_folder)
        ass_path_bckp = os.path.join(ass_bckp_folder, ass_file)

        log("\t - Haciendo backup...")

        if not os.path.exists(ass_path_bckp):
            shutil.copy2(ass_path, ass_path_bckp)
            log(f"\t\t - Backup: {ass_path_bckp}")

        log(f"\t\t - Backup DONE :) ")

        log("\t - Abrimos el archivo...")

        with open(ass_path, "r", encoding="utf-8") as f:
            contenido = f.read()

        log("\t\t - Cambiamos los filenames del ass:")

        equivalencias = _buscar_files(contenido, asset)

        if not equivalencias:
            ERROR.append(asset)
            continue

        # Hacemos replace en el .ass
        for current_path, new_path in equivalencias.items():
            contenido = contenido.replace(current_path, new_path)

        try:
            with open(ass_path, "w", encoding="utf-8") as f:
                f.write(contenido)
        except:
            ERROR.append(asset)
            continue

        log(f"✅ DONE --> {ass_path}\n")
        DONE.append(asset["code"])

    log("\n\n❌❌❌ ERRORES =======================================")
    log(ERROR)


    log("\n\n🪇🏄‍♂️🌞✅ DONES =======================================")
    log(DONE)

###############################################


if __name__ == "__main__":
    main()
