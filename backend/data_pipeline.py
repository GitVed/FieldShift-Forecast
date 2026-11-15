"""Offline Stage 1 parsers. Never mutate raw inputs or infer scenario values.

Run: python -m backend.data_pipeline [--dataset all|climate|soil]
"""
from __future__ import annotations

import argparse
import calendar
import csv
import datetime as dt
import hashlib
import io
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

import netCDF4
import numpy as np
import rasterio
from rasterio.warp import transform
from rasterio.windows import Window

# Support both direct script execution and python -m invocation.
if __package__ in (None, ''):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.provenance import load_manifest, save_manifest, write_csv

ROOT = Path(__file__).resolve().parents[1]
LAT, LON = 42.0356, -82.9183
FIELDS = ["date", "depth_top_cm", "depth_bottom_cm", "variable", "value", "unit",
          "native_value", "native_unit", "cell_id", "source_id", "quality_flag", "reason"]
SOILS = {"phh2o": ("ph", 10, "pH", "pH x 10"),
         "nitrogen": ("total_nitrogen", 100, "g/kg", "cg/kg"),
         "soc": ("organic_carbon", 10, "g/kg", "dg/kg"),
         "sand": ("sand", 10, "%", "g/kg"), "silt": ("silt", 10, "%", "g/kg"),
         "clay": ("clay", 10, "%", "g/kg")}
DEPTHS = [(0, 10), (10, 40), (40, 100), (100, 200)]


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def finite(value):
    try:
        f = float(value)
        return f if math.isfinite(f) else None
    except (ValueError, TypeError):
        return None


def clean(value, variable, fill_values=(-999, -9999)):
    number = finite(value)
    if number is None or number in fill_values:
        return None, "missing", "fill_value_or_nonfinite"
    bounds = {"temperature": (-90, 65), "humidity": (0, 100),
              "precipitation": (0, None), "soil_moisture": (0, 1),
              "ph": (0, 14), "sand": (0, 100), "silt": (0, 100), "clay": (0, 100),
              "organic_carbon": (0, 1000), "total_nitrogen": (0, 1000)}
    lo, hi = bounds[variable]
    if number < lo or (hi is not None and number > hi) or (variable == "ph" and number == 0):
        return None, "invalid", "outside_physical_screen"
    return number, "valid", ""


def monthly_rate_total(value, year, month):
    return value * calendar.monthrange(year, month)[1]


def water_volume(mass, top_cm, bottom_cm):
    """kg/m2 / (1000 kg/m3 * layer thickness in m) -> m3/m3."""
    if bottom_cm <= top_cm:
        raise ValueError("Soil layer must have positive thickness")
    return mass / (1000.0 * (bottom_cm - top_cm) / 100.0)


def distance_km(lat1, lon1, lat2, lon2):
    a, b = math.radians(lat1), math.radians(lat2)
    dlat, dlon = b-a, math.radians(lon2-lon1)
    v = math.sin(dlat/2)**2 + math.cos(a)*math.cos(b)*math.sin(dlon/2)**2
    return 6371.0088 * 2 * math.asin(min(1, math.sqrt(v)))


def power_reader(path):
    text = Path(path).read_text(encoding="utf-8-sig")
    if "-END HEADER-" not in text:
        raise ValueError(f"Missing POWER header terminator: {path}")
    header, body = text.split("-END HEADER-", 1)
    return header, list(csv.DictReader(io.StringIO(body.lstrip("\r\n"))))


def validate_power_header(header):
    expected = {"T2M": "C", "PRECTOTCORR": "mm/day", "RH2M": "%"}
    for parameter, unit in expected.items():
        match = re.search(r"^" + parameter + r"\s+.*\(([^()]*)\)\s*$", header, re.MULTILINE)
        if not match or match.group(1) != unit:
            raise ValueError(f"Unexpected or missing POWER unit for {parameter}; expected {unit}")
    point = re.search(r"Location:\s*Latitude\s+([-\d.]+)\s+Longitude\s+([-\d.]+)", header, re.IGNORECASE)
    if not point or abs(float(point.group(1))-LAT) > 1e-6 or abs(float(point.group(2))-LON) > 1e-6:
        raise ValueError("POWER response location does not match the requested Harrow point")


