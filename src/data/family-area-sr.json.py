"""Build family richness from accepted WCVP species and native distributions.

Run without arguments as an Observable loader, or pass --archive for an offline
validation of a downloaded WCVP ZIP. Diagnostics go to stderr; stdout is JSON.
"""
import argparse
from io import BytesIO
import json
from pathlib import Path
import sys
from urllib.request import urlopen
from zipfile import ZipFile

import pandas as pd

WCVP_URL = "https://sftp.kew.org/pub/data-repositories/WCVP/wcvp.zip"
# Present in the current WCVP archive but absent from the bundled map.
# I updated the map data to re add these, so I've removed all the unmapped codes. I
UNMAPPED_CODES = frozenset({})
MAP_PATH = Path(__file__).with_name("level3.json")
NAME_COLUMNS = ["plant_name_id", "taxon_status", "taxon_rank", "family", "climate_description"]
DISTRIBUTION_COLUMNS = ["plant_name_id", "area_code_l3", "introduced"]


def map_codes(path=MAP_PATH):
    with open(path) as source:
        topology = json.load(source)
    return sorted({geometry["properties"]["LEVEL3_COD"]
                   for obj in topology["objects"].values()
                   for geometry in obj["geometries"]})


def build_richness(names, distributions, area_codes):
    """Deterministic aggregation; duplicate localities never inflate species richness."""
    species = names.loc[(names.taxon_status == "Accepted") &
                        (names.taxon_rank == "Species"), NAME_COLUMNS].drop_duplicates()
    if species.empty:
        raise ValueError("No accepted species in WCVP names")
    if species[["plant_name_id", "family"]].isna().any().any():
        raise ValueError("Accepted species must have an ID and family")
    if species.plant_name_id.duplicated().any():
        raise ValueError("Conflicting accepted species records for the same ID")

    native = distributions.loc[distributions.introduced.astype("string") == "0"]
    native = native.merge(species[["plant_name_id", "family"]],
                          on="plant_name_id", how="inner", validate="many_to_one")
    # Some WCVP localities specify only a continent or region, not level 3.
    # They cannot be assigned to a map area, but remain in global counts.
    native = native.loc[native.area_code_l3.notna() & (native.area_code_l3 != "")]
    unmapped = set(native.area_code_l3) - set(area_codes)
    unknown = unmapped - UNMAPPED_CODES
    if unknown:
        raise ValueError(f"Unknown WGSRPD level 3 codes: {sorted(unknown)}")
    if unmapped:
        print(f"WCVP areas absent from level3.json (excluded from area counts): {sorted(unmapped)}", file=sys.stderr)
    counts = native.groupby(["family", "area_code_l3"]).plant_name_id.nunique()
    result = {}
    for family, group in species.groupby("family", sort=True):
        # pandas mode sorts ties; choose the first, or null when all are missing.
        climates = group.climate_description.dropna()
        modes = climates[climates != ""].mode()
        result[family] = {
            "sr": {code: int(counts.get((family, code), 0)) for code in sorted(set(area_codes))},
            # WCVP names contains no family-rank records. Species IPNI IDs are
            # not family IDs; leave this unavailable until an authority is added.
            "ipni_id": None,
            "global": int(group.plant_name_id.nunique()),
            "climate": str(modes.iloc[0]) if not modes.empty else None,
        }
    return result


def load_archive(archive, area_codes):
    with ZipFile(archive) as zf:
        with zf.open("wcvp_names.csv") as source:
            names = pd.read_csv(source, sep="|", usecols=NAME_COLUMNS, dtype="string")
        with zf.open("wcvp_distribution.csv") as source:
            distributions = pd.read_csv(source, sep="|", usecols=DISTRIBUTION_COLUMNS, dtype="string")
    return build_richness(names, distributions, area_codes)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, help="Use a local WCVP ZIP instead of downloading")
    args = parser.parse_args()
    if args.archive:
        result = load_archive(args.archive, map_codes())
    else:
        with urlopen(WCVP_URL, timeout=120) as response:
            result = load_archive(BytesIO(response.read()), map_codes())
    json.dump(result, sys.stdout, allow_nan=False, sort_keys=True)
    # with open('src/data/family-area-sr.json', 'w') as f:
    #     json.dump(result, f, allow_nan=False, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
