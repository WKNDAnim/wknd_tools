import maya.cmds as mc
import math

    
def catmull_rom(p0, p1, p2, p3, t, tension=0.5):
    """Interpolacion suave entre p1 y p2 usando p0 y p3 como tangentes"""
    
    """
    tension = 0.0  → curvas muy pronunciadas
    tension = 0.5  → comportamiento normal (lo que tienes ahora)
    tension = 1.0  → casi líneas rectas
    """
    t2 = t * t
    t3 = t2 * t
    
    x = tension * ((2*p1[0]) +
                (-p0[0] + p2[0]) * t +
                (2*p0[0] - 5*p1[0] + 4*p2[0] - p3[0]) * t2 +
                (-p0[0] + 3*p1[0] - 3*p2[0] + p3[0]) * t3)
    
    z = tension * ((2*p1[2]) +
                (-p0[2] + p2[2]) * t +
                (2*p0[2] - 5*p1[2] + 4*p2[2] - p3[2]) * t2 +
                (-p0[2] + 3*p1[2] - 3*p2[2] + p3[2]) * t3)
    
    return [x, 0.0, z]

def smooth_path(positions, total_samples=100 , tension = 0.5):
    """
    En vez de samples fijos por segmento,
    distribuye los samples proporcional a la distancia
    """
    if len(positions) < 2:
        return positions
    
    pts = [positions[0]] + positions + [positions[-1]]
    
    # Calcula la distancia total de cada segmento
    segment_lengths = []
    for i in range(1, len(pts) - 2):
        dx = pts[i+1][0] - pts[i][0]
        dz = pts[i+1][2] - pts[i][2]
        segment_lengths.append(math.sqrt(dx**2 + dz**2))
    
    total_length = sum(segment_lengths)
    
    smoothed = []
    for i in range(1, len(pts) - 2):
        p0 = pts[i-1]
        p1 = pts[i]
        p2 = pts[i+1]
        p3 = pts[i+2]
        
        # Samples proporcionales a la longitud del segmento
        samples = max(2, int(total_samples * 
                             segment_lengths[i-1] / total_length))
        
        for j in range(samples):
            t = j / samples
            smoothed.append(catmull_rom(p0, p1, p2, p3, t, tension))
    
    smoothed.append(positions[-1])
    return smoothed


def string_pulling(path_positions, nav_graph):
    """
    Elimina waypoints intermedios innecesarios.
    Si hay linea de vision directa entre dos puntos, 
    elimina los puntos intermedios.
    """
    if len(path_positions) <= 2:
        return path_positions
    
    simplified = [path_positions[0]]
    current_idx = 0
    
    while current_idx < len(path_positions) - 1:
        # Intenta saltar al punto mas lejano posible en linea recta
        furthest = current_idx + 1
        
        for test_idx in range(current_idx + 2, len(path_positions)):
            if can_go_straight(path_positions[current_idx],
                               path_positions[test_idx],
                               nav_graph):
                furthest = test_idx
            else:
                break
        
        simplified.append(path_positions[furthest])
        current_idx = furthest
    
    return simplified

def can_go_straight(pos_a, pos_b, nav_graph, samples=5):
    """
    Comprueba si la linea recta entre dos puntos
    se mantiene dentro del navmesh
    """
    for i in range(1, samples):
        t = i / samples
        # Punto intermedio en la linea recta
        mid_x = pos_a[0] + (pos_b[0] - pos_a[0]) * t
        mid_z = pos_a[2] + (pos_b[2] - pos_a[2]) * t
        
        # Comprueba si ese punto esta dentro del navmesh
        nearest_face = find_nearest_face(nav_graph, [mid_x, 0, mid_z])
        nearest_center = nav_graph[nearest_face]['center']
        
        # Si el punto mas cercano del navmesh esta muy lejos
        # es que estamos fuera del navmesh
        dx = nearest_center[0] - mid_x
        dz = nearest_center[2] - mid_z
        dist = math.sqrt(dx**2 + dz**2)
        
        if dist > 10.0:  # threshold — ajusta según el tamaño de tus triángulos
            return False
    
    return True

