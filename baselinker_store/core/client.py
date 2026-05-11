import json
import time

import requests


API_URL = "https://api.baselinker.com/connector.php"
REQUEST_INTERVAL = 0.65


class BaselinkerClient:
    def __init__(self, token):
        self._token = token
        self._session = requests.Session()
        self._last_request_at = 0.0

    def wait_turn(self):
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < REQUEST_INTERVAL:
            time.sleep(REQUEST_INTERVAL - elapsed)

    def execute(self, method, parameters=None):
        self.wait_turn()
        response = self._post(method, parameters or {})
        self._last_request_at = time.monotonic()
        return self._result(response)

    def _post(self, method, parameters):
        return self._session.post(
            API_URL,
            data=self._payload(method, parameters),
            headers={"X-BLToken": self._token},
            timeout=60,
        )

    def _payload(self, method, parameters):
        return {
            "method": method,
            "parameters": json.dumps(parameters, ensure_ascii=False),
        }

    def _result(self, response):
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "ERROR":
            code = data.get("error_code", "UNKNOWN")
            message = data.get("error_message", "BaseLinker request failed")
            raise RuntimeError(f"{code}: {message}")
        return data
