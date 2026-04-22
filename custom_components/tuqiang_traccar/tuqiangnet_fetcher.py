"""TuqiangNet (www.tuqiang.net) data fetcher."""
import logging
import requests
from datetime import datetime
import time

_LOGGER = logging.getLogger(__name__)

TUQIANGNET_API_HOST = "https://www.tuqiang.net"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"

class TuqiangNetFetcher:
    """Fetch device positions from TuqiangNet platform."""

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.token = None

    def login(self) -> bool:
        """Login to TuqiangNet and get token."""
        url = f"{TUQIANGNET_API_HOST}/loginVerification"
        data = {
            "timeZone": "28800",
            "token": "",
            "userName": self.username,
            "password": self.password,
            "lang": "zh"
        }
        try:
            resp = self.session.post(url, data=data)
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") == 0:
                self.token = result["data"]["token"]
                _LOGGER.info("TuqiangNet login successful")
                return True
            else:
                _LOGGER.error("TuqiangNet login failed: %s", result.get("msg"))
                return False
        except Exception as e:
            _LOGGER.error("TuqiangNet login error: %s", e)
            return False

    def get_device_list(self) -> dict:
        """Return dict of {imei: device_name} for all devices under account."""
        if not self.token:
            if not self.login():
                return {}
        url = f"{TUQIANGNET_API_HOST}/device/getDeviceList"
        data = {"token": self.token}
        try:
            resp = self.session.post(url, data=data)
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") != 0:
                _LOGGER.error("Failed to get device list: %s", result.get("msg"))
                return {}
            devices = {}
            for item in result["data"]:
                imei = item["imei"]
                name = item.get("deviceName") or item.get("carNumber") or imei
                devices[imei] = name
            return devices
        except Exception as e:
            _LOGGER.error("Error fetching device list: %s", e)
            return {}

    def get_device_position(self, imei: str) -> dict:
        """Fetch current position data for a single device."""
        if not self.token:
            if not self.login():
                return None
        url = f"{TUQIANGNET_API_HOST}/redis/getGps"
        data = {"imei": imei, "token": self.token}
        try:
            resp = self.session.post(url, data=data)
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") != 0:
                _LOGGER.error("Get device position failed: %s", result.get("msg"))
                return None
            gps = result["data"]
            # Parse timestamp
            ts = time.time()
            if gps.get("hbTime"):
                try:
                    ts = datetime.strptime(gps["hbTime"], "%Y-%m-%d %H:%M:%S").timestamp()
                except ValueError:
                    pass
            speed = float(gps.get("speed", 0))
            return {
                "imei": imei,
                "latitude": float(gps["latitude"]),
                "longitude": float(gps["longitude"]),
                "speed": speed,
                "course": float(gps.get("direction", 0)),
                "timestamp": ts,
                "acc": gps.get("acc") == "1",
                "status": gps.get("status"),
                "raw": gps,
            }
        except Exception as e:
            _LOGGER.error("Error fetching position for %s: %s", imei, e)
            return None