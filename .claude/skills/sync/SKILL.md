---
name: sync
description: Sync addon source files to local Kodi and clear the For You cache for live testing.
allowed-tools:
  - Bash
---

# Sync to Kodi Skill

When this skill is invoked, execute the following steps:

1. **Sync files**: Rsync both the main plugin and context menu addon to the local Kodi addon directory.

2. **Clear For You cache**: Delete the For You cache from the database so it rebuilds on next open.

Execute these commands:

```bash
# Sync main plugin to Kodi addon directory
rsync -av --delete \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  /home/hdtra/projects/otakucustom/plugin.video.otaku.testing/ \
  "/mnt/c/Users/hdtra/AppData/Roaming/Kodi/addons/plugin.video.otaku.testing/"

# Sync context menu addon to Kodi addon directory
rsync -av --delete \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  /home/hdtra/projects/otakucustom/context.otaku.testing/ \
  "/mnt/c/Users/hdtra/AppData/Roaming/Kodi/addons/context.otaku.testing/"

# Clear For You cache
python3 -c "
import sqlite3
db = sqlite3.connect('/mnt/c/Users/hdtra/AppData/Roaming/Kodi/userdata/addon_data/plugin.video.otaku.testing/malSync.db')
db.execute('DELETE FROM for_you_cache')
db.commit()
db.close()
print('For You cache cleared')
"
```

Report what was synced and confirm the cache was cleared.
