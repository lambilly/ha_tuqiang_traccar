"""Tuqiang to Traccar integration."""
import logging
import asyncio
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN, CONF_DEVICES, CONF_TRACCAR_URL, CONF_DEVICE_PREFIX, CONF_UPDATE_INTERVAL
from .tuqiangnet_data_fetcher import TuqiangNetFetcher

_LOGGER = logging.getLogger(__name__)

PLATFORMS = []  # 不创建实体

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """设置集成入口"""
    config = entry.data
    username = config["username"]
    password = config["password"]
    selected_devices = config["devices"]
    traccar_url = config[CONF_TRACCAR_URL].rstrip("/")
    device_prefix = config.get(CONF_DEVICE_PREFIX, "")
    update_interval = config.get(CONF_UPDATE_INTERVAL, 30)

    session = async_get_clientsession(hass)
    fetcher = TuqiangNetFetcher(session, username, password)

    # 存储数据供卸载使用
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "fetcher": fetcher,
        "remove_timer": None,
    }

    async def fetch_and_forward(*_):
        """获取位置并转发到 Traccar"""
        if not await fetcher.ensure_login():
            _LOGGER.error("途强登录失效，请检查账号密码")
            return

        for imei in selected_devices:
            try:
                data = await fetcher.get_device_position(imei)
                if not data:
                    continue

                # 构造 Traccar 设备标识符
                device_id = f"{device_prefix}{imei}" if device_prefix else imei

                # OsmAnd 协议参数
                params = {
                    "id": device_id,
                    "lat": data["latitude"],
                    "lon": data["longitude"],
                    "timestamp": int(data["timestamp"]),
                }
                if data.get("speed") is not None:
                    # 途强速度单位 km/h，Traccar OsmAnd 默认使用节，这里转换一下
                    speed_knots = data["speed"] * 0.539957
                    params["speed"] = speed_knots
                if data.get("course"):
                    params["bearing"] = data["course"]
                if data.get("altitude"):
                    params["altitude"] = data["altitude"]

                # 发送 GET 请求到 Traccar 的 OsmAnd 端点
                async with session.get(f"{traccar_url}/", params=params) as resp:
                    if resp.status == 200:
                        _LOGGER.debug("设备 %s 位置上报成功", imei)
                    else:
                        _LOGGER.warning("设备 %s 上报失败，HTTP %s", imei, resp.status)

            except Exception as e:
                _LOGGER.error("处理设备 %s 时出错: %s", imei, e)

    # 立即执行一次
    await fetch_and_forward()

    # 定时任务
    interval = timedelta(seconds=update_interval)
    remove_timer = async_track_time_interval(hass, fetch_and_forward, interval)
    hass.data[DOMAIN][entry.entry_id]["remove_timer"] = remove_timer

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """卸载集成"""
    data = hass.data[DOMAIN].pop(entry.entry_id)
    if remove_timer := data.get("remove_timer"):
        remove_timer()
    return True