def verify_imerg_json(payload, rows):
    """Bind an official JSON source declaration to every original CSV day/value."""
    header = payload.get("header", {})
    if set(header.get("sources", [])) != {"IMERG"} or header.get("time_standard") != "UTC":
        raise ValueError("JSON must explicitly declare IMERG-only source and UTC")
    unit = payload.get("parameters", {}).get("IMERG_PRECTOT", {}).get("units")
    if unit not in ["mm", "mm/day"]:
        raise ValueError("Unrecognized IMERG daily precipitation unit")
    coordinates = payload.get("geometry", {}).get("coordinates", [])
    if len(coordinates) < 2 or abs(coordinates[0]-LON) > .00051 or abs(coordinates[1]-LAT) > .00051:
        raise ValueError("IMERG JSON location does not match Harrow (including API rounding)")
    original = {}
    for row in rows:
        year, doy = int(row["YEAR"]), int(row["DOY"])
        if not 1 <= doy <= (366 if calendar.isleap(year) else 365):
            raise ValueError("Invalid day of year in IMERG CSV")
        date = (dt.date(year, 1, 1)+dt.timedelta(days=doy-1)).strftime("%Y%m%d")
        if date in original:
            raise ValueError("Duplicate IMERG CSV date")
        original[date] = finite(row["IMERG_PRECTOT"])
    values = payload.get("properties", {}).get("parameter", {}).get("IMERG_PRECTOT", {})
    if not original or set(original) != set(values):
        raise ValueError("IMERG CSV/JSON date coverage differs")
    if header.get("start") != min(original) or header.get("end") != max(original):
        raise ValueError("IMERG JSON declared period differs from the CSV")
    if any(finite(values[date]) != value for date, value in original.items()):
        raise ValueError("IMERG CSV/JSON precipitation values differ")
    return {"status": "verified", "source": "IMERG", "matching_daily_values": len(original),
            "api_version": header.get("api", {}).get("version"), "time_standard": "UTC",
            "native_daily_unit": unit,
            "interpretation": "Each mm/day value is integrated over one day (numeric amount in mm); monthly totals sum daily amounts once",
            "legacy_csv_header": "MERRA-2 label retained unchanged; overridden only by matching official JSON source metadata",
            "native_final_archive_comparison": "not performed; verification uses official POWER JSON provenance, not an independent native-file comparison"}


def month_dates(start_year, end_year):
    return [dt.date(y, m, 1).isoformat() for y in range(start_year, end_year+1) for m in range(1, 13)]


def measurement(variable, value, unit, native_value, native_unit, cell, source,
                date="", top="", bottom="", flag="valid", reason=""):
    return dict(zip(FIELDS, [date, top, bottom, variable, value, unit, native_value,
                             native_unit, cell, source, flag, reason]))


def choose_hwsd_component(rows):
    """Choose only a documented dominant component; never mix components silently."""
    if not rows:
        raise ValueError("No HWSD attributes for the containing soil mapping unit")
    shares = {}
    for row in rows:
        sequence, share = int(row["SEQUENCE"]), finite(row["SHARE"])
        if share is None or not 0 < share <= 100:
            raise ValueError("Invalid HWSD component share")
        if sequence in shares and shares[sequence] != share:
            raise ValueError("HWSD component share changes between layers")
        shares[sequence] = share
    if abs(sum(shares.values()) - 100) > .1:
        raise ValueError("HWSD component shares do not sum to 100 percent")
    maximum = max(shares.values())
    dominant = [sequence for sequence, share in shares.items() if share == maximum]
    if len(dominant) != 1:
        raise ValueError("Ambiguous HWSD dominant component; no automatic tie breaking")
    sequence = dominant[0]
    selected = sorted((r for r in rows if int(r["SEQUENCE"]) == sequence), key=lambda r: r["TOPDEP"])
    if [(r["TOPDEP"], r["BOTDEP"]) for r in selected] != [(0,20),(20,40),(40,60),(60,80),(80,100),(100,150),(150,200)]:
        raise ValueError("HWSD native layers missing, duplicated, or unexpected")
    return selected, sequence, shares


def completeness(rows):
    counts = Counter(r["quality_flag"] for r in rows)
    return {"rows": len(rows), "flags": dict(counts),
            "usable_rows": counts.get("valid", 0),
            "regional_estimate_rows": counts.get("regional_estimate", 0),
            "valid_value_min": min((r["value"] for r in rows if r["quality_flag"] in ["valid", "regional_estimate"] and r["value"] is not None), default=None),
            "valid_value_max": max((r["value"] for r in rows if r["quality_flag"] in ["valid", "regional_estimate"] and r["value"] is not None), default=None),
            "verdict": "usable" if counts.get("valid", 0) == len(rows) and rows else
            "regional_estimate" if counts.get("regional_estimate", 0) == len(rows) and rows else "review_required"}


