# -*- coding: utf-8 -*-

import pickle
from resources.lib.ui import control, database


def _get_show_metadata(mal_id):
    """Fetch full show metadata from database cache."""
    if not mal_id:
        return None

    try:
        # Get show data which has kodi_meta with full details
        show = database.get_show(mal_id)
        if show and show.get('kodi_meta'):
            kodi_meta = pickle.loads(show['kodi_meta'])
            return kodi_meta
    except Exception as e:
        control.log(f"[INFO_WALL] Error fetching show metadata for {mal_id}: {e}", "warning")

    return None


def _format_items_for_wall(items):
    """Convert browser items to info wall format."""
    formatted = []
    for idx, item in enumerate(items):
        if not item:
            continue

        info = item.get('info', {}) or {}
        image_data = item.get('image', {})

        # Handle image which can be a string URL or a dict with multiple URLs
        if isinstance(image_data, dict):
            poster = image_data.get('poster') or image_data.get('icon') or image_data.get('thumb') or ''
            fanart = image_data.get('fanart', [])
            if isinstance(fanart, list) and fanart:
                fanart = fanart[0]  # Get first fanart
            elif not fanart:
                fanart = poster
            banner = image_data.get('banner') or poster
        else:
            poster = image_data or item.get('poster') or ''
            fanart = item.get('fanart') or poster
            banner = item.get('banner') or poster

        # Debug: log first item's full structure
        if idx == 0:
            control.log(f"[INFO_WALL] First item keys: {list(item.keys())}", "info")
            control.log(f"[INFO_WALL] First item info keys: {list(info.keys()) if info else 'None'}", "info")
            control.log(f"[INFO_WALL] First item info: {info}", "info")

        # Get genres - can be list of strings or list of dicts with 'name' key
        genres = info.get('genre') or []
        if genres and isinstance(genres[0], dict):
            genres = [g.get('name', '') for g in genres if g]
        # Filter out None/empty values
        genres = [g for g in genres if g]

        # Get MAL ID - check multiple locations
        mal_id = ''
        unique_ids = info.get('UniqueIDs') or {}
        if unique_ids:
            mal_id = unique_ids.get('mal_id', '')
        if not mal_id:
            mal_id = item.get('mal_id') or item.get('id') or ''

        # Try to get richer metadata from database cache
        cached_meta = _get_show_metadata(mal_id) if mal_id else None
        if cached_meta and idx == 0:
            control.log(f"[INFO_WALL] Found cached metadata for {mal_id}: {list(cached_meta.keys())}", "info")

        # Get title - check multiple locations
        title = item.get('name') or info.get('title') or ''
        # Clean up any Kodi formatting tags for display
        if title:
            title = title.replace('[B]', '').replace('[/B]', '')
            title = title.replace('[I]', '').replace('[/I]', '')
            # Remove color tags like [COLOR red]...[/COLOR]
            import re
            title = re.sub(r'\[COLOR[^\]]*\]', '', title)
            title = title.replace('[/COLOR]', '')
            title = title.strip()

        # Get year - check multiple locations, fallback to cached
        year = info.get('year')
        if not year and info.get('premiered'):
            try:
                premiered = info.get('premiered')
                if premiered:
                    year = premiered.split('-')[0]
            except (AttributeError, IndexError):
                pass
        if not year and cached_meta:
            year = cached_meta.get('year')

        # Get plot - handle None explicitly, fallback to cached
        plot = info.get('plot') or info.get('description') or ''
        if not plot and cached_meta:
            plot = cached_meta.get('plot') or ''
        if plot:
            # Clean up any HTML/Kodi tags
            plot = str(plot).replace('[CR]', '\n').replace('<br>', '\n')

        # Get status - format nicely, fallback to cached
        status = info.get('status') or ''
        if not status and cached_meta:
            status = cached_meta.get('status') or ''
        if status:
            # Convert AniList/MAL status format to readable format
            status_map = {
                'FINISHED': 'Finished',
                'RELEASING': 'Airing',
                'NOT_YET_RELEASED': 'Not Yet Aired',
                'CANCELLED': 'Cancelled',
                'HIATUS': 'Hiatus',
                'Finished Airing': 'Finished',
                'Currently Airing': 'Airing',
                'Not yet aired': 'Not Yet Aired'
            }
            status = status_map.get(status, status.replace('_', ' ').title())

        # Get episodes - fallback to cached
        episodes = info.get('episode_count') or info.get('episodes') or ''
        if not episodes and cached_meta:
            episodes = cached_meta.get('episodes') or ''

        # Get studio - fallback to cached
        studio_list = info.get('studio') or []
        if not studio_list and cached_meta:
            studio_list = cached_meta.get('studio') or []
        if isinstance(studio_list, list):
            studio_list = [s for s in studio_list if s]  # Filter None values
            studio = ', '.join(studio_list)
        else:
            studio = str(studio_list) if studio_list else ''

        # Get genres - fallback to cached (genres already extracted above, but may be empty)
        if not genres and cached_meta:
            cached_genres = cached_meta.get('genres') or cached_meta.get('genre') or []
            if isinstance(cached_genres, str):
                genres = [g.strip() for g in cached_genres.split(',') if g.strip()]
            elif isinstance(cached_genres, list):
                genres = [g for g in cached_genres if g]

        # Determine media type
        media_type = 'tv'  # default
        if info.get('mediatype') == 'movie':
            media_type = 'movie'
        elif cached_meta and cached_meta.get('episodes') == 1:
            media_type = 'movie'

        formatted_item = {
            'mal_id': str(mal_id) if mal_id else '',
            'id': str(mal_id) if mal_id else '',
            'release_title': title,
            'poster': poster,
            'image': poster,
            'fanart': fanart,
            'banner': banner,
            'plot': plot,
            'genres': ', '.join(genres) if genres else '',
            'studio': studio,
            'year': str(year) if year else '',
            'premiered': info.get('premiered') or '',
            'status': status,
            'media_type': media_type,
            'rating': '',
            'episodes': str(episodes) if episodes else '',
        }

        # Handle rating - can be dict with 'score' or direct value, fallback to cached
        rating_info = info.get('rating')
        if isinstance(rating_info, dict):
            score = rating_info.get('score')
            if score is not None:
                formatted_item['rating'] = str(score)
        elif rating_info is not None and rating_info != '':
            try:
                formatted_item['rating'] = str(float(rating_info))
            except (ValueError, TypeError):
                pass

        # Fallback to cached rating if still empty
        if not formatted_item['rating'] and cached_meta:
            cached_rating = cached_meta.get('rating')
            if isinstance(cached_rating, dict):
                score = cached_rating.get('score')
                if score is not None:
                    formatted_item['rating'] = str(score)
            elif cached_rating is not None:
                formatted_item['rating'] = str(cached_rating)

        # Log formatted data for debugging
        if idx == 0:
            control.log(f"[INFO_WALL] Formatted item: plot={bool(plot)}, year={year}, rating={formatted_item['rating']}, genres={bool(genres)}, status={status}, cached={bool(cached_meta)}", "info")

        formatted.append(formatted_item)

    return formatted


