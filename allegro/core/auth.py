import base64
import time
from dataclasses import dataclass

import requests

from .credentials import AllegroCredentials


AUTH_URL = "https://allegro.pl/auth/oauth/token"
DEVICE_URL = "https://allegro.pl/auth/oauth/device"


@dataclass(frozen=True)
class DeviceGrant:
    device_code: str
    user_code: str
    url: str
    expires_in: int
    interval: int


def request_device_grant(credentials: AllegroCredentials) -> DeviceGrant:
    body = post_auth(DEVICE_URL, credentials, {"client_id": credentials.client_id})
    return DeviceGrant(
        device_code=body["device_code"],
        user_code=body["user_code"],
        url=body.get("verification_uri_complete") or body["verification_uri"],
        expires_in=int(body["expires_in"]),
        interval=int(body.get("interval", 5)),
    )


def poll_device_token(credentials: AllegroCredentials, grant: DeviceGrant) -> dict:
    deadline = time.monotonic() + grant.expires_in
    while time.monotonic() < deadline:
        body = token_attempt(credentials, grant.device_code)
        if "access_token" in body:
            return body
        if body.get("error") != "authorization_pending":
            raise RuntimeError(body.get("error_description", body.get("error")))
        time.sleep(grant.interval)
    raise RuntimeError("Allegro device authorization expired.")


def refresh_token(credentials: AllegroCredentials, token: dict) -> dict:
    refresh = token.get("refresh_token", "")
    if not refresh:
        return {}
    return post_auth(AUTH_URL, credentials, token_params("refresh_token", refresh))


def token_attempt(credentials: AllegroCredentials, device_code: str) -> dict:
    return post_auth(AUTH_URL, credentials, token_params("urn:ietf:params:oauth:grant-type:device_code", device_code))


def token_params(grant_type: str, code: str) -> dict[str, str]:
    if grant_type == "refresh_token":
        return {"grant_type": grant_type, "refresh_token": code}
    return {"grant_type": grant_type, "device_code": code}


def post_auth(url: str, credentials: AllegroCredentials, data: dict) -> dict:
    response = requests.post(url, headers=auth_headers(credentials), data=data, timeout=60)
    body = response.json()
    if response.status_code >= 400 and body.get("error") != "authorization_pending":
        raise RuntimeError(body.get("error_description", body.get("error")))
    return body


def auth_headers(credentials: AllegroCredentials) -> dict[str, str]:
    raw = f"{credentials.client_id}:{credentials.client_secret}".encode()
    return {
        "Authorization": "Basic " + base64.b64encode(raw).decode(),
        "Content-Type": "application/x-www-form-urlencoded",
    }
