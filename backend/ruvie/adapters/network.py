"""Admin-owned SOCKS5 configuration and checked, DNS-pinned proxy endpoints."""
import ipaddress
import socket
import httpcore
import httpx
from urllib.parse import urlsplit

class InvalidNetworkConfiguration(ValueError):
    def __init__(self):
        super().__init__('invalid_network_configuration')

class ProxyUnavailableError(httpx.ProxyError):
    def __init__(self):
        super().__init__('proxy_unavailable')


class ProxyNetworkBackend(httpcore.SyncBackend):
    """Classify TCP failures while dialing the proxy; leave provider TLS errors intact."""
    def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        try:
            return super().connect_tcp(host=host, port=port, timeout=timeout,
                                       local_address=local_address, socket_options=socket_options)
        except (httpcore.ConnectError, httpcore.ConnectTimeout):
            raise ProxyUnavailableError() from None

class NetworkConfigurationPendingError(RuntimeError):
    def __init__(self):
        super().__init__('network_configuration_pending')

# Never admit non-unicast, link-local, metadata or broadcast destinations.
_METADATA = {'100.100.100.200', '168.63.129.16', 'fd00:ec2::254', '169.254.169.254'}

def _safe_address(value: str) -> str:
    try:
        address = ipaddress.ip_address(value)
        address = getattr(address, 'ipv4_mapped', None) or address
    except ValueError:
        raise InvalidNetworkConfiguration() from None
    forbidden = (address.is_unspecified or address.is_multicast or address.is_link_local
                 or (address.is_reserved and not address.is_loopback)
                 or str(address) in _METADATA)
    if forbidden or not (address.is_global or address.is_private or address.is_loopback):
        raise InvalidNetworkConfiguration()
    return str(address)

def normalize_proxy_url(value: str) -> str:
    """Syntax-only validation; DNS is rechecked/pinned at each connection."""
    if not isinstance(value, str) or not value or len(value) > 2048 or value != value.strip():
        raise InvalidNetworkConfiguration()
    if any(ord(ch) < 33 or ord(ch) == 127 or ch == '\\' for ch in value):
        raise InvalidNetworkConfiguration()
    try:
        url = urlsplit(value)
        if (url.scheme.lower() != 'socks5' or not url.hostname or not url.port
                or url.username is not None or url.password is not None
                or '@' in url.netloc or url.query or url.fragment
                or url.path not in ('', '/') or '?' in value or '#' in value):
            raise InvalidNetworkConfiguration()
        host = url.hostname.lower().rstrip('.')
        if not host or '%' in host:
            raise InvalidNetworkConfiguration()
        try:
            host = _safe_address(host)
        except InvalidNetworkConfiguration:
            # A literal IP must never escape the IP guard by posing as DNS.
            if all(c in '0123456789.:' for c in host):
                raise
            if not all(part and len(part) <= 63 and
                       part[0].isalnum() and part[-1].isalnum() and
                       all(ch.isascii() and (ch.isalnum() or ch == '-') for ch in part)
                       for part in host.split('.')):
                raise InvalidNetworkConfiguration()
        bracketed = f'[{host}]' if ':' in host else host
        return f'socks5://{bracketed}:{url.port}'
    except (ValueError, TypeError):
        raise InvalidNetworkConfiguration() from None

def pinned_proxy_url(url: str | None) -> str | None:
    """Reject any unsafe DNS answer; connect to a vetted numeric address only."""
    if url is None:
        return None
    normalized = normalize_proxy_url(url)
    parts = urlsplit(normalized)
    try:
        answers = socket.getaddrinfo(parts.hostname, parts.port, type=socket.SOCK_STREAM)
        if not answers:
            raise ProxyUnavailableError()
        addresses = [_safe_address(answer[4][0]) for answer in answers]
    except InvalidNetworkConfiguration:
        raise
    except OSError:
        raise ProxyUnavailableError() from None
    address = addresses[0]
    return f'socks5://{("[" + address + "]") if ":" in address else address}:{parts.port}'

def effective_proxy(mode: str | None, url: str | None) -> str | None:
    if mode is None:
        raise NetworkConfigurationPendingError()
    if mode == 'direct' and url is None:
        return None
    if mode == 'proxy' and url is not None:
        return pinned_proxy_url(url)
    raise InvalidNetworkConfiguration()
