from maya.api import OpenMaya as om
import maya.cmds as mc
import heapq
import math


class NavGrid:

    def __init__(self, cell_size, obstacles):
        self.cell_size = cell_size
        self.obstacles = obstacles
        self.origin = None
        self.cols = 0
        self.rows = 0
        self.grid = []
        self.agent_radius = 3  # Tamaño que expandimos los obstaculos para que no se choque el agente

    def _world_to_grid(self, wx, wz):
        """Convierte posición en Maya a coordenadas de celda."""
        col = int((wx - self.origin[0]) / self.cell_size)
        row = int((wz - self.origin[2]) / self.cell_size)
        return col, row

    def _grid_to_world(self, col, row):
        """Convierte coordenadas de celda al centro de esa celda en Maya."""
        wx = self.origin[0] + col * self.cell_size + self.cell_size * 0.5
        wz = self.origin[2] + row * self.cell_size + self.cell_size * 0.5
        return wx, self.origin[1], wz

    def bake_from_plane(self, plane_name):
        """Calcula origin, width y height a partir del bounding box de un plano Maya."""

        bbox = mc.exactWorldBoundingBox(plane_name) # bbox = [xmin, ymin, zmin, xmax, ymax, zmax]

        self.origin = [bbox[0], bbox[1], bbox[2]]
        width  = bbox[3] - bbox[0]  # xmax - xmin
        height = bbox[5] - bbox[2]  # zmax - zmin

        self.cols = int(width  / self.cell_size)
        self.rows = int(height / self.cell_size)
        self.grid = [[True] * self.cols for _ in range(self.rows)]

        # Ahora hace el bake normal
        self.bake()
        self._inflate_obstacles()

    def bake(self):
        ray_origin_y = self.origin[1] + 1000

        for row in range(self.rows):
            for col in range(self.cols):
                wx, wy, wz = self._grid_to_world(col, row)

                blocked = False
                for obs in self.obstacles:
                    # Obtenemos el MFnMesh del obstáculo
                    sel = om.MSelectionList()
                    sel.add(obs)
                    dag = sel.getDagPath(0)
                    mesh = om.MFnMesh(dag)

                    # Definimos el rayo
                    ray_src = om.MFloatPoint(wx, ray_origin_y, wz)
                    ray_dir = om.MFloatVector(0, -1, 0)

                    # Lanzamos el rayo
                    result = mesh.closestIntersection(
                        ray_src, ray_dir,
                        om.MSpace.kWorld,
                        99999,
                        False
                    )

                    if result is not None:
                        hit_point, hit_ray_param, hit_face, hit_triangle, hit_bary1, hit_bary2 = result
                        if hit_ray_param > 0:
                            blocked = True
                            break

                self.grid[row][col] = not blocked

    def is_walkable(self, col, row):
        """Devuelve True si la celda está dentro del grid y es transitable."""
        if col < 0 or col >= self.cols:
            return False
        if row < 0 or row >= self.rows:
            return False
        return self.grid[row][col]

    def find_path(self, start_world, end_world):
        """
        start_world -- [x, y, z] posición de inicio en Maya
        end_world   -- [x, y, z] posición de destino en Maya
        Devuelve lista de posiciones en Maya, o [] si no hay camino.
        """

        # Convertimos posiciones del mundo a celdas del grid
        start = self._world_to_grid(start_world[0], start_world[2])
        end   = self._world_to_grid(end_world[0],   end_world[2])

        # Heurística: distancia euclídea (funciona bien con diagonales)
        def heuristic(a, b):
            return ((a[0]-b[0])**2 + (a[1]-b[1])**2) ** 0.5

        # Las 8 direcciones: cardinales + diagonales
        neighbors = [
            (0,1),(0,-1),(1,0),(-1,0),   # cardinales
            (1,1),(1,-1),(-1,1),(-1,-1)  # diagonales
        ]
        # Coste: cardinal = 1.0, diagonal = 1.414
        costs = [1.0, 1.0, 1.0, 1.0, 1.414, 1.414, 1.414, 1.414]

        # Open list: (f, g, nodo)
        open_list = []
        heapq.heappush(open_list, (0, 0, start))

        came_from = {}         # para reconstruir el camino
        g_score = {start: 0}  # coste real desde el inicio

        while open_list:
            f, g, current = heapq.heappop(open_list)

            if current == end:
                # Reconstruimos el camino
                path = []
                while current in came_from:
                    wx, wy, wz = self._grid_to_world(current[0], current[1])
                    path.append([wx, wy, wz])
                    current = came_from[current]
                path.reverse()
                return path

            for i, (dc, dr) in enumerate(neighbors):
                neighbor = (current[0]+dc, current[1]+dr)

                if not self.is_walkable(neighbor[0], neighbor[1]):
                    continue

                tentative_g = g_score[current] + costs[i]

                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    g_score[neighbor] = tentative_g
                    f_score = tentative_g + heuristic(neighbor, end)
                    heapq.heappush(open_list, (f_score, tentative_g, neighbor))
                    came_from[neighbor] = current

        return []  # no hay camino

    def _inflate_obstacles(self):
        """Marca como bloqueadas las celdas cercanas a obstáculos según agent_radius."""
        padding = int(math.ceil(self.agent_radius / self.cell_size))
        original = [row[:] for row in self.grid]  # copia del grid original

        for row in range(self.rows):
            for col in range(self.cols):
                if not original[row][col]:  # celda bloqueada
                    # Marcamos todas las celdas en el radio de padding
                    for dr in range(-padding, padding+1):
                        for dc in range(-padding, padding+1):
                            nr, nc = row+dr, col+dc
                            if 0 <= nr < self.rows and 0 <= nc < self.cols:
                                self.grid[nr][nc] = False

    def smooth_path(self, path):
        """Elimina waypoints intermedios si hay línea de visión directa."""
        if len(path) <= 2:
            return path

        smoothed = [path[0]]
        current = 0

        while current < len(path) - 1:
            # Intentamos llegar al punto más lejano posible con visión directa
            furthest = current + 1
            for i in range(current + 2, len(path)):
                if self._has_line_of_sight(path[current], path[i]):
                    furthest = i
            smoothed.append(path[furthest])
            current = furthest

        return smoothed

    def _has_line_of_sight(self, a, b):
        """Comprueba si hay visión directa entre dos posiciones del mundo."""
        col_a, row_a = self._world_to_grid(a[0], a[2])
        col_b, row_b = self._world_to_grid(b[0], b[2])

        # Algoritmo de Bresenham para recorrer las celdas entre A y B
        dx = abs(col_b - col_a)
        dz = abs(row_b - row_a)
        x, z = col_a, row_a
        sx = 1 if col_b > col_a else -1
        sz = 1 if row_b > row_a else -1
        err = dx - dz

        while True:
            if not self.is_walkable(x, z):
                return False
            if x == col_b and z == row_b:
                return True
            e2 = 2 * err
            if e2 > -dz:
                err -= dz
                x += sx
            if e2 < dx:
                err += dx
                z += sz

    def interpolate_path_old(self, path, samples_per_segment=10):
        """
        Interpola el camino con Catmull-Rom.
        samples_per_segment -- cuántos puntos generar entre cada par de waypoints.
        Más samples = más suave pero más keyframes.
        """
        if len(path) < 2:
            return path
        
        # Catmull-Rom necesita puntos fantasma al inicio y al final
        extended = [path[0]] + path + [path[-1]]
        result = []
        
        for i in range(1, len(extended) - 2):
            p0 = extended[i-1]
            p1 = extended[i]
            p2 = extended[i+1]
            p3 = extended[i+2]
            
            for j in range(samples_per_segment):
                t = j / samples_per_segment
                t2 = t * t
                t3 = t2 * t
                
                # Fórmula Catmull-Rom para cada eje
                def catmull(a, b, c, d):
                    return 0.5 * (
                        2*b +
                        (-a + c) * t +
                        (2*a - 5*b + 4*c - d) * t2 +
                        (-a + 3*b - 3*c + d) * t3
                    )
                
                x = catmull(p0[0], p1[0], p2[0], p3[0])
                y = catmull(p0[1], p1[1], p2[1], p3[1])
                z = catmull(p0[2], p1[2], p2[2], p3[2])
                result.append([x, y, z])
        
        result.append(path[-1])
        return result

    def interpolate_path(self, path, agent_speed, frames_per_segment=None):
        """
        Interpola el camino con Catmull-Rom.
        Calcula automáticamente los samples según la velocidad del agente.
        """
        if len(path) < 2:
            return path
        
        if frames_per_segment is None:
            # Calculamos la distancia media entre waypoints
            total_dist = 0
            for i in range(len(path) - 1):
                dx = path[i+1][0] - path[i][0]
                dz = path[i+1][2] - path[i][2]
                total_dist += (dx**2 + dz**2) ** 0.5
            avg_dist = total_dist / (len(path) - 1)
            
            # Cuántos frames necesita el agente para recorrer esa distancia
            # frames_per_segment = max(2, int(avg_dist / agent_speed))
            frames_per_segment = max(2, int(self.cell_size / agent_speed))
        
        # Catmull-Rom
        extended = [path[0]] + path + [path[-1]]
        result = []
        
        for i in range(1, len(extended) - 2):
            p0 = extended[i-1]
            p1 = extended[i]
            p2 = extended[i+1]
            p3 = extended[i+2]
            
            for j in range(frames_per_segment):
                t = j / frames_per_segment
                t2 = t * t
                t3 = t2 * t
                
                def catmull(a, b, c, d):
                    return 0.5 * (
                        2*b +
                        (-a + c) * t +
                        (2*a - 5*b + 4*c - d) * t2 +
                        (-a + 3*b - 3*c + d) * t3
                    )
                
                x = catmull(p0[0], p1[0], p2[0], p3[0])
                y = catmull(p0[1], p1[1], p2[1], p3[1])
                z = catmull(p0[2], p1[2], p2[2], p3[2])
                result.append([x, y, z])
        
        result.append(path[-1])
        return result

