#!/bin/bash

# Build and push script
ADDON_XML="plugin.video.otaku.testing/addon.xml"

echo "=== Building and pushing ==="

# Step 1: Bump version
if [ -f "$ADDON_XML" ]; then
    CURRENT_VERSION=$(grep -oP 'version="\K[0-9]+\.[0-9]+\.[0-9]+' "$ADDON_XML" | head -1)
    
    if [ -n "$CURRENT_VERSION" ]; then
        MAJOR=$(echo $CURRENT_VERSION | cut -d. -f1)
        MINOR=$(echo $CURRENT_VERSION | cut -d. -f2)
        PATCH=$(echo $CURRENT_VERSION | cut -d. -f3)
        
        NEW_PATCH=$((PATCH + 1))
        NEW_VERSION="$MAJOR.$MINOR.$NEW_PATCH"
        
        sed -i "s/version=\"$CURRENT_VERSION\"/version=\"$NEW_VERSION\"/" "$ADDON_XML"
        
        echo "Version: $CURRENT_VERSION -> $NEW_VERSION"
    fi
fi

# Step 2: Build repository
echo "Building zips..."
python build_repo.py

if [ $? -ne 0 ]; then
    echo "ERROR: build_repo.py failed!"
    exit 1
fi

# Step 3: Commit the build
git add -A
git commit -m "Build v$NEW_VERSION"

# Step 4: Push
git push origin main

echo "=== Done! ==="
