import os
import sys
import tempfile
import subprocess
from collections import defaultdict
import re

sys.path.insert(0, r"Z:\05Framework\users\aferraz\packages\dev_tk\master_tk_config\install\core\python")

import sgtk
tk = sgtk.sgtk_from_path(r"Z:\05Framework\users\aferraz\packages\dev_tk\master_tk_config")
sg = tk.shotgun

from PySide6 import QtWidgets


##########
# CONFIG #
##########

DEADLINECOMMAND = r"C:\Program Files\Thinkbox\Deadline10\bin\deadlinecommand.exe"
MAYAPY = r"C:\Program Files\Autodesk\Maya2026\bin\mayapy.exe"

LAUNCH_RENDER_SCRIPT = os.path.join(os.path.dirname(__file__), "sendFlayRender.py")
PREP_JSON_SCRIPT = os.path.join(os.path.dirname(os.path.dirname(__file__)), r"utils\setAutoExporter.py")

POOL = "none"
GROUP = "none"
PRIORITY = 50

####################
# GET INFO FROM SG #
####################


def _get_seqs_from_sg():

    # =========================
    # 1) TRAER SHOTS NO OMIT
    # =========================
    filters = [["project", "is", {"type": "Project", "id": 91}], ["code", "not_contains", "master"], ["sg_status_list", "is_not", "omt"]]
    query = ["code", "sg_sequence", "sg_status_list", "sg_set_json_exported", "sg_auto_flay"]

    shots = sg.find("Shot", filters, query)

    # Filtramos los shots que ya han sido procesados
    shots = [s for s in shots if not s.get("sg_set_json_exported") or not s.get("sg_auto_flay")]

    if not shots:
        return ["No quedan shots para procesar :)"]

    # Nos quedamos solo con shots que tengan secuencia asignada
    shots = [s for s in shots if s.get("sg_sequence")]

    if not shots:
        return ["No hay shots con secuencias para procesar :)"]

    shot_ids = [s["id"] for s in shots]

    # shot_id -> sequence_name
    shot_to_sequence = {}
    # sequence_name -> lista de shot_ids no OMIT
    sequence_to_shots = defaultdict(list)

    for shot in shots:
        seq = shot["sg_sequence"]
        seq_name = seq["name"]
        shot_id = shot["id"]

        shot_to_sequence[shot_id] = seq_name
        sequence_to_shots[seq_name].append(shot_id)

    # =========================
    # 2) TRAER TASKS DE ANIMACIÓN
    # =========================

    task_filters = [
        ["entity", "type_is", "Shot"],
        ["entity", "in", [{"type": "Shot", "id": sid} for sid in shot_ids]],
        ["content", "is", "Animation"],
    ]

    task_fields = [
        "id",
        "content",
        "sg_status_list",
        "entity",
    ]

    tasks = sg.find("Task", task_filters, task_fields)

    # shot_id -> status de su task de animación
    anim_status_by_shot = {}

    for task in tasks:
        shot = task.get("entity")
        if shot and shot["type"] == "Shot":
            anim_status_by_shot[shot["id"]] = task.get("sg_status_list")

    # =========================
    # 3) FILTRAR SECUENCIAS
    # =========================
    valid_sequences = []

    for seq_name, seq_shot_ids in sequence_to_shots.items():
        all_ok = True

        for shot_id in seq_shot_ids:
            anim_status = anim_status_by_shot.get(shot_id)

            # Si un shot no tiene task de animación, lo damos por NO válido
            if anim_status not in ["na", "apppbl"]:
                all_ok = False
                break

        if all_ok and seq_shot_ids:
            valid_sequences.append(seq_name)

    # =========================
    # RESULTADO
    # =========================
    print("Secuencias válidas:")
    for seq_name in sorted(valid_sequences):
        print(f" - {seq_name}")

    return sorted(valid_sequences)


###################
# DEADLINE SUBMIT #
###################

