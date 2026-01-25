"""
OpenSubtitles API integration for automatic subtitle fetching
API Documentation: https://opensubtitles.stoplight.io/docs/opensubtitles-api
"""

import os
import struct
import requests
import xbmcvfs
from resources.lib.ui import control

API_BASE = "https://api.opensubtitles.com/api/v1"
USER_AGENT = "Otaku v5.2"
HASH_BLOCK_SIZE = 65536  # 64KB for hash calculation


def get_api_key():
    """Get API key from settings"""
    return control.getSetting('opensubtitles.apikey')


def is_enabled():
    """Check if OpenSubtitles fallback is enabled"""
    return control.getBool('opensubtitles.enable') and bool(get_api_key())


def calculate_hash_from_url(url):
    """
    Calculate OpenSubtitles hash from a remote video URL using range requests.

    The OpenSubtitles hash algorithm:
    1. Read first 64KB and last 64KB of file
    2. Sum all bytes as 64-bit little-endian unsigned integers
    3. Add the file size to the sum
    4. Return as 16-character lowercase hex string

    Args:
        url: Video file URL (must support range requests)

    Returns:
        Tuple of (hash_string, file_size) or (None, None) on failure
    """
    try:
        # First, get file size with a HEAD request
        headers = {'User-Agent': USER_AGENT}
        head_response = requests.head(url, headers=headers, timeout=10, allow_redirects=True)

        if head_response.status_code != 200:
            control.log(f'OpenSubtitles Hash: HEAD request failed with {head_response.status_code}', 'warning')
            return None, None

        file_size = int(head_response.headers.get('Content-Length', 0))

        if file_size < HASH_BLOCK_SIZE * 2:
            control.log(f'OpenSubtitles Hash: File too small ({file_size} bytes)', 'warning')
            return None, None

        # Check if server supports range requests
        accept_ranges = head_response.headers.get('Accept-Ranges', '')
        if accept_ranges != 'bytes':
            control.log('OpenSubtitles Hash: Server may not support range requests', 'warning')

        # Get first 64KB
        range_header = {'User-Agent': USER_AGENT, 'Range': f'bytes=0-{HASH_BLOCK_SIZE - 1}'}
        first_response = requests.get(url, headers=range_header, timeout=15)

        if first_response.status_code not in (200, 206):
            control.log(f'OpenSubtitles Hash: Failed to get first chunk: {first_response.status_code}', 'warning')
            return None, None

        first_chunk = first_response.content[:HASH_BLOCK_SIZE]

        # Get last 64KB
        last_start = file_size - HASH_BLOCK_SIZE
        range_header = {'User-Agent': USER_AGENT, 'Range': f'bytes={last_start}-{file_size - 1}'}
        last_response = requests.get(url, headers=range_header, timeout=15)

        if last_response.status_code not in (200, 206):
            control.log(f'OpenSubtitles Hash: Failed to get last chunk: {last_response.status_code}', 'warning')
            return None, None

        last_chunk = last_response.content[-HASH_BLOCK_SIZE:]

        # Calculate hash
        hash_value = file_size

        # Sum first chunk as 64-bit little-endian unsigned integers
        for i in range(0, len(first_chunk), 8):
            chunk = first_chunk[i:i+8]
            if len(chunk) == 8:
                hash_value += struct.unpack('<Q', chunk)[0]
                hash_value &= 0xFFFFFFFFFFFFFFFF  # Keep it 64-bit

        # Sum last chunk as 64-bit little-endian unsigned integers
        for i in range(0, len(last_chunk), 8):
            chunk = last_chunk[i:i+8]
            if len(chunk) == 8:
                hash_value += struct.unpack('<Q', chunk)[0]
                hash_value &= 0xFFFFFFFFFFFFFFFF  # Keep it 64-bit

        hash_string = format(hash_value, '016x')
        control.log(f'OpenSubtitles Hash: Calculated hash={hash_string}, size={file_size}')
        return hash_string, file_size

    except requests.exceptions.Timeout:
        control.log('OpenSubtitles Hash: Request timed out', 'error')
    except Exception as e:
        control.log(f'OpenSubtitles Hash: Error calculating hash - {e}', 'error')

    return None, None


