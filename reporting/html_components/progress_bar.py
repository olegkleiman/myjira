"""
Progress bar module - makes emoji progress bars
"""

from typing import Dict, Any


class ProgressBarGenerator:
    """Makes emoji progress bars"""
    
    def __init__(self, config: Dict[str, Any]):
        # setup with config for length and colors
        self.length = config.get('length', 5)
        self.colors = config.get('colors', {
            'filled': '🟩',
            'default': '⬜'
        })

    def create_progress_bar(self, done: int, total: int) -> str:
        # creates an emoji progress bar
        # shows completion ratio - no colorization, just filled vs empty blocks
        if total == 0:
            return self.colors['default'] * self.length + ' (0/0)'

        # Calculate filled and empty blocks
        filled_blocks = int(round(self.length * done / total))
        empty_blocks = self.length - filled_blocks

        # Create progress bar
        progress_bar = self.colors['filled'] * filled_blocks + self.colors['default'] * empty_blocks
        completion_text = f' ({done:g}/{total:g})'

        return progress_bar + completion_text