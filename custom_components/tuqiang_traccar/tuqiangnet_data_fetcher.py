"""途强物联数据获取器（异步版本）"""
import logging
import aiohttp
from datetime import datetime

_LOGGER = logging.getLogger(__name__)

TUQIANGNET_API_HOST = "http://www.tuqiang.net"

class TuqiangNetAuth:
    """处理途强物联的登录认证"""

    def __init__(self, session: aiohttp.ClientSession):
        """初始化，传入 aiohttp session"""
        self.session = session
        self.token = None

    async def login(self, username: str, password: str) -> bool:
        """登录途强物联平台，获取 token"""
        url = f"{TUQIANGNET_API_HOST}/loginVerification"
        data = {
            "timeZone": "28800",
            "token": "",
            "userName": username,
            "password": password,
            "lang": "zh"
        }
        try:
            async with self.session.post(url, data=data) as resp:
                result = await resp.json()
                _LOGGER.debug("途强登录响应: %s", result)
                if result.get("code") == 0:
                    self.token = result["data"]["token"]
                    return True
                else:
                    _LOGGER.error("途强登录失败: %s", result.get("msg", "未知错误"))
        except Exception as e:
            _LOGGER.error("途强登录异常: %s", e)
        return False

    async def get_device_list(self) -> dict:
        """获取账号下的设备列表，返回 {imei: device_name}"""
        if not self.token:
            _LOGGER.error("未登录，无法获取设备列表")
            return {}
        url = f"{TUQIANGNET_API_HOST}/device/getDeviceList"
        data = {"token": self.token}
        try:
            async with self.session.post(url, data=data) as resp:
                result = await resp.json()
                _LOGGER.debug("设备列表响应: %s", result)
                if result.get("code") == 0:
                    devices = {}
                    for dev in result["data"]:
                        imei = dev["imei"]
                        # 设备名称可能不存在，回退到 IMEI
                        name = dev.get("deviceName") or dev.get("carNumber") or imei
                        devices[imei] = name
                    return devices
                else:
                    _LOGGER.error("获取设备列表失败: %s", result.get("msg", "未知错误"))
        except Exception as e:
            _LOGGER.error("获取设备列表异常: %s", e)
        return {}


class TuqiangNetFetcher(TuqiangNetAuth):
    """途强物联数据获取器（含登录和位置获取）"""

    def __init__(self, session: aiohttp.ClientSession, username: str, password: str):
        """初始化并保存账号信息"""
        super().__init__(session)
        self.username = username
        self.password = password
        self._login_flag = False  # 标记是否已登录成功

    async def ensure_login(self) -> bool:
        """确保登录有效（若未登录或 token 失效则重新登录）"""
        if not self._login_flag or not self.token:
            self._login_flag = await self.login(self.username, self.password)
        return self._login_flag

    async def get_device_position(self, imei: str) -> dict:
        """获取指定设备的最新位置信息"""
        if not await self.ensure_login():
            _LOGGER.error("登录失败，无法获取设备位置")
            return None

        url = f"{TUQIANGNET_API_HOST}/redis/getGps"
        data = {"imei": imei, "token": self.token}
        try:
            async with self.session.post(url, data=data) as resp:
                result = await resp.json()
                _LOGGER.debug("设备位置原始响应: %s", result)
                if result.get("code") == 0:
                    gps = result["data"]
                    # 解析时间戳
                    hb_time = gps.get("hbTime")
                    if hb_time:
                        try:
                            ts = datetime.strptime(hb_time, "%Y-%m-%d %H:%M:%S").timestamp()
                        except ValueError:
                            ts = datetime.now().timestamp()
                    else:
                        ts = datetime.now().timestamp()

                    # 速度单位：途强返回 km/h，Traccar OsmAnd 协议默认使用节（knots）
                    # 1 km/h = 0.539957 knots，但通常我们直接按 km/h 上报，由 Traccar 转换
                    # 若希望 Traccar 显示正确 km/h，需在 Traccar 中设置速度单位或这里转换。
                    speed_kmh = float(gps.get("speed", 0))
                    # 转换为节（如需）
                    # speed_knots = speed_kmh * 0.539957

                    return {
                        "latitude": float(gps["latitude"]),
                        "longitude": float(gps["longitude"]),
                        "speed": speed_kmh,          # km/h
                        "course": float(gps.get("direction", 0)),
                        "altitude": None,            # 途强物联通常不提供海拔
                        "timestamp": ts,
                        "acc": gps.get("acc") == "1",
                        "status": gps.get("status"),  # 在线状态 2/3 为在线
                        "raw": gps,
                    }
                else:
                    _LOGGER.warning("获取设备 %s 位置失败: %s", imei, result.get("msg", "未知错误"))
        except Exception as e:
            _LOGGER.error("获取设备 %s 位置异常: %s", imei, e)
        return None

    async def get_device_info(self, imei: str) -> dict:
        """获取设备详细信息（如型号、到期时间等）"""
        if not await self.ensure_login():
            return None
        url = f"{TUQIANGNET_API_HOST}/device/getDeviceList"
        data = {"imeis": imei, "token": self.token}
        try:
            async with self.session.post(url, data=data) as resp:
                result = await resp.json()
                if result.get("code") == 0 and result["data"]:
                    return result["data"][0]
        except Exception as e:
            _LOGGER.error("获取设备信息异常: %s", e)
        return None