def get_face_center(mesh, face_id):
    # Obtiene los vertices de la cara
    vert_info = mc.polyInfo(f'{mesh}.f[{face_id}]', faceToVertex=True)[0]
    # El resultado es algo como "FACE      0:    0    1    2    3"
    vert_ids = [int(v) for v in vert_info.split(':')[1].split()]
    
    # Calcula el centro promediando las posiciones de los vertices
    positions = []
    for vid in vert_ids:
        pos = mc.pointPosition(f'{mesh}.vtx[{vid}]', world=True)
        positions.append(pos)
    
    center_x = sum(p[0] for p in positions) / len(positions)
    center_y = sum(p[1] for p in positions) / len(positions)
    center_z = sum(p[2] for p in positions) / len(positions)
    
    return [center_x, center_y, center_z]

def get_adjacent_faces(mesh, face_id):
    # Obtiene las aristas de la cara
    edge_info = mc.polyInfo(f'{mesh}.f[{face_id}]', faceToEdge=True)[0]
    edge_ids = [int(e) for e in edge_info.split(':')[1].split()]
    
    adjacent = []
    for edge_id in edge_ids:
        # Para cada arista, busca las caras que la comparten
        face_info = mc.polyInfo(f'{mesh}.e[{edge_id}]', edgeToFace=True)[0]
        face_ids = [int(f) for f in face_info.split(':')[1].split()]
        
        for fid in face_ids:
            if fid != face_id:  # no añadir la cara actual
                adjacent.append(fid)
    
    return adjacent
    
def build_nav_graph(mesh):
    nav_graph = {}
    face_count = mc.polyEvaluate(mesh, face=True)
    
    print(f"Construyendo grafo de {face_count} caras...")
    
    for face_id in range(face_count):
        center = get_face_center(mesh, face_id)
        neighbors = get_adjacent_faces(mesh, face_id)
        nav_graph[face_id] = {
            'center': center,
            'neighbors': neighbors
        }
    
    print(f"Grafo construido con {len(nav_graph)} nodos")
    return nav_graph
    
def heuristic(pos_a, pos_b):
    # Distancia directa entre dos centros de cara
    dx = pos_a[0] - pos_b[0]
    dz = pos_a[2] - pos_b[2]
    return math.sqrt(dx**2 + dz**2)

def find_nearest_face(nav_graph, world_pos):
    # Encuentra la cara mas cercana a una posicion world space
    nearest_id = None
    nearest_dist = float('inf')
    
    for face_id, node in nav_graph.items():
        dist = heuristic(node['center'], world_pos)
        if dist < nearest_dist:
            nearest_dist = dist
            nearest_id = face_id
    
    return nearest_id

def astar(nav_graph, start_face, goal_face):
    open_list = [start_face]
    came_from = {}
    g_cost = {start_face: 0.0}
    
    while open_list:
        # Nodo con menor coste total f = g + h
        current = min(open_list, key=lambda n: 
                      g_cost[n] + heuristic(
                          nav_graph[n]['center'],
                          nav_graph[goal_face]['center']
                      ))
        
        if current == goal_face:
            # Reconstruye el path como lista de posiciones
            path = []
            while current in came_from:
                path.append(nav_graph[current]['center'])
                current = came_from[current]
            path.reverse()
            return path
        
        open_list.remove(current)
        
        for neighbor_id in nav_graph[current]['neighbors']:
            new_g = g_cost[current] + heuristic(
                nav_graph[current]['center'],
                nav_graph[neighbor_id]['center']
            )
            if new_g < g_cost.get(neighbor_id, float('inf')):
                came_from[neighbor_id] = current
                g_cost[neighbor_id] = new_g
                if neighbor_id not in open_list:
                    open_list.append(neighbor_id)
    
    return None  # no hay camino
    
