"""URL validation boundary for remote research fetches."""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


class UnsafeFetchURL(ValueError):
    pass


def _blocked_ip(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    return bool(
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_multicast
        or address.is_unspecified
    )


def validate_fetch_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise UnsafeFetchURL("fetch URL must use https and include a hostname")
    if parsed.username or parsed.password:
        raise UnsafeFetchURL("fetch URL must not contain userinfo")

    hostname = parsed.hostname.rstrip(".").lower()
    if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(".local"):
        raise UnsafeFetchURL("private or local host is not allowed")

    try:
        if _blocked_ip(hostname):
            raise UnsafeFetchURL("private or special-use IP is not allowed")
        port = parsed.port or 443
        addresses = {
            info[4][0]
            for info in socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
        }
    except UnsafeFetchURL:
        raise
    except ValueError as exc:
        raise UnsafeFetchURL("fetch URL has an invalid hostname or port") from exc
    except OSError as exc:
        raise UnsafeFetchURL("hostname could not be resolved safely") from exc

    for address in addresses:
        if _blocked_ip(address):
            raise UnsafeFetchURL("hostname resolves to a private or special-use IP")
    return url
