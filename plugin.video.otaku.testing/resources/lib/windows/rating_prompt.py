import xbmc

from resources.lib.ui import control
from resources.lib.windows.base_window import BaseWindow


class RatingPrompt(BaseWindow):
    def __init__(self, xml_file, xml_location, actionArgs=None):
        super().__init__(xml_file, xml_location, actionArgs=actionArgs)
        self.player = xbmc.Player()
        self.playing_file = self.player.getPlayingFile() if self.player.isPlaying() else None
        self.mal_id = actionArgs.get('mal_id')
        self.title = actionArgs.get('title', 'this anime')
        self.closed = False
        self.selected_score = None
        # Control IDs: 3001-3010 for scores 10-1, 3011 for skip
        self.score_map = {
            3001: 10, 3002: 9, 3003: 8, 3004: 7, 3005: 6,
            3006: 5, 3007: 4, 3008: 3, 3009: 2, 3010: 1
        }

    def onInit(self):
        # Set the title label
        self.setProperty('anime.title', self.title)
        self.background_tasks()

    def background_tasks(self):
        """Wait until playback ends or user interacts"""
        # Keep window open until playback ends or user makes a choice
        while not self.closed:
            # If playback stopped or changed, close after brief delay
            if not self.player.isPlaying():
                xbmc.sleep(500)
                if not self.closed:
                    self.close()
                break
            # Check if file changed (user started different video)
            try:
                current_file = self.player.getPlayingFile()
                if self.playing_file and current_file != self.playing_file:
                    self.close()
                    break
            except RuntimeError:
                # Player might not be available
                pass
            xbmc.sleep(500)

    def doModal(self):
        super(RatingPrompt, self).doModal()
        return self.selected_score

    def close(self):
        self.closed = True
        self.player = None
        super(RatingPrompt, self).close()

    def onClick(self, controlId):
        self.handle_action(controlId)

    def handle_action(self, controlId):
        if controlId in self.score_map:
            self.selected_score = self.score_map[controlId]
            self.close()
        elif controlId == 3011:  # Skip button
            self.selected_score = None
            self.close()

    def onAction(self, action):
        actionID = action.getId()
        if actionID in [92, 10]:  # BACKSPACE / ESCAPE
            self.selected_score = None
            self.close()


def show_rating_prompt(mal_id, title):
    """Show the rating prompt overlay and return the selected score (or None if skipped)"""
    prompt = RatingPrompt(
        'rating_prompt.xml',
        control.ADDON_PATH,
        actionArgs={'mal_id': mal_id, 'title': title, 'item_type': 'skip_intro'}
    )
    return prompt.doModal()
