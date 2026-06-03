import maya.cmds as mc

from wknd_tools.crowds import NavGrid, Agente
import imp
imp.reload(NavGrid)
imp.reload(Agente)

DEBUG = True


def exec():

    try:
        manolo.reset_to_start()
    except:
        pass

    # Definimos el time
    frame_in = int(mc.playbackOptions(min=True, q=1))
    frame_out = int(mc.playbackOptions(max=True, q=1))
    # time = list(range(frame_in, frame_out))

    print(f"⏱️ FRAME RANGE --> {frame_in} - {frame_out}")

    # Creamos el agente
    locator_name = "Manolo"
    agent_id = 1

    manolo = Agente.Agent(agent_id, locator_name, speed=.8)
    manolo.setTarget("t2")

    print(f"👽 Agent created! ")

    # Creamos el Grid
    nav = NavGrid.NavGrid(cell_size=50, obstacles=["obstaculo1", "obstaculo2"])
    nav.bake_from_plane("suelo")
    # nav.debug_draw()

    print(f"🌍 Grid created!")

    # Calculamos el camino
    start = mc.xform("Manolo", q=True, ws=True, t=True)
    end   = mc.xform(manolo.target, q=True, ws=True, t=True)
    path = nav.find_path(start, end)
    print(f"🚶 PATH --> {path}")
    path = nav.smooth_path(path)
    print(f"🚶 SMOOTH PATH --> {path}")
    # path = nav.interpolate_path(path, agent_speed=manolo.speed)

    # Asignamos el camino al agente
    manolo.set_path(path)

    # Seteamos los rangos de movimiento
    manolo.set_move_range((1020, 1150))

    # Duración total de movimiento sumando todos los rangos
    print(f"🪇 Move Ranges --> {manolo.move_ranges}")

    total_duration = sum(end - start for start, end in manolo.move_ranges)
    print(f"\t - Duration --> {total_duration}")
    manolo.speed   = manolo.calculate_speed(total_duration)
    print(f"\t - Velocidad --> {manolo.speed}")
    path           = nav.interpolate_path(path, agent_speed=manolo.speed)
    print(f"\t - Path --> {path}")

    # Dividimos el path proporcionalmente entre los rangos
    total_frames  = len(path)
    range_lengths = [end - start for start, end in manolo.move_ranges]
    range_total   = sum(range_lengths)

    path_per_range = {}
    idx = 0
    for (move_start, move_end), length in zip(manolo.move_ranges, range_lengths):
        count = int(total_frames * length / range_total)
        path_per_range[(move_start, move_end)] = path[idx:idx + count]
        idx += count

    # El último rango se lleva el resto por si hay decimales
    last_range = manolo.move_ranges[-1]
    path_per_range[last_range] = path_per_range[last_range] + path[idx:]

    # Animamos
    for frame in range(frame_in, frame_out):

        active_range = None
        for move_start, move_end in manolo.move_ranges:
            if move_start <= frame <= move_end:
                active_range = (move_start, move_end)
                break

        if active_range is None:
            manolo._write_keyframe(frame, height=None)
            continue

        move_start, move_end = active_range
        if frame == move_start:
            manolo.set_path(path_per_range[active_range])

        if manolo.waypoint_index >= len(manolo.camino):
            break  # ha llegado al final

        target_pos = manolo.camino[manolo.waypoint_index]
        if manolo.has_reached(target_pos, threshold=20):
            manolo.waypoint_index += 1
            if manolo.waypoint_index >= len(manolo.camino):
                manolo._write_keyframe(frame, height=None)
                break
            target_pos = manolo.camino[manolo.waypoint_index]

        manolo.move(target_pos)
        manolo._write_keyframe(frame, height=None)


    if DEBUG:
        nav.debug_draw_path(path)

if __name__ == "__main__":
    exec()