class Pipeline:
    def __init__(self, root=ROOT):
        self.root = Path(root)
        self.seed = self.root / "data/seed"
        self.manifest_path = self.seed / ("sources.csv" if (self.seed/"sources.csv").exists() else "sources.json")
        self.manifest = load_manifest(self.root)
        self.sources = {e.get("local_file"): e for e in self.manifest["downloads_and_attempts"] if e.get("local_file")}
        self.inputs, self.outputs, self.cells = {}, {}, {}
        self.report = {"scope": "Stage 1 data tables only; no crop summaries, trends, or scenarios",
                       "datasets": {}, "issues": [], "buddy_check": "see data/metadata/power_grid_checks.csv and data/seed/trend_results.csv", "point_status": "user_supplied; field boundary not verified"}

    def source(self, path):
        rel = str(Path(path).relative_to(self.root))
        if rel not in self.sources:
            raise ValueError(f"Input missing from acquisition provenance: {rel}")
        entry = self.sources[rel]
        digest = sha256(path)
        if entry.get("sha256") and digest != entry["sha256"]:
            raise ValueError(f"Input changed since acquisition: {rel}")
        self.inputs[rel] = {"source_id": entry["id"], "sha256": digest, "bytes": Path(path).stat().st_size}
        return entry["id"]

    def emit(self, name, rows, note=None):
        path = self.seed / name
        with path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        result = completeness(rows)
        if note:
            result["note"] = note
        result["date_min"] = min((r["date"] for r in rows if r["date"]), default=None)
        result["date_max"] = max((r["date"] for r in rows if r["date"]), default=None)
        self.report["datasets"][name] = result
        self.outputs[path.relative_to(self.root).as_posix()] = {
            "sha256": sha256(path), "rows": len(rows), "columns": FIELDS,
            "source_ids": sorted({r["source_id"] for r in rows}), "status": "CACHED",
            "scientific_verdict": result["verdict"], "processing": note or name}

    def point_cell(self, cell_id, lat, lon, **extra):
        self.cells[cell_id] = {"requested_latitude": LAT, "requested_longitude": LON,
                               "center_latitude": lat, "center_longitude": lon,
                               "distance_km": distance_km(LAT, LON, lat, lon) if lat is not None else None,
                               **extra}

    def climate(self):
        path = self.seed / "power_harrow_monthly_1981_2025.csv"
        source = self.source(path)
        header, data = power_reader(path)
        validate_power_header(header)
        for expected in ["T2M", "PRECTOTCORR", "RH2M"]:
            if expected not in header:
                raise ValueError(f"Missing POWER parameter {expected}")
        # POWER echoes requested coordinates; these are not a verified native centre.
        cell = "power_harrow_point"
        self.point_cell(cell, None, None, resolved_cell_status="unverified_upstream_selection",
                        documented_spacing_degrees=[0.5, 0.625],
                        candidate_merra2_center=[42.0, -83.125],
                        candidate_status="inferred nearest MERRA-2 grid point; not verified by response",
                        time_standard="LST", source_id=source)
        existing = self.manifest.get("resolved_cells", {}).get(cell, {})
        if existing.get("resolved_cell_status", "").startswith("documented_merra2"):
            self.cells[cell] = existing
        self.report["issues"].append({"code": "power_upstream_identifier_not_exposed", "detail": "API echoes request coordinates. See power_grid_checks.csv for empirical centre equivalence; the upstream provider cell ID is not exposed."})
        lookup = defaultdict(list)
        for record in data:
            if record["PARAMETER"] in ["T2M", "PRECTOTCORR", "RH2M"]:
                year = int(record["YEAR"])
                if 1981 <= year <= 2025:
                    for month in range(1, 13):
                        lookup[(record["PARAMETER"], year, month)].append(record[calendar.month_abbr[month].upper()])
        for parameter, variable, unit, name in [
            ("T2M", "temperature", "degC", "power_t2m_harrow_1981_2025.csv"),
            ("PRECTOTCORR", "precipitation", "mm/month", "power_precip_harrow_1981_2025.csv"),
            ("RH2M", "humidity", "%", "power_humidity_harrow_1981_2025.csv")]:
            rows = []
            for date in month_dates(1981, 2025):
                y, m = map(int, date[:7].split("-"))
                values = lookup.get((parameter, y, m), [])
                raw = finite(values[0]) if len(values) == 1 else None
                value, flag, reason = clean(raw, variable)
                if len(values) != 1:
                    flag, reason = "missing" if not values else "invalid", "missing_record" if not values else "duplicate_record"
                if parameter == "PRECTOTCORR" and value is not None:
                    value = monthly_rate_total(value, y, m)
                rows.append(measurement(variable, value, unit, raw,
                                        "mm/day" if parameter == "PRECTOTCORR" else unit,
                                        cell, source, date, flag=flag, reason=reason))
            self.emit(name, rows, "Original POWER monthly record; precipitation rate multiplied by calendar days; no ANN column or interpolation")
        self.daily_power()
        self.imerg()

    def daily_power(self):
        path = self.seed / "power_harrow_daily_1981_2025.csv"
        source = self.source(path)
        header, data = power_reader(path)
        validate_power_header(header)
        if "in UTC" not in header:
            raise ValueError("Expected daily POWER UTC time standard")
        lookup = defaultdict(list)
        bad_dates = []
        for record in data:
            y, doy = int(record["YEAR"]), int(record["DOY"])
            if doy < 1 or doy > (366 if calendar.isleap(y) else 365):
                bad_dates.append([y, doy]); continue
            lookup[dt.date(y, 1, 1) + dt.timedelta(days=doy-1)].append(record)
        expected = (dt.date(2025, 12, 31)-dt.date(1981, 1, 1)).days+1
        missing, duplicate, invalid = [], [], Counter()
        for i in range(expected):
            date = dt.date(1981, 1, 1) + dt.timedelta(days=i)
            records = lookup.get(date, [])
            if not records: missing.append(str(date))
            if len(records) > 1: duplicate.append(str(date))
            if len(records) == 1:
                for parameter, variable in [("T2M", "temperature"), ("PRECTOTCORR", "precipitation"), ("RH2M", "humidity")]:
                    _, flag, _ = clean(records[0].get(parameter), variable)
                    if flag != "valid": invalid[parameter] += 1
        self.report["daily_power_audit"] = {"source_id": source, "time_standard": "UTC", "expected_days": expected,
                                             "missing_dates": missing, "duplicate_dates": duplicate,
                                             "invalid_dates": bad_dates, "invalid_value_counts": dict(invalid),
                                             "note": "Daily UTC data audited separately; not substituted into monthly LST tables"}

    def imerg(self):
        path = self.root / "data/source/imerg_harrow_daily_19980601_20251231.csv"
        if not path.exists():
            path = self.root / "data/raw/imerg_harrow_daily_19980601_20251231.csv"
        source = self.source(path)
        header, data = power_reader(path)
        # Current provider response contradicts the product guide: fail closed.
        parameter_line = next((line for line in header.splitlines() if line.startswith("IMERG_PRECTOT")), "")
        conflicted = "MERRA-2" in parameter_line or "(mm)" not in parameter_line
        evidence = {"status": "unverified", "reason": "no matching official JSON proof"}
        proof_path = self.root / "data/raw/verification/imerg_power_full_daily.json"
        proof_source = None
        csv_proof = self.root / "data/source/imerg_power_full_daily_evidence.csv"
        if not proof_path.exists() and csv_proof.exists():
            proof_path = csv_proof
        if proof_path.exists():
            proof_source = self.source(proof_path)
            from urllib.parse import urlparse, parse_qs
            proof_entry = self.sources[str(proof_path.relative_to(self.root))]
            request = urlparse(proof_entry.get("url", ""))
            query = parse_qs(request.query)
            if request.scheme != "https" or request.hostname != "power.larc.nasa.gov" or query.get("parameters") != ["IMERG_PRECTOT"]:
                raise ValueError("IMERG proof is not registered as an official POWER parameter request")
            if query.get("latitude") != [str(LAT)] or query.get("longitude") != [str(LON)]:
                raise ValueError("IMERG proof request point differs from Harrow")
            try:
                if proof_path.suffix == ".csv":
                    with proof_path.open(newline="") as stream:
                        payload = {r["section"]: json.loads(r["metadata"]) for r in csv.DictReader(stream)}
                else:
                    payload = json.loads(proof_path.read_text())
                evidence = verify_imerg_json(payload, data)
                evidence["verification_source_id"] = proof_source
                evidence["verification_artifact_sha256"] = self.inputs[str(proof_path.relative_to(self.root))]["sha256"]
                evidence["csv_sha256"] = self.inputs[str(path.relative_to(self.root))]["sha256"]
                conflicted = False
            except ValueError as exc:
                conflicted = True
                evidence = {"status": "unverified", "reason": str(exc)}
        self.report["imerg_verification"] = evidence
        if conflicted:
            self.report["issues"].append({"code": "imerg_provenance_unverified", "source_id": source,
                                          "detail": evidence["reason"]})
        cell = "imerg_harrow_point_unverified"
        self.point_cell(cell, None, None, resolved_cell_status="unverified", time_standard="UTC",
                        documented_spacing_degrees=[0.1, 0.1], source_id=source)
        lookup = defaultdict(list)
        for record in data:
            y, doy = int(record["YEAR"]), int(record["DOY"])
            if doy < 1 or doy > (366 if calendar.isleap(y) else 365):
                raise ValueError("Invalid IMERG day of year")
            date = dt.date(y, 1, 1) + dt.timedelta(days=doy-1)
            lookup[date].append(record.get("IMERG_PRECTOT"))
        rows = []
        for date in month_dates(1998, 2025):
            y, m = map(int, date[:7].split("-"))
            if y == 1998 and m < 6: continue
            daily = []
            reason = ""
            for day in range(1, calendar.monthrange(y, m)[1]+1):
                values = lookup.get(dt.date(y, m, day), [])
                if len(values) != 1:
                    reason = "duplicate_daily_record" if len(values) > 1 else "incomplete_month"; continue
                value, flag, _ = clean(values[0], "precipitation")
                if flag != "valid": reason = "invalid_or_missing_daily_value"
                else: daily.append(value)
            valid = not reason and not conflicted
            total = sum(daily) if valid else None
            rows.append(measurement("precipitation", total, "mm/month", None, "mm/day (daily rate integrated over one day)",
                                    cell, source, date, flag="valid" if valid else "unverified" if conflicted and not reason else "missing",
                                    reason=reason or ("source_label_and_units_conflict" if conflicted else "")))
        self.emit("imerg_precip_harrow.csv", rows,
                  "Daily rates integrated over one day and summed only for complete months; product source verified against all matching official JSON observations" if not conflicted else
                  "No monthly totals released while source/units remain unverified")
        self.outputs["data/seed/imerg_precip_harrow.csv"]["source_verification"] = evidence

    def water(self):
        paths = sorted((self.root / "data/raw/glda").glob("*.nc4"))
        lookup = defaultdict(list)
        cells_by_file = {}
        excluded = []
        for path in paths:
            match = re.search(r"\.A(\d{4})(\d{2})\.", path.name)
            if not match: raise ValueError(f"Unrecognized GLDAS filename {path}")
            year, month = map(int, match.groups())
            if not 2000 <= year <= 2025:
                excluded.append(path.name); continue
            source = self.source(path)
            with netCDF4.Dataset(path) as ds:
                time = ds.variables["time"]
                stamps = netCDF4.num2date(time[:], time.units, calendar=getattr(time, "calendar", "standard"))
                if len(stamps) != 1 or (stamps[0].year, stamps[0].month) != (year, month):
                    raise ValueError(f"GLDAS internal timestamp mismatch: {path.name}")
                lat, lon = ds.variables["lat"][:], ds.variables["lon"][:]
                iy, ix = int(np.argmin(abs(lat-LAT))), int(np.argmin(abs(lon-LON)))
                cy, cx = float(lat[iy]), float(lon[ix])
                cell = f"gldas_noah025_{iy}_{ix}"
                self.point_cell(cell, cy, cx, selection="nearest source coordinate; no nearest-land substitution",
                                row=iy, column=ix, documented_spacing_degrees=[0.25, 0.25])
                cells_by_file[path.name] = cell
                for top, bottom in DEPTHS:
                    variable = ds.variables[f"SoilMoi{top}_{bottom}cm_inst"]
                    if str(variable.units).strip() not in ["kg m-2", "kg/m2", "kg/m^2"]:
                        raise ValueError(f"Unexpected GLDAS water unit in {path.name}")
                    native = variable[0, iy, ix]
                    mass = None if np.ma.is_masked(native) else finite(native)
                    value = water_volume(mass, top, bottom) if mass is not None else None
                    value, flag, reason = clean(value, "soil_moisture")
                    lookup[(year, month, top, bottom)].append(measurement("soil_moisture", value, "m3/m3", mass,
                                                                                      "kg/m2", cell, source,
                                                                                      dt.date(year, month, 1).isoformat(),
                                                                                      top, bottom, flag, reason))
        if len(set(cells_by_file.values())) != 1:
            raise ValueError("GLDAS nearest cell changes between source files")
        rows = []
        for date in month_dates(2000, 2025):
            year, month = map(int, date[:7].split("-"))
            for top, bottom in DEPTHS:
                entries = lookup.get((year, month, top, bottom), [])
                if len(entries) != 1:
                    # Do not invent a source reference for an absent monthly granule.
                    raise ValueError(f"Missing or duplicate GLDAS month/layer: {date} {top}-{bottom}")
                rows.append(entries[0])
        self.report["gldas"] = {"internal_months_verified": 312, "excluded_files_outside_shared_period": excluded,
                                 "native_depths_cm": DEPTHS, "modeled_not_smap": True}
        self.emit("gldas_soil_moisture_harrow.csv", rows, "Single nearest Harrow cell; four distinct layers; kg/m2 divided by water density and layer thickness; 2000-2025 only")

    def raster_point(self, path):
        with rasterio.open(path) as ds:
            if ds.crs is None: raise ValueError(f"Missing raster CRS: {path}")
            x, y = transform("EPSG:4326", ds.crs, [LON], [LAT])
            row, col = ds.index(x[0], y[0])
            if not (0 <= row < ds.height and 0 <= col < ds.width):
                raise ValueError(f"Harrow lies outside raster: {path}")
            value = ds.read(1, window=Window(col, row, 1, 1), masked=True)[0, 0]
            center_x, center_y = ds.xy(row, col)
            lon, lat = transform(ds.crs, "EPSG:4326", [center_x], [center_y])
            cell = f"{path.stem}_r{row}_c{col}"
            self.point_cell(cell, lat[0], lon[0], row=row, column=col,
                            crs=ds.crs.to_string(), pixel_size=list(ds.res),
                            selection="containing pixel, no interpolation or neighboring pixel substitution",
                            declared_nodata=ds.nodata)
            return None if np.ma.is_masked(value) else finite(value), cell

    def soil(self):
        rows, by_depth = [], defaultdict(dict)
        for prop, (variable, divisor, unit, native_unit) in SOILS.items():
            for top, bottom in [(0, 5), (5, 15), (15, 30)]:
                path = self.root / f"data/raw/soilgrids/{prop}_{top}-{bottom}cm_mean_harrow.tif"
                source = self.source(path)
                raw, cell = self.raster_point(path)
                value, flag, reason = clean(raw/divisor if raw is not None else None, variable, (-32768, -9999, -999))
                row = measurement(variable, value, unit, raw, native_unit, cell, source,
                                  top=top, bottom=bottom, flag=flag, reason=reason)
                rows.append(row); by_depth[(top, bottom)][variable] = row
        for depth, group in by_depth.items():
            texture = [group[k]["value"] for k in ["sand", "silt", "clay"]]
            bad_texture = any(v is None for v in texture) or not 95 <= sum(v or 0 for v in texture) <= 105
            bad_ph = group["ph"]["value"] is None
            if bad_texture or bad_ph:
                # Unlabelled zeros at the point cannot be accepted as measured soil.
                for row in group.values():
                    row.update(value=None, quality_flag="invalid", reason="soil_pixel_invalid_ph_or_texture; no numeric fallback")
                self.report["issues"].append({"code": "soil_point_unusable", "depth_cm": list(depth),
                                              "detail": "Invalid pH or texture mass balance at supplied point; retain Brookston descriptor only; numerical soil inputs require a valid source or confirmed field point."})
        original = self.root / "data/raw/soilgrids_original/phh2o_0-5cm_mean_harrow.tif"
        if original.exists():
            source = self.source(original)
            raw, cell = self.raster_point(original)
            self.report["original_soilgrids_verification"] = {"source_id":source,"cell_id":cell,
                "original_ph_times_10":raw,"status":"nodata_at_point" if raw is None else "value_available",
                "interpretation":"Original 250 m source tile declares NoData -32768; no neighboring pixel substitution"}
        native_probe = self.root / "data/raw/soilgrids_native/phh2o_0-5cm_mean_harrow.tif"
        if native_probe.exists():
            source = self.source(native_probe)
            value, cell = self.raster_point(native_probe)
            self.report["native_soil_probe"] = {"source_id": source, "cell_id": cell, "native_ph_times_10": value,
                                                 "note": "Additional provider native-projection request; zero pH still invalid, original files preserved"}
        self.emit("soilgrids_harrow.csv", rows, "ISRIC scale factors applied; depths kept separate; invalid field pixel emits nulls, never nearby substitutes; modelled total N, not available N")

    def hwsd(self):
        """Explicit regional fallback from FAO source map + its original attribute DB."""
        import zipfile
        from access_parser import AccessParser
        directory = self.root / "data/raw/hwsd"
        db_path, map_zip = directory / "HWSD2.mdb", directory / "HWSD2_RASTER.zip"
        if not db_path.exists() or not map_zip.exists():
            return  # Original SoilGrids remains missing; never fabricate a fallback.
        db_source = self.source(db_path)
        map_source = self.source(map_zip)
        archive = directory / "HWSD2_DB.zip"
        self.source(archive)
        # Verify that the decompressed file is the original archive member.
        with zipfile.ZipFile(archive) as z:
            member = next(n for n in z.namelist() if Path(n).name == "HWSD2.mdb")
            with z.open(member) as stream:
                digest = hashlib.sha256()
                for chunk in iter(lambda: stream.read(1024*1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() != self.inputs[str(db_path.relative_to(self.root))]["sha256"]:
                raise ValueError("HWSD database differs from original FAO archive")
        with zipfile.ZipFile(map_zip) as z:
            member = next(n for n in z.namelist() if Path(n).name == "HWSD2.bil")
        with rasterio.open(f"/vsizip/{map_zip.resolve()}/{member}") as ds:
            x, y = transform("EPSG:4326", ds.crs, [LON], [LAT])
            row, col = ds.index(x[0], y[0])
            sample = ds.read(1, window=Window(col,row,1,1), masked=True)[0,0]
            if np.ma.is_masked(sample) or finite(sample) is None or sample <= 0:
                raise ValueError("HWSD has no soil mapping unit at supplied point")
            unit_id = int(sample)
            x, y = ds.xy(row,col)
            lon, lat = transform(ds.crs, "EPSG:4326", [x], [y])
            cell = f"hwsd2_unit{unit_id}_r{row}_c{col}"
            self.point_cell(cell, lat[0], lon[0], row=row, column=col,
                            crs=ds.crs.to_string(), spacing_degrees=list(ds.res),
                            soil_mapping_unit=unit_id, support="regional mapping unit; not field measurement",
                            selection="containing original map pixel at unchanged user coordinates",
                            map_source_id=map_source)
        database = AccessParser(str(db_path))
        metadata = database.parse_table("HWSD2_LAYERS_METADATA")
        units = {field.strip(): metadata["UNIT"][i] for i, field in enumerate(metadata["FIELD"])}
        expected = {"PH_WATER": "-log(H+)", "TOTAL_N": "g/kg", "ORG_CARBON": "% weight",
                    "SAND": "% weight", "SILT": "% weight", "CLAY": "% weight",
                    "TOPDEP": "cm", "BOTDEP": "cm"}
        if any(units.get(key) != value for key,value in expected.items()):
            raise ValueError("HWSD source database units differ from documented conversions")
        table = database.parse_table("HWSD2_LAYERS")
        candidates = [{key: values[i] for key, values in table.items()}
                      for i, identifier in enumerate(table["HWSD2_SMU_ID"]) if identifier == unit_id]
        selected, sequence, shares = choose_hwsd_component(candidates)
        rows = []
        mapping = [("PH_WATER","ph",1,"pH"),("TOTAL_N","total_nitrogen",1,"g/kg"),
                   ("ORG_CARBON","organic_carbon",10,"g/kg"),
                   ("SAND","sand",1,"%"),("SILT","silt",1,"%"),("CLAY","clay",1,"%")]
        for layer in selected:
            texture = [finite(layer[key]) for key in ["SAND","SILT","CLAY"]]
            valid_texture = all(v is not None for v in texture) and 95 <= sum(v or 0 for v in texture) <= 105
            for key, variable, multiplier, canonical_unit in mapping:
                native = finite(layer[key])
                value, flag, reason = clean(native*multiplier if native is not None else None, variable)
                if not valid_texture:
                    value, flag, reason = None, "invalid", "invalid_texture_mass_balance"
                elif flag == "valid":
                    flag, reason = "regional_estimate", f"FAO regional mapping unit {unit_id}, component {sequence}, share {shares[sequence]}%; not a field soil test"
                rows.append(measurement(variable,value,canonical_unit,native,units[key],cell,db_source,
                                        top=int(layer["TOPDEP"]),bottom=int(layer["BOTDEP"]),flag=flag,reason=reason))
        self.report["soil_fallback"] = {
            "dataset": "FAO/IIASA HWSD v2 original database",
            "status": "regional_estimate_available" if all(r["quality_flag"] == "regional_estimate" for r in rows) else "review_required",
            "point_changed": False, "soil_mapping_unit": unit_id, "component_sequence": sequence,
            "component_share_pct": shares[sequence], "all_component_shares": shares,
            "map_source_id": map_source, "attribute_source_id": db_source,
            "units_verified_from": "HWSD2_LAYERS_METADATA in original FAO database",
            "depth_policy": "native seven layers retained; no interpolation to SoilGrids depths",
            "acceptance": "Use only when a regional-estimate fallback is explicitly accepted; preserve source/quality labels. No field-scale accuracy is established."}
        self.emit("hwsd_soil_harrow.csv", rows, "Explicit regional fallback at original coordinates; original soil mapping unit and dominant component; no neighbor copying; source metadata units verified")
        self.outputs["data/seed/hwsd_soil_harrow.csv"]["map_source_id"] = map_source

    def save(self, dataset):
        self.report["cells"] = self.cells
        self.report["input_files"] = self.inputs
        signature = hashlib.sha256(json.dumps({"dataset": dataset, "inputs": self.inputs, "code": sha256(__file__)}, sort_keys=True).encode()).hexdigest()
        run_id = signature[:16]
        self.report["run_id"] = run_id
        report_path = self.seed / f"quality_report_{dataset}.csv"
        write_csv(report_path, [{"section": k, "metadata": json.dumps(v, allow_nan=False)} for k,v in self.report.items()])
        # Merge separate notebook runs, retaining other completed derived tables.
        self.manifest.setdefault("derived_datasets", {}).update(self.outputs)
        for cell, details in self.cells.items():
            old = self.manifest.setdefault("resolved_cells", {}).get(cell, {})
            if old.get("resolved_cell_status", "").startswith("documented_merra2"):
                details = old
            self.manifest["resolved_cells"][cell] = details
        runs = self.manifest.setdefault("processing_runs", [])
        if not any(r["run_id"] == run_id for r in runs):
            runs.append({"run_id": run_id, "stage": "data_handoff", "dataset": dataset,
                         "processed_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                         "point": {"latitude": LAT, "longitude": LON, "status": "user_supplied"},
                         "input_files": self.inputs, "outputs": self.outputs,
                         "quality_report": str(report_path.relative_to(self.root)),
                         "code_sha256": sha256(__file__)})
        self.manifest.setdefault("source_verifications", {}).update({"imerg": self.report["imerg_verification"]} if "imerg_verification" in self.report else {})
        if "soil_fallback" in self.report:
            self.manifest.setdefault("source_verifications", {})["soil_fallback"] = self.report["soil_fallback"]
        self.manifest["scientific_data_processing_performed"] = True
        self.manifest.setdefault("readiness", {})["stage1"] = {
            "status": "processed_with_quality_flags",
            "review_required_outputs": sorted(path for path, info in self.manifest["derived_datasets"].items()
                                              if info["scientific_verdict"] != "usable"),
            "trend_and_buddy": "see cached grid checks and trend_results.csv"}
        self.manifest["readiness"]["value_quality_check"] = "performed for derived outputs; see per-source verdicts"
        self.manifest["readiness"]["raw_input_acquisition"] = "files acquired; file presence does not imply valid Harrow measurements"
        self.manifest.setdefault("review_state", {})["quality"] = "see derived_datasets and latest processing quality report"
        self.manifest["review_state"]["cell_selection"] = "GLDAS and soil pixels selected; POWER centres empirically checked, upstream identifier not exposed"
        if self.manifest_path.suffix == ".csv":
            save_manifest(self.manifest, self.root)
        else:
            self.manifest_path.write_text(json.dumps(self.manifest, indent=2, allow_nan=False)+"\n")
        return self.report


def run(dataset="all", root=ROOT):
    pipeline = Pipeline(root)
    if dataset in ["all", "climate"]:
        pipeline.climate(); pipeline.water()
    if dataset in ["all", "soil"]:
        pipeline.soil(); pipeline.hwsd()
    return pipeline.save(dataset)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=["all", "climate", "soil"], default="all")
    args = parser.parse_args()
    report = run(args.dataset)
    print(json.dumps({"run_id": report["run_id"], "datasets": report["datasets"], "issues": report["issues"]}, indent=2))


if __name__ == "__main__":
    main()
