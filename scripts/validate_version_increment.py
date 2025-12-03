#!/usr/bin/env python3
"""
Version Increment Validation Script

This script validates that version numbers are properly incremented according to 
semantic versioning rules when changes are made to the configuration.

Usage:
    python validate_version_increment.py

Environment Variables (GitHub Actions):
    GITHUB_BASE_REF: Base branch for comparison
    GITHUB_HEAD_REF: Head branch being merged
    
Exit Codes:
    0: Validation passed
    1: Validation failed
"""

import os
import sys
import subprocess
import importlib.util
import re
from typing import Tuple, Optional


def run_git_command(command: list) -> str:
    """Run a git command and return output."""
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running git command: {e}")
        return ""


def parse_version(version_str: str) -> Tuple[int, int, int]:
    """Parse semantic version string into major, minor, patch tuple."""
    # Remove any pre-release or build metadata
    version_core = re.split(r'[-+]', version_str)[0]
    parts = version_core.split('.')
    
    if len(parts) != 3:
        raise ValueError(f"Invalid version format: {version_str}")
    
    try:
        return (int(parts[0]), int(parts[1]), int(parts[2]))
    except ValueError:
        raise ValueError(f"Invalid version format: {version_str}")


def read_version_from_file(file_path: str) -> Optional[str]:
    """Read version from version.py file."""
    try:
        spec = importlib.util.spec_from_file_location("version", file_path)
        version_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(version_module)
        return version_module.__version__
    except Exception as e:
        print(f"Error reading version from {file_path}: {e}")
        return None


def get_current_version() -> Optional[str]:
    """Get current version from version.py."""
    version_file = "version.py"
    if not os.path.exists(version_file):
        print("❌ ERROR: version.py not found")
        return None
    
    return read_version_from_file(version_file)


def get_base_version() -> Optional[str]:
    """Get version from base branch."""
    base_ref = os.getenv('GITHUB_BASE_REF', 'main')
    
    # Create temporary file to store base version
    temp_version_file = "base_version.py"
    
    try:
        # Get version.py content from base branch
        git_show_output = run_git_command([
            'git', 'show', f'origin/{base_ref}:version.py'
        ])
        
        if not git_show_output:
            print(f"⚠️  WARNING: Could not retrieve version.py from base branch {base_ref}")
            return None
        
        # Write to temporary file
        with open(temp_version_file, 'w') as f:
            f.write(git_show_output)
        
        # Read version from temporary file
        base_version = read_version_from_file(temp_version_file)
        
        # Clean up
        os.remove(temp_version_file)
        
        return base_version
        
    except Exception as e:
        print(f"Error getting base version: {e}")
        if os.path.exists(temp_version_file):
            os.remove(temp_version_file)
        return None


def validate_version_increment(current_version: str, base_version: str) -> bool:
    """Validate that current version is a proper increment of base version."""
    try:
        current_parts = parse_version(current_version)
        base_parts = parse_version(base_version)
        
        current_major, current_minor, current_patch = current_parts
        base_major, base_minor, base_patch = base_parts
        
        print(f"Base version: {base_version} ({base_major}.{base_minor}.{base_patch})")
        print(f"Current version: {current_version} ({current_major}.{current_minor}.{current_patch})")
        
        # Check if version increased
        if current_parts <= base_parts:
            print("❌ ERROR: Version must be incremented from base version")
            return False
        
        # Validate semantic versioning rules
        if current_major > base_major:
            # Major version increment - minor and patch should be 0
            if current_minor != 0 or current_patch != 0:
                print("❌ ERROR: When incrementing major version, minor and patch should be 0")
                return False
            print("✅ Valid major version increment")
            
        elif current_minor > base_minor:
            # Minor version increment - patch should be 0, major should be same
            if current_major != base_major:
                print("❌ ERROR: Major version should not change with minor increment")
                return False
            if current_patch != 0:
                print("❌ ERROR: When incrementing minor version, patch should be 0")
                return False
            print("✅ Valid minor version increment")
            
        elif current_patch > base_patch:
            # Patch version increment - major and minor should be same
            if current_major != base_major or current_minor != base_minor:
                print("❌ ERROR: Major and minor versions should not change with patch increment")
                return False
            print("✅ Valid patch version increment")
            
        else:
            print("❌ ERROR: Invalid version increment")
            return False
        
        return True
        
    except ValueError as e:
        print(f"❌ ERROR: Version parsing failed: {e}")
        return False


def analyze_changes() -> str:
    """Analyze git changes to suggest appropriate version increment."""
    try:
        # Get list of changed files in config/ and root level
        base_ref = os.getenv('GITHUB_BASE_REF', 'main')
        changed_files = run_git_command([
            'git', 'diff', '--name-only', f'origin/{base_ref}...HEAD'
        ])
        
        if not changed_files:
            return "No config changes detected"
        
        files = changed_files.split('\n')
        
        # Simple heuristics for suggesting version increment
        config_files = [f for f in files if f.startswith('config/')]
        
        if any('core/' in f or 'env/' in f for f in config_files):
            return "MAJOR or MINOR increment recommended (core/env changes may affect compatibility)"
        elif any('hooks/' in f for f in config_files):
            return "MINOR increment recommended (new hooks or hook changes)"
        elif any('templates.yml' in f or 'roots.yml' in f for f in config_files):
            return "MINOR or MAJOR increment recommended (template/root changes may affect paths)"
        else:
            return "PATCH increment recommended (minor configuration changes)"
            
    except Exception:
        return "Could not analyze changes"


def main():
    """Main validation function."""
    print("=== VERSION INCREMENT VALIDATION ===")
    
    # Get current version
    current_version = get_current_version()
    if not current_version:
        print("❌ VALIDATION FAILED: Cannot read current version")
        sys.exit(1)
    
    # Get base version for comparison
    base_version = get_base_version()
    if not base_version:
        print("⚠️  WARNING: Cannot get base version for comparison")
        print("✅ Skipping version increment validation")
        print(f"Current version: {current_version}")
        return
    
    # Skip validation if versions are the same (no version change)
    if current_version == base_version:
        print("⚠️  WARNING: Version was not changed")
        print("If you made configuration changes, please increment the version appropriately")
        
        # Analyze changes to suggest increment
        suggestion = analyze_changes()
        print(f"Suggestion based on changes: {suggestion}")
        print("✅ Validation passed (no version requirement for this PR)")
        return
    
    # Validate version increment
    if validate_version_increment(current_version, base_version):
        print("✅ VALIDATION PASSED: Version increment is valid")
        
        # Provide additional suggestions
        suggestion = analyze_changes()
        print(f"Change analysis: {suggestion}")
        
    else:
        print("❌ VALIDATION FAILED: Invalid version increment")
        print("\nSemantic Versioning Guidelines:")
        print("- MAJOR: Incompatible changes, breaking changes")
        print("- MINOR: New features, backwards compatible")
        print("- PATCH: Bug fixes, backwards compatible")
        print("\nExample valid increments from 1.2.3:")
        print("- 2.0.0 (major), 1.3.0 (minor), 1.2.4 (patch)")
        sys.exit(1)


if __name__ == "__main__":
    main()