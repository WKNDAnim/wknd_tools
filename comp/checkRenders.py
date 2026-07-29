"""
Chequeo de renders de Lighting aprobados.

Para cada Task "Lighting" aprobada en ShotGrid:
  1. Busca el shot al que pertenece.
  2. Busca el último render en disco (publish tiene prioridad; si no
     existe, cae al fallback de la carpeta de work/lighting).
  3. Verifica que estén todas las layers presentes en esa ruta.
  4. Comprueba que el rango de frames de cada layer coincide con el
     cut_in / cut_out del shot en ShotGrid (sin huecos).

Un shot nunca tiene render simultáneamente en publish y en lighting,
por eso la búsqueda es "o uno o el otro", nunca ambos.
"""

import os
import re
from dataclasses import dataclass, field
from typing import Optional

import OpenEXR

import sys
sys.path.insert(0, r"Z:\05Framework\users\aferraz\packages\dev_tk\master_tk_config\install\core\python")

import sgtk
tk = sgtk.sgtk_from_path(r"Z:\05Framework\users\aferraz\packages\dev_tk\master_tk_config")
shotgun = tk.shotgun


# --------------------------------------------------------------------------
# CONFIG
# --------------------------------------------------------------------------

PROJECT_ID = 91
EXCLUDED_SEQUENCES = ["sq9100", "sq9999", "sqTEST"]
IGNORED_ENTRIES = {"renderFinalslapMain", "snapshots", "tmp"}

FIELDS = [
    "content",
    "entity.Shot.code",
    "entity.Shot.sg_keyshot",
    "sg_status_list",
    "entity.Shot.sg_sequence.Sequence.code",
    "entity.Shot.sg_cut_in",
    "entity.Shot.sg_cut_out",
    "entity.Shot.sg_cam_mov",
]

FILTERS = [
    ["project.Project.id", "is", PROJECT_ID],
    ["content", "is", "Lighting"],
    ["entity", "type_is", "Shot"],
    # ["entity.Shot.code", "is", "sq0250_sh0020"],
    ["entity.Shot.sg_sequence.Sequence.code", "not_in", EXCLUDED_SEQUENCES],
    ["sg_status_list", "is", "apr"],
]

VERSION_RE = re.compile(r"v(\d+)")
FRAME_RE = re.compile(r"\.(\d+)\.exr$", re.IGNORECASE)
PATH_VERSION_RE = re.compile(r"_v(\d+)", re.IGNORECASE)


def extract_layer_version(path: Optional[str]) -> Optional[str]:
    """
    Extrae la versión (ej. 'v003') a partir de la ruta de una layer,
    buscando el patrón '_v###' que usan los templates ('..._v{version}...').
    Devuelve None si no encuentra ninguna coincidencia.
    """
    if not path:
        return None
    match = PATH_VERSION_RE.search(path)
    return f"v{match.group(1)}" if match else None


# --------------------------------------------------------------------------
# BÚSQUEDA DE RENDERS EN DISCO
# --------------------------------------------------------------------------

def list_dir_clean(path, ignored=IGNORED_ENTRIES):
    """Lista el contenido de un directorio, excluyendo entradas ignoradas."""
    if not os.path.isdir(path):
        return []
    return sorted(set(os.listdir(path)) - ignored)


def extract_version(name: str) -> int:
    """Extrae el número de versión de un nombre tipo '..._v012'. -1 si no matchea."""
    match = VERSION_RE.search(name)
    return int(match.group(1)) if match else -1


def latest_by_version(entries):
    """Devuelve la entrada con mayor número de versión, o None si la lista está vacía."""
    if not entries:
        return None
    return max(entries, key=extract_version)


def first_exr(folder: str) -> Optional[str]:
    """Devuelve el primer .exr de una carpeta (por nombre), o None si no hay ninguno."""
    if not os.path.isdir(folder):
        return None
    exrs = sorted(f for f in os.listdir(folder) if f.lower().endswith(".exr"))
    return os.path.join(folder, exrs[0]) if exrs else None


