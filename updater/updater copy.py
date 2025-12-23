"""
Maya Shotgrid Breakdown Tool
Replica simplificada de tk-multi-breakdown para listar referencias y verificar versiones
"""

import maya.cmds as cmds
import sgtk
from collections import defaultdict
import imp
import os


class BreakdownTool:

    def __init__(self):
        """Inicializa la herramienta con el contexto de Shotgrid actual"""

        self.engine = sgtk.platform.current_engine()
        self.context = self.engine.context
        self.tk = self.engine.sgtk
        self.sg = self.engine.shotgun

    def get_all_references(self):

        refs_data = []
        refs = cmds.file(q=True, r=True) or []

        # Diccionario para trackear referencias únicas por path
        unique_refs = {}

        for ref_path in refs:
            # Si ya procesamos este path, skip
            if ref_path in unique_refs:
                continue

            ref_node = cmds.referenceQuery(ref_path, referenceNode=True)

            # Verifica si es una referencia nested (referencia dentro de otra referencia)
            # Queremos mantener solo las referencias top-level o las que no son instancias
            parent_ref = cmds.referenceQuery(ref_node, parent=True, referenceNode=True)

            ref_info = {
                'node': ref_node,
                'path': ref_path,
                'namespace': cmds.referenceQuery(ref_path, namespace=True),
                'is_loaded': cmds.referenceQuery(ref_path, isLoaded=True),
                'is_nested': parent_ref is not None,
                'parent_ref': parent_ref
            }

            # Guarda en el diccionario de referencias únicas
            unique_refs[ref_path] = ref_info
            refs_data.append(ref_info)

        print(f"Referencias únicas encontradas: {len(refs_data)} (de {len(refs)} total con instancias)")

        return refs_data

    def get_entity_from_path(self, file_path):
        """
        Extrae información de la entity usando los templates de Shotgrid

        Args:
            file_path (str): Path completo del archivo

        Returns:
            dict: Información de la entity (type, id, name, etc.)
        """
        try:
            # Intenta obtener el template que coincide con el path
            template = self.tk.template_from_path(file_path)

            if not template:
                return None

            # Extrae los campos del path usando el template
            fields = template.get_fields(file_path)

            # Construye la info de la entity
            entity_info = {
                'template': template.name,
                'path': file_path,
                'fields': fields
            }

            # Identifica el tipo de entity (Asset, Shot, etc.)
            if 'Asset' in fields:
                entity_info['type'] = 'Asset'
                entity_info['code'] = fields.get('Asset')
            elif 'Shot' in fields:
                entity_info['type'] = 'Shot'
                entity_info['code'] = fields.get('Shot')
            else:
                entity_info['type'] = fields.get('sg_asset_type', 'Unknown')
                entity_info['code'] = 'Unknown'

            # Otros campos útiles
            entity_info['step'] = fields.get('Step')
            entity_info['task'] = fields.get('Task')
            entity_info['version'] = fields.get('version')
            entity_info['name'] = fields.get('name')

            if file_path.endswith("abc"):
                entity_info["publishedFileType"] = "Alembic Cache"
            elif "shader" in template.name:
                entity_info["publishedFileType"] = "Maya Shaders"
            else:
                entity_info["publishedFileType"] = "Unknown"

            return entity_info

        except Exception as e:
            print(f"Error extrayendo entity de {file_path}: {e}")
            return None

    def find_latest_published_files(self, entity_info, entity_type, entity_code, task_name=None):
        """
        Busca los últimos published files en Shotgrid para una entity

        Args:
            entity_type (str): Tipo de entity (Asset, Shot, etc.)
            entity_code (str): Código/nombre de la entity
            task_name (str): Nombre del task (opcional)

        Returns:
            list: Lista de published files ordenados por versión (más reciente primero)
        """
        try:
            # Primero encuentra la entity en Shotgrid
            entity = self.sg.find_one(
                entity_type,
                [['code', 'is', entity_code], ['project', 'is', self.context.project]],
                ['id', 'code']
            )

            if not entity:
                print(f"No se encontró {entity_type} '{entity_code}' en Shotgrid")
                return []

            # Define los filtros para buscar published files
            filters = [
                ['entity', 'is', entity],
                ['project', 'is', self.context.project],
                ['published_file_type.PublishedFileType.code', 'is', entity_info["publishedFileType"]],
                ['code', 'contains', entity_info['name']]
            ]

            # Añade filtro de task si se especifica
            if task_name:
                task = self.sg.find_one(
                    'Task',
                    [
                        ['entity', 'is', entity],
                        ['content', 'is', task_name]
                    ],
                    ['id']
                )
                if task:
                    filters.append(['task', 'is', task])

            # Busca los published files
            published_files = self.sg.find(
                'PublishedFile',
                filters,
                [
                    'id',
                    'code',
                    'name',
                    'version_number',
                    'path',
                    'published_file_type',
                    'task',
                    'created_at',
                    'sg_status_list',
                    'version.Version.sg_status_list'
                ],
                order=[{'field_name': 'version_number', 'direction': 'desc'}]
            )

            return published_files

        except Exception as e:
            print(f"Error buscando published files: {e}")
            return []

    def analyze_scene(self):
        """
        Analiza toda la escena y compara referencias actuales con versiones en Shotgrid

        Returns:
            list: Lista de diccionarios con análisis completo de cada referencia
        """
        results = []
        refs = self.get_all_references()

        print(f"\n{'='*80}")
        print("BREAKDOWN TOOL - Análisis de Referencias")
        print(f"{'='*80}\n")
        print(f"Referencias encontradas: {len(refs)}\n")

        for ref in refs:
            print(f"Analizando: {ref['node']}")

            # Obtiene info de la entity desde el path
            entity_info = self.get_entity_from_path(ref['path'])

            if not entity_info:
                print(f"  ⚠ No se pudo extraer entity del path")
                results.append({
                    'reference': ref,
                    'entity_info': None,
                    'latest_publishes': [],
                    'status': 'unknown'
                })
                continue

            print(f"  Reference: {entity_info.get('code')}")
            print(f"  Entity: {entity_info.get('type')} - {entity_info.get('code')}")
            print(f"  Versión actual: {entity_info.get('version', 'N/A')}")

            # Busca las últimas versiones publicadas
            latest_publishes = self.find_latest_published_files(
                entity_info,
                entity_info.get('type'),
                entity_info.get('code'),
                entity_info.get('task')
            )

            if latest_publishes:

                # Buscamos los aprobados
                try:
                    latest_publishes_apr_aux = [pub for pub in latest_publishes if pub["sg_status_list"] == "apr"]
                    latest_publishes_apr = sorted(latest_publishes_apr_aux, key=lambda x: x["version_number"])
                except:
                    print("No Approved publishes for that Task")
                    latest_publishes_apr = []

                # Determina el estado actual de la ref
                status = 'up_to_date'
                current_version = entity_info.get('version', 0)

                if latest_publishes_apr:
                    latest_version = latest_publishes_apr[0].get('version_number', 0)
                    latest_version_path = latest_publishes_apr[0]["path"]["local_path"]
                else:
                    latest_version = latest_publishes[0].get('version_number', 0)
                    latest_version_path = latest_publishes[0]["path"]["local_path"]

                print(f"  Última versión disponible: v{latest_version:03d}")

                if current_version < latest_version:
                    status = 'out_of_date'
                    print(f"  ⚠ DESACTUALIZADO - Hay {latest_version - current_version} versión(es) más reciente(s)")
                    print(f"Actual -> {entity_info['path']}")
                    print(f"New -> {latest_version_path}")
                else:
                    print(f"  ✓ Actualizado")
            else:
                status = 'no_publishes'
                print(f"  ⚠ No se encontraron published files")

            results.append({
                'reference': ref,
                'entity_info': entity_info,
                'latest_publish_apr': latest_publishes_apr or [],
                'latest_publishes': latest_publishes[:5],
                'status': status
            })

        # Resumen
        print(f"{'='*80}")
        print("RESUMEN:")
        statuses = defaultdict(int)
        for r in results:
            statuses[r['status']] += 1
        
        print(f"  Actualizadas: {statuses['up_to_date']}")
        print(f"  Desactualizadas: {statuses['out_of_date']}")
        print(f"  Sin publishes: {statuses['no_publishes']}")
        print(f"  Desconocidas: {statuses['unknown']}")
        print(f"{'='*80}\n")
        
        return results

    def get_outdated_references(self):
        """
        Retorna solo las referencias desactualizadas
        
        Returns:
            list: Referencias que tienen versiones más recientes disponibles
        """
        results = self.analyze_scene()
        return [r for r in results if r['status'] == 'out_of_date']

    def update_reference(self, ref_data, new_publish):
        """
        Actualiza una referencia a una nueva versión
        
        Args:
            ref_data (dict): Datos de la referencia a actualizar
            new_publish (dict): PublishedFile de Shotgrid con la nueva versión
        """
        try:
            ref_node = ref_data['reference']['node']
            new_path = new_publish['path']['local_path']
            
            print(f"Actualizando {ref_node} a {new_path}")
            
            cmds.file(new_path, loadReference=ref_node)
            
            print(f"  ✓ Actualizado correctamente")
            return True
            
        except Exception as e:
            print(f"  ✗ Error actualizando: {e}")
            return False


