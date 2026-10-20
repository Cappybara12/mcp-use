import ipaddress
import socket


def resolve_ipv4_host(host_only: str, label: str) -> str:
    if host_only == "localhost":
        return "127.0.0.1"

    host = host_only
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]

    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        if literal.version != 4:
            raise ValueError(_ipv4_error(label))
        return str(literal)

    try:
        addresses = socket.getaddrinfo(host, None)
    except (socket.gaierror, UnicodeError):
        raise ValueError(f"Cannot resolve {_inline_label(label)} hostname '{host_only}'.") from None

    for family, _, _, _, sockaddr in addresses:
        if family == socket.AF_INET:
            return sockaddr[0]

    raise ValueError(_ipv4_error(label))


def _ipv4_error(label: str) -> str:
    return f"{label} hostname must resolve to an IPv4 address."


def _inline_label(label: str) -> str:
    return label if label.upper() == label else label[0].lower() + label[1:]
