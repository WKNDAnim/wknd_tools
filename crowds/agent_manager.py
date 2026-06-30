# agent_manager.py

import maya.cmds as mc
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

        agent = Agent(self.next_id, locator_name, scene, default_state)
        self.agents.append(agent)
        self.next_id += 1

        print(f"Agent added: {agent}")
        return agent

    def remove_agent(self, agent_id):

        agent = next((a for a in self.agents if a.id == agent_id), None)
        if agent:
            agent.delete_locator()
        self.agents = [a for a in self.agents if a.id != agent_id]
        print(f"Agent {agent_id} removed.")

    def clear_agents(self):

        for agent in self.agents[:]:
            self.remove_agent(agent.id)
        self.next_id = 1

    def scan_scene(self):
        locators = mc.ls(type="locator")
        if not locators:
            return

        found = []
        for shape in locators:
            transform = mc.listRelatives(shape, parent=True)[0]
            if mc.objExists(transform + ".agent_id"):
                found.append((mc.getAttr(transform + ".agent_id"), transform))

        found.sort(key=lambda x: x[0])

        for _, transform in found:
            try:
                agent = Agent.load_from_locator(transform)
                self.agents.append(agent)
            except ValueError as e:
                print(f"Warning: {e}")

        if self.agents:
            self.next_id = max(a.id for a in self.agents) + 1
            print(f"Recovered {len(self.agents)} agents from scene.")
