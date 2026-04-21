"""Config flow for Tuqiang to Traccar integration."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_DEVICES,
    CONF_TRACCAR_URL,
    CONF_DEVICE_PREFIX,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
)
from .tuqiangnet_data_fetcher import TuqiangNetAuth

_LOGGER = logging.getLogger(__name__)


async def validate_tuqiang_credentials(username: str, password: str, session):
    """验证途强账号并返回设备列表 {imei: name}."""
    auth = TuqiangNetAuth(session)
    if await auth.login(username, password):
        devices = await auth.get_device_list()
        return devices
    return None


class TuqiangTraccarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tuqiang to Traccar."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._tuqiang_data = {}
        self._devices = {}

    async def async_step_user(self, user_input=None):
        """Step 1: Input Tuqiang credentials."""
        errors = {}
        if user_input is not None:
            username = user_input["username"].strip()
            password = user_input["password"]
            session = async_get_clientsession(self.hass)

            devices = await validate_tuqiang_credentials(username, password, session)
            if devices is not None:
                if not devices:
                    errors["base"] = "no_devices"
                else:
                    self._tuqiang_data = {"username": username, "password": password}
                    self._devices = devices
                    return await self.async_step_device_select()
            else:
                errors["base"] = "invalid_auth"

        schema = vol.Schema(
            {
                vol.Required("username"): str,
                vol.Required("password"): str,
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )

    async def async_step_device_select(self, user_input=None):
        """Step 2: Select devices to forward."""
        errors = {}
        if user_input is not None:
            selected_devices = user_input["devices"]
            if not selected_devices:
                errors["devices"] = "no_device_selected"
            else:
                self._tuqiang_data["devices"] = selected_devices
                return await self.async_step_traccar_config()

        # Build options for multi-select
        device_options = {
            imei: f"{imei} ({name})" for imei, name in self._devices.items()
        }
        schema = vol.Schema(
            {
                vol.Required("devices"): cv.multi_select(device_options),
            }
        )
        return self.async_show_form(
            step_id="device_select", data_schema=schema, errors=errors
        )

    async def async_step_traccar_config(self, user_input=None):
        """Step 3: Configure Traccar server."""
        errors = {}
        if user_input is not None:
            url = user_input[CONF_TRACCAR_URL].strip()
            # Basic URL validation
            if not url.startswith(("http://", "https://")):
                errors[CONF_TRACCAR_URL] = "invalid_url"
            else:
                config_data = {
                    **self._tuqiang_data,
                    CONF_TRACCAR_URL: url.rstrip("/"),
                    CONF_DEVICE_PREFIX: user_input.get(CONF_DEVICE_PREFIX, ""),
                    CONF_UPDATE_INTERVAL: user_input[CONF_UPDATE_INTERVAL],
                }
                # Set unique ID to prevent duplicate entries
                await self.async_set_unique_id(
                    f"tuqiang_traccar_{self._tuqiang_data['username']}"
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"途强转Traccar ({self._tuqiang_data['username']})",
                    data=config_data,
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_TRACCAR_URL, default=""): str,
                vol.Optional(CONF_DEVICE_PREFIX, default=""): str,
                vol.Optional(
                    CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL
                ): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
            }
        )
        return self.async_show_form(
            step_id="traccar_config",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "port_info": "Traccar 客户端接入端口通常为 5055，Web 管理端口为 8082。请填写客户端端口地址。"
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return TuqiangTraccarOptionsFlow(config_entry)


class TuqiangTraccarOptionsFlow(config_entries.OptionsFlow):
    """Options flow for Tuqiang to Traccar."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Load current options or fallback to config data
        options = self.config_entry.options
        data = self.config_entry.data

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_TRACCAR_URL,
                    default=options.get(CONF_TRACCAR_URL, data.get(CONF_TRACCAR_URL, "")),
                ): str,
                vol.Optional(
                    CONF_DEVICE_PREFIX,
                    default=options.get(CONF_DEVICE_PREFIX, data.get(CONF_DEVICE_PREFIX, "")),
                ): str,
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=options.get(
                        CONF_UPDATE_INTERVAL,
                        data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)