# -*- coding: utf-8 -*-

import xbmcgui
import time

from resources.lib.ui import control
from resources.lib.windows.anichart_window import BaseWindow
from resources.lib import WatchlistIntegration


class InfoWallWindow(BaseWindow):
    """Generic info wall window for displaying anime with poster grid and info panel."""

    FILTER_TV = 'tv'
    FILTER_MOVIE = 'movie'
    FILTER_ALL = 'all'

    # Control IDs
    BUTTON_TV = 100
    BUTTON_MOVIE = 101
    BUTTON_ALL = 102
    LIST_CONTROL = 1000

    def __init__(self, xml_file, location, anime_items=None, title="", mode="default"):
        super().__init__(xml_file, location)
        self.all_items = anime_items or []
        self.filtered_items = []
        self.current_filter = self.FILTER_TV  # Default to TV Shows
        self.display_list = None
        self.position = -1
        self.last_action_time = 0
        self.last_touch_position = -1
        self.window_title = title
        self.mode = mode  # "for_you", "recommendations", "relations", etc.

    def onInit(self):
        self.display_list = self.getControl(self.LIST_CONTROL)

        # Set window title
        if self.window_title:
            self.setProperty('window.title', self.window_title)

        # Set initial filter state
        self.setProperty('filter.active', self.current_filter)
        self.setProperty('loading', 'false')

        # Apply filter and populate list
        self._apply_filter()

        # Focus on the list
        self.setFocusId(self.LIST_CONTROL)

    def _apply_filter(self):
        """Filter items based on current filter and populate the list."""
        self.display_list.reset()

        if self.current_filter == self.FILTER_ALL:
            self.filtered_items = self.all_items
        elif self.current_filter == self.FILTER_TV:
            self.filtered_items = [
                item for item in self.all_items
                if item.get('media_type', 'TV').upper() != 'MOVIE'
            ]
        elif self.current_filter == self.FILTER_MOVIE:
            self.filtered_items = [
                item for item in self.all_items
                if item.get('media_type', '').upper() == 'MOVIE'
            ]

        # Update item count
        count = len(self.filtered_items)
        self.setProperty('item.count', f'{count} titles')

        # Populate list
        for item in self.filtered_items:
            if not item:
                continue

            menu_item = control.menuItem(label=item.get('release_title', ''))

            # Set all properties
            for key, value in item.items():
                try:
                    if isinstance(value, dict):
                        # Skip dicts - they're not valid property values
                        continue
                    if isinstance(value, list):
                        value = ', '.join(str(v) for v in value)
                    menu_item.setProperty(key, str(value) if value is not None else '')
                except (UnicodeEncodeError, TypeError):
                    pass

            self.display_list.addItem(menu_item)

        control.log(f"[INFO_WALL] Showing {count} items with filter: {self.current_filter}", "info")

    def _set_filter(self, new_filter):
        """Change the active filter."""
        if new_filter != self.current_filter:
            self.current_filter = new_filter
            self.setProperty('filter.active', new_filter)
            self._apply_filter()

    def onClick(self, controlId):
        """Handle button clicks."""
        if controlId == self.BUTTON_TV:
            self._set_filter(self.FILTER_TV)
        elif controlId == self.BUTTON_MOVIE:
            self._set_filter(self.FILTER_MOVIE)
        elif controlId == self.BUTTON_ALL:
            self._set_filter(self.FILTER_ALL)
        elif controlId == self.LIST_CONTROL:
            self.handle_action(controlId)

    def onDoubleClick(self, controlId):
        """Handle double-click on list items."""
        if controlId == self.LIST_CONTROL:
            self.handle_action(controlId)

    def onAction(self, action):
        actionID = action.getId()

        # Back navigation
        if actionID in [xbmcgui.ACTION_NAV_BACK,
                        xbmcgui.ACTION_BACKSPACE,
                        xbmcgui.ACTION_PREVIOUS_MENU]:
            self.close()
            return

        # Handle different input methods
        if actionID == xbmcgui.ACTION_SELECT_ITEM:
            focused_id = self.getFocusId()
            if focused_id == self.LIST_CONTROL:
                self.handle_action(actionID)
            elif focused_id in [self.BUTTON_TV, self.BUTTON_MOVIE, self.BUTTON_ALL]:
                pass

        elif actionID in [xbmcgui.ACTION_TOUCH_TAP, xbmcgui.ACTION_MOUSE_LEFT_CLICK]:
            if self.getFocusId() == self.LIST_CONTROL:
                current_time = time.time()
                current_position = self.display_list.getSelectedPosition()
                time_diff = current_time - self.last_action_time

                if time_diff < 0.5 and current_position == self.last_touch_position:
                    self.handle_action(actionID)
                    self.last_action_time = 0
                    self.last_touch_position = -1
                else:
                    self.last_action_time = current_time
                    self.last_touch_position = current_position

        elif actionID == xbmcgui.ACTION_MOUSE_DOUBLE_CLICK:
            if self.getFocusId() == self.LIST_CONTROL:
                self.handle_action(actionID)

        # Context menu
        if actionID == 117:
            self._show_context_menu()

    def _show_context_menu(self):
        """Show context menu for selected item."""
        if self.getFocusId() != self.LIST_CONTROL:
            return

        self.position = self.display_list.getSelectedPosition()
        if self.position < 0 or self.position >= len(self.filtered_items):
            return

        selected_item = self.filtered_items[self.position]
        anime_id = selected_item.get('mal_id') or selected_item.get('id')

        if not anime_id:
            return

        context_menu_options = []

        # Mode-specific options
        if self.mode == "for_you":
            context_menu_options.append("Remove from For You")

        # Common options based on settings
        if control.getBool('context.otaku.testing.ratethis'):
            context_menu_options.append("Rate This")
        if control.getBool('context.otaku.testing.watchlist'):
            context_menu_options.append("WatchList Manager")
        if control.getBool('context.otaku.testing.findrecommendations'):
            context_menu_options.append("Find Recommendations")
        if control.getBool('context.otaku.testing.findrelations'):
            context_menu_options.append("Find Relations")
        if control.getBool('context.otaku.testing.getwatchorder'):
            context_menu_options.append("Get Watch Order")

        if not context_menu_options:
            return

        context = control.context_menu(context_menu_options)
        if context < 0:
            return

        choice = context_menu_options[context]

        if choice == "Remove from For You":
            from resources.lib.ui import database
            database.dismiss_recommendation(int(anime_id))
            self.all_items = [i for i in self.all_items if i.get('mal_id') != anime_id and i.get('id') != anime_id]
            self._apply_filter()

        elif choice == "Find Recommendations":
            from resources.lib.windows import show_info_wall
            show_info_wall.show_recommendations(anime_id)

        elif choice == "Find Relations":
            from resources.lib.windows import show_info_wall
            show_info_wall.show_relations(anime_id)

        elif choice == "Get Watch Order":
            from resources.lib import MetaBrowser
            control.draw_items(MetaBrowser.BROWSER.get_watch_order(anime_id), 'tvshows')
            self.close()

        elif choice == "WatchList Manager":
            payload = f"some_path/{anime_id}/0"
            params = {}
            try:
                WatchlistIntegration.CONTEXT_MENU(payload, params)
            except SystemExit:
                pass

        elif choice == "Rate This":
            payload = f"some_path/{anime_id}/0"
            params = {}
            try:
                WatchlistIntegration.RATE_ANIME(payload, params)
            except SystemExit:
                pass

    def handle_action(self, actionID):
        """Handle item selection - navigate to anime page."""
        if self.getFocusId() != self.LIST_CONTROL:
            return

        self.position = self.display_list.getSelectedPosition()
        if self.position < 0 or self.position >= len(self.filtered_items):
            return

        selected_item = self.filtered_items[self.position]
        anime_id = selected_item.get('mal_id') or selected_item.get('id')

        if anime_id:
            from resources.lib import Main
            Main.ANIMES(f"{anime_id}/", {})
            self.close()
