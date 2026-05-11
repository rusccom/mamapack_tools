from urllib.parse import urlencode

import requests


API_URL = "https://api.allegro.pl"


class AllegroClient:
    def __init__(self, token: str):
        self.token = token
        self.session = requests.Session()

    def get(self, path: str, params: dict | None = None) -> dict | list:
        url = API_URL + path
        if params:
            url = f"{url}?{urlencode(params, doseq=True)}"
        response = self.session.get(url, headers=self.headers(), timeout=60)
        if response.status_code >= 400:
            raise RuntimeError(response.text)
        return response.json()

    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.allegro.public.v1+json",
            "Content-Type": "application/vnd.allegro.public.v1+json",
            "Accept-Language": "pl-PL",
        }
