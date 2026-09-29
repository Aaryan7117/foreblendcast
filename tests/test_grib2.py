"""GRIB2 ingestion end to end: real GRIB2 files are written with ecCodes, then read through
the adapter, the registry, the quality gate and the forecast cycle.

The files are synthetic (copies of archive fields, or constructed fields). These tests
prove the code path from a GRIB2 file to the blend, not skill on operational data.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

eccodes = pytest.importorskip("eccodes")
pytest.importorskip("cfgrib")

from canonical import accumulation as acc  # noqa: E402
from canonical.grid import LAT, LON  # noqa: E402
from ingestion import grib2, registry  # noqa: E402

INIT = pd.Timestamp("2022-06-14")
# a grid that is larger than the India box, north to south, as operational files are
SRC_LAT = np.arange(42.0, 2.9, -0.25)
SRC_LON = np.arange(60.0, 105.1, 0.25)


def write_grib(path: Path, short_name: str, values: np.ndarray, step_h: int,
               lat=SRC_LAT, lon=SRC_LON) -> None:
    gid = eccodes.codes_grib_new_from_samples("regular_ll_sfc_grib2")
    try:
        for key, value in {
            "Ni": len(lon), "Nj": len(lat),
            "latitudeOfFirstGridPointInDegrees": float(lat[0]),
            "latitudeOfLastGridPointInDegrees": float(lat[-1]),
            "longitudeOfFirstGridPointInDegrees": float(lon[0]),
            "longitudeOfLastGridPointInDegrees": float(lon[-1]),
            "iDirectionIncrementInDegrees": 0.25, "jDirectionIncrementInDegrees": 0.25,
            "dataDate": int(INIT.strftime("%Y%m%d")), "dataTime": 0,
        }.items():
            eccodes.codes_set(gid, key, value)
        eccodes.codes_set(gid, "shortName", short_name)
        eccodes.codes_set(gid, "stepUnits", 1)
        if short_name == "tp":
            eccodes.codes_set(gid, "stepRange", f"0-{step_h}")
        else:
            eccodes.codes_set(gid, "step", step_h)
        eccodes.codes_set(gid, "bitsPerValue", 24)
        eccodes.codes_set_values(gid, np.asarray(values, dtype=np.float64).ravel())
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            eccodes.codes_write(gid, f)
    finally:
        eccodes.codes_release(gid)


def on_source_grid(canonical_field: np.ndarray, fill: float = 0.0) -> np.ndarray:
    """Embed a canonical (south-to-north) field in the larger north-to-south source grid."""
    out = np.full((len(SRC_LAT), len(SRC_LON)), fill, np.float64)
    i0 = int(np.abs(SRC_LAT - LAT[-1]).argmin())
    j0 = int(np.abs(SRC_LON - LON[0]).argmin())
    out[i0:i0 + len(LAT), j0:j0 + len(LON)] = canonical_field[::-1]
    return out


def write_cycle(root: Path, model: str, rain_mm_per_6h: np.ndarray | None, t2m_c: np.ndarray,
                u: np.ndarray, v: np.ndarray, lead_days=(1, 3)) -> None:
    """A cycle as ECMWF encodes it: rain in metres accumulated since init, temperature in K."""
    hours = sorted({h for d in lead_days for end in acc.rain_leads(d) for h in (end, end - 24)} - {0})
    for h in hours if rain_mm_per_6h is not None else []:
        total_m = rain_mm_per_6h * (h / 6.0) / 1000.0
        write_grib(grib2.grib_path(root / model, model, INIT, h), "tp", on_source_grid(total_m), h)
    for d in lead_days:
        h = acc.inst_lead(d)
        path = grib2.grib_path(root / model, model, INIT, h)
        for short, field in (("2t", t2m_c + 273.15), ("10u", u), ("10v", v)):
            single = path.with_name(path.stem + f"_{short}.grib2")
            write_grib(single, short, on_source_grid(field, fill=float(np.mean(field))), h)
        # one multi-variable file per lead, like an operational download
        path.write_bytes(b"".join(path.with_name(path.stem + f"_{s}.grib2").read_bytes()
                                  for s in ("2t", "10u", "10v")))
        for s in ("2t", "10u", "10v"):
            path.with_name(path.stem + f"_{s}.grib2").unlink()


@pytest.fixture()
def fields():
    rng = np.random.default_rng(11)
    shape = (len(LAT), len(LON))
    return {"rain": rng.gamma(2.0, 2.0, shape), "t2m": 25 + 10 * rng.random(shape),
            "u": 6 * rng.standard_normal(shape), "v": 6 * rng.standard_normal(shape)}


@pytest.fixture()
def clean_registry():
    saved = dict(registry._ADAPTERS)
    yield
    registry._ADAPTERS.clear()
    registry._ADAPTERS.update(saved)


def test_fields_survive_the_round_trip(tmp_path, fields):
    write_cycle(tmp_path, "gfs", fields["rain"], fields["t2m"], fields["u"], fields["v"])
    adapter = grib2.Grib2Adapter("gfs", grib_dir=tmp_path / "gfs")

    t = adapter.load(INIT, "t2m", [1, 3])
    assert t.lead_days == [1, 3] and t.units == "degC"
    assert t.values.shape == (2, len(LAT), len(LON))
    assert np.allclose(t.sel_lead(1), fields["t2m"], atol=0.01)      # K -> degC, north-south flipped

    u = adapter.load(INIT, "u10", [1])
    assert np.allclose(u.sel_lead(1), fields["u"], atol=0.01)


def test_rain_day_is_built_from_totals_since_init(tmp_path, fields):
    write_cycle(tmp_path, "gfs", fields["rain"], fields["t2m"], fields["u"], fields["v"])
    rain = grib2.Grib2Adapter("gfs", grib_dir=tmp_path / "gfs").load(INIT, "precip", [1, 3])
    assert rain.units == "mm" and rain.accumulation_window_utc == "03:00-03:00"
    # a steady rate gives the same 24 h total on every day: four 6 h bins
    assert np.allclose(rain.sel_lead(1), 4 * fields["rain"], atol=0.02)
    assert np.allclose(rain.sel_lead(3), 4 * fields["rain"], atol=0.02)


def test_missing_lead_is_skipped_and_missing_cycle_is_none(tmp_path, fields):
    write_cycle(tmp_path, "gfs", fields["rain"], fields["t2m"], fields["u"], fields["v"], lead_days=(1,))
    adapter = grib2.Grib2Adapter("gfs", grib_dir=tmp_path / "gfs")
    assert adapter.load(INIT, "t2m", [1, 3]).lead_days == [1]
    assert adapter.load(INIT, "precip", [3]) is None
    assert adapter.load(pd.Timestamp("2022-06-16"), "t2m", [1]) is None
    assert not adapter.has_cycle(pd.Timestamp("2022-06-16"))


def test_file_that_misses_the_india_box_is_refused(tmp_path):
    lat, lon = np.arange(60.0, 39.9, -0.25), np.arange(0.0, 20.1, 0.25)
    path = grib2.grib_path(tmp_path / "gfs", "gfs", INIT, 12)
    write_grib(path, "2t", np.full((len(lat), len(lon)), 280.0), 12, lat, lon)
    with pytest.raises(ValueError, match="India box"):
        grib2.read_field(path, "t2m")


def test_registry_prefers_grib_and_falls_back_to_the_archive(tmp_path, fields, clean_registry):
    from ingestion.base import Adapter
    from ingestion.registry import register

    class Archive(Adapter):
        name, label, kind, variables = "hres", "ECMWF IFS HRES", "nwp", ("precip", "t2m", "u10", "v10")

        def load(self, init_time, variable, lead_days=None):
            return self._build_forecast(init_time, variable, lead_days,
                                        np.full((len(lead_days), len(LAT), len(LON)), -5.0, np.float32))

    registry._ADAPTERS.clear()
    register(Archive())
    write_cycle(tmp_path, "hres", fields["rain"], fields["t2m"], fields["u"], fields["v"], lead_days=(1,))
    write_cycle(tmp_path, "gfs", fields["rain"], fields["t2m"], fields["u"], fields["v"], lead_days=(1,))

    new = grib2.register_grib_sources(tmp_path)
    assert new == ["gfs"] and grib2.register_grib_sources(tmp_path) == ["gfs"]    # idempotent
    hres = registry.get("hres")
    assert isinstance(hres, grib2.GribFirst)

    from_grib = hres.load(INIT, "t2m", [1])
    assert np.allclose(from_grib.sel_lead(1), fields["t2m"], atol=0.01)
    assert hres.last_source[(INIT, "t2m")] == "grib2"

    other_day = pd.Timestamp("2022-06-20")
    assert np.all(hres.load(other_day, "t2m", [1]).values == -5.0)
    assert hres.last_source[(other_day, "t2m")] == "archive"


HAS_FROZEN = Path("data/frozen/precip_L1_train_to_2020.joblib").exists() and Path("data/raw/hres").exists()


@pytest.mark.skipif(not HAS_FROZEN, reason="needs the archive and the frozen weights of a pipeline run")
def test_cycle_blends_a_model_that_arrived_as_grib2(tmp_path, monkeypatch, clean_registry):
    """HRES is served from GRIB2 files holding the archive's own fields: the cycle must
    report the GRIB2 source and produce the same blend as from the archive. A GRIB2-only
    model without skill history must be gated and excluded."""
    from experiments import cycle as cyc, data
    from regimes import detector as rg

    geo = rg.load_geography()
    registry.load_all()
    reference = cyc.forecast_variable("t2m", INIT, 1, geo)

    j = data.LEAD_DAYS.index(1)
    k = data.init_dates(2022).index(INIT)
    grab = lambda v: np.asarray(data.forecast_year("hres", v, 2022)[k, j], dtype=np.float64)
    t2m, u, v = grab("t2m"), grab("u10"), grab("v10")
    # no rainfall files: rainfall (which sets the regime) must still come from the archive
    write_cycle(tmp_path, "hres", None, t2m, u, v, lead_days=(1,))
    write_cycle(tmp_path, "gfs", None, t2m + 1.0, u, v, lead_days=(1,))

    monkeypatch.setattr(grib2, "GRIB_ROOT", tmp_path)
    registry._ADAPTERS.clear()
    for module in ("ecmwf", "graphcast", "pangu"):
        mod = __import__(f"ingestion.{module}", fromlist=["x"])
        for obj in vars(mod).values():
            if isinstance(obj, type) and obj.__module__ == mod.__name__ and hasattr(obj, "load"):
                registry.register(obj())
    grib2.register_grib_sources(tmp_path)

    fc = cyc.forecast_variable("t2m", INIT, 1, geo)
    assert fc["status"]["hres"] == "ok (grib2)"
    assert fc["status"]["graphcast"] == "ok"
    assert fc["status"]["gfs"].startswith("no_skill_history")
    assert "gfs" not in fc["members"] and "gfs" not in fc["weights"]
    assert np.allclose(fc["members"]["hres"], reference["members"]["hres"], atol=0.01)
    assert np.allclose(fc["blend"][geo.land], reference["blend"][geo.land], atol=0.01)
    assert fc["regimes"] == reference["regimes"]
    assert registry.get("hres").last_source[(INIT, "precip")] == "archive"
