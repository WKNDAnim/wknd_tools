# Changelog

All notable changes to the Toolkit Configuration will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.17] - 2026-04-17

   - SendFLayRender:
      - Añadimos en 'is_arnes_visible()' una opción que tiene en cuenta si el perro puede llevar arnés o no

## [1.1.16] - 2026-04-16

   - SendFLayRender --> Igualamos el script de UTILS al de FLAY

## [1.1.15] - 2026-04-15

   - SendFLayRender
      - Habia una ruta relativa en un import y no funcionaba...

## [1.1.14] - 2026-04-14

   - SendFLayRender:
      - Añadimos Cesped


## [1.1.13] - 2026-04-14

   - Fix Escuela Exterior:
      - Añadimos Cesped
      - Añadimos Vallas


## [1.1.12] - 2026-04-13

   - Forzamos el playblast a 24 fps en `.../media/video_encoder.py`


## [1.1.11] - 2026-04-13

   - Publish FLAY:
      - Arreglamos el bool que entra en la función de publish en `render_qt_and_publish.py`
      - REFACTOR de `sendFLayRender.py`

   - Primera versión de Fix Escuela Ext

## [1.1.10] - 2026-04-09

   - Publish FLAY:
      - No borramos la versión, pasamos la versión como parámetro!!

   - Añadimos a `rmadrid` para que pueda hacer publish de anim por elemento.

## [1.1.9] - 2026-04-08

   - Publish FLAY:
      - Borramos la versión que se crea con el Publish normal para crearla desde Deadline.
         ** Esto se puede mejorar pasando la versión como parámetro

   - Render_qt_and_publish:
      -Faltaba pasar el argumento `auto` a publish()


## [1.1.8] - 2026-04-08

   - Añadimos argumentos a la función `sendFLayRender.submit_render_and_post_job()`:
      - version --> para la gestion de la versión del render y la escena
      - description --> Descripción de la versión
      - auto --> BOOL -> marca si se ha lanzado de forma automática o desde un publish manual

## [1.1.7] - 2026-04-07

   - Add  `./utils /createLightingScenes.py` to standalone create LGT v001 scenes.


## [1.1.6] - 2026-04-01

   - Creamos la carpeta de `./flay` y movemos allí los scripts `sendFlayRender.py` y `sendFlaytoDeadline.py`
      - Conservamos `sendFlayRender.py` en utils temporalmente porque los jobs que ya están lanzados usan ese...

   - Fixes en la creación de las escenas de Lighting:
      - Reconnect shaders ahora llama a la función del módulo `reconnect_shaders`
      - Nueva función para render settings
      - ...

   - PUBLISHER:
      - Añadimos Publisher de FLAY


## [1.1.5] - 2026-02-16

   - ANIM PUBLISHER:
      - _get_instance_number(namespace) --> Tenemos en cuenta si el namespace es "compuesto" y cogemos solamente la parte que necesitamos.

      - Arreglamos:
         - Si la geo de "hair" ya estaba cargada no exportaba el abc de hair
         - Si hay un elemento repetido, exporta con instanceNum y lo carga en la escena

   - FINAL LAYOUT:

      - sendFlaytoDeadline:
         - Recoge las secuencias que tienen la animación aprobada y crea una UI de python para que Prod lance las secuencias a Deadline.
         - Crea dos jobs:
            - Uno abre el mastershot, exporta y publica el JSON que define el SET con `setAutoExporter.py`
            - El otro crea la escena de Lighting y la de FLAY y crea un batch de render por Shot.

      - sendFlaytoRender:
         - Crea la escena de Lighting y la de FLAY 
         - Setea la Render Layer con el script `createColissionRenderLayer.py`
         - Crea un batch de render por Shot con dos Jobs:
            - MayaBatch de la escena de FLAY
            - Render QT --> Renderiza una movie de los exr renderizados y la publica a SG


## [1.1.4] - 2026-02-12

   - PROP UPDATER:
      - Se añade que también actualiza Characters al hair o a la última versión


## [1.1.3] - 2026-02-11

   - ANIM PUBLISHER:
      - Evitamos hacer el cambio a la geo de Rig de HAIR si ya está cargada en la escena.
      - Quitamos la lógica de backupear la escena para restaurarla.
      - Cambiamos el manager a DG para exportar hair.
   
   - RIG ATTR UPDATER:
      - Añadimos un script que busca en SG todos los PROPS que tengan la task de Shading aprobada. Abre su última escena de Rig, carga el alembic de Shading y, para cada mesh:
         - Copia los atributos custom de GUS y los que hayan sido modificados de Arnold.
         - Copia las UVs al Rig conectando el outMesh de la shape al inMesh del ShapeOrig.

   - PROP UPDATER:
      - Hacemos un updater SG agnostic. Busca la última versión de Rig en la carpeta publish y hace replace de la referencia.

