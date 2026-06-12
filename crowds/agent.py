class Agent:
    def __init__(self, agent_id, locator_name, scene):
        self.id      = agent_id
        self.locator = locator_name
        self.scene   = scene
        self.state   = "idle"
        self.blocks  = []  # lista de StateBlock y TransitionBlock

    def __repr__(self):
        return f"Agent({self.id} | {self.locator} | {self.scene})"
