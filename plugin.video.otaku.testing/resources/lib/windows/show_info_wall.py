# -*- coding: utf-8 -*-

from resources.lib.ui import control


def _format_items_for_wall(items):
    """Convert browser items to info wall format."""
    formatted = []
    for item in items:
        if not item:
            continue

        info = item.get('info', {})

        formatted_item = {
            'mal_id': info.get('UniqueIDs', {}).get('mal_id', ''),
            'id': info.get('UniqueIDs', {}).get('mal_id', ''),
            'release_title': item.get('name', ''),
            'poster': item.get('poster', ''),
            'image': item.get('image', ''),
            'fanart': item.get('fanart', ''),
            'banner': item.get('banner', ''),
            'plot': info.get('plot', ''),
            'genre': info.get('genre', []),
            'studio': info.get('studio', []),
            'year': info.get('year', ''),
            'premiered': info.get('premiered', ''),
            'status': info.get('status', ''),
            'media_type': 'MOVIE' if info.get('mediatype') == 'movie' else 'TV',
            'rating': '',
            'episodes': '',
        }

        # Handle rating
        rating_info = info.get('rating', {})
        if isinstance(rating_info, dict) and rating_info.get('score'):
            formatted_item['rating'] = str(rating_info['score'])

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
