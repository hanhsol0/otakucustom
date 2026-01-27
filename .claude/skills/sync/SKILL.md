---
name: sync
description: Sync addon source files to local Kodi and clear the For You cache for live testing.
allowed-tools:
  - Bash
---

# Sync to Kodi Skill

When this skill is invoked, execute the following steps:

1. **Clean stale bytecode**: Remove `__pycache__` dirs from the Kodi addon directories so Kodi doesn't use old compiled Python.

2. **Sync files**: Rsync both the main plugin and context menu addon to the local Kodi addon directory.

3. **Clear For You cache**: Delete the For You cache from the database so it rebuilds on next open.

4. **Reload Kodi skin**: Send a Kodi EventServer action to reload the skin cache so XML changes take effect without restarting Kodi.

Execute these commands:

```bash
# Step 1: Clean stale __pycache__ from destination
find "/mnt/c/Users/hdtra/AppData/Roaming/Kodi/addons/plugin.video.otaku.testing/" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
find "/mnt/c/Users/hdtra/AppData/Roaming/Kodi/addons/context.otaku.testing/" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null

# Step 2: Sync main plugin to Kodi addon directory
rsync -av --delete --no-times --no-perms --no-group \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  /home/hdtra/projects/otakucustom/plugin.video.otaku.testing/ \
  "/mnt/c/Users/hdtra/AppData/Roaming/Kodi/addons/plugin.video.otaku.testing/"

# Sync context menu addon to Kodi addon directory
rsync -av --delete --no-times --no-perms --no-group \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  /home/hdtra/projects/otakucustom/context.otaku.testing/ \
  "/mnt/c/Users/hdtra/AppData/Roaming/Kodi/addons/context.otaku.testing/"

# Step 3: Clear For You cache
python3 -c "
import sqlite3
db = sqlite3.connect('/mnt/c/Users/hdtra/AppData/Roaming/Kodi/userdata/addon_data/plugin.video.otaku.testing/malSync.db')
db.execute('DELETE FROM for_you_cache')
db.commit()
db.close()
print('For You cache cleared')
"

# Step 4: Reload Kodi skin via EventServer (clears XML cache)
python3 -c "
import socket, struct

def send_kodi_action(action, host='localhost', port=9777):
    sig = b'XBMC'
    payload = b'\x01' + action.encode('utf-8')  # ACTION_EXECBUILTIN
    header = sig
    header += struct.pack('!BB', 2, 0)        # version 2.0
    header += struct.pack('!H', 0x000A)        # PT_ACTION
    header += struct.pack('!I', 1)             # seq
    header += struct.pack('!I', 1)             # max_seq
    header += struct.pack('!H', len(payload))  # payload size
    header += struct.pack('!I', 0)             # uid
    header += b'\x00' * 10                     # reserved
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2)
    try:
        sock.sendto(header + payload, (host, port))
        print(f'Kodi skin reload sent')
    except Exception as e:
        print(f'Could not reach Kodi EventServer (port {port}): {e}')
        print('Tip: If in the addon, back out first or restart Kodi to see XML changes')
    finally:
        sock.close()

send_kodi_action('ReloadSkin()')
"
```

Report what was synced, confirm the cache was cleared, and whether the skin reload succeeded.
