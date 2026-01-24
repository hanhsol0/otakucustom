"""
Release script - bumps version, rebuilds repo, commits and pushes

Usage:
    python release.py           # Bump patch version (5.2.71 -> 5.2.72)
    python release.py minor     # Bump minor version (5.2.71 -> 5.3.0)
    python release.py major     # Bump major version (5.2.71 -> 6.0.0)
    python release.py 5.3.0     # Set specific version
"""

import os
import re
import sys
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ADDON_XML = os.path.join(SCRIPT_DIR, "plugin.video.otaku.testing", "addon.xml")


def get_current_version():
    """Get current version from addon.xml"""
    with open(ADDON_XML, 'r', encoding='utf-8') as f:
        content = f.read()
    match = re.search(r'version="(\d+\.\d+\.\d+)"', content)
    if match:
        return match.group(1)
    raise ValueError("Could not find version in addon.xml")


def bump_version(current, bump_type):
    """Bump version based on type"""
    major, minor, patch = map(int, current.split('.'))

    if bump_type == 'major':
        return f"{major + 1}.0.0"
    elif bump_type == 'minor':
        return f"{major}.{minor + 1}.0"
    elif bump_type == 'patch':
        return f"{major}.{minor}.{patch + 1}"
    elif re.match(r'^\d+\.\d+\.\d+$', bump_type):
        return bump_type
    else:
        raise ValueError(f"Invalid bump type: {bump_type}")


def set_version(new_version):
    """Update version in addon.xml"""
    with open(ADDON_XML, 'r', encoding='utf-8') as f:
        content = f.read()

    content = re.sub(
        r'(id="plugin\.video\.otaku\.testing".*?version=")[\d.]+(")',
        rf'\g<1>{new_version}\2',
        content
    )

    with open(ADDON_XML, 'w', encoding='utf-8') as f:
        f.write(content)


def run_command(cmd, description):
    """Run a shell command"""
    print(f"  {description}...")
    result = subprocess.run(cmd, shell=True, cwd=SCRIPT_DIR, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"    Error: {result.stderr}")
        return False
    return True


def main():
    bump_type = sys.argv[1] if len(sys.argv) > 1 else 'patch'

    print("=" * 50)
    print("Otaku Custom Release Script")
    print("=" * 50)

    # Get and bump version
    current = get_current_version()
    new_version = bump_version(current, bump_type)

    print(f"\nVersion: {current} -> {new_version}")

    # Confirm
    response = input("\nProceed? [Y/n]: ").strip().lower()
    if response and response != 'y':
        print("Cancelled.")
        return

    print("\n1. Updating version...")
    set_version(new_version)
    print(f"    Updated addon.xml to v{new_version}")

    print("\n2. Building repository...")
    run_command("python build_repo.py", "Running build_repo.py")

    print("\n3. Committing changes...")
    run_command("git add -A", "Staging files")
    run_command(f'git commit -m "Release v{new_version}"', "Creating commit")

    print("\n4. Pushing to GitHub...")
    if run_command("git push custom main", "Pushing"):
        print("\n" + "=" * 50)
        print(f"Released v{new_version}!")
        print("=" * 50)
        print("\nKodi will auto-update when it checks for updates.")
        print("(Or manually: Add-ons -> Check for updates)")
    else:
        print("\nPush failed. You may need to push manually:")
        print("  git push custom main")


if __name__ == "__main__":
    main()
