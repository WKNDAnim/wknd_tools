"""
Toolkit Configuration Version

This file tracks the current version of the toolkit configuration.
Update __version__ when making changes to the configuration.

Version Format: MAJOR.MINOR.PATCH
- MAJOR: Incompatible API changes, major restructuring
- MINOR: Add functionality in backwards compatible manner  
- PATCH: Backwards compatible bug fixes

Release Types:
- stable: Production ready
- beta: Feature complete, testing phase
- alpha: Early development, may have breaking changes
"""

import os
import subprocess

__version__ = "1.0.0"
__version_info__ = {
    "major": 1,
    "minor": 0,
    "patch": 0,
    "release": "stable",  # stable, beta, alpha
    "build": None
}


def get_version_string():
    """Return formatted version string"""
    version = f"{__version_info__['major']}.{__version_info__['minor']}.{__version_info__['patch']}"
    if __version_info__['release'] != 'stable':
        version += f"-{__version_info__['release']}"
    if __version_info__['build']:
        version += f"+{__version_info__['build']}"
    return version


def get_version_info():
    """Return complete version information"""
    return {
        'version': __version__,
        'version_string': get_version_string(),
        'version_info': __version_info__,
        'is_stable': __version_info__['release'] == 'stable'
    }


if __name__ == "__main__":
    # Allow reading version from command line
    print(__version__)