def submit_prepare_job(sequence_name: str) -> str:

    # if not os.path.exists(DEADLINECOMMAND):
    #     raise FileNotFoundError(f"No existe deadlinecommand: {DEADLINECOMMAND}")
    # if not os.path.exists(MAYAPY):
    #     raise FileNotFoundError(f"No existe mayapy: {MAYAPY}")
    if not os.path.exists(PREP_JSON_SCRIPT):
        raise FileNotFoundError(f"No existe el script: {PREP_JSON_SCRIPT}")
    if not os.path.exists(LAUNCH_RENDER_SCRIPT):
        raise FileNotFoundError(f"No existe el script: {LAUNCH_RENDER_SCRIPT}")

    def submit(job_name, script_path, dependency=None):

        job_info_lines = [
            "Plugin=CommandLine",
            f"Name={job_name}",
            "Comment=Job lanzado desde interfaz de producción",
            f"Pool={POOL}",
            f"Group={GROUP}",
            "Priority=60",
            "Frames=0",
            "ChunkSize=1",
            f"BatchName=FLAY_{sequence_name}",
        ]
        if dependency:
            job_info_lines.append(f"JobDependencies={dependency}")

        plugin_info_lines = [
            f"Executable={MAYAPY}",
            f'Arguments="{script_path}" "{sequence_name}"',
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            job_info_path = os.path.join(tmpdir, "job_info.job")
            plugin_info_path = os.path.join(tmpdir, "plugin_info.job")

            with open(job_info_path, "w", encoding="utf-8") as f:
                f.write("\n".join(job_info_lines))
            with open(plugin_info_path, "w", encoding="utf-8") as f:
                f.write("\n".join(plugin_info_lines))

            result = subprocess.run(
                [DEADLINECOMMAND, job_info_path, plugin_info_path],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                raise RuntimeError(
                    f"Error enviando {job_name} para {sequence_name}\n"
                    f"STDOUT:\n{result.stdout}\n\n"
                    f"STDERR:\n{result.stderr}"
                )

            match = re.search(r"JobID=([a-fA-F0-9]+)", result.stdout)
            if not match:
                raise RuntimeError(f"No se pudo extraer el JobID de {job_name}")

            return result.stdout, match.group(1)

    out1, job1_id = submit(f"Create_JSON - {sequence_name}", PREP_JSON_SCRIPT)
    out2, _ = submit(f"Launch RENDER_FLAY - {sequence_name}", LAUNCH_RENDER_SCRIPT, dependency=job1_id)

    return f"{out1}\n{out2}"


######
# UI #
######

class ProductionLauncher(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lanzador de secuencias a Deadline")
        self.resize(550, 500)

        self.layout = QtWidgets.QVBoxLayout(self)

        self.info_label = QtWidgets.QLabel(
            "Selecciona una o varias secuencias y pulsa 'Lanzar jobs'."
        )
        self.layout.addWidget(self.info_label)

        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.addItems(_get_seqs_from_sg())

        # IMPORTANTE: habilitar selección múltiple
        self.list_widget.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )

        self.layout.addWidget(self.list_widget)

        self.launch_button = QtWidgets.QPushButton("Lanzar jobs")
        self.layout.addWidget(self.launch_button)

        self.output_text = QtWidgets.QPlainTextEdit()
        self.output_text.setReadOnly(True)
        self.layout.addWidget(self.output_text)

        self.launch_button.clicked.connect(self.launch_selected_sequences)

    def launch_selected_sequences(self):
        items = self.list_widget.selectedItems()

        if not items:
            QtWidgets.QMessageBox.warning(
                self,
                "Aviso",
                "Selecciona al menos una secuencia."
            )
            return

        reply = QtWidgets.QMessageBox.question(
            self,
            "Confirmar envío",
            f"Se van a enviar {len(items)} jobs a Deadline.\n\n¿Continuar?"
        )

        if reply != QtWidgets.QMessageBox.Yes:
            return

        sequence_names = [item.text() for item in items]

        # Desactivar botón mientras envía
        self.launch_button.setEnabled(False)

        ok_count = 0
        error_count = 0

        try:
            for sequence_name in sequence_names:
                self.output_text.appendPlainText(
                    f"Enviando job para {sequence_name}..."
                )
                QtWidgets.QApplication.processEvents()

                try:
                    output = submit_prepare_job(sequence_name)
                    self.output_text.appendPlainText(
                        f"[OK] Job enviado para {sequence_name}\n{output}\n"
                    )
                    ok_count += 1

                except Exception as e:
                    self.output_text.appendPlainText(
                        f"[ERROR] {sequence_name}: {e}\n"
                    )
                    error_count += 1

            QtWidgets.QMessageBox.information(
                self,
                "Proceso terminado",
                f"Envío completado.\n\nOK: {ok_count}\nErrores: {error_count}"
            )

        finally:
            self.launch_button.setEnabled(True)


#####################################################################################

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    w = ProductionLauncher()
    w.show()
    sys.exit(app.exec())