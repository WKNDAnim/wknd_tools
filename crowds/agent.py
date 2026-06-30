import maya.cmds as mc
import json
import math
from .block_manager import BlockManager
from . import constants


class Agent:

    def __init__(self, agent_id, locator_name, scene, default_state="idle"):

        self.id = agent_id
        self.locator = locator_name
        self.scene = scene
        self.state = default_state
        self.blocks = []

        # Creamos el BlockManager con el bloque por defecto
        frame_start = int(mc.playbackOptions(q=True, min=True))
        frame_end = int(mc.playbackOptions(q=True, max=True))
        bm = BlockManager(frame_start, frame_end)
        bm.initialize(default_state)
        self.blocks = bm.serialize()

        # Creamos el locator en Maya
        self._create_locator()

    @classmethod
    def load_from_locator(cls, transform_name):
        """Reconstruye un Agent desde un locator existente en Maya."""

        # Verificamos que tiene los atributos necesarios
        required_attrs = ["agent_id", "agent_scene", "agent_state", "agent_blocks"]
        for attr in required_attrs:
            if not mc.objExists(f"{transform_name}.{attr}"):
                raise ValueError(f"Locator '{transform_name}' no tiene el atributo '{attr}'. No es un agente válido.")

        agent_id = mc.getAttr(transform_name + ".agent_id")
        scene = mc.getAttr(transform_name + ".agent_scene")
        state = mc.getAttr(transform_name + ".agent_state")
        blocks_json = mc.getAttr(transform_name + ".agent_blocks")

        agent = object.__new__(cls)
        agent.id = agent_id
        agent.locator = transform_name
        agent.scene = scene
        agent.state = state
        agent.blocks = json.loads(blocks_json) if blocks_json else []

        return agent

    def _create_locator(self):
        """Crea el locator en Maya y guarda todos los datos como atributos."""

        # Creamos el grupo CROWDS si no existe
        if not mc.objExists(constants.CROWDS_GROUP):
            mc.group(empty=True, name=constants.CROWDS_GROUP)

        locator = mc.spaceLocator(name=self.locator)[0]
        mc.xform(locator, t=[0, 0, 0], ws=True)
        mc.parent(locator, constants.CROWDS_GROUP)

        mc.addAttr(locator, longName="agent_id", attributeType="long", keyable=False)
        mc.addAttr(locator, longName="agent_scene", dataType="string", keyable=False)
        mc.addAttr(locator, longName="agent_state", dataType="string", keyable=False)
        mc.addAttr(locator, longName="agent_blocks", dataType="string", keyable=False)

        self.save_to_locator()

    def save_to_locator(self):
        """Guarda todos los datos del agente en el locator de Maya."""

        if not mc.objExists(self.locator):
            return

        mc.setAttr(self.locator + ".agent_id", self.id)
        mc.setAttr(self.locator + ".agent_scene", self.scene, type="string")
        mc.setAttr(self.locator + ".agent_state", self.state, type="string")
        mc.setAttr(self.locator + ".agent_blocks", json.dumps(self.blocks), type="string")

    def save_blocks(self, blocks_data):
        """Actualiza los bloques del agente y los persiste."""

        self.blocks = blocks_data
        if mc.objExists(self.locator + ".agent_blocks"):
            mc.setAttr(self.locator + ".agent_blocks", json.dumps(blocks_data), type="string")

    def change_scene(self, scene):

        self.scene = scene
        if mc.objExists(self.locator + ".agent_scene"):
            mc.setAttr(self.locator + ".agent_scene", scene, type="string")

    def change_state(self, state):

        self.state = state
        if mc.objExists(self.locator + ".agent_state"):
            mc.setAttr(self.locator + ".agent_state", state, type="string")

    def delete_locator(self):

        self.unload_reference()
        if mc.objExists(self.locator):
            mc.delete(self.locator)

    def __repr__(self):

        return f"Agent({self.id} | {self.locator} | {self.scene})"

    def load_reference(self):
        """Carga la escena del agente como referencia en Maya."""

        if not self.scene:
            raise ValueError(f"Agent {self.id} no tiene escena asignada.")

        if self.is_referenced():
            print(f"Agent {self.id} ya tiene una referencia cargada.")
            return

        mc.file(self.scene, reference=True, namespace=self.namespace)

        self._constrain_ref_to_locator()

        print(f"Agent {self.id} reference loaded: {self.scene}")

    def unload_reference(self):
        """Descarga la referencia del agente."""

        if not self.is_referenced():
            return

        # Borramos el constraint antes de eliminar la referencia
        master_ctrl = f"{self.namespace}:{constants.MASTER_CTRL}"
        if mc.objExists(master_ctrl):
            constraints = mc.listRelatives(master_ctrl, type="parentConstraint")
            if constraints:
                mc.delete(constraints)

        refs = mc.ls(references=True)
        for ref in refs:
            if mc.referenceQuery(ref, namespace=True) == f":{self.namespace}":
                mc.file(mc.referenceQuery(ref, filename=True), removeReference=True)
                print(f"Agent {self.id} reference unloaded.")
                return

    def is_referenced(self):
        """Comprueba si la referencia ya está cargada."""

        if not hasattr(self, 'namespace') or not self.namespace:
            return False
        refs = mc.ls(references=True)
        for ref in refs:
            try:
                if mc.referenceQuery(ref, namespace=True) == f":{self.namespace}":
                    return True
            except:
                pass
        return False

    def _constrain_ref_to_locator(self):
        master_ctrl = f"{self.namespace}:{constants.MASTER_CTRL}"

        if not mc.objExists(master_ctrl):
            print(f"Warning: no se encontró {master_ctrl}")
            return

        # Creamos el grupo CROWDS_RIGS si no existe
        if not mc.objExists(constants.CROWDS_RIGS_GROUP):
            mc.group(empty=True, name=constants.CROWDS_RIGS_GROUP)

        # Buscamos el nodo raíz de la referencia
        ref_nodes  = mc.ls(f"{self.namespace}:*", type="transform")
        root_nodes = [n for n in ref_nodes if mc.listRelatives(n, parent=True) is None]

        for root in root_nodes:
            mc.parent(root, constants.CROWDS_RIGS_GROUP)

        # Creamos el constraint
        mc.parentConstraint(self.locator, master_ctrl, maintainOffset=False)
        print(f"parentConstraint: {self.locator} -> {master_ctrl}")

    @property
    def namespace(self):
        return f"{self.locator}_RN"