import random

def get_random_point_on_navmesh(nav_graph, mesh_name, rng=None):
    """
    Devuelve una posicion random dentro del navmesh.
    rng es opcional — si pasas un random.Random(seed) 
    el resultado es reproducible
    """
    if rng is None:
        rng = random
    
    # Elige una cara random
    face_id = rng.choice(list(nav_graph.keys()))
    
    # Obtiene los vertices de esa cara
    vert_info = mc.polyInfo(f'{mesh_name}.f[{face_id}]', 
                            faceToVertex=True)[0]
    vert_ids = [int(v) for v in vert_info.split(':')[1].split()]
    
    positions = []
    for vid in vert_ids:
        pos = mc.pointPosition(f'{mesh_name}.vtx[{vid}]', world=True)
        positions.append(pos)
    
    # Punto random dentro del poligono
    # usando interpolacion random entre los vertices
    if len(positions) == 3:
        # Triangulo — formula exacta
        r1 = math.sqrt(rng.random())
        r2 = rng.random()
        x = (1 - r1) * positions[0][0] + \
             r1 * (1 - r2) * positions[1][0] + \
             r1 * r2 * positions[2][0]
        z = (1 - r1) * positions[0][2] + \
             r1 * (1 - r2) * positions[1][2] + \
             r1 * r2 * positions[2][2]
    else:
        # Quad o poligono — promedio ponderado random
        weights = [rng.random() for _ in positions]
        total = sum(weights)
        weights = [w/total for w in weights]
        x = sum(w * p[0] for w, p in zip(weights, positions))
        z = sum(w * p[2] for w, p in zip(weights, positions))
    
    return [x, 0.0, z]
    
    
class WaypointPath:
    def __init__(self, positions):
        self.waypoints = list(positions)
        self._current_index = 0
    
    def get_next(self):
        if self.waypoints:
            return self.waypoints[0]
        return None
    
    def advance(self):
        if self.waypoints:
            self.waypoints.pop(0)
    
    def is_complete(self):
        return len(self.waypoints) == 0
    
class Agent:
    def __init__(self, locator_name, speed=1.0):
        self.locator = locator_name
        self.speed = speed
        self.max_speed = self.speed  # guarda la velocidad maxima
        self.current_speed = 0.0     # empieza parado
        self.walk_weight = 0.0       # weight actual de la layer
        self.path = None
        self.ry = 0.0
        self.acceptance_radius = 5.0
        self.prev_pos = None
        
        self.anim_layer = locator_name.split(':')[0] + ':Walk'
        
        pos = mc.xform(locator_name, q=True, worldSpace=True, translation=True)
        self.current_pos = [pos[0], pos[1], pos[2]]
    
    def update(self, frame):
        if self.path and not self.path.is_complete():
            self._walk(frame)
        else:
            self.current_speed = self._lerp(self.current_speed, 0.0, 0.5)
            self.walk_weight = self.current_speed / self.max_speed
            self._write_keyframe(frame)
    
    def _walk(self, frame):
        
        target_pos = self.path.get_next()
        
        dx = target_pos[0] - self.current_pos[0]
        dz = target_pos[2] - self.current_pos[2]
        magnitude = math.sqrt(dx**2 + dz**2)
        
        # Acelera hacia max_speed
        self.current_speed = self._lerp(self.current_speed, self.max_speed, 0.05)
        
        # Mueve una distancia fija — self.speed unidades por frame
        if magnitude > 0.001:
            self.current_pos[0] += (dx/magnitude) * self.current_speed
            self.current_pos[2] += (dz/magnitude) * self.current_speed
        
        # Avanza TODOS los waypoints que hayan quedado por detras
        # no solo el primero
        while not self.path.is_complete():
            next_pos = self.path.get_next()
            dx = next_pos[0] - self.current_pos[0]
            dz = next_pos[2] - self.current_pos[2]
            dist = math.sqrt(dx**2 + dz**2)
            
            if dist < self.acceptance_radius:
                self.path.advance()  # este waypoint ya ha quedado atras
            else:
                break  # el siguiente waypoint aun esta por delante
                
        
        # Rotacion basada en velocidad
        if self.prev_pos is not None:
            vel_x = self.current_pos[0] - self.prev_pos[0]
            vel_z = self.current_pos[2] - self.prev_pos[2]
            vel_mag = math.sqrt(vel_x**2 + vel_z**2)
            if vel_mag > 0.001:
                target_ry = math.degrees(math.atan2(vel_x, vel_z))
                self.ry = self._lerp_angle(self.ry, target_ry, 0.35)
                
        self.walk_weight = self.current_speed / self.max_speed
        
        self.prev_pos = self.current_pos[:]
        self._write_keyframe(frame)
    
    def _write_keyframe(self, frame):
        mc.xform(self.locator, t=self.current_pos, ws=True)
        mc.xform(self.locator, ro=[0, self.ry, 0], ws=True)
        mc.setKeyframe(self.locator + '.t', time=frame)
        mc.setKeyframe(self.locator + '.r', time=frame)
        
        if self.anim_layer:
            mc.setAttr(self.anim_layer + '.weight', self.walk_weight)
            mc.setKeyframe(self.anim_layer, attribute='weight', time=frame)
            
    
    def _lerp_angle(self, a, b, t):
        diff = (b - a + 180) % 360 - 180
        return a + diff * t
        

    def _lerp(self, a, b, t):
        return a + (b - a) * t