#####################

    def debug_draw(self):
        if mc.objExists("DEBUG_GRID"):
            mc.delete("DEBUG_GRID")
        debug_grp = mc.group(empty=True, name="DEBUG_GRID")

        for row in range(self.rows):
            for col in range(self.cols):
                wx, wy, wz = self._grid_to_world(col, row)
                loc = mc.spaceLocator()[0]
                mc.setAttr(loc + ".sx", 100)
                mc.setAttr(loc + ".sy", 50)
                mc.setAttr(loc + ".sz", 100)
                mc.xform(loc, t=[wx, wy, wz], ws=True)

                # Obtenemos el shape del locator
                shape = mc.listRelatives(loc, shapes=True)[0]

                if self.grid[row][col]:
                    mc.setAttr(shape + ".localScaleX", 0.2)
                    mc.setAttr(shape + ".localScaleZ", 0.2)
                else:
                    mc.setAttr(shape + ".localScaleX", 0.5)
                    mc.setAttr(shape + ".localScaleZ", 0.5)

                mc.parent(loc, debug_grp)

    def debug_draw_path(self, path):
        """Dibuja el camino como locators en Maya."""
        if mc.objExists("DEBUG_PATH"):
            mc.delete("DEBUG_PATH")
        grp = mc.group(empty=True, name="DEBUG_PATH")

        for pos in path:
            loc = mc.spaceLocator()[0]
            mc.xform(loc, t=pos, ws=True)
            mc.setAttr(loc + ".sx", 100)
            mc.setAttr(loc + ".sy", 50)
            mc.setAttr(loc + ".sz", 100)
            shape = mc.listRelatives(loc, shapes=True)[0]
            mc.setAttr(shape + ".localScaleX", 0.3)
            mc.setAttr(shape + ".localScaleZ", 0.3)
            mc.parent(loc, grp)