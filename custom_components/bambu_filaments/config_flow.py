"""Config flow for Bambu Filaments."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    SOURCE_REAUTH,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import (
    AuthFailed,
    BambuCloudClient,
    BambuCloudError,
    CloudflareBlocked,
    CodeIncorrect,
    EmailCodeRequired,
    TfaRequired,
)
from .const import (
    COLOR_LANGS,
    CONF_EMAIL,
    CONF_REGION,
    CONF_TOKEN,
    DEFAULT_COLOR_LANG,
    DEFAULT_INCLUDE_INACTIVE,
    DEFAULT_SCAN_INTERVAL_MIN,
    DEFAULT_SPOOL_ENTITIES,
    DOMAIN,
    OPT_COLOR_LANG,
    OPT_INCLUDE_INACTIVE,
    OPT_SCAN_INTERVAL,
    OPT_SPOOL_ENTITIES,
    REGION_GLOBAL,
    REGIONS,
)

_LOGGER = logging.getLogger(__name__)


class BambuFilamentsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle login (password -> optional email code / 2FA) and reauth."""

    VERSION = 1

    def __init__(self) -> None:
        self._client: BambuCloudClient | None = None
        self._region: str = REGION_GLOBAL
        self._email: str = ""
        self._tfa_key: str = ""

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> "BambuFilamentsOptionsFlow":
        return BambuFilamentsOptionsFlow()

    async def _async_finish(self) -> ConfigFlowResult:
        """Create or update the entry once self._client holds a valid token."""
        assert self._client and self._client.token
        data = {
            CONF_REGION: self._region,
            CONF_EMAIL: self._email,
            CONF_TOKEN: self._client.token,
        }
        await self.async_set_unique_id(f"{self._region}-{self._email.lower()}")
        if self.source == SOURCE_REAUTH:
            return self.async_update_reload_and_abort(self._get_reauth_entry(), data=data)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=self._email, data=data)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Initial step: region, email, password."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._region = user_input[CONF_REGION]
            self._email = user_input[CONF_EMAIL].strip()
            self._client = BambuCloudClient(self._region)
            try:
                await self.hass.async_add_executor_job(
                    self._client.login, self._email, user_input["password"]
                )
            except EmailCodeRequired:
                return await self.async_step_code()
            except TfaRequired as err:
                self._tfa_key = err.tfa_key
                return await self.async_step_tfa()
            except CloudflareBlocked:
                errors["base"] = "cloudflare"
            except AuthFailed:
                errors["base"] = "invalid_auth"
            except BambuCloudError:
                errors["base"] = "cannot_connect"
            else:
                return await self._async_finish()

        schema = vol.Schema(
            {
                vol.Required(CONF_REGION, default=self._region): SelectSelector(
                    SelectSelectorConfig(
                        options=REGIONS,
                        mode=SelectSelectorMode.DROPDOWN,
                        translation_key="region",
                    )
                ),
                vol.Required(CONF_EMAIL, default=self._email): str,
                vol.Required("password"): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_code(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Bambu emailed/texted a verification code during the login attempt."""
        errors: dict[str, str] = {}
        if user_input is not None:
            assert self._client
            code = (user_input.get("code") or "").strip()
            try:
                if user_input.get("resend"):
                    await self.hass.async_add_executor_job(
                        self._client.request_code, self._email
                    )
                    errors["base"] = "code_resent"
                elif not code:
                    errors["base"] = "code_incorrect"
                else:
                    await self.hass.async_add_executor_job(
                        self._client.login_with_code, self._email, code
                    )
                    return await self._async_finish()
            except CodeIncorrect:
                errors["base"] = "code_incorrect"
            except CloudflareBlocked:
                errors["base"] = "cloudflare"
            except BambuCloudError:
                errors["base"] = "cannot_connect"
        return self.async_show_form(
            step_id="code",
            data_schema=vol.Schema(
                {
                    vol.Optional("code", default=""): str,
                    vol.Optional("resend", default=False): bool,
                }
            ),
            errors=errors,
            description_placeholders={"email": self._email},
        )

    async def async_step_tfa(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """The account has TOTP two-factor authentication enabled."""
        errors: dict[str, str] = {}
        if user_input is not None:
            assert self._client
            try:
                await self.hass.async_add_executor_job(
                    self._client.login_with_tfa, self._tfa_key, user_input["code"].strip()
                )
            except CodeIncorrect:
                errors["base"] = "code_incorrect"
            except CloudflareBlocked:
                errors["base"] = "cloudflare"
            except BambuCloudError:
                errors["base"] = "cannot_connect"
            else:
                return await self._async_finish()
        return self.async_show_form(
            step_id="tfa",
            data_schema=vol.Schema({vol.Required("code"): str}),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Token expired (~90 days): rerun the login with prefilled account."""
        self._region = entry_data.get(CONF_REGION, REGION_GLOBAL)
        self._email = entry_data.get(CONF_EMAIL, "")
        return await self.async_step_user()


class BambuFilamentsOptionsFlow(OptionsFlow):
    """Options: polling interval and per-spool entity behavior."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        options = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    OPT_SCAN_INTERVAL,
                    default=options.get(OPT_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_MIN),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=5, max=1440, step=1, mode=NumberSelectorMode.BOX,
                        unit_of_measurement="min",
                    )
                ),
                vol.Required(
                    OPT_SPOOL_ENTITIES,
                    default=options.get(OPT_SPOOL_ENTITIES, DEFAULT_SPOOL_ENTITIES),
                ): bool,
                vol.Required(
                    OPT_INCLUDE_INACTIVE,
                    default=options.get(OPT_INCLUDE_INACTIVE, DEFAULT_INCLUDE_INACTIVE),
                ): bool,
                vol.Required(
                    OPT_COLOR_LANG,
                    default=options.get(OPT_COLOR_LANG, DEFAULT_COLOR_LANG),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=COLOR_LANGS,
                        mode=SelectSelectorMode.DROPDOWN,
                        translation_key="color_language",
                    )
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
