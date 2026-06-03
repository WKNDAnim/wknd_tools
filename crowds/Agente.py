import maya.cmds as mc
import math


class Agent:

    def __init__(self, agent_id, locator_name, speed=0.2, move_ranges=None, forward_axis="+Z"):

        self.id = agent_id  # ID
        self.locator = locator_name  # Name of the Transform object in Maya
        self.move_ranges = move_ranges or []
        self.speed = speed  # Velocidad
        self.forward_axis = forward_axis  # Dirección frontal
        self.ry = 0  # Rotación en el eje Y
        self.target = None  # Punto de destino
        self.path = None
        self.prev_pos = None
        self.waypoints = []
        self.waypoint_index = 0

        # Get initial position
        pos = mc.xform(locator_name, q=True, worldSpace=True, translation=True)
        self.current_pos = [pos[0], pos[1], pos[2]]
        self.start_position = self.current_pos[:]  # esto es una copia real con [:]

    def setTarget(self, target):
        self.target = target

    def reset_to_start(self, frame_in, frame_out):
        """  Initial cleanup para borrar keys y mantener la posicion inicial """
        mc.currentTime(frame_in)
        mc.cutKey(self.locator, clear=True, time=(frame_in, frame_out))
        mc.xform(self.locator, translation=self.start_position, ws=True)

    def set_path(self, waypoints):
        """Recibe la lista de posiciones devuelta por find_path."""
        self.path = waypoints
        self.waypoint_index = 0

    def set_move_range(self, range):

        self.move_ranges.append(range)

    def get_current_target(self):
        if self.waypoint_index < len(self.waypoints):
            return self.waypoints[self.waypoint_index]
        return None

    def has_reached(self, target_pos, threshold=0.1):
        """Calculamos la direccion"""
        dx = target_pos[0] - self.current_pos[0]
        dy = target_pos[1] - self.current_pos[1]
        dz = target_pos[2] - self.current_pos[2]
        dist = (dx**2 + dy**2 + dz**2) ** 0.5
        return dist < threshold

    def __calculate_direction(self, target_pos):
        """Calculamos la dirección"""
        dx = target_pos[0] - self.current_pos[0]
        dy = target_pos[1] - self.current_pos[1]
        dz = target_pos[2] - self.current_pos[2]

        return dx, dy, dz

    def __calculate_rotation_y(self, target_pos):
        """Calculamos la rotación"""
        dx = target_pos[0] - self.current_pos[0]
        dz = target_pos[2] - self.current_pos[2]
        angle = math.degrees(math.atan2(dx, dz))

        offsets = {"+Z": 0, "-Z": 180, "+X": -90, "-X": 90}
        return angle + offsets.get(self.forward_axis, 0)

    def calculate_speed(self, duration):
        """
        Calcula la speed necesaria para recorrer el camino en exactamente 'duration' frames.
        """
        # Distancia total del camino
        total_dist = 0
        for i in range(len(self.path) - 1):
            dx = self.path[i+1][0] - self.path[i][0]
            dz = self.path[i+1][2] - self.path[i][2]
            total_dist += (dx**2 + dz**2) ** 0.5

        return total_dist / duration

    def move(self, target_pos):

        dx, dy, dz = self.__calculate_direction(target_pos)
        target_ry= self.__calculate_rotation_y(target_pos)
        self.smooth_rotation(target_ry, factor=0.2)

        # Guardamos la posición anterior
        self.prev_pos = self.current_pos

        # Calculamos la nueva posición
        self.current_pos[0] = self.current_pos[0] + dx * self.speed
        self.current_pos[1] = self.current_pos[1] + dy * self.speed
        self.current_pos[2] = self.current_pos[2] + dz * self.speed

    def _set_key(self, frame):
        # Seteamos la nueva posición
        mc.xform(self.locator, t=self.current_pos, ws=True)
        mc.setKeyframe(self.locator + '.t', time=frame) 

    def _write_keyframe(self, frame, height):

        if height is not None:
            self.current_pos[1] = height

        mc.xform(self.locator, t = self.current_pos, ws=True)
        mc.xform(self.locator, ro = [0,self.ry,0] , ws=True)
        mc.setKeyframe(self.locator + '.t' , time=frame)
        mc.setKeyframe(self.locator + '.r' , time=frame)

    def smooth_rotation(self, target_ry, factor=0.1):
        """
        Interpola suavemente la rotación actual hacia target_ry.
        factor -- 0.0 = no gira nunca, 1.0 = gira instantáneo
        """
        # Calculamos la diferencia más corta entre los dos ángulos
        diff = (target_ry - self.ry + 180) % 360 - 180
        self.ry += diff * factor

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

