---
name: deploy
description: Deploy the Otaku Custom addon - bumps version, builds repository, commits, and pushes to GitHub.
allowed-tools:
  - Bash
---

# Deploy Skill

When this skill is invoked, execute the following steps:

1. **Bump Version**: Read `plugin.video.otaku.testing/addon.xml`, extract the current version, increment the patch number (e.g., 5.2.134 -> 5.2.135), and update the file.

2. **Build Repository**: Run `python build_repo.py` to generate the repository zips.

3. **Commit**: Stage all changes with `git add -A` and commit with message "Build v{NEW_VERSION}"

4. **Push**: Push to the remote repository with `git push`

Execute these commands:

```bash
cd /c/Users/hdtra/OtakuCustom/otakucustom

# Get current version and bump it
ADDON_XML="plugin.video.otaku.testing/addon.xml"
CURRENT_VERSION=$(grep -oP 'version="\K[0-9]+\.[0-9]+\.[0-9]+' "$ADDON_XML" | head -1)
MAJOR=$(echo $CURRENT_VERSION | cut -d. -f1)
MINOR=$(echo $CURRENT_VERSION | cut -d. -f2)
PATCH=$(echo $CURRENT_VERSION | cut -d. -f3)
NEW_PATCH=$((PATCH + 1))
NEW_VERSION="$MAJOR.$MINOR.$NEW_PATCH"

# Update version in addon.xml
sed -i "s/version=\"$CURRENT_VERSION\"/version=\"$NEW_VERSION\"/" "$ADDON_XML"
echo "Version: $CURRENT_VERSION -> $NEW_VERSION"

# Build
python build_repo.py

# Commit and push
git add -A
git commit -m "Build v$NEW_VERSION"
git push
```

Report the new version number when complete.
