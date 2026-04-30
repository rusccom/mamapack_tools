import json
import time

import requests


class BaselinkerClient:
    def __init__(self, token):
        self._token = token
        self._session = requests.Session()
        self._last_request_at = 0.0

    def wait_turn(self):
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < 0.65:
            time.sleep(0.65 - elapsed)

    def execute(self, method, parameters):
        self.wait_turn()
        payload = {
            "method": method,
            "parameters": json.dumps(parameters, ensure_ascii=False),
        }
        headers = {"X-BLToken": self._token}
        response = self._session.post("https://api.baselinker.com/connector.php", data=payload, headers=headers, timeout=60)
        self._last_request_at = time.monotonic()
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "ERROR":
            code = data.get("error_code", "UNKNOWN")
            message = data.get("error_message", "BaseLinker request failed")
            raise RuntimeError(f"{code}: {message}")
        return data
