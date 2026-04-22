"""Constants for Tuqiang to Traccar integration."""
DOMAIN = "tuqiang_traccar"

CONF_PLATFORM = "platform"           # 平台选择
CONF_DEVICES = "devices"
CONF_TRACCAR_URL = "traccar_url"
CONF_DEVICE_PREFIX = "device_prefix"
CONF_UPDATE_INTERVAL = "update_interval"

DEFAULT_UPDATE_INTERVAL = 30

PLATFORM_TUQIANGNET = "tuqiang.net"
PLATFORM_TUQIANG123 = "tuqiang123.com"

PLATFORMS = [
    PLATFORM_TUQIANGNET,
    PLATFORM_TUQIANG123,
]