def get_exr_aovs(exr_path: Optional[str]) -> Optional[list]:
    """
    Abre un frame de ejemplo y devuelve solo los NOMBRES de AOV (capas)
    que contiene el exr -- sin desglosar sus canales.

    Soporta multipart cuando el binding de OpenEXR lo permite; si no,
    cae a InputFile normal. Devuelve None si el exr no existe o es
    ilegible/corrupto.
    """
    if exr_path is None or not os.path.isfile(exr_path):
        return None

    try:
        if not OpenEXR.isOpenExrFile(exr_path):
            return None

        try:
            mp_file = OpenEXR.MultiPartInputFile(exr_path)
            channel_names = []
            for i in range(mp_file.parts()):
                channel_names.extend(mp_file.header(i)["channels"].keys())
        except AttributeError:
            exr_file = OpenEXR.InputFile(exr_path)
            channel_names = list(exr_file.header()["channels"].keys())
            exr_file.close()

        aovs = set()
        for name in channel_names:
            aov = name.rsplit(".", 1)[0] if "." in name else "default"
            aovs.add(aov)

        return sorted(aovs)

    except Exception:
        return None


def build_fields(shot_name, sequence_code, task, step):
    return {
        "Shot": shot_name,
        "Sequence": sequence_code,
        "name": "scene",
        "Task": task,
        "Step": step,
    }


def find_publish_layers(fields: dict) -> dict:
    """
    Estructura: root/{render_layer}/{version}/exr
    Cada layer tiene sus versiones propias -> se coge la última versión POR layer.
    Devuelve {layer_name: carpeta_de_la_ultima_version or None}.
    """

    # print("Analizando...")

    render_root = tk.templates["maya_shot_render_publish_root"].apply_fields(fields)
    location = "Render PT"
    if not os.path.exists(render_root):
        render_root = tk.templates["maya_shot_render_root"].apply_fields(fields)
        location = "Render ES"

    # print(f"Render root => {render_root}")        

    if not os.path.exists(render_root):
        # print("ERROR: Estos paths de root no existen...")
        return None, {}

    if location == "Render PT":

        layer_names = list_dir_clean(render_root)
        print(f"layer_names => {layer_names}")

        result = {}
        for layer in layer_names:
            layer_root = os.path.join(render_root, layer)
            versions = list_dir_clean(layer_root)
            latest_version = latest_by_version(versions)

            if latest_version is None:
                result[layer] = None
                continue

            result[layer] = os.path.join(layer_root, latest_version)

    else:

        versions = os.listdir(render_root)
        versions.sort(reverse=True)
        if "tmp" in versions:
            versions.remove("tmp")
        if "snapshots" in versions:
            versions.remove("snapshots")

        result = {}
        processed = []
        template_exr_root = tk.templates["maya_shot_render_exr_root"]
        for v in versions:
            version_root = os.path.join(render_root, v)

            # Filter files or folders in the root not fitting template
            try:
                fields_exr_root = template_exr_root.get_fields(version_root)
            except:
                continue

            layers = os.listdir(version_root)
            for lay in layers:
                if not lay in processed:
                    if any(elem in lay.lower() for elem in ["masterlayer", "all"]):
                        continue
                    result[lay] = os.path.join(version_root, lay)
                    processed.append(lay)

    return location, result


def find_lighting_layers(fields: dict) -> dict:
    """
    Estructura: root/{version}/{render_layer}/exr
    Una única carpeta de versión contiene todas las layers de esa versión.
    Devuelve {layer_name: carpeta_de_la_layer or None}.
    """

    render_root = tk.templates["maya_shot_render_root"].apply_fields(fields)
    versions = os.listdir(render_root)
    versions.sort(reverse=True)
    if "tmp" in versions:
        versions.remove("tmp")
    if "snapshots" in versions:
        versions.remove("snapshots")

    result = {}
    processed = []
    template_exr_root = tk.templates["maya_shot_render_exr_root"]
    for v in versions:
        version_root = os.path.join(render_root, v)

        # Filter files or folders in the root not fitting template
        try:
            fields_exr_root = template_exr_root.get_fields(version_root)
        except:
            continue

        layers = os.listdir(version_root)
        for lay in layers:
            if not lay in processed:
                if any(elem in lay.lower() for elem in ["masterlayer", "all"]):
                    continue
                result[lay] = os.path.join(version_root, lay)
                processed.append(lay)

    return result


