"""Constants for the Bambu Filaments integration."""

from __future__ import annotations

DOMAIN = "bambu_filaments"

CONF_REGION = "region"
CONF_EMAIL = "email"
CONF_TOKEN = "token"

REGION_GLOBAL = "global"
REGION_CHINA = "china"
REGIONS = [REGION_GLOBAL, REGION_CHINA]

OPT_SCAN_INTERVAL = "scan_interval"
OPT_SPOOL_ENTITIES = "spool_entities"
OPT_AUTO_DEDUP = "auto_dedup_manual"
OPT_COLOR_LANG = "color_language"

DEFAULT_SCAN_INTERVAL_MIN = 15
DEFAULT_SPOOL_ENTITIES = True
DEFAULT_AUTO_DEDUP = False
DEFAULT_COLOR_LANG = "auto"
COLOR_LANGS = ["auto", "de", "en"]

SERVICE_REFRESH = "refresh"

CARD_URL_BASE = "/bambu_filaments_files"
CARD_FILENAME = "bambu-filaments-card.js"
