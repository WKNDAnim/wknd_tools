import maya.cmds as mc

# Lista de escenas disponibles para los agentes
AGENT_SCENES = {
    "Hombre01": r"Z:\02Proyectos\Gus\assets\CHE\hombre01\RIG\RigAnimation\publish\maya\hombre01_scene_RigAnimation_v006.ma",
    "Mujer01": r"Z:\02Proyectos\Gus\assets\CHE\mujer01\RIG\RigAnimation\publish\maya\mujer01_scene_RigAnimation_v003.ma",
    "Mujer02": r"Z:\02Proyectos\Gus\assets\CHE\mujer02\RIG\RigAnimation\publish\maya\mujer02_scene_RigAnimation_v005.ma",
}

AGENT_STATES = ["idle", "walking", "sitting", "custom"]

class Agent:
    def __init__(self, agent_id, locator_name, scene):
        self.id        = agent_id
        self.locator   = locator_name
        self.scene     = scene
        self.state     = "idle"

    def __repr__(self):
        return f"Agent({self.id} | {self.locator} | {self.scene})"


class AgentManager:
    def __init__(self):
        self.agents  = []
        self.next_id = 1
        self.window  = "AgentManagerWin"
        self.build_ui()

    # -------------------------
    # UI
    # -------------------------
    def build_ui(self):
        if mc.window(self.window, exists=True):
            mc.deleteUI(self.window)

        mc.window(self.window, title="Agent Manager", widthHeight=(400, 500), sizeable=True)
        
        main_col = mc.columnLayout(adjustableColumn=True, rowSpacing=5)

        # -- Header
        mc.text(label="AGENT MANAGER", height=30, backgroundColor=[0.2, 0.2, 0.2])
        mc.separator(height=10)

        # -- Formulario nuevo agente
        mc.frameLayout(label="New Agent", collapsable=True, marginHeight=8, marginWidth=8)
        
        mc.rowColumnLayout(numberOfColumns=2, columnWidth=[(1,120),(2,240)])
        
        mc.text(label="Locator name:")
        self.field_locator = mc.textField(placeholderText="Ej: Manolo")
        
        mc.text(label="Scene:")
        self.field_scene = mc.optionMenu()
        for name in AGENT_SCENES.keys():
            mc.menuItem(label=name)

        mc.setParent("..")  # salimos del rowColumnLayout
        
        mc.separator(height=8)
        mc.button(label="Add Agent", height=35, 
                  backgroundColor=[0.2, 0.5, 0.2],
                  command=lambda x: self.add_agent())

        mc.setParent("..")  # salimos del frameLayout

        mc.separator(height=10)

        # -- Lista de agentes
        mc.frameLayout(label="Agents", collapsable=False, marginHeight=8, marginWidth=8)

        self.agents_col = mc.columnLayout(adjustableColumn=True, rowSpacing=4)

        mc.setParent("..")
        mc.setParent("..")

        mc.separator(height=10)

        # -- Botón limpiar
        mc.button(label="Clear All Agents", height=30,
                  backgroundColor=[0.5, 0.2, 0.2],
                  command=lambda x: self.clear_agents(),
                  parent=main_col)

        self._scan_scene()
        self._refresh_agent_list()

        mc.showWindow(self.window)

    def _refresh_agent_list(self):
        children = mc.columnLayout(self.agents_col, q=True, childArray=True)
        if children:
            for child in children:
                mc.deleteUI(child)

        if not self.agents:
            mc.text(label="No agents yet.", parent=self.agents_col)
            return

        for agent in self.agents:
            row = mc.rowLayout(numberOfColumns=6,
                            columnWidth6=[30, 100, 160, 60, 50, 50],
                            parent=self.agents_col)
            mc.text(label=f"#{agent.id}")
            mc.text(label=agent.locator)

            menu = mc.optionMenu(changeCommand=lambda val, a=agent: self._change_scene(a, val))
            for name in AGENT_SCENES.keys():
                mc.menuItem(label=name)
            current_name = next(k for k, v in AGENT_SCENES.items() if v == agent.scene)
            mc.optionMenu(menu, e=True, value=current_name)

            # Estado actual -- solo lectura en la lista
            mc.text(label=agent.state, backgroundColor=[0.2, 0.2, 0.3])

            mc.button(label="Edit",
                    backgroundColor=[0.2, 0.3, 0.5],
                    command=lambda x, a=agent: self.open_detail(a))
            mc.button(label="X",
                    backgroundColor=[0.6, 0.2, 0.2],
                    command=lambda x, aid=agent.id: self.remove_agent(aid))
            mc.setParent("..")

    def open_detail(self, agent):
        win_name = f"AgentDetail_{agent.id}"

        if mc.window(win_name, exists=True):
            mc.deleteUI(win_name)

        mc.window(win_name, title=f"Agent {agent.id} — {agent.locator}",
                  widthHeight=(300, 200), sizeable=False)

        mc.columnLayout(adjustableColumn=True, rowSpacing=8)

        # mc.columnLayout(adjustableColumn=True, rowSpacing=8, marginHeight=10, marginWidth=10)

        mc.text(label=f"Agent #{agent.id}  |  {agent.locator}", 
                backgroundColor=[0.2, 0.2, 0.2], height=25)
        mc.separator(height=10)

        mc.rowLayout(numberOfColumns=2, columnWidth2=[100, 170])
        mc.text(label="State:")
        state_menu = mc.optionMenu(
            changeCommand=lambda val, a=agent: self._change_state(a, val)
        )
        for state in AGENT_STATES:
            mc.menuItem(label=state)
        mc.optionMenu(state_menu, e=True, value=agent.state)
        mc.setParent("..")

        mc.separator(height=10)
        mc.button(label="Close", height=30,
                command=lambda x: mc.deleteUI(win_name))

        mc.showWindow(win_name)

    def _change_state(self, agent, state):
        agent.state = state
        if mc.objExists(agent.locator + ".agent_state"):
            mc.setAttr(agent.locator + ".agent_state", state, type="string")
        self._refresh_agent_list()  # actualizamos el texto de estado en la lista
        print(f"Agent {agent.id} state changed to: {state}")

    # -------------------------
    # Lógica
    # -------------------------

    def add_agent(self):
        locator_name = mc.textField(self.field_locator, q=True, text=True).strip()
        scene = scene = AGENT_SCENES[mc.optionMenu(self.field_scene, q=True, value=True)]

        if not locator_name:
            mc.confirmDialog(title="Error", message="Introduce un nombre de locator.", button=["OK"])
            return
        if any(a.locator == locator_name for a in self.agents):
            mc.confirmDialog(title="Error", message=f"'{locator_name}' ya tiene un agente asignado.", button=["OK"])
            return

        locator = mc.spaceLocator(name=locator_name)[0]
        mc.xform(locator, t=[0, 0, 0], ws=True)

        # Guardamos los datos del agente como atributos custom en el locator
        mc.addAttr(locator, longName="agent_id", attributeType="long", keyable=False)
        mc.addAttr(locator, longName="agent_scene", dataType="string", keyable=False)
        mc.addAttr(locator, longName="agent_state", dataType="string", keyable=False)

        mc.setAttr(locator + ".agent_id",    self.next_id)
        mc.setAttr(locator + ".agent_scene", scene, type="string")
        mc.setAttr(locator + ".agent_state", "idle", type="string")

        # Creamos la instancia
        agent = Agent(self.next_id, locator_name, scene)
        self.agents.append(agent)
        self.next_id += 1

        mc.textField(self.field_locator, e=True, text="")
        self._refresh_agent_list()
        print(f"Agent added: {agent}")

    def remove_agent(self, agent_id):
        agent = next((a for a in self.agents if a.id == agent_id), None)
        if agent and mc.objExists(agent.locator):
            mc.delete(agent.locator)
        self.agents = [a for a in self.agents if a.id != agent_id]
        self._refresh_agent_list()
        print(f"Agent {agent_id} removed.")

    def clear_agents(self):
        for agent in self.agents[:]:  # [:] itera sobre una copia
            self.remove_agent(agent.id)
        self.next_id = 1

    def _change_scene(self, agent, name):
        scene = AGENT_SCENES[name]
        agent.scene = scene
        if mc.objExists(agent.locator + ".agent_scene"):
            mc.setAttr(agent.locator + ".agent_scene", scene, type="string")
        print(f"Agent {agent.id} scene changed to: {scene}")

    def _scan_scene(self):
        """Busca locators con atributos de agente en la escena y los recupera."""
        locators = mc.ls(type="locator")
        if not locators:
            return

        found = []
        for shape in locators:
            # El atributo está en el transform, no en el shape
            transform = mc.listRelatives(shape, parent=True)[0]
            if mc.objExists(transform + ".agent_id"):
                agent_id    = mc.getAttr(transform + ".agent_id")
                agent_scene = mc.getAttr(transform + ".agent_scene")
                agent_state = mc.getAttr(transform + ".agent_state")
                found.append((agent_id, transform, agent_scene, agent_state))

        # Ordenamos por id para mantener el orden original
        found.sort(key=lambda x: x[0])

        for agent_id, locator_name, scene, state in found:
            agent = Agent(agent_id, locator_name, scene)
            agent.state = state
            self.agents.append(agent)

        if self.agents:
            self.next_id = max(a.id for a in self.agents) + 1
            print(f"Recovered {len(self.agents)} agents from scene.")


# # Lanzar
# manager = AgentManager()