"""
def on_reached(agent):
    new_target = get_random_point_on_navmesh(nav_graph, 'navMesh')
    start_face = find_nearest_face(nav_graph, agent.current_pos)
    goal_face = find_nearest_face(nav_graph, new_target)
    path_pos = astar(nav_graph, start_face, goal_face)
    path_pos = string_pulling(path_pos, nav_graph)
    path_pos = smooth_path(path_pos, total_samples=150, tension=0.3)
    agent.path = WaypointPath(path_pos)
    #agent.set_state('walk')
"""




# Setup y bake
frame_in = 1
frame_out = 300

#all_characters = mc.ls('pCube*', type = 'transform')
#print (all_characters)

all_characters = ['crowdAssetToTest:TransformGrp' , 'crowdAssetToTest1:TransformGrp' , 'crowdAssetToTest2:TransformGrp' , 'crowdAssetToTest3:TransformGrp' , 'crowdAssetToTest4:TransformGrp']


all_agents = []

nav_graph = build_nav_graph('navMesh')

for char in all_characters:
    
    # Limpia keys
    mc.cutKey(char, clear=True, time=(frame_in, frame_out))

    # Crea el agente
    agent = Agent(char, speed=1)

    # Genera el path con A*
    #nav_graph = build_nav_graph('navMesh')
    cube_pos = mc.xform(char, q=True, worldSpace=True, translation=True)
    #target_pos = mc.xform('locator1', q=True, worldSpace=True, translation=True)
    target_pos = get_random_point_on_navmesh(nav_graph, 'navMesh')
    start_face = find_nearest_face(nav_graph, cube_pos)
    goal_face = find_nearest_face(nav_graph, target_pos)
    path_positions = astar(nav_graph, start_face, goal_face)
    path_positions = string_pulling(path_positions, nav_graph) # Simplifica eliminadno waypoints
    path_positions = smooth_path(path_positions, total_samples=150 , tension = 0.5) # suaviza usando curvas catmull
    
    # Asigna el path al agente
    agent.path = WaypointPath(path_positions)
    #agent.on_target_reached = on_reached
    
    all_agents.append(agent)

# Bake
mc.refresh(suspend=True)
try:
    for frame in range(frame_in, frame_out + 1):
        mc.currentTime(frame)
        for agent in all_agents:
            agent.update(frame)
finally:
    mc.refresh(suspend=False)

print("Bake completado!")