def calculate_hash_from_file(filepath):
    """
    Calculate OpenSubtitles hash from a local file.

    Args:
        filepath: Path to local video file

    Returns:
        Tuple of (hash_string, file_size) or (None, None) on failure
    """
    try:
        file_size = os.path.getsize(filepath)

        if file_size < HASH_BLOCK_SIZE * 2:
            control.log(f'OpenSubtitles Hash: File too small ({file_size} bytes)', 'warning')
            return None, None

        hash_value = file_size

        with open(filepath, 'rb') as f:
            # Read first 64KB
            first_chunk = f.read(HASH_BLOCK_SIZE)

            # Read last 64KB
            f.seek(-HASH_BLOCK_SIZE, 2)  # Seek from end
            last_chunk = f.read(HASH_BLOCK_SIZE)

        # Sum first chunk
        for i in range(0, len(first_chunk), 8):
            chunk = first_chunk[i:i+8]
            if len(chunk) == 8:
                hash_value += struct.unpack('<Q', chunk)[0]
                hash_value &= 0xFFFFFFFFFFFFFFFF

        # Sum last chunk
        for i in range(0, len(last_chunk), 8):
            chunk = last_chunk[i:i+8]
            if len(chunk) == 8:
                hash_value += struct.unpack('<Q', chunk)[0]
                hash_value &= 0xFFFFFFFFFFFFFFFF

        hash_string = format(hash_value, '016x')
        control.log(f'OpenSubtitles Hash: Calculated hash={hash_string}, size={file_size}')
        return hash_string, file_size

    except Exception as e:
        control.log(f'OpenSubtitles Hash: Error calculating hash from file - {e}', 'error')

    return None, None


