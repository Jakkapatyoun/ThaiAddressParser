#!/usr/bin/env python3
"""Download and convert the MIT-licensed Thai geography master data to CSV."""
import csv
import json
import subprocess
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


SOURCE_URL = (
    "https://raw.githubusercontent.com/thailand-geography-data/"
    "thailand-geography-json/main/src/geography.json"
)
ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "data" / "thai_administrative_areas.csv"


def main() -> None:
    try:
        with urlopen(SOURCE_URL) as response:
            rows = json.load(response)
    except URLError:
        # Some macOS Python installations do not have the system CA bundle
        # wired into urllib. curl still validates TLS with the OS trust store.
        downloaded = subprocess.run(
            ["curl", "--fail", "--silent", "--show-error", "--location", SOURCE_URL],
            check=True,
            capture_output=True,
        )
        rows = json.loads(downloaded.stdout)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "subdistrict_code",
        "postal_code",
        "sub_district_th",
        "district_th",
        "province_th",
        "sub_district_en",
        "district_en",
        "province_en",
    ]
    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "subdistrict_code": row["subdistrictCode"],
                "postal_code": row["postalCode"],
                "sub_district_th": row["subdistrictNameTh"],
                "district_th": row["districtNameTh"],
                "province_th": row["provinceNameTh"],
                "sub_district_en": row["subdistrictNameEn"],
                "district_en": row["districtNameEn"],
                "province_en": row["provinceNameEn"],
            })
    print(f"Wrote {len(rows):,} administrative areas to {OUTPUT}")


if __name__ == "__main__":
    main()