## [1.1.2] - 2026-02-05

   - SPLITTER:
      - Fix: Se quedaban todos los audios en el Trax de las escenas de LAY y ANIM. Los eliminamos y los volvemos a cargar dependiendo de si se necesitan.

## [1.1.1] - 2026-02-02

   - ANIMATION PUBLISHER:
      - Improve logging
      - Check character rig version is the last one. If not, notify artist to change it.
      - Create a publish on SG to track

## [1.1.0] - 2026-02-02

   - ANIMATION PUBLISHER

## [1.0.18] - 2026-01-26

   - SPLITTER:
      - Añadimos dos funciones al script "capture" que seleccionan el panel editor con la cámara del Shot para que el playblast salga bien.

## [1.0.18] - 2026-01-26

   - RECAP AND FIX VERSION ----------------

## [1.0.17] - 2026-01-26

   - SPLITTER:
      - Especificamos que el contexto que usamos al publicar el playblast es el de la task de Layout

## [1.0.16] - 2026-01-26

   - UPDATER:
      - Now able to update Rigs and Cameras right

   - SPLITTER:
      - Hace Playblast de cada plano y lo guarda en LAY/publish/movies. Crea una versión en SG.
      - Eliminamos el grupo PREVIS de 

## [1.0.15] - 2026-01-22

   - Update de reconnect_shaders para que tenga en cuenta el nombre del asset al que pertenece el shader.
   - Al cargar los audios al hacer split de layout, copiamos cada audio a editorial del shot manteniendo el nombre.
   - Al hacer split, cambiamos la forma de buscar la cámara para eliminarla al ir de LAY a ANIM.

## [1.0.14] - 2026-01-20

   - Add `-writeUVSets` to Alembic exporter.

## [1.0.13] - 2026-01-19

   - Si la cámara de Layout no tiene Movimiento al hacer SPLIT devuelve "NO MOVEMENT"

## [1.0.12] - 2026-01-16

   - Añadimos `CameraRigAutoRenamer` for Layout
   - Ahora miramos el movimiento de camara con la cámara bakeada (posiblemente mejorar esto)

## [1.0.11] - 2026-01-15

   - Publish version:
      - Playblast tool:
         - Add `Animation` to playblast with sound steps

## [1.0.10] - 2026-01-15

   - Improved Logging on Splitter

## [1.0.9] - 2026-01-1X

   ## Added
      - Splitter:
         - Que se importen los audios en cada plano al hacer el split y que se copien a la carpeta del Shot

   ## Fixed
      - Splitter:
         - Change parent_safe() to avoid parenting
      - Create Playblast:
         - Corregido que al hacer playblast sin sonido que no de error

## [1.0.8] - 2025-12-23

   - Añadimos el UPDATER:
      - Es como una mini copia del tk-multi-breakdown2 que mira las referencias de la escena y las actualiza a la versión aprobada o a la última versión

## [1.0.7] - 2025-12-16

   - Publisher:
      - Added function to do Playblast with Sound for Layout Single Shots

## [1.0.6] - 2025-12-16

   - Layout Splitter: Added camera parenting to CAMERAS group, and delete ma camera ref for ANIM

## [1.0.5] - 2025-12-15

   - Layout Splitter: Reducimos el número de atributos de la shape de cámara que bakeamos para que tarde menos

## [1.0.4] - 2025-12-11

## [1.0.3] - 2025-12-03

   ### Added
   - Layout splitter
   - Animation publisher script - NOT WORKING YET

## [1.0.2] - 2025-12-03

- testing

## [1.0.1] - 2025-12-03

- Starting point of Version Changelog2 (added script)

## [1.0.0] - 2025-12-03

- Starting point of Version Changelog

## ####################################################

## Guidelines for Updating This Changelog

When making changes to the configuration:

1. **Add entries under [Unreleased]** section
2. **Use these categories:**
   - `Added` for new features
   - `Changed` for changes in existing functionality  
   - `Deprecated` for soon-to-be removed features
   - `Removed` for now removed features
   - `Fixed` for bug fixes
   - `Security` for vulnerability fixes

3. **When releasing a new version:**
   - Move entries from [Unreleased] to new version section
   - Update version in `config/version.py`
   - Create new [Unreleased] section

4. **Example entry format:**
   ```
   ### Added
   - New Maya 2024 integration with USD support
   - Custom validation rules for asset naming conventions
   
   ### Changed  
   - Updated Nuke templates for 4K rendering workflows
   - Enhanced error reporting in publisher
   
   ### Fixed
   - Bug in sequence folder creation hook
   - Template resolution issues on Windows
   ```

5. **Version numbering:**
   - **MAJOR**: Breaking changes, incompatible API changes
   - **MINOR**: New features, backwards compatible
   - **PATCH**: Bug fixes, backwards compatible