"""Human-readable addresses for the supported module/script launcher."""
import ipaddress
import socket


def primary_ipv4():
    """Ask the local routing table for an IPv4; UDP connect sends no packet."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.settimeout(.1)
            probe.connect(("192.0.2.1", 9))
            address = probe.getsockname()[0]
        parsed = ipaddress.ip_address(address)
        return address if not (parsed.is_loopback or parsed.is_unspecified) else None
    except OSError:
        return None


def host_ipv4s():
    candidates = set()
    address = primary_ipv4()
    if address:
        candidates.add(address)
    try:
        candidates.update(item[4][0] for item in socket.getaddrinfo(
            socket.gethostname(), None, socket.AF_INET, socket.SOCK_DGRAM))
    except OSError:
        pass
    return sorted(address for address in candidates
                  if not (ipaddress.ip_address(address).is_loopback
                          or ipaddress.ip_address(address).is_unspecified))


def startup_summary(host, port, mode):
    addresses = host_ipv4s()
    display_host = f"[{host}]" if ":" in host else host
    if host == "0.0.0.0":
        base = f"http://127.0.0.1:{port}"
    elif host == "::":
        base = f"http://[::1]:{port}"
    else:
        base = f"http://{display_host}:{port}"
    lines = [f"ACField · {mode}", f"  Listen:     {display_host}:{port}",
             f"  Console:    {base}", f"  API docs:   {base}/docs",
             f"  Host IPv4:  {', '.join(addresses) or 'not detected'}"]
    if host == "0.0.0.0":
        lines.extend(f"  LAN / SDK:  http://{address}:{port}" for address in addresses)
    elif host in ("localhost", "::1") or host.startswith("127."):
        lines.append("  Local access only. For LAN, set ROBOT_HOST to 0.0.0.0 and restart.")
    lines.append("  Choose the address reachable from your client network (VPNs may add addresses).")
    return "\n".join(lines)
