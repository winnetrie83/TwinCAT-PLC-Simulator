"""Best-effort ADS symbol diagnostics; never writes unknown symbols."""
from __future__ import annotations


def is_missing_symbol(exc: Exception) -> bool:
    code = getattr(exc, 'err_code', None)
    if code is None:
        code = getattr(exc, 'error_code', None)
    return code == 1808 or ('1808' in str(exc) and 'symbol' in str(exc).lower())


def discover(conn, expected: dict[str, str], reader):
    """Return (availability, unknown, inventory_status), preserving hard errors.

    Absent expected signals do not fail connection, other ADS errors do.
    Inventory scanning is best effort; extra PLC variables are NOT written.
    """
    available = {}
    for key, name in expected.items():
        try:
            reader(key, name)
        except Exception as exc:
            if not is_missing_symbol(exc):
                raise RuntimeError(f'Kan PLC-symbool {name} niet controleren: {exc}') from exc
            available[key] = False
        else:
            available[key] = True
    extras = []
    inventory_status = 'available'
    try:
        symbols = conn.get_all_symbols()
        known_names = {n.lower() for n in expected.values()}
        # MAIN is the exercise namespace. Ignore library/system variables.
        extras = sorted({s.name for s in symbols if isinstance(getattr(s, 'name', None), str)
                         and s.name.lower().startswith('main.')
                         and s.name.lower() not in known_names}, key=str.lower)[:100]
    except Exception:
        inventory_status = 'unavailable'
    return available, extras, inventory_status