# --------------------------------------------------------------------------
# CHEQUEO DE DURACIÓN (frames vs cut_in / cut_out)
# --------------------------------------------------------------------------

def analyze_layer_frames(folder: Optional[str], cut_in: Optional[int], cut_out: Optional[int], cam_mov: Optional[bool]) -> Optional[dict]:
    """
    Analiza los frames .exr de una carpeta y los compara con el cut_in/cut_out
    del shot en ShotGrid.

    Devuelve None si la carpeta no existe o no tiene ningún .exr.
    """
    if folder is None or not os.path.isdir(folder):
        return None

    frames = []
    for fname in os.listdir(folder):
        match = FRAME_RE.search(fname)
        if match:
            frames.append(int(match.group(1)))

    if not frames:
        return None

    frames = sorted(frames)
    found_range = (frames[0], frames[-1])

    if cut_in is None or cut_out is None:
        # No hay cut_in/cut_out en ShotGrid para comparar
        return {
            "frame_range": found_range,
            "frame_count": len(frames),
            "missing_frames": [],
            "duration_ok": None,  # desconocido, no hay referencia
        }

    expected = set(range(int(cut_in), int(cut_out) + 1))
    found_set = set(frames)
    missing = sorted(expected - found_set)
    duration_ok = not missing

    if len(found_set) == 1 and "char" not in os.path.basename(folder).lower():  #any(elem in os.path.basename(folder).lower() for elem in ["bg", "volum", "volm"]):
        if not cam_mov:
            duration_ok = True

    return {
        "frame_range": found_range,
        "frame_count": len(frames),
        "missing_frames": missing,
        "duration_ok": duration_ok,  # not missing,
    }


# --------------------------------------------------------------------------
# CHEQUEO POR SHOT
# --------------------------------------------------------------------------

@dataclass
class RenderResult:
    shot_name: str
    cam_mov: bool
    source: Optional[str] = None                  # "Render PT", "Render ES", "lighting" o None
    cut_in: Optional[int] = None
    cut_out: Optional[int] = None
    layers: dict = field(default_factory=dict)     # {layer_name: folder_path or None}
    frames: dict = field(default_factory=dict)     # {layer_name: frame_info dict or None}
    aovs: dict = field(default_factory=dict)        # {layer_name: [aov_names] or None}
    error: Optional[str] = None

    @property
    def missing_layers(self):
        return [name for name, path in self.layers.items() if path is None]

    @property
    def is_complete(self):
        return bool(self.layers) and not self.missing_layers

    @property
    def has_any_render(self):
        return any(path is not None for path in self.layers.values())

    @property
    def layers_missing_frames(self):
        """Layers cuyo rango de frames no coincide con cut_in/cut_out (o no se pudo leer)."""
        bad = []
        for name, path in self.layers.items():
            if path is None:
                continue
            info = self.frames.get(name)
            if info is None or info["duration_ok"] is False:
                bad.append(name)
        return bad


def check_shot(shot: dict) -> RenderResult:
    shot_name = shot["entity.Shot.code"]
    sequence_code = shot["entity.Shot.sg_sequence.Sequence.code"]
    cut_in = shot.get("entity.Shot.sg_cut_in")
    cut_out = shot.get("entity.Shot.sg_cut_out")
    cam_mov = shot.get("entity.Shot.sg_cam_mov")

    try:
        # Un shot solo puede tener render en publish O en lighting, nunca ambos.
        # Se comprueba publish primero porque es el estado "final" esperado del pipeline.
        publish_fields = build_fields(shot_name, sequence_code, "Render", "RND")
        location, publish_layers = find_publish_layers(publish_fields)

        if publish_layers:
            frames = {name: analyze_layer_frames(path, cut_in, cut_out, cam_mov) for name, path in publish_layers.items()}
            aovs = {name: get_exr_aovs(first_exr(path)) if path else None for name, path in publish_layers.items()}
            return RenderResult(shot_name, cam_mov, location, cut_in, cut_out, publish_layers, frames, aovs)

        lighting_fields = build_fields(shot_name, sequence_code, "Lighting", "LGT")
        lighting_layers = find_lighting_layers(lighting_fields)

        if lighting_layers:
            frames = {name: analyze_layer_frames(path, cut_in, cut_out, cam_mov) for name, path in lighting_layers.items()}
            aovs = {name: get_exr_aovs(first_exr(path)) if path else None for name, path in lighting_layers.items()}
            return RenderResult(shot_name, cam_mov, "lighting", cut_in, cut_out, lighting_layers, frames, aovs)

        return RenderResult(shot_name, cam_mov, None, cut_in, cut_out, {})

    except Exception as e:
        return RenderResult(shot_name, cam_mov, None, cut_in, cut_out, {}, error=str(e))


