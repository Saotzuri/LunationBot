import requests
import logging
from config import WOWAUDIT_API_BASE, WOWAUDIT_TOKEN

logger = logging.getLogger("lunation-bot")

class WoWAuditAPI:
    def __init__(self, token: str = None):
        self.token = token or WOWAUDIT_TOKEN
        self.headers = {"Authorization": self.token} if self.token else {}

    @property
    def is_configured(self) -> bool:
        return bool(self.token)

    def _request(self, method: str, endpoint: str, **kwargs):
        if not self.token:
            raise Exception("WoWAudit Token nicht konfiguriert")

        url = f"{WOWAUDIT_API_BASE}{endpoint}"
        resp = requests.request(method, url, headers=self.headers, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def get_raids(self):
        return self._request("GET", "/raids")

    def get_raid(self, raid_id: int):
        return self._request("GET", f"/raids/{raid_id}")

    def get_characters(self):
        return self._request("GET", "/characters")

    def get_attendance(self):
        return self._request("GET", "/attendance")

    def get_period(self):
        return self._request("GET", "/period")

    def get_team(self):
        return self._request("GET", "/team")

    def get_wishlists(self):
        return self._request("GET", "/wishlists")

    def get_wishlist(self, char_id: int):
        return self._request("GET", f"/wishlists/{char_id}")

    def get_historical_data(self):
        return self._request("GET", "/historical_data")

    def get_loot_history(self, season_id: int):
        return self._request("GET", f"/loot_history/{season_id}")

wowaudit_api = WoWAuditAPI() if WOWAUDIT_TOKEN else None