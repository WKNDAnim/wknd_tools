import maya.cmds as mc
import math

class Agent:
    def __init__(self, agent_id, locator_name, speed = 0.2):
        self.id = agent_id
        self.locator = locator_name
        self.speed = speed
        self.state = 'idle'
        self.target = None
        self.ry = 0.0
        self.acceptance_radius = 10.0
        self.path = None
        self.avoidance_radius = 80.0
        self.avoidance_strength = 2.0
        self.prev_pos = None
        self.rotation_speed = 0.5
        self.wall_radius = 20.0
        self.wall_strength = 10.0
                
        
        
        # get initial position
        
        pos = mc.xform(locator_name, q=True, 
                         worldSpace=True, translation=True)
        self.current_pos = [pos[0], pos[1], pos[2]]
        self.start_position = self.current_pos[:] # esto es una copia real con [:]
        
    def reset_to_start(self, frame_in , frame_out):
        
        # Initial cleanup para borrar keys y mantener la posicion inicial
        
        mc.currentTime(frame_in)
        mc.cutKey(self.locator, clear=True, time=(frame_in, frame_out))
        mc.xform(self.locator, translation=self.start_position, ws=True)
        
    def update(self, frame, other_positions=None, walls=None, height=None):
        if self.state == 'walk':
            self.walk_to_target(frame, other_positions, walls, height)
        elif self.state == 'idle':
            self.idle(frame, height)
        elif self.state == 'action':
            self.action(frame)
            
    def set_state(self , new_state):
        self.state = new_state
        
    def idle(self,frame, height):
        self._write_keyframe(frame , height)
        
    def walk_to_target(self, frame, other_positions=None , walls=None, height=None):
        
        print(f"walls recibidas: {walls}")
        
        # Si tenemos path, el target es el siguiente waypoint
        # Si no, usamos self.target directamente (como antes)
        if self.path and not self.path.is_complete():
            current_target = self.path.get_next()
        elif self.target:
            current_target = self.target
        else:
            self.set_state('idle')
            return
        
        target_pos = mc.xform(current_target, q=True,
                              worldSpace=True, translation=True)
        
        dx = target_pos[0] - self.current_pos[0]
        dy = target_pos[1] - self.current_pos[1]
        dz = target_pos[2] - self.current_pos[2]
        
        magnitude = math.sqrt(dx**2 + dy**2 + dz**2)
        
        if magnitude > self.acceptance_radius:
            # Seek hacia target
            seek_x = (dx/magnitude) * self.speed
            seek_z = (dz/magnitude) * self.speed
            
            # Avoidance
            avoid_x, avoid_z = self._calculate_avoidance(other_positions)
            
            # Wall avoidance
            wall_x, wall_z = self._calculate_wall_avoidance(walls)
            print(f"seek: {seek_x:.4f}, {seek_z:.4f}")
            print(f"wall force: {wall_x:.4f}, {wall_z:.4f}")
            print(f"suma total z: {seek_z + avoid_z + wall_z:.4f}")
            

            
            # Suma de fuerzas
            self.current_pos[0] += seek_x + avoid_x + wall_x
            self.current_pos[1] += (dy/magnitude) * self.speed
            self.current_pos[2] += seek_z + avoid_z + wall_z
            
            if height is not None:
                self.current_pos[1] = height
            
            # Rotacion basada en el target
            #target_ry = math.degrees(math.atan2(dx, dz))
            #self.ry = self._lerp_angle(self.ry, target_ry, 0.1)
            
            #Rotacion basada en la propia velocidad
            if self.prev_pos is not None:
                vel_x = self.current_pos[0] - self.prev_pos[0]
                vel_z = self.current_pos[2] - self.prev_pos[2]
                vel_magnitude = math.sqrt(vel_x**2 + vel_z**2)
                
                if vel_magnitude > 0.001:  # solo rota si realmente se mueve
                    target_ry = math.degrees(math.atan2(vel_x, vel_z))
                    self.ry = self._lerp_angle(self.ry, target_ry, self.rotation_speed)
                    
                else:
                    # Rotacion basada en el target
                    target_ry = math.degrees(math.atan2(dx, dz))
                    self.ry = self._lerp_angle(self.ry, target_ry, self.rotation_speed)
                    
            
            
        
        else:
            # Ha llegado al waypoint actual
            if self.path and not self.path.is_complete():
                self.path.advance()  # pasa al siguiente waypoint
                
                if self.path.is_complete():
                    self.set_state('idle')  # ha llegado al final
            else:
                self.set_state('idle')
        
        self._write_keyframe(frame, height)
        self.prev_pos = self.current_pos[:]
            
    def _write_keyframe(self, frame, height):
        
        if height is not None:
            self.current_pos[1] = height
        
        mc.xform(self.locator, t = self.current_pos, ws=True)
        mc.xform(self.locator, ro = [0,self.ry,0] , ws=True)
        mc.setKeyframe(self.locator + '.t' , time=frame)
        mc.setKeyframe(self.locator + '.r' , time=frame)
        
    def _lerp_angle(self , a, b, t):
        # Calcula la diferencia más corta entre dos ángulos
        # Tiene como input solo floats, en este caso, la rotacion en Y
        diff = (b - a + 180) % 360 - 180
        return a + diff * t
        
    def _calculate_avoidance(self, other_positions):
        avoid_x, avoid_z = 0.0, 0.0
        
        if not other_positions:
            return avoid_x, avoid_z
        
        for other_id, other_pos in other_positions.items():
            dx = self.current_pos[0] - other_pos[0]
            dz = self.current_pos[2] - other_pos[2]
            dist = math.sqrt(dx**2 + dz**2)
            
            if dist < self.avoidance_radius and dist > 0.001:
                #strength = 1.0 - (dist / self.avoidance_radius)
                strength = (self.wall_radius / dist) ** 2
                avoid_x += (dx/dist) * strength * self.avoidance_strength
                avoid_z += (dz/dist) * strength * self.avoidance_strength
        
        return avoid_x, avoid_z
        
    def _calculate_wall_avoidance(self, walls):
        avoid_x, avoid_z = 0.0, 0.0
        
        if not walls:
            return avoid_x, avoid_z
        
        for wall in walls:
            dist, cx, cz = self._point_to_segment_distance(
                self.current_pos[0], self.current_pos[2],
                wall.start[0], wall.start[2],
                wall.end[0], wall.end[2]
            )
            
            print(f"dist a pared: {dist:.2f}, punto cercano: {cx:.2f}, {cz:.2f}")
            print(f"dist: {dist:.2f}, closest: {cx:.2f}, {cz:.2f}")
            print(f"agent pos: {self.current_pos[0]:.2f}, {self.current_pos[2]:.2f}")
            print(f"avoid force: {avoid_x:.4f}, {avoid_z:.4f}")
            

            
            if dist < self.wall_radius and dist > 0.001:
                dx = self.current_pos[0] - cx
                dz = self.current_pos[2] - cz
                strength = 1.0 - (dist / self.wall_radius)
                avoid_x += (dx/dist) * strength * self.wall_strength
                avoid_z += (dz/dist) * strength * self.wall_strength
                
                print(f"dx hacia pared: {dx:.4f}, dz hacia pared: {dz:.4f}")
                print(f"avoid_x: {avoid_x:.4f}, avoid_z: {avoid_z:.4f}")
        
        return avoid_x, avoid_z
    
    def _point_to_segment_distance(self, px, pz, ax, az, bx, bz):
        dx = bx - ax
        dz = bz - az
        seg_length_sq = dx**2 + dz**2
        
        if seg_length_sq < 0.001:
            return math.sqrt((px-ax)**2 + (pz-az)**2), ax, az
        
        t = ((px-ax)*dx + (pz-az)*dz) / seg_length_sq
        t = max(0.0, min(1.0, t))
        
        closest_x = ax + t * dx
        closest_z = az + t * dz
        
        dist = math.sqrt((px-closest_x)**2 + (pz-closest_z)**2)
        return dist, closest_x, closest_z


