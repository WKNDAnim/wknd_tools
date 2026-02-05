# Changelog

All notable changes to the Toolkit Configuration will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.2] - 2026-02-05

   - SPLITTER:
      - Fix: Se quedaban todos los audios en el Trax de las escenas de LAY y ANIM. Los eliminamos y los volvemos a cargar dependiendo de si se necesitan

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