import maya.cmds as mc
import math


class Agent:

    def __init__(self, agent_id, locator_name, speed=0.2, forward_axis="+Z"):
        self.id = agent_id
        self.locator = locator_name
        self.speed = speed
        self.forward_axis = forward_axis
        self.ry = 0
        self.target = None
        self.camino = None
        self.prev_pos = None
        self.waypoints = [] 
        self.waypoint_index = 0
        # Get initial position
        pos = mc.xform(locator_name, q=True, worldSpace=True, translation=True)
        self.current_pos = [pos[0], pos[1], pos[2]]
        self.start_position = self.current_pos[:] # esto es una copia real con [:]

    def reset_to_start(self, frame_in, frame_out):
        # Initial cleanup para borrar keys y mantener la posicion inicial
        mc.currentTime(frame_in)
        mc.cutKey(self.locator, clear=True, time=(frame_in, frame_out))
        mc.xform(self.locator, translation=self.start_position, ws=True)

    def set_path(self, waypoints):
        """Recibe la lista de posiciones devuelta por find_path."""
        self.camino = waypoints
        self.waypoint_index = 0

    def get_current_target(self):
        if self.waypoint_index < len(self.waypoints):
            return self.waypoints[self.waypoint_index]
        return None

    def has_reached(self, target_pos, threshold=0.1):
        dx = target_pos[0] - self.current_pos[0]
        dy = target_pos[1] - self.current_pos[1]
        dz = target_pos[2] - self.current_pos[2]
        dist = (dx**2 + dy**2 + dz**2) ** 0.5
        return dist < threshold

    def __calculate_direction(self, target_pos):
        # Calculamos la direccion
        dx = target_pos[0] - self.current_pos[0]
        dy = target_pos[1] - self.current_pos[1]
        dz = target_pos[2] - self.current_pos[2]

        return dx,dy,dz

    def get_rotation_y(self, target_pos):
        dx = target_pos[0] - self.current_pos[0]
        dz = target_pos[2] - self.current_pos[2]
        angle = math.degrees(math.atan2(dx, dz))

        offsets = {"+Z": 0, "-Z": 180, "+X": -90, "-X": 90}
        return angle + offsets.get(self.forward_axis, 0)

    def move(self, target_pos):
        dx,dy,dz = self.__calculate_direction(target_pos)

        self.ry = self.get_rotation_y(target_pos)

        # Guardamos la posición anterior
        self.prev_pos = self.current_pos

        # Calculamos la nueva posición
        self.current_pos[0] = self.current_pos[0] + dx * self.speed
        self.current_pos[1] = self.current_pos[1] + dy * self.speed
        self.current_pos[2] = self.current_pos[2] + dz * self.speed

    def _set_key(self, frame):
        # Seteamos la nueva posición
        mc.xform(self.locator, t = self.current_pos, ws=True)
        mc.setKeyframe(self.locator + '.t' , time=frame) 

    def _write_keyframe(self, frame, height):

        if height is not None:
            self.current_pos[1] = height

        mc.xform(self.locator, t = self.current_pos, ws=True)
        mc.xform(self.locator, ro = [0,self.ry,0] , ws=True)
        mc.setKeyframe(self.locator + '.t' , time=frame)
        mc.setKeyframe(self.locator + '.r' , time=frame)


# #############################

# frame_in = 1001
# frame_out = 1050
        
# locator_name = "Manolo"
# agent_id = 1
# manolo = Agent(agent_id, locator_name)

# time = list(range(frame_in,frame_out))

# target = "t4"
# target_pos = mc.xform(target, q=True, worldSpace=True, translation=True)

# t = 1001

# recorrido = {}

# for frame in time:
#     if manolo.current_pos != target_pos:
#         manolo.move(target_pos)
#         manolo._write_keyframe(frame, height=None)
        
#         recorrido[frame] = manolo.current_pos

# import pprint    
# pprint.pprint(recorrido)

# # manolo.reset_to_start(frame_in,frame_out)