# ============================================================================
# Funciones de conveniencia para usar desde la consola
# ============================================================================

def run_breakdown():
    """Ejecuta el análisis completo de la escena"""
    tool = BreakdownTool()
    return tool.analyze_scene()


def get_outdated():
    """Retorna solo referencias desactualizadas"""
    tool = BreakdownTool()
    return tool.get_outdated_references()


def update_all_outdated():
    """Actualiza todas las referencias desactualizadas a su última versión"""
    tool = BreakdownTool()
    outdated = tool.get_outdated_references()

    if not outdated:
        print("No hay referencias desactualizadas")
        return

    print(f"\nActualizando {len(outdated)} referencia(s)...\n")

    updates = []
    for ref_data in outdated:
        try:
            latest = ref_data['latest_publish_apr'][0]
        except:
            latest = ref_data['latest_publishes'][0]
        tool.update_reference(ref_data, latest)
        updates.append([ref_data["entity_info"]["path"], latest["code"]])

    # Finalizamos actualizando las conexiones con los shaders
    from wknd_tools.utils import reconnect_shaders
    imp.reload(reconnect_shaders)

    reconnect_shaders._reconnect_shaders()

    message = ""
    for i,j in updates:
        message += f"'{os.path.basename(i)}' updated to '{j}'\n"
    cmds.confirmDialog(title='Confirm', message=message)



# ============================================================================
# Ejemplo de uso
# ============================================================================

# if __name__ == "__main__":
#     # Análisis completo
#     results = run_breakdown()

#     # O solo las desactualizadas
#     # outdated = get_outdated()

#     # O actualizar todo
#     # update_all_outdated()
