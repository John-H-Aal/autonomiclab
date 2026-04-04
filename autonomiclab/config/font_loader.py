"""Load and manage font configuration from YAML"""

import logging
from pathlib import Path
import yaml


class FontLoader:
    """Load fonts and settings from YAML config file"""
    
    CONFIG_PATH = Path(__file__).parent / "fonts.yaml"
    
    _config = None
    _ui_zoom = 100
    
    @classmethod
    def load(cls):
        """Load fonts.yaml"""
        if cls._config is not None:
            return cls._config
        
        try:
            with open(cls.CONFIG_PATH, 'r', encoding='utf-8') as f:
                cls._config = yaml.safe_load(f)
                return cls._config
        except FileNotFoundError:
            logging.warning("Font config not found at %s", cls.CONFIG_PATH)
            cls._config = cls._default_config()
            return cls._config
    
    @classmethod
    def _default_config(cls):
        """Default config if file not found"""
        return {
            'layout': {
                'left_width_percent': 15
            },
            'left_panel': {
                'title': {'size': 13, 'weight': 'bold'},
                'button': {'size': 12, 'weight': 'bold'},
                'status': {'size': 11, 'weight': 'normal'},
                'filter_label': {'size': 13, 'weight': 'bold'},
                'filter_combo': {'size': 13, 'weight': 'bold'},
                'table_header': {'size': 10, 'weight': 'bold'},
                'table_content': {'size': 10, 'weight': 'normal'},
                'info_box': {'size': 10, 'weight': 'normal'},
            },
            'plot_panel': {
                'title': {'size': 15, 'weight': 'bold'},
                'ylabel': {'size': 14, 'weight': 'bold'},
                'xlabel': {'size': 14, 'weight': 'bold'},
                'tick_labels': {'size': 11, 'weight': 'normal'},
                'placeholder': {'size': 14, 'weight': 'normal'},
            },
            'mouse': {
                'zoom_speed': 1.1,
                'pan_speed': 0.02
            },
        }
    
    @classmethod
    def get_layout(cls) -> dict:
        """Get layout configuration"""
        config = cls.load()
        return config.get('layout', {'left_width_percent': 15})
    
    @classmethod
    def get_mouse_config(cls) -> dict:
        """Get mouse configuration"""
        config = cls.load()
        return config.get('mouse', {'zoom_speed': 1.1, 'pan_speed': 0.02})
    
    @classmethod
    def get(cls, section: str, key: str) -> dict:
        """Get font config for section.key"""
        config = cls.load()
        
        # Apply UI zoom
        zoom_factor = cls._ui_zoom / 100.0
        
        try:
            font_config = config[section][key]
            size = int(font_config['size'] * zoom_factor)
            weight = font_config['weight']
            return {'size': size, 'weight': weight}
        except KeyError:
            return {'size': 12, 'weight': 'normal'}
    
    @classmethod
    def style(cls, section: str, key: str) -> str:
        """Generate CSS style string"""
        font = cls.get(section, key)
        return f"font-size: {font['size']}px; font-weight: {font['weight']};"
    
    @classmethod
    def set_zoom(cls, zoom_percent: int):
        """Change global UI zoom (50-200%)"""
        zoom_percent = max(50, min(200, zoom_percent))
        cls._ui_zoom = zoom_percent
    
    @classmethod
    def get_zoom(cls) -> int:
        """Get current UI zoom percentage"""
        return cls._ui_zoom
    
    @classmethod
    def save_zoom(cls, zoom_percent: int):
        """Update in-memory zoom (persisted via AppSettings)."""
        cls._ui_zoom = zoom_percent