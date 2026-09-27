"""Static layers: districts, states, IMD homogeneous regions, population, land mask.

    python -m ingestion.static

Sources (licences in MASTER_PLAN §15.2):
- geoBoundaries IND ADM2 (736 districts, 2021, LGD-derived, ODbL) and ADM1 (states).
- WorldPop 2020 1 km UN-adjusted population (CC-BY 4.0).

Writes data/static/:
  districts.geojson   simplified, one feature per district, properties {id, name, state, region}
  grid_static.nc      on the canonical grid: land (bool), district_frac (district, lat, lon),
                      population (people per cell), cell_district (dominant district index)
"""
from __future__ import annotations

import json
import re
import unicodedata
import urllib.request
import warnings
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
import regionmask
import xarray as xr
from rasterio.warp import Resampling, reproject

from canonical.grid import BOUNDS, LAT, LON, RES

warnings.filterwarnings("ignore")
STATIC = Path("data/static")
URLS = {
    "adm2": "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/IND/ADM2/geoBoundaries-IND-ADM2.geojson",
    "adm1": "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/IND/ADM1/geoBoundaries-IND-ADM1.geojson",
    "pop": "https://data.worldpop.org/GIS/Population/Global_2000_2020_1km_UNadj/2020/IND/ind_ppp_2020_1km_Aggregated_UNadj.tif",
}

# ISO 3166-2:IN codes, keyed by a normalised state name.
STATE_CODE = {
    "andamanandnicobar": "AN", "andhrapradesh": "AP", "arunachalpradesh": "AR", "assam": "AS",
    "bihar": "BR", "chandigarh": "CH", "chhattisgarh": "CT", "dadraandnagarhavelianddamananddiu": "DH",
    "delhi": "DL", "goa": "GA", "gujarat": "GJ", "haryana": "HR", "himachalpradesh": "HP",
    "jammuandkashmir": "JK", "jharkhand": "JH", "karnataka": "KA", "kerala": "KL", "ladakh": "LA",
    "lakshadweep": "LD", "madhyapradesh": "MP", "maharashtra": "MH", "manipur": "MN",
    "meghalaya": "ML", "mizoram": "MZ", "nagaland": "NL", "odisha": "OR", "puducherry": "PY",
    "punjab": "PB", "rajasthan": "RJ", "sikkim": "SK", "tamilnadu": "TN", "telangana": "TG",
    "tripura": "TR", "uttarpradesh": "UP", "uttarakhand": "UT", "westbengal": "WB",
}
# IMD rainfall homogeneous regions.
REGION_OF_STATE = {
    **{c: "NW" for c in ["JK", "LA", "HP", "PB", "CH", "HR", "DL", "UT", "UP", "RJ"]},
    **{c: "CENTRAL" for c in ["GJ", "DH", "MP", "CT", "MH", "GA", "OR"]},
    **{c: "SOUTH" for c in ["AP", "TG", "KA", "KL", "TN", "PY", "LD", "AN"]},
    **{c: "EAST_NE" for c in ["BR", "JH", "WB", "SK", "AS", "ML", "AR", "NL", "MN", "MZ", "TR"]},
}
REGION_LABEL = {"NW": "Northwest India", "CENTRAL": "Central India", "SOUTH": "South Peninsula",
                "EAST_NE": "East & Northeast India"}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = s.replace("&", "and").replace("national capital territory of", "")
    s = s.replace("nct of", "").replace("the ", "").replace("islands", "")
    return re.sub(r"[^a-z]", "", s)


def _slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]+", "-", s.upper()).strip("-")


def _state_code(name: str) -> str:
    n = _norm(name)
    for key, code in STATE_CODE.items():
        if key == n or key in n or n in key:
            return code
    raise KeyError(f"unmapped state {name!r}")


def _fetch(url: str, dest: Path) -> Path:
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        print(f"downloading {url}")
        urllib.request.urlretrieve(url, dest)
    return dest


