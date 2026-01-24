"""
OpenSubtitles API integration for automatic subtitle fetching
API Documentation: https://opensubtitles.stoplight.io/docs/opensubtitles-api
"""

import os
import requests
from resources.lib.ui import control

API_BASE = "https://api.opensubtitles.com/api/v1"
USER_AGENT = "Otaku v5.2"


def get_api_key():
    """Get API key from settings"""
    return control.getSetting('opensubtitles.apikey')


def is_enabled():
    """Check if OpenSubtitles fallback is enabled"""
    return control.getBool('opensubtitles.enable') and bool(get_api_key())


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
                    temp_dir = control.translatePath('special://temp/')
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


def fetch_and_apply_subtitle(player, title, season=None, episode=None, language='en', imdb_id=None):
    """
    Search, download, and apply subtitle to player

    Args:
        player: Kodi player instance
        title: Show title
        season: Season number
        episode: Episode number
        language: 2-letter language code
        imdb_id: IMDB ID if available

    Returns:
        True if subtitle was applied, False otherwise
    """
    if not is_enabled():
        control.log('OpenSubtitles: Not enabled or no API key')
        return False

    # Search for subtitles
    results = search_subtitles(title, season, episode, language, imdb_id)

    if not results:
        # Try without season/episode for movies or specials
        if season or episode:
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
        control.log(f'OpenSubtitles: Applied subtitle from {attributes.get("release", "unknown")}')
        return True

    return False
