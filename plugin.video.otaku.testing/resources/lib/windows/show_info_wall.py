# -*- coding: utf-8 -*-

from resources.lib.ui import control


def _format_items_for_wall(items):
    """Convert browser items to info wall format."""
    formatted = []
    for idx, item in enumerate(items):
        if not item:
            continue

        info = item.get('info', {})
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

        # Get genres - can be list of strings or list of dicts with 'name' key
        genres = info.get('genre', [])
        if genres and isinstance(genres[0], dict):
            genres = [g.get('name', '') for g in genres]

        formatted_item = {
            'mal_id': info.get('UniqueIDs', {}).get('mal_id', ''),
            'id': info.get('UniqueIDs', {}).get('mal_id', ''),
            'release_title': item.get('name', ''),
            'poster': poster,
            'image': poster,
            'fanart': fanart,
            'banner': banner,
            'plot': info.get('plot', ''),
            'genres': ', '.join(genres) if genres else '',  # XML expects 'genres' not 'genre'
            'studio': ', '.join(info.get('studio', [])) if info.get('studio') else '',
            'year': str(info.get('year', '')) if info.get('year') else '',
            'premiered': info.get('premiered', ''),
            'status': info.get('status', ''),
            'media_type': 'MOVIE' if info.get('mediatype') == 'movie' else 'TV',
            'rating': '',
            'episodes': '',
        }

        # Handle rating - can be dict with 'score' or direct value
        rating_info = info.get('rating', {})
        if isinstance(rating_info, dict) and rating_info.get('score'):
            formatted_item['rating'] = str(rating_info['score'])
        elif isinstance(rating_info, (int, float)):
            formatted_item['rating'] = str(rating_info)

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