def show_recommendations(mal_id):
    """Show recommendations for an anime in the info wall window."""
    from resources.lib import MetaBrowser
    from resources.lib.windows.info_wall_window import InfoWallWindow

    # Get recommendations
    items = MetaBrowser.BROWSER.get_recommendations(mal_id, 1)

    if not items:
        control.notify(control.ADDON_NAME, "No recommendations found")
        return

    # Format items for display
    formatted_items = _format_items_for_wall(items)

    # Show in info wall
    window = InfoWallWindow(
        'for_you.xml',
        control.ADDON_PATH,
        anime_items=formatted_items,
        title="Recommendations",
        mode="recommendations"
    )
    window.doModal()
    del window


def show_relations(mal_id):
    """Show relations for an anime in the info wall window."""
    from resources.lib import MetaBrowser
    from resources.lib.windows.info_wall_window import InfoWallWindow

    # Get relations
    items = MetaBrowser.BROWSER.get_relations(mal_id)

    if not items:
        control.notify(control.ADDON_NAME, "No relations found")
        return

    # Format items for display
    formatted_items = _format_items_for_wall(items)

    # Show in info wall
    window = InfoWallWindow(
        'for_you.xml',
        control.ADDON_PATH,
        anime_items=formatted_items,
        title="Relations",
        mode="relations"
    )
    window.doModal()
    del window