class WaypointPath:
    def __init__(self, path_id, waypoint_locators):
        self.id = path_id
        # ['loc_acera1', 'loc_esquina', 'loc_fruteria']
        self.waypoints = list(waypoint_locators)
    
    def get_next(self):
        """Devuelve el primer waypoint, saltando los que ya están cerca"""
        if not self.waypoints:
            return None
        return self.waypoints[0]
    
    def advance(self):
        """El agente ha llegado al waypoint actual, pasa al siguiente"""
        if self.waypoints:
            self.waypoints.pop(0)
    
    def is_complete(self):
        return len(self.waypoints) == 0
        
    def copy(self):
        # Devuelve un nuevo WaypointPath con la misma lista de waypoints
        return WaypointPath(self.id, self.waypoints[:])


class Wall:
    def __init__(self, wall_id, locator_start, locator_end):
        self.id = wall_id
        pos_a = mc.xform(locator_start, q=True, worldSpace=True, translation=True)
        pos_b = mc.xform(locator_end, q=True, worldSpace=True, translation=True)
        self.start = pos_a
        self.end = pos_b
        self.strength = 20.0
        self.radius = 30.0


class CrowdManager:
    def __init__(self, frame_in, frame_out):
        self.frame_in = frame_in
        self.frame_out = frame_out
        self.agents = {}
        self.paths = {}
        self.events = []
        self.walls = {}
        self.terrain = None

        self.hm_min_x = 0
        self.hm_min_z = 0
        self.hm_step_x = 0
        self.hm_step_z = 0
        self.hm_res = 0

    # SETUP ---------------------------------------------------------
    
    def add_agent(self, agent_id, locator_name, speed = 0.2):
        agent = Agent(agent_id, locator_name, speed)
        self.agents[agent_id] = agent
        return agent # lo devolvemos por si necesitamos configurar algo mas
        
    def add_path(self, path_id, waypoint_locators):
        self.paths[path_id] = WaypointPath(path_id, waypoint_locators)
    
    def add_event(self, frame, agent_id, action):
        self.events.append({
            'frame': frame,
            'agent_id': agent_id,  # None = todos los agentes
            'action': action       # funcion a llamar
        })
        
    def add_wall(self, wall_id, locator_start, locator_end):
        self.walls[wall_id] = Wall(wall_id, locator_start, locator_end)
        
    # SIM ---------------------------------------------------------

    def _check_events(self, frame):
        for event in self.events:
            if event['frame'] == frame:
                if event['agent_id'] is None:
                    for agent in self.agents.values():
                        event['action'](agent)
                else:
                    agent = self.agents[event['agent_id']]
                    event['action'](agent)
    
    def bake(self, agent_ids=None):
        
        if self.terrain:
            self.bake_heightmap(self.terrain)
        
        agents_to_bake = (
            {aid: self.agents[aid] for aid in agent_ids}
            if agent_ids
            else self.agents
        )
        
        # Reset de todos los agentes antes de simular
        for agent in agents_to_bake.values():
            agent.reset_to_start(self.frame_in, self.frame_out)
        
        #mc.refresh(suspend=True)
        try:
            for frame in range(self.frame_in, self.frame_out + 1):
                mc.currentTime(frame)
                self._check_events(frame)
                
                # Snapshot de posiciones para avoidance
                positions = {aid: a.current_pos[:] 
                             for aid, a in self.agents.items()}
                
                for agent in agents_to_bake.values():
                    other_pos = {aid: pos for aid, pos 
                                 in positions.items() 
                                 if aid != agent.id}
                    
                    # Calcula la altura AQUI en el manager y se la pasa
                    height = self.get_height(
                        agent.current_pos[0], 
                        agent.current_pos[2]
                    ) if self.terrain else None
                    
                    
                    print (f'this is my height: {height}')
                    agent.update(frame, other_pos, list(self.walls.values()) , height)
                    
        finally:
            mc.refresh(suspend=False)
            
    def bake_heightmap(self, terrain_mesh, resolution=100):
        """
        Antes de la sim, muestrea el terreno y guarda las alturas
        en un grid 2D. Durante la sim, interpolamos — sin tocar Maya.
        """
        self.heightmap = {}
        
        # Bounding box del terreno
        bbox = mc.exactWorldBoundingBox(terrain_mesh)
        min_x, min_z = bbox[0], bbox[2]
        max_x, max_z = bbox[3], bbox[5]
        
        step_x = (max_x - min_x) / resolution
        step_z = (max_z - min_z) / resolution
        
        cpom = mc.createNode('closestPointOnMesh')
        mc.connectAttr(terrain_mesh + '.worldMesh', cpom + '.inMesh')
        
        for i in range(resolution + 1):
            for j in range(resolution + 1):
                x = min_x + i * step_x
                z = min_z + j * step_z
                mc.setAttr(cpom + '.inPosition', x, 0, z)
                y = mc.getAttr(cpom + '.position')[0][1]
                self.heightmap[(i, j)] = y
        
        mc.delete(cpom)
        
        # Guardamos metadata para interpolacion
        self.hm_min_x = min_x
        self.hm_min_z = min_z
        self.hm_step_x = step_x
        self.hm_step_z = step_z
        self.hm_res = resolution
    
    def get_height(self, x, z):
        """Interpolacion bilineal — rapido, sin tocar Maya"""
        i = (x - self.hm_min_x) / self.hm_step_x
        j = (z - self.hm_min_z) / self.hm_step_z
        
        i0, j0 = int(i), int(j)
        i1, j1 = i0 + 1, j0 + 1
        
        # Clamp para no salir del grid
        i0 = max(0, min(i0, self.hm_res - 1))
        i1 = max(0, min(i1, self.hm_res - 1))
        j0 = max(0, min(j0, self.hm_res - 1))
        j1 = max(0, min(j1, self.hm_res - 1))
        
        # Interpolacion bilineal entre los 4 puntos mas cercanos
        tx = i - i0
        tz = j - j0
        
        h00 = self.heightmap[(i0, j0)]
        h10 = self.heightmap[(i1, j0)]
        h01 = self.heightmap[(i0, j1)]
        h11 = self.heightmap[(i1, j1)]
        
        return (h00 * (1-tx) * (1-tz) +
                h10 * tx * (1-tz) +
                h01 * (1-tx) * tz +
                h11 * tx * tz)
            
            

# SETUP

manager = CrowdManager(frame_in=1, frame_out=200)

manager.add_path('to_fruteria', 
                 ['loc_acera', 'loc_esquina', 'loc_fruteria'])
                 
manager.add_path('to_home', 
                 ['loc_inicio', 'loc_medioHome', 'loc_home'])

agent = manager.add_agent(0, 'pCube1', speed=2)
agent.path = manager.paths['to_fruteria'].copy()
agent.set_state('walk')

agent = manager.add_agent(1, 'pCube2', speed=3)
agent.path = manager.paths['to_home'].copy()
agent.set_state('walk')

manager.add_wall('pared_calle', 'wall_a1', 'wall_a2')

# Evento manual mientras no hay callbacks
manager.add_event(frame=50, agent_id=0, 
                  action=lambda a: a.set_state('idle'))
manager.add_event(frame=80, agent_id=0, 
                  action=lambda a: a.set_state('walk'))
                  
manager.terrain = 'pPlane1'
                  
      

manager.bake()




