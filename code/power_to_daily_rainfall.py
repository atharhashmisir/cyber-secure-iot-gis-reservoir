"""Convert a NASA POWER daily point CSV (columns YEAR, DOY, PRECTOTCORR) to the 'date,rain_mm' format used by make_figures.py.
Usage: python power_to_daily_rainfall.py POWER_Point_Daily_....csv daily_rainfall.csv
PRECTOTCORR is MERRA-2 corrected precipitation in mm/day; -999 (missing) rows are skipped."""
import csv, sys, datetime as dt

src, dst = sys.argv[1], sys.argv[2]
with open(src, newline="", encoding="utf-8-sig") as f:
    lines = f.read().splitlines()
start = next(i for i, l in enumerate(lines) if l.split(",")[0].strip() == "YEAR")  # skip the metadata header
n = skipped = 0
with open(dst, "w", newline="") as out:
    w = csv.writer(out); w.writerow(["date", "rain_mm"])
    for r in csv.DictReader(lines[start:]):
        v = float(r["PRECTOTCORR"])
        if v <= -990: skipped += 1; continue
        if "DOY" in r: d = dt.date(int(r["YEAR"]), 1, 1) + dt.timedelta(days=int(r["DOY"]) - 1)
        else: d = dt.date(int(r["YEAR"]), int(r["MO"]), int(r["DY"]))
        w.writerow([d.isoformat(), f"{v:.2f}"]); n += 1
print(f"wrote {n} days to {dst}; skipped {skipped} missing")
