"""Tuqiang123 (www.tuqiang123.com) data fetcher."""
import logging
import requests
from datetime import datetime
import time

_LOGGER = logging.getLogger(__name__)

TUQIANG123_API_HOST = "https://www.tuqiang123.com"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"

class Tuqiang123Fetcher:
    """Fetch device positions from Tuqiang123 platform."""

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.userid = None
        self.usertype = None

    @staticmethod
    def _encode(code: str) -> str:
        return "|".join(str(ord(c)) for c in code)

    def login(self) -> bool:
        """Login and retrieve userid/usertype."""
        url = f"{TUQIANG123_API_HOST}/api/regdc"
        data = {
            "ver": "1",
            "method": "login",
            "account": self.username,
            "password": self._encode(self.password),
            "language": "zh"
        }
        try:
            resp = self.session.post(url, data=data)
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") != 0:
                _LOGGER.error("Tuqiang123 login failed: %s", result.get("msg"))
                return False
            url2 = f"{TUQIANG123_API_HOST}/customer/getProviderList"
            resp2 = self.session.post(url2, data=None)
            resp2.raise_for_status()
            data2 = resp2.json()
            self.userid = data2["data"]["user"]["userId"]
            self.usertype = data2["data"]["user"]["type"]
            _LOGGER.info("Tuqiang123 login successful, userid=%s", self.userid)
            return True
        except Exception as e:
            _LOGGER.error("Tuqiang123 login error: %s", e)
            return False

    def get_device_list(self) -> dict:
        """Return dict of {imei: device_name}."""
        if not self.userid:
            if not self.login():
                return {}
        url = f"{TUQIANG123_API_HOST}/device/list"
        data = {
            "dateType": "activation",
            "equipment.userId": self.userid
        }
        try:
            resp = self.session.post(url, data=data)
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") != 0:
                _LOGGER.error("Failed to get device list: %s", result.get("msg"))
                return {}
            devices = {}
            for item in result["data"]["result"]:
                imei = item["imei"]
                name = item.get("carNumber") or item.get("deviceModel") or imei
                devices[imei] = name
            return devices
        except Exception as e:
            _LOGGER.error("Error fetching device list: %s", e)
            return {}

    def get_device_position(self, imei: str) -> dict:
        """Fetch current position data."""
        if not self.userid:
            if not self.login():
                return None
        url = f"{TUQIANG123_API_HOST}/console/refresh"
        data = {
            "choiceUserId": self.userid,
            "normalImeis": str(imei),
            "userType": self.usertype,
            "followImeis": "",
            "userId": self.userid,
            "stock": "2"
        }
        try:
            resp = self.session.post(url, data=data)
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") != 0:
                _LOGGER.error("Get device position failed: %s", result.get("msg"))
                return None
            device_data = result["data"]["normalList"][0]
            ts = time.time()
            if device_data.get("hbTime"):
                try:
                    ts = datetime.strptime(device_data["hbTime"], "%Y-%m-%d %H:%M:%S").timestamp()
                except ValueError:
                    pass
            speed = device_data.get("speed")
            speed = float(speed) if speed and speed != "" else 0.0
            return {
                "imei": imei,
                "latitude": float(device_data["lat"]),
                "longitude": float(device_data["lng"]),
                "speed": speed,
                "course": float(device_data.get("direction", 0)),
                "timestamp": ts,
                "acc": device_data.get("acc") == "1",
                "status": device_data.get("status"),
                "raw": device_data,
            }
        except Exception as e:
            _LOGGER.error("Error fetching position for %s: %s", imei, e)
            return None