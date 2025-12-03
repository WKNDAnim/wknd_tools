# Changelog

All notable changes to the Toolkit Configuration will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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