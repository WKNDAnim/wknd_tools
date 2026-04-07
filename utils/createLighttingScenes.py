import sys
sys.path.insert(0, r"Z:\05Framework\users\aferraz\packages\dev_tk\master_tk_config\install\core\python")
sys.path.insert(0, r"Z:\05Framework\users\aferraz")

import sgtk
import os

import wknd_tools
from wknd_tools.flay import sendFLayRender
import importlib
importlib.reload(sendFLayRender)

DEADLINECOMMAND = r"C:\Program Files\Thinkbox\Deadline10\bin\deadlinecommand.exe"

#######################
# Conectar a ShotGrid #
#######################

tk = sgtk.sgtk_from_path(r"Z:\05Framework\users\aferraz\packages\dev_tk\master_tk_config")
sg = tk.shotgun

#################################


def main():

    sequences = ["sq0240", "sq0260", "sq0270"]

    print("="*70)
    print(f"Sequences: {sequences}")
    print("="*70)

    for seq_name in sequences:

        print("="*40)
        print(f"- Searching shots in seq: {seq_name}")
        print("="*40)

        shots = _search_shots_in_seq(seq_name)

        print(f"** {len(shots)} shots found!")

        for shot in shots:

            print(f"\t - SHOT: {shot}")

            sendFLayRender._create_scenes(shot, create_flay=False)


def _search_shots_in_seq(seq_name):
    """ Dado el nombre de una secuencia, buscamos en SG sus shots que no estén omitidos """

    filters = [
        ["project", "is", {"type": "Project", "id": 91}],
        ["sg_sequence.Sequence.code", "is", seq_name],
        ["code", "not_contains", "master"],
        ["sg_status_list", "is_not", "omt"]
    ]
    query = ["code", "sg_sequence", "sg_status_list", "sg_auto_flay"]

    return sg.find("Shot", filters, query)


if __name__ == "__main__":
    main()
