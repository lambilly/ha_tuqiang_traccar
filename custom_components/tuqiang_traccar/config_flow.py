"""Config flow for Tuqiang to Traccar integration."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_PLATFORM,
    CONF_DEVICES,
    CONF_TRACCAR_URL,
    CONF_DEVICE_PREFIX,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    PLATFORM_TUQIANGNET,
    PLATFORM_TUQIANG123,
)

_LOGGER = logging.getLogger(__name__)


async def validate_credentials(platform: str, username: str, password: str, hass):
    """Validate credentials and return device dict."""
    if platform == PLATFORM_TUQIANGNET:
        from .tuqiangnet_fetcher import TuqiangNetFetcher
        fetcher = TuqiangNetFetcher(username, password)
    elif platform == PLATFORM_TUQIANG123:
        from .tuqiang123_fetcher import Tuqiang123Fetcher
        fetcher = Tuqiang123Fetcher(username, password)
    else:
        return None

    success = await hass.async_add_executor_job(fetcher.login)
    if not success:
        return None
    devices = await hass.async_add_executor_job(fetcher.get_device_list)
    return devices


class TuqiangTraccarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Tuqiang to Traccar."""

    VERSION = 1

    def __init__(self):
        self._platform = None
        self._username = None
        self._password = None
        self._devices = {}

    async def async_step_user(self, user_input=None):
        """Step 1: Select platform."""
        errors = {}
        if user_input is not None:
            self._platform = user_input[CONF_PLATFORM]
            return await self.async_step_auth()

        schema = vol.Schema({
            vol.Required(CONF_PLATFORM): vol.In({
                PLATFORM_TUQIANGNET: "途强物联 (tuqiang.net)",
                PLATFORM_TUQIANG123: "途强在线 (tuqiang123.com)",
            })
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_auth(self, user_input=None):
        """Step 2: Enter username and password."""
        errors = {}
        if user_input is not None:
            username = user_input["username"].strip()
            password = user_input["password"]
            devices = await validate_credentials(self._platform, username, password, self.hass)
            if devices is not None:
                if not devices:
                    errors["base"] = "no_devices"
                else:
                    self._username = username
                    self._password = password
                    self._devices = devices
                    return await self.async_step_device_select()
            else:
                errors["base"] = "invalid_auth"

        schema = vol.Schema({
            vol.Required("username"): str,
            vol.Required("password"): str,
        })
        return self.async_show_form(step_id="auth", data_schema=schema, errors=errors)

    async def async_step_device_select(self, user_input=None):
        """Step 3: Select devices to forward."""
        errors = {}
        if user_input is not None:
            selected = user_input["devices"]
            if not selected:
                errors["devices"] = "no_device_selected"
            else:
                return await self.async_step_traccar_config(data={"devices": selected})

        options = {imei: f"{imei} ({name})" for imei, name in self._devices.items()}
        schema = vol.Schema({vol.Required("devices"): cv.multi_select(options)})
        return self.async_show_form(step_id="device_select", data_schema=schema, errors=errors)

    async def async_step_traccar_config(self, user_input=None, data=None):
        """Step 4: Traccar server config."""
        if data is not None:
            # Called from device_select
            self._selected_devices = data["devices"]
            errors = {}
        else:
            errors = {}
            if user_input is not None:
                url = user_input[CONF_TRACCAR_URL].strip()
                if not url.startswith(("http://", "https://")):
                    errors[CONF_TRACCAR_URL] = "invalid_url"
                else:
                    config_data = {
                        CONF_PLATFORM: self._platform,
                        "username": self._username,
                        "password": self._password,
                        CONF_DEVICES: self._selected_devices,
                        CONF_TRACCAR_URL: url.rstrip("/"),
                        CONF_DEVICE_PREFIX: user_input.get(CONF_DEVICE_PREFIX, ""),
                        CONF_UPDATE_INTERVAL: user_input[CONF_UPDATE_INTERVAL],
                    }
                    unique_id = f"{self._platform}_{self._username}"
                    await self.async_set_unique_id(unique_id)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"途强转Traccar ({self._platform} - {self._username})",
                        data=config_data
                    )

        schema = vol.Schema({
            vol.Required(CONF_TRACCAR_URL, default=""): str,
            vol.Optional(CONF_DEVICE_PREFIX, default=""): str,
            vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
        })
        return self.async_show_form(
            step_id="traccar_config",
            data_schema=schema,
            errors=errors,
            description_placeholders={"port_info": "客户端端口通常为 5055，Web 管理端口为 8082。请填写客户端端口地址。"}
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return TuqiangTraccarOptionsFlow(config_entry)


class TuqiangTraccarOptionsFlow(config_entries.OptionsFlow):
    """Options flow."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        data = self.config_entry.data

        schema = vol.Schema({
            vol.Required(CONF_TRACCAR_URL, default=options.get(CONF_TRACCAR_URL, data.get(CONF_TRACCAR_URL, ""))): str,
            vol.Optional(CONF_DEVICE_PREFIX, default=options.get(CONF_DEVICE_PREFIX, data.get(CONF_DEVICE_PREFIX, ""))): str,
            vol.Optional(CONF_UPDATE_INTERVAL, default=options.get(CONF_UPDATE_INTERVAL, data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
        })
        return self.async_show_form(step_id="init", data_schema=schema)