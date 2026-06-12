import maya.cmds as mc
import json

from . import agent
from .block_manager import BlockManager

import importlib
importlib.reload(agent)

from .agent import Agent


class AgentManager:

    def __init__(self):

        self.agents = []
        self.next_id = 1

    def add_agent(self, locator_name, scene, default_state="idle"):

        if not locator_name:
            raise ValueError("Introduce un nombre de locator.")
        if any(a.locator == locator_name for a in self.agents):
            raise ValueError(f"'{locator_name}' ya tiene un agente asignado.")

        locator = mc.spaceLocator(name=locator_name)[0]
        mc.xform(locator, t=[0, 0, 0], ws=True)

        # Creamos el BlockManager con el bloque por defecto
        frame_start = int(mc.playbackOptions(q=True, min=True))
        frame_end   = int(mc.playbackOptions(q=True, max=True))
        bm = BlockManager(frame_start, frame_end)
        bm.initialize(default_state)
        blocks_data = bm.serialize()

        mc.addAttr(locator, longName="agent_id",     attributeType="long",  keyable=False)
        mc.addAttr(locator, longName="agent_scene",  dataType="string",     keyable=False)
        mc.addAttr(locator, longName="agent_state",  dataType="string",     keyable=False)
        mc.addAttr(locator, longName="agent_blocks", dataType="string",     keyable=False)

        mc.setAttr(locator + ".agent_id",     self.next_id)
        mc.setAttr(locator + ".agent_scene",  scene,                    type="string")
        mc.setAttr(locator + ".agent_state",  default_state,            type="string")
        mc.setAttr(locator + ".agent_blocks", json.dumps(blocks_data),  type="string")

        from .agent import Agent
        agent        = Agent(self.next_id, locator_name, scene)
        agent.state  = default_state
        agent.blocks = blocks_data
        self.agents.append(agent)
        self.next_id += 1

        print(f"Agent added: {agent}")
        return agent

    def remove_agent(self, agent_id):
        agent = next((a for a in self.agents if a.id == agent_id), None)
        if agent and mc.objExists(agent.locator):
            mc.delete(agent.locator)
        self.agents = [a for a in self.agents if a.id != agent_id]
        print(f"Agent {agent_id} removed.")

    def clear_agents(self):
        for agent in self.agents[:]:
            self.remove_agent(agent.id)
        self.next_id = 1

    def change_scene(self, agent, scene):
        agent.scene = scene
        if mc.objExists(agent.locator + ".agent_scene"):
            mc.setAttr(agent.locator + ".agent_scene", scene, type="string")
        print(f"Agent {agent.id} scene changed to: {scene}")

    def change_state(self, agent, state):
        agent.state = state
        if mc.objExists(agent.locator + ".agent_state"):
            mc.setAttr(agent.locator + ".agent_state", state, type="string")
        print(f"Agent {agent.id} state changed to: {state}")

    def scan_scene(self):
        """Recupera agentes existentes en la escena."""
        locators = mc.ls(type="locator")
        if not locators:
            return

        found = []
        for shape in locators:
            transform = mc.listRelatives(shape, parent=True)[0]
            if mc.objExists(transform + ".agent_id"):
                found.append((
                    mc.getAttr(transform + ".agent_id"),
                    transform,
                    mc.getAttr(transform + ".agent_scene"),
                    mc.getAttr(transform + ".agent_state"),
                    mc.getAttr(transform + ".agent_blocks")
                ))

        found.sort(key=lambda x: x[0])

        for agent_id, locator_name, scene, state, blocks_json in found:
            agent = Agent(agent_id, locator_name, scene)
            agent.state = state
            agent.blocks = json.loads(blocks_json)
            self.agents.append(agent)

        if self.agents:
            self.next_id = max(a.id for a in self.agents) + 1
            print(f"Recovered {len(self.agents)} agents from scene.")

    def save_blocks(self, agent, blocks_data):
        import json
        agent.blocks = blocks_data
        if mc.objExists(agent.locator + ".agent_blocks"):
            mc.setAttr(agent.locator + ".agent_blocks", json.dumps(blocks_data), type="string")