# --------------------------------------------------------------------------
# REPORTE HTML
# --------------------------------------------------------------------------

def _status_for(r: "RenderResult") -> str:
    if r.error is not None:
        return "error"
    if not r.has_any_render:
        return "no_render"
    if not r.is_complete:
        return "incomplete"
    if r.layers_missing_frames:
        return "missing_frames"
    return "ok"


def _result_to_dict(r: "RenderResult") -> dict:
    status = _status_for(r)
    layers = {}
    for name, path in r.layers.items():
        info = r.frames.get(name)
        layers[name] = {
            "path": path,
            "version": extract_layer_version(path),
            "missing": path is None,
            "frame_range": info["frame_range"] if info else None,
            "frame_count": info["frame_count"] if info else None,
            "missing_frames": info["missing_frames"] if info else [],
            "duration_ok": info["duration_ok"] if info else None,
            "aovs": r.aovs.get(name),  # lista de nombres de AOV, o None si el exr no se pudo leer
        }
    return {
        "shot": r.shot_name,
        "source": r.source,
        "status": status,
        "cut_in": r.cut_in,
        "cut_out": r.cut_out,
        "layers": layers,
        "error": r.error,
    }


def generate_render_report_html(results, output_html: str = None, auto_open: bool = True) -> str:
    """
    Genera un reporte HTML autocontenido a partir de una lista de RenderResult.

    Cada shot se muestra con su estado (ok / incompleto / duración incorrecta /
    sin render / error) y, al desplegarlo, las layers encontradas con su
    versión, rango de frames comparado contra el cut_in/cut_out de ShotGrid,
    y los AOVs que contiene.
    """
    import json
    import tempfile
    import webbrowser

    data = [_result_to_dict(r) for r in results]

    counts = {"ok": 0, "incomplete": 0, "missing_frames": 0, "no_render": 0, "error": 0}
    for d in data:
        counts[d["status"]] += 1

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Reporte de renders — Lighting aprobados</title>
<style>
  body {{ font-family: -apple-system, sans-serif; background:#fff; color:#111; padding:2rem; max-width:960px; margin:0 auto; }}
  h1 {{ font-size:18px; margin:0 0 4px; }}
  .subtitle {{ color:#888; font-size:13px; margin-bottom:1.5rem; }}
  .summary {{ display:flex; gap:10px; margin-bottom:1.5rem; flex-wrap:wrap; }}
  .summary .stat {{ border:1px solid #e2e2e2; border-radius:10px; padding:8px 14px; font-size:13px; }}
  .summary .stat b {{ display:block; font-size:18px; margin-bottom:2px; }}
  .filters {{ display:flex; gap:6px; margin-bottom:1rem; flex-wrap:wrap; }}
  .filters button {{ font-size:12px; padding:5px 10px; border-radius:8px; border:1px solid #ddd; background:#fff; cursor:pointer; }}
  .filters button.active {{ background:#111; color:#fff; border-color:#111; }}
  .row {{ border:1px solid #e2e2e2; border-radius:10px; margin-bottom:8px; overflow:hidden; }}
  .row-header {{ display:flex; align-items:center; justify-content:space-between; padding:10px 14px; cursor:pointer; }}
  .row-header:hover {{ background:#fafafa; }}
  .shot-name {{ font-weight:600; font-size:14px; }}
  .badge {{ font-size:11px; padding:3px 9px; border-radius:999px; font-weight:600; }}
  .badge-ok {{ background:#e6f6ea; color:#1a7a34; }}
  .badge-incomplete {{ background:#fdf3e0; color:#a15c00; }}
  .badge-missing_frames {{ background:#fdf3e0; color:#a15c00; }}
  .badge-no_render {{ background:#fbe9e9; color:#b3261e; }}
  .badge-error {{ background:#eee; color:#555; }}
  .source-tag {{ font-size:11px; color:#999; margin-left:8px; }}
  .cut-tag {{ font-size:11px; color:#999; margin-left:8px; }}
  .detail {{ display:none; padding:0 14px 14px; border-top:1px solid #eee; }}
  .detail.open {{ display:block; }}
  .layer-card {{ background:#fafafa; border:1px solid #eee; border-radius:8px; padding:8px 12px; margin-top:8px; }}
  .layer-name {{ font-size:13px; font-weight:600; margin-bottom:4px; display:flex; align-items:center; gap:8px; }}
  .layer-version {{ font-size:11px; font-weight:500; color:#555; background:#eee; padding:1px 7px; border-radius:6px; }}
  .layer-path {{ font-size:11px; color:#999; word-break:break-all; margin-bottom:6px; }}
  .frame-info {{ font-size:12px; color:#333; margin-bottom:6px; }}
  .aov-label {{ font-size:11px; color:#999; margin:6px 0 4px; }}
  .pill {{ display:inline-block; font-size:11px; padding:2px 8px; border-radius:6px; background:#e6f1fb; color:#0c447c; margin:0 4px 4px 0; }}
  .missing-text {{ font-size:12px; color:#b3261e; }}
  .ok-text {{ font-size:12px; color:#1a7a34; }}
  .error-text {{ font-size:12px; color:#b3261e; padding:10px 14px; }}
  .mini-badge {{ font-size:10px; padding:2px 7px; border-radius:999px; font-weight:600; }}
</style>
</head>
<body>
  <h1>Reporte de renders — Lighting aprobados</h1>
  <div class="subtitle" id="subtitle"></div>

  <div class="summary" id="summary"></div>
  <div class="filters" id="filters"></div>
  <div id="rows"></div>

<script>
const data = {json.dumps(data)};
const counts = {json.dumps(counts)};

const labels = {{
  ok: "Completo",
  incomplete: "Faltan layers",
  missing_frames: "Faltan Frames",
  no_render: "Sin render",
  error: "Error"
}};

document.getElementById("subtitle").textContent = data.length + " shots analizados";

const summary = document.getElementById("summary");
Object.entries(counts).forEach(([status, n]) => {{
  const el = document.createElement("div");
  el.className = "stat";
  el.innerHTML = "<b>" + n + "</b>" + labels[status];
  summary.appendChild(el);
}});

let activeFilter = "all";
const filtersEl = document.getElementById("filters");
const filterOptions = [["all", "Todos"], ...Object.entries(labels)];
filterOptions.forEach(([status, label]) => {{
  const btn = document.createElement("button");
  btn.textContent = label;
  btn.className = status === "all" ? "active" : "";
  btn.onclick = () => {{
    activeFilter = status;
    [...filtersEl.children].forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    render();
  }};
  filtersEl.appendChild(btn);
}});

const rowsEl = document.getElementById("rows");

function render() {{
  rowsEl.innerHTML = "";
  const filtered = activeFilter === "all" ? data : data.filter(d => d.status === activeFilter);

  filtered.forEach((d) => {{
    const row = document.createElement("div");
    row.className = "row";

    const cutText = (d.cut_in != null && d.cut_out != null) ? ("cut " + d.cut_in + "-" + d.cut_out) : "";

    const header = document.createElement("div");
    header.className = "row-header";
    header.innerHTML =
      '<div><span class="shot-name">' + d.shot + '</span>' +
      (d.source ? '<span class="source-tag">' + d.source + '</span>' : '') +
      (cutText ? '<span class="cut-tag">' + cutText + '</span>' : '') + '</div>' +
      '<span class="badge badge-' + d.status + '">' + labels[d.status] + '</span>';

    const detail = document.createElement("div");
    detail.className = "detail";

    if (d.error) {{
      detail.innerHTML = '<div class="error-text">' + d.error + '</div>';
    }} else if (Object.keys(d.layers).length === 0) {{
      detail.innerHTML = '<div class="error-text">No se encontr\\u00f3 ninguna carpeta de render.</div>';
    }} else {{
      Object.entries(d.layers).forEach(([layerName, info]) => {{
        const card = document.createElement("div");
        card.className = "layer-card";

        let durBadge = "";
        if (info.duration_ok === true) {{
          durBadge = '<span class="mini-badge badge-ok">OK</span>';
        }} else if (info.duration_ok === false) {{
          durBadge = '<span class="mini-badge badge-missing_frames">Faltan frames</span>';
        }}

        const versionTag = info.version ? '<span class="layer-version">' + info.version + '</span>' : '';

        let inner = '<div class="layer-name">' + layerName + versionTag + durBadge + '</div>';

        if (info.missing) {{
          inner += '<div class="missing-text">Falta esta layer</div>';
        }} else {{
          inner += '<div class="layer-path">' + info.path + '</div>';
          if (info.frame_range) {{
            inner += '<div class="frame-info">Frames encontrados: ' + info.frame_range[0] + '-' + info.frame_range[1] + ' (' + info.frame_count + ' frames)</div>';
            if (info.missing_frames && info.missing_frames.length > 0) {{
              const shown = info.missing_frames.slice(0, 15).join(', ');
              const extra = info.missing_frames.length > 15 ? ' ... (+' + (info.missing_frames.length - 15) + ')' : '';
              inner += '<div class="missing-text">Frames faltantes: ' + shown + extra + '</div>';
            }} else if (info.duration_ok) {{
              inner += '<div class="ok-text">Coincide con el cut de ShotGrid</div>';
            }}

            if (info.aovs && info.aovs.length > 0) {{
              inner += '<div class="aov-label">AOVs (' + info.aovs.length + ')</div>';
              inner += info.aovs.map(a => '<span class="pill">' + a + '</span>').join('');
            }} else if (info.aovs === null) {{
              inner += '<div class="missing-text">No se pudo leer el exr para listar AOVs</div>';
            }}
          }} else {{
            inner += '<div class="missing-text">No se encontr\\u00f3 ning\\u00fan .exr en la carpeta</div>';
          }}
        }}
        card.innerHTML = inner;
        detail.appendChild(card);
      }});
    }}

    header.onclick = () => detail.classList.toggle("open");
    row.appendChild(header);
    row.appendChild(detail);
    rowsEl.appendChild(row);
  }});
}}

render();
</script>
</body>
</html>"""

    if output_html is None:
        fd, output_html = tempfile.mkstemp(suffix=".html", prefix="render_report_")
        os.close(fd)

    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html)

    if auto_open:
        webbrowser.open(f"file://{os.path.abspath(output_html)}")

    return output_html


# --------------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------------

def main():
    approved_lgt = shotgun.find("Task", FILTERS, FIELDS)
    results = [check_shot(shot) for shot in approved_lgt]

    no_render = [r for r in results if not r.has_any_render and r.error is None]
    incomplete = [r for r in results if r.has_any_render and not r.is_complete]
    missing_frames_list = [r for r in results if r.is_complete and r.layers_missing_frames]
    with_errors = [r for r in results if r.error is not None]
    complete_ok = [r for r in results if r.is_complete and not r.layers_missing_frames]

    print(f"\nTotal shots: {len(results)}")
    print(f"OK (completos y con duracion correcta): {len(complete_ok)}")

    print(f"\nSin render: {len(no_render)}")
    for r in no_render:
        print(f"  - {r.shot_name}")

    print(f"\nIncompletos (faltan layers): {len(incomplete)}")
    for r in incomplete:
        print(f"  - {r.shot_name} [{r.source}]  faltan: {r.missing_layers}")

    print(f"\nFaltan frames: {len(missing_frames_list)}")
    for r in missing_frames_list:
        print(f"  - {r.shot_name} [{r.source}] cut={r.cut_in}-{r.cut_out}  layers: {r.layers_missing_frames}")

    if with_errors:
        print(f"\nCon errores: {len(with_errors)}")
        for r in with_errors:
            print(f"  - {r.shot_name}: {r.error}")

    report_path = generate_render_report_html(results)
    print(f"\nReporte HTML generado: {report_path}")

    return results


if __name__ == "__main__":
    main()
