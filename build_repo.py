"""
Build script for Kodi repository
Generates addon zips, addons.xml, and repository installer

Run this script after making changes to rebuild the repository files.
"""

import os
import zipfile
import hashlib
import shutil
import xml.etree.ElementTree as ET

# Configuration - uses paths relative to script location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ZIPS_DIR = os.path.join(SCRIPT_DIR, "repo", "zips")
DOCS_DIR = os.path.join(SCRIPT_DIR, "docs")

ADDONS_TO_PACKAGE = [
    "plugin.video.otaku.testing",
    "context.otaku.testing",
]


def get_addon_version(addon_path):
    """Extract version from addon.xml"""
    addon_xml = os.path.join(addon_path, "addon.xml")
    tree = ET.parse(addon_xml)
    root = tree.getroot()
    return root.get("version")


def create_addon_zip(addon_name, source_dir, output_dir):
    """Create a zip file for an addon"""
    addon_path = os.path.join(source_dir, addon_name)
    version = get_addon_version(addon_path)
    zip_name = f"{addon_name}-{version}.zip"

    # Create addon subfolder in zips
    addon_zip_dir = os.path.join(output_dir, addon_name)
    os.makedirs(addon_zip_dir, exist_ok=True)

    zip_path = os.path.join(addon_zip_dir, zip_name)

    # Remove old zips for this addon
    for f in os.listdir(addon_zip_dir):
        if f.endswith('.zip'):
            os.remove(os.path.join(addon_zip_dir, f))

    print(f"Creating {zip_name}...")

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(addon_path):
            # Skip .git and __pycache__ directories
            dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', '.idea']]

            for file in files:
                if file.endswith('.pyc'):
                    continue
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, source_dir)
                zf.write(file_path, arcname)

    # Also copy addon.xml to the addon folder for Kodi to read
    shutil.copy(
        os.path.join(addon_path, "addon.xml"),
        os.path.join(addon_zip_dir, "addon.xml")
    )

    return addon_path, version


def generate_addons_xml(addon_paths, output_dir):
    """Generate addons.xml from all addon.xml files"""
    addons_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<addons>\n'

    for addon_path in addon_paths:
        addon_xml_path = os.path.join(addon_path, "addon.xml")
        with open(addon_xml_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Remove XML declaration if present
            if content.startswith('<?xml'):
                content = content.split('?>', 1)[1].strip()
            addons_xml += content + '\n'

    # Add repository addon itself
    repo_addon_xml = os.path.join(SCRIPT_DIR, "repository.otakucustom", "addon.xml")
    with open(repo_addon_xml, 'r', encoding='utf-8') as f:
        content = f.read()
        if content.startswith('<?xml'):
            content = content.split('?>', 1)[1].strip()
        addons_xml += content + '\n'

    addons_xml += '</addons>\n'

    # Write addons.xml
    addons_xml_path = os.path.join(output_dir, "addons.xml")
    with open(addons_xml_path, 'w', encoding='utf-8') as f:
        f.write(addons_xml)

    print(f"Created addons.xml")

    # Generate MD5
    md5 = hashlib.md5(addons_xml.encode('utf-8')).hexdigest()
    md5_path = os.path.join(output_dir, "addons.xml.md5")
    with open(md5_path, 'w') as f:
        f.write(md5)

    print(f"Created addons.xml.md5: {md5}")


def create_repository_zip():
    """Create the repository installer zip for GitHub Pages"""
    repo_addon_dir = os.path.join(SCRIPT_DIR, "repository.otakucustom")
    zip_path = os.path.join(DOCS_DIR, "repository.otakucustom-1.0.zip")

    os.makedirs(DOCS_DIR, exist_ok=True)

    print(f"Creating repository installer zip...")

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file in os.listdir(repo_addon_dir):
            file_path = os.path.join(repo_addon_dir, file)
            if os.path.isfile(file_path):
                zf.write(file_path, f"repository.otakucustom/{file}")

    print(f"Created {zip_path}")


def main():
    print("="*50)
    print("Building Otaku Custom Repository")
    print("="*50)

    # Ensure directories exist
    os.makedirs(ZIPS_DIR, exist_ok=True)

    # Package addons
    addon_paths = []
    for addon_name in ADDONS_TO_PACKAGE:
        addon_path, version = create_addon_zip(addon_name, SCRIPT_DIR, ZIPS_DIR)
        addon_paths.append(addon_path)
        print(f"  -> {addon_name} v{version}")

    # Generate addons.xml and md5
    generate_addons_xml(addon_paths, ZIPS_DIR)

    # Create repository installer
    create_repository_zip()

    print("="*50)
    print("Repository build complete!")
    print("="*50)
    print(f"\nTo release updates:")
    print(f"1. Make your code changes")
    print(f"2. Update version in addon.xml")
    print(f"3. Run: python build_repo.py")
    print(f"4. Commit and push to GitHub")


if __name__ == "__main__":
    main()
