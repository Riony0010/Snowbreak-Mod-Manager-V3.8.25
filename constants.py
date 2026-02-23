from PyQt6.QtCore import Qt

VERSION = "3.8.25"
CONFIG_FILE = "config.json"
MAX_PREVIEW_SIZE = 585
HOVER_DELAY_MS = 200

COL_CAT = 0
COL_CHECK = 1
COL_PREVIEW = 2
COL_NAME = 3
COL_ACTION = 4

COLUMN_PROPORTIONS = [0.18, 0.05, 0.10, 0.47, 0.20]

ROLE_REL_PATH = Qt.ItemDataRole.UserRole + 1
ROLE_ITEM_TYPE = Qt.ItemDataRole.UserRole + 2
ROLE_DEPTH = Qt.ItemDataRole.UserRole + 3

