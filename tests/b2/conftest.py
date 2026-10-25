"""Test setup for the B2 data scripts and engine/privacy.py.

Lives at: urbanpulse/tests/b2/conftest.py

If the real `h3` package is installed it is used. If not, a tiny stand-in with the same call
signatures (lat/lng square grid, parent = 2x2 block) is injected so the pure logic can still be
tested. Tests that need the real H3 geometry are skipped in that case: see REAL_H3.
"""
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "data" / "download_scripts"))
try:
    import h3  # noqa: F401
    REAL_H3 = hasattr(h3, "geo_to_cells")
except ImportError:
    REAL_H3 = False

if not REAL_H3:
    STEP = 0.002

    def latlng_to_cell(lat, lng, res):
        ix, iy = int(lat // STEP), int(lng // STEP)
        if res == 9:
            return f"9:{ix}:{iy}"
        return f"8:{ix // 2}:{iy // 2}"

    def _parse(c):
        r, a, b = c.split(":")
        return int(r), int(a), int(b)

    def cell_to_latlng(c):
        r, a, b = _parse(c)
        s = STEP * (2 if r == 8 else 1) * 1.0
        return ((a + 0.5) * s, (b + 0.5) * s)

    def cell_to_parent(c, res):
        r, a, b = _parse(c)
        return c if r == res else f"{res}:{a // 2}:{b // 2}"

    def get_resolution(c):
        return _parse(c)[0]

    def cell_to_boundary(c):
        lat, lng = cell_to_latlng(c)
        d = STEP / 2
        return [(lat - d, lng - d), (lat - d, lng + d), (lat + d, lng + d), (lat + d, lng - d)]

    stub = types.ModuleType("h3")
    for f in (latlng_to_cell, cell_to_latlng, cell_to_parent, get_resolution, cell_to_boundary):
        setattr(stub, f.__name__, f)
    sys.modules["h3"] = stub
    REAL_H3 = False


def pytest_report_header(config):
    return "h3: REAL package" if REAL_H3 else "h3: STAND-IN (real h3 not installed; geometry tests skipped)"