def search_subtitles_by_hash(moviehash, file_size=None, language='en'):
    """
    Search for subtitles using file hash for exact matching.

    This provides the most accurate subtitle matches as it identifies
    the exact video file release.

    Args:
        moviehash: OpenSubtitles hash (16-character hex string)
        file_size: File size in bytes (optional, improves accuracy)
        language: 2-letter language code

    Returns:
        List of subtitle results or empty list
    """
    api_key = get_api_key()
    if not api_key:
        control.log('OpenSubtitles: No API key configured', 'warning')
        return []

    headers = {
        'Api-Key': api_key,
        'User-Agent': USER_AGENT,
        'Content-Type': 'application/json'
    }

    params = {
        'moviehash': moviehash,
        'languages': language,
        'order_by': 'download_count',
        'order_direction': 'desc'
    }

    # Add file size if available for better matching
    if file_size:
        params['moviehash_match'] = 'include'

    try:
        control.log(f'OpenSubtitles: Searching by hash={moviehash} ({language})')
        response = requests.get(
            f"{API_BASE}/subtitles",
            headers=headers,
            params=params,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            results = data.get('data', [])

            # Filter for hash matches if we have results
            hash_matched = [r for r in results if r.get('attributes', {}).get('moviehash_match', False)]

            if hash_matched:
                control.log(f'OpenSubtitles: Found {len(hash_matched)} hash-matched subtitles (exact match!)')
                return hash_matched
            elif results:
                control.log(f'OpenSubtitles: Found {len(results)} subtitles (no exact hash match)')
                return results
            else:
                control.log('OpenSubtitles: No subtitles found for hash')
        elif response.status_code == 401:
            control.log('OpenSubtitles: Invalid API key', 'error')
        else:
            control.log(f'OpenSubtitles: Hash search failed with status {response.status_code}', 'error')

    except requests.exceptions.Timeout:
        control.log('OpenSubtitles: Hash search timed out', 'error')
    except Exception as e:
        control.log(f'OpenSubtitles: Error in hash search - {e}', 'error')

    return []


def search_subtitles(title, season=None, episode=None, language='en', imdb_id=None):
    """
    Search for subtitles on OpenSubtitles

    Args:
        title: Anime/show title
        season: Season number (optional)
        episode: Episode number (optional)
        language: 2-letter language code (default: 'en')
        imdb_id: IMDB ID if available (optional)

    Returns:
        List of subtitle results or empty list
    """
    api_key = get_api_key()
    if not api_key:
        control.log('OpenSubtitles: No API key configured', 'warning')
        return []

    headers = {
        'Api-Key': api_key,
        'User-Agent': USER_AGENT,
        'Content-Type': 'application/json'
    }

    params = {
        'languages': language,
        'order_by': 'download_count',
        'order_direction': 'desc'
    }

    # Prefer IMDB ID search if available
    if imdb_id:
        params['imdb_id'] = imdb_id
    else:
        params['query'] = title

    if season:
        params['season_number'] = season
    if episode:
        params['episode_number'] = episode

    try:
        control.log(f'OpenSubtitles: Searching for "{title}" S{season}E{episode} ({language})')
        response = requests.get(
            f"{API_BASE}/subtitles",
            headers=headers,
            params=params,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            results = data.get('data', [])
            control.log(f'OpenSubtitles: Found {len(results)} subtitles')
            return results
        elif response.status_code == 401:
            control.log('OpenSubtitles: Invalid API key', 'error')
        else:
            control.log(f'OpenSubtitles: Search failed with status {response.status_code}', 'error')

    except requests.exceptions.Timeout:
        control.log('OpenSubtitles: Request timed out', 'error')
    except Exception as e:
        control.log(f'OpenSubtitles: Error searching - {e}', 'error')

    return []


def download_subtitle(file_id):
    """
    Download a subtitle file

    Args:
        file_id: The file_id from search results

    Returns:
        Path to downloaded subtitle file or None
    """
    api_key = get_api_key()
    if not api_key:
        return None

    headers = {
        'Api-Key': api_key,
        'User-Agent': USER_AGENT,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    try:
        # Request download link
        response = requests.post(
            f"{API_BASE}/download",
            headers=headers,
            json={'file_id': file_id},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            download_link = data.get('link')

            if download_link:
                # Download the actual subtitle file
                sub_response = requests.get(download_link, timeout=15)
                if sub_response.status_code == 200:
                    # Save to Kodi's temp directory
                    temp_dir = xbmcvfs.translatePath('special://temp/')
                    sub_path = os.path.join(temp_dir, 'opensubtitles_temp.srt')

                    with open(sub_path, 'wb') as f:
                        f.write(sub_response.content)

                    control.log(f'OpenSubtitles: Downloaded subtitle to {sub_path}')
                    return sub_path
        elif response.status_code == 406:
            control.log('OpenSubtitles: Download quota exceeded', 'warning')
        else:
            control.log(f'OpenSubtitles: Download failed with status {response.status_code}', 'error')

    except Exception as e:
        control.log(f'OpenSubtitles: Error downloading - {e}', 'error')

    return None


def fetch_and_apply_subtitle(player, title, season=None, episode=None, language='en', imdb_id=None, video_url=None):
    """
    Search, download, and apply subtitle to player.

    Uses a multi-stage search strategy:
    1. Hash-based search (most accurate - exact file match)
    2. Title + episode search
    3. Title-only search (fallback)

    Args:
        player: Kodi player instance
        title: Show title
        season: Season number
        episode: Episode number
        language: 2-letter language code
        imdb_id: IMDB ID if available
        video_url: Video URL for hash-based search (optional)

    Returns:
        True if subtitle was applied, False otherwise
    """
    if not is_enabled():
        control.log('OpenSubtitles: Not enabled or no API key')
        return False

    results = []
    hash_matched = False

    # Stage 1: Try hash-based search first (most accurate)
    if video_url:
        control.log('OpenSubtitles: Attempting hash-based search for exact match...')

        # Determine if it's a local file or remote URL
        if video_url.startswith(('http://', 'https://')):
            moviehash, file_size = calculate_hash_from_url(video_url)
        elif os.path.isfile(video_url):
            moviehash, file_size = calculate_hash_from_file(video_url)
        else:
            moviehash, file_size = None, None

        if moviehash:
            results = search_subtitles_by_hash(moviehash, file_size, language)
            if results:
                # Check if any result is a hash match
                hash_matched = any(r.get('attributes', {}).get('moviehash_match', False) for r in results)
                if hash_matched:
                    control.log('OpenSubtitles: Found exact hash match!')
                else:
                    control.log('OpenSubtitles: Hash search returned results (no exact match)')
        else:
            control.log('OpenSubtitles: Could not calculate hash, falling back to title search')

    # Stage 2: Title + episode search (if no hash results)
    if not results:
        control.log('OpenSubtitles: Trying title-based search...')
        results = search_subtitles(title, season, episode, language, imdb_id)

    # Stage 3: Title-only search (fallback)
    if not results and (season or episode):
        control.log('OpenSubtitles: Trying title-only search as fallback...')
        results = search_subtitles(title, language=language, imdb_id=imdb_id)

    if not results:
        control.log('OpenSubtitles: No subtitles found')
        return False

    # Get the best result (first one, sorted by download count)
    best_result = results[0]
    attributes = best_result.get('attributes', {})
    files = attributes.get('files', [])

    if not files:
        control.log('OpenSubtitles: No files in result')
        return False

    file_id = files[0].get('file_id')
    if not file_id:
        control.log('OpenSubtitles: No file_id found')
        return False

    # Download the subtitle
    sub_path = download_subtitle(file_id)

    if sub_path:
        # Apply subtitle to player
        player.setSubtitles(sub_path)
        match_type = "HASH MATCH" if hash_matched else "title match"
        control.log(f'OpenSubtitles: Applied subtitle ({match_type}) from {attributes.get("release", "unknown")}')
        return True

    return False
