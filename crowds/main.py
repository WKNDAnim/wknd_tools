import importlib
import wknd_tools.crowds.constants as constants
import wknd_tools.crowds.agent as agent
import wknd_tools.crowds.agent_manager as agent_manager
import wknd_tools.crowds.blocks as blocks
import wknd_tools.crowds.block_manager as block_manager
import wknd_tools.crowds.ui.manager_ui as manager_ui


importlib.reload(constants)
importlib.reload(agent)
importlib.reload(agent_manager)
importlib.reload(blocks)
importlib.reload(block_manager)
importlib.reload(manager_ui)

from wknd_tools.crowds.agent_manager import AgentManager
from wknd_tools.crowds.ui.manager_ui import ManagerUI


def exec():
    manager = AgentManager()
    manager.scan_scene()
    ui = ManagerUI(manager)
    ui.show()
