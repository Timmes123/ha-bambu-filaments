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
OPT_AUTO_REGISTER = "auto_register_ams"
# Shown read-only in the options flow while the printer integration is missing.
OPT_AUTO_REGISTER_UNAVAILABLE = "auto_register_ams_unavailable"
OPT_SYNC_REMAINING = "sync_ams_remaining"
OPT_SYNC_REMAINING_UNAVAILABLE = "sync_ams_remaining_unavailable"
OPT_EMPTY_PCT = "empty_on_removal_pct"
OPT_EMPTY_PCT_UNAVAILABLE = "empty_on_removal_pct_unavailable"
OPT_DEDUCT_USAGE = "deduct_print_usage"

DEFAULT_SCAN_INTERVAL_MIN = 15
DEFAULT_SPOOL_ENTITIES = True
DEFAULT_AUTO_DEDUP = False
DEFAULT_COLOR_LANG = "auto"
DEFAULT_AUTO_REGISTER = False
DEFAULT_SYNC_REMAINING = False
DEFAULT_EMPTY_PCT = 5  # 0 = off
DEFAULT_DEDUCT_USAGE = False
# Studio pushes AMS weights at most every 10 min per spool while the printer is busy.
REMAINING_PUSH_COOLDOWN_S = 600

# Domain of the Bambu Lab printer integration (github.com/greghesp/ha-bambulab)
# whose AMS slot sensors feed the auto-register feature.
BAMBULAB_DOMAIN = "bambu_lab"
# ha-bambulab AMS device model string -> cloud amsType (see AMS_TYPE_NAMES in the card).
AMS_TYPE_BY_MODEL = {"AMS": 1, "AMS Lite": 2, "AMS 2 Pro": 3, "AMS HT": 4}
COLOR_LANGS = ["auto", "de", "en"]

SERVICE_REFRESH = "refresh"

CARD_URL_BASE = "/bambu_filaments_files"
CARD_FILENAME = "bambu-filaments-card.js"
