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
    BooleanSelector,
    BooleanSelectorConfig,
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
from .ams_register import BAMBULAB_REPO_URL, bambulab_available
from .const import (
    COLOR_LANGS,
    CONF_EMAIL,
    CONF_REGION,
    CONF_TOKEN,
    DEFAULT_AUTO_DEDUP,
    DEFAULT_AUTO_REGISTER,
    DEFAULT_COLOR_LANG,
    DEFAULT_DEDUCT_USAGE,
    DEFAULT_EMPTY_ON_RUNOUT,
    DEFAULT_EMPTY_PCT,
    DEFAULT_SYNC_REMAINING,
    DEFAULT_SCAN_INTERVAL_MIN,
    DEFAULT_SPOOL_ENTITIES,
    DOMAIN,
    OPT_AUTO_DEDUP,
    OPT_AUTO_REGISTER,
    OPT_AUTO_REGISTER_UNAVAILABLE,
    OPT_COLOR_LANG,
    OPT_DEDUCT_USAGE,
    OPT_EMPTY_ON_RUNOUT,
    OPT_EMPTY_ON_RUNOUT_UNAVAILABLE,
    OPT_EMPTY_PCT,
    OPT_EMPTY_PCT_UNAVAILABLE,
    OPT_SYNC_REMAINING,
    OPT_SYNC_REMAINING_UNAVAILABLE,
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
            # Reauth must stay on the same account - a login for a different
            # email/region would silently swap the entry's identity.
            self._abort_if_unique_id_mismatch(reason="wrong_account")
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
        options = self.config_entry.options
        has_bambulab = bambulab_available(self.hass)
        if user_input is not None:
            # The read-only placeholder is not a setting: drop it and keep
            # whatever value the real option had.
            for key in (
                OPT_AUTO_REGISTER_UNAVAILABLE,
                OPT_SYNC_REMAINING_UNAVAILABLE,
                OPT_EMPTY_ON_RUNOUT_UNAVAILABLE,
                OPT_EMPTY_PCT_UNAVAILABLE,
            ):
                user_input.pop(key, None)
            if not has_bambulab:
                for key, default in (
                    (OPT_AUTO_REGISTER, DEFAULT_AUTO_REGISTER),
                    (OPT_SYNC_REMAINING, DEFAULT_SYNC_REMAINING),
                    (OPT_EMPTY_ON_RUNOUT, DEFAULT_EMPTY_ON_RUNOUT),
                    (OPT_EMPTY_PCT, DEFAULT_EMPTY_PCT),
                ):
                    user_input[key] = options.get(key, default)
            return self.async_create_entry(data=user_input)
        pct_selector = lambda read_only: NumberSelector(  # noqa: E731
            NumberSelectorConfig(
                min=0, max=50, step=1, mode=NumberSelectorMode.BOX,
                unit_of_measurement="%", read_only=read_only,
            )
        )
        register_value = options.get(OPT_AUTO_REGISTER, DEFAULT_AUTO_REGISTER)
        remaining_value = options.get(OPT_SYNC_REMAINING, DEFAULT_SYNC_REMAINING)
        runout_value = options.get(OPT_EMPTY_ON_RUNOUT, DEFAULT_EMPTY_ON_RUNOUT)
        pct_value = options.get(OPT_EMPTY_PCT, DEFAULT_EMPTY_PCT)
        if has_bambulab:
            ams_fields = {
                vol.Required(OPT_AUTO_REGISTER, default=register_value): bool,
                vol.Required(OPT_SYNC_REMAINING, default=remaining_value): bool,
                vol.Required(OPT_EMPTY_ON_RUNOUT, default=runout_value): bool,
                vol.Required(OPT_EMPTY_PCT, default=pct_value): pct_selector(False),
            }
        else:
            # Greyed-out fields + hint (with link) while the printer integration
            # that provides the AMS slot sensors is not installed/loaded.
            ro = BooleanSelector(BooleanSelectorConfig(read_only=True))
            ams_fields = {
                vol.Optional(OPT_AUTO_REGISTER_UNAVAILABLE, default=register_value): ro,
                vol.Optional(OPT_SYNC_REMAINING_UNAVAILABLE, default=remaining_value): ro,
                vol.Optional(OPT_EMPTY_ON_RUNOUT_UNAVAILABLE, default=runout_value): ro,
                vol.Optional(OPT_EMPTY_PCT_UNAVAILABLE, default=pct_value): pct_selector(True),
            }
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
                    OPT_AUTO_DEDUP,
                    default=options.get(OPT_AUTO_DEDUP, DEFAULT_AUTO_DEDUP),
                ): bool,
                **ams_fields,
                vol.Required(
                    OPT_DEDUCT_USAGE,
                    default=options.get(OPT_DEDUCT_USAGE, DEFAULT_DEDUCT_USAGE),
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
        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            description_placeholders={"bambulab_url": BAMBULAB_REPO_URL},
        )
