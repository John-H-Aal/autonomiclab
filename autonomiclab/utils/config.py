"""Application configuration"""

APP_NAME = "AutonomicLab"
APP_VERSION = "0.1.0"
ORGANIZATION = "Aarhus University"

# GUI Settings
WINDOW_SIZE = (1600, 900)
DARK_MODE = False
FONT_SIZE = 10

# Protocol phases
PROTOCOL_PHASES = {
    'Valsalva': ['VM1', 'VM2', 'VM3', 'VM4'],
    'Stand Test': ['SM1', 'SM2', 'SM3', 'SM4'],
    'Deep Breathing': ['DBM1', 'DBM2', 'DBM3', 'DBM4'],
}

# Known signal names
KNOWN_SIGNALS = ['HR.csv', 'Markers.csv', 'reBAP.csv', 'Resp Wave.csv']