def build_districts() -> gpd.GeoDataFrame:
    adm2 = gpd.read_file(_fetch(URLS["adm2"], STATIC / "src" / "adm2.geojson")).to_crs(4326)
    adm1 = gpd.read_file(_fetch(URLS["adm1"], STATIC / "src" / "adm1.geojson")).to_crs(4326)
    adm1["state_code"] = adm1["shapeName"].map(_state_code)
    # parent state by largest overlap (robust to slivers on shared borders)
    pts = adm2.copy()
    pts["geometry"] = adm2.representative_point()
    joined = gpd.sjoin(pts, adm1[["shapeName", "state_code", "geometry"]], how="left",
                       predicate="within")
    joined = joined[~joined.index.duplicated()]
    d = adm2.copy()
    d["state"] = joined["shapeName_right"].values
    d["state_code"] = joined["state_code"].values
    missing = d["state_code"].isna()
    if missing.any():  # point fell in a gap: nearest state
        near = gpd.sjoin_nearest(pts[missing].to_crs(3857), adm1.to_crs(3857)[["state_code", "shapeName", "geometry"]])
        near = near[~near.index.duplicated()]
        d.loc[missing, "state_code"] = near["state_code"].values
        d.loc[missing, "state"] = near["shapeName_right"].values
    d["name"] = d["shapeName"]
    d["id"] = d["state_code"] + "-" + d["name"].map(_slug)
    dup = d["id"].duplicated(keep=False)
    d.loc[dup, "id"] = d.loc[dup, "id"] + "-" + d.loc[dup].groupby("id").cumcount().add(1).astype(str)
    d["region"] = d["state_code"].map(REGION_OF_STATE)
    return d[["id", "name", "state", "state_code", "region", "geometry"]].reset_index(drop=True)


def population_on_grid() -> np.ndarray:
    """Sum WorldPop 1 km people into canonical 0.25° cells."""
    src_path = _fetch(URLS["pop"], STATIC / "src" / "worldpop_2020_1km.tif")
    dst = np.zeros((len(LAT), len(LON)), np.float64)
    transform = rasterio.transform.from_origin(BOUNDS["west"], BOUNDS["north"], RES, RES)
    with rasterio.open(src_path) as src:
        data = src.read(1).astype(np.float64)
        data[(data < 0) | ~np.isfinite(data)] = 0
        reproject(data, dst, src_transform=src.transform, src_crs=src.crs,
                  dst_transform=transform, dst_crs="EPSG:4326", resampling=Resampling.sum)
    return dst[::-1]  # north-up raster -> ascending lat


def main() -> None:
    STATIC.mkdir(parents=True, exist_ok=True)
    d = build_districts()
    lon2d, lat2d = np.meshgrid(LON, LAT)
    regions = regionmask.from_geopandas(d, names="id", abbrevs="id", overlap=False)
    frac = regions.mask_3D_frac_approx(LON, LAT)  # (region, lat, lon) area fraction per cell
    frac_np = frac.values.astype(np.float32)
    land = frac_np.sum(0) >= 0.5
    # every district gets at least one cell (tiny districts: nearest cell to its centroid)
    for k in np.where(frac_np.reshape(len(d), -1).max(1) == 0)[0]:
        c = d.geometry.iloc[k].representative_point()
        i, j = int(np.abs(LAT - c.y).argmin()), int(np.abs(LON - c.x).argmin())
        frac_np[k, i, j] = 1.0
    cell_district = np.where(frac_np.sum(0) > 0, frac_np.argmax(0), -1).astype(np.int16)
    pop = population_on_grid()
    ds = xr.Dataset(
        {"land": (("lat", "lon"), land),
         "district_frac": (("district", "lat", "lon"), frac_np),
         "cell_district": (("lat", "lon"), cell_district),
         "population": (("lat", "lon"), pop.astype(np.float32))},
        coords={"district": d["id"].values, "lat": LAT, "lon": LON},
        attrs={"population_source": "WorldPop 2020 1km UN-adjusted (CC-BY 4.0)",
               "district_source": "geoBoundaries IND ADM2 2021 (ODbL)"})
    ds.to_netcdf(STATIC / "grid_static.nc")
    simple = d.copy()
    simple["geometry"] = simple.geometry.simplify(0.01, preserve_topology=True)
    simple.to_file(STATIC / "districts.geojson", driver="GeoJSON")
    meta = d.drop(columns="geometry").to_dict("records")
    (STATIC / "districts_index.json").write_text(json.dumps(meta, indent=1))
    print(f"{len(d)} districts, {int(land.sum())} land cells, population {pop.sum() / 1e9:.3f} bn, "
          f"regions {d['region'].value_counts().to_dict()}")


if __name__ == "__main__":
    main()
