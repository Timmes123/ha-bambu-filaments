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
OPT_INCLUDE_INACTIVE = "include_inactive"

DEFAULT_SCAN_INTERVAL_MIN = 15
DEFAULT_SPOOL_ENTITIES = True
DEFAULT_INCLUDE_INACTIVE = False

SERVICE_REFRESH = "refresh"

ATTR_SPOOLS = "spools"
