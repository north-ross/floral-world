"""Build family richness from accepted WCVP species and native distributions.

Run without arguments as an Observable loader, or pass --archive for an offline
validation of a downloaded WCVP ZIP. Diagnostics go to stderr; stdout is JSON.
"""
#%%
import argparse
from io import BytesIO
import json
from pathlib import Path
import sys
from urllib.request import urlopen
from urllib.parse import urlparse, unquote
import re
from zipfile import ZipFile
import pandas as pd
import requests


WCVP_URL = "https://sftp.kew.org/pub/data-repositories/WCVP/wcvp.zip"
# Present in the current WCVP archive but absent from the bundled map.
# I updated the map data to re add these, so I've removed all the unmapped codes. I
UNMAPPED_CODES = frozenset({})
MAP_PATH = Path(__file__).with_name("level3.json")
NAME_COLUMNS = ["plant_name_id", "taxon_status", "taxon_rank", "family", "climate_description"]
DISTRIBUTION_COLUMNS = ["plant_name_id", "area_code_l3", "introduced"]
WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"
QUERY_PATH = Path(__file__).with_name("wikidata-sparql-query.rq")
COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"
with open(QUERY_PATH) as f:
    SPARQL_TEMPLATE = f.read()
#%%

def map_codes(path=MAP_PATH):
    with open(path) as source:
        topology = json.load(source)
    return sorted({geometry["properties"]["LEVEL3_COD"]
                   for obj in topology["objects"].values()
                   for geometry in obj["geometries"]})
#%%
def fetch_wikidata_info(family_names, chunk_size=100):
    headers = {
        "Accept": "application/sparql-results+json",
        "User-Agent": "floral-world/1.0 (https://github.com/north-ross/floral-world)",
    }
    all_bindings = []
    for i in range(0, len(family_names), chunk_size):
        chunk = family_names[i:i + chunk_size]
        values_clause = " ".join(f'"{name}"' for name in chunk)
        query = SPARQL_TEMPLATE.replace("$familiesList$", values_clause)
        print(f"Requesting query {i} ({chunk_size})")
        response = requests.get(
            WIKIDATA_SPARQL_URL,
            params={"query": query},
            headers=headers,
            timeout=90,
        )
        response.raise_for_status()
        all_bindings.extend(response.json()["results"]["bindings"])
        
    return bindings_to_dict(all_bindings)
    # return all_bindings
#%%
def bindings_to_dict(bindings):
    """Group SPARQL rows by family name; each row -> plain dict with missing OPTIONALs as None."""
    result = {}
    for row in bindings:
        family = row["taxonname"]["value"]
        parsed = {var: val["value"] for var, val in row.items() if var != "taxonname"}
        result.setdefault(family, []).append(parsed)
    return result

def fetch_commons_info(filename, width=300):
    """Get thumbnail image and attribution for filename fetched from wikidata
        So it can be displayed properly on the site.
        Returns (info_dict_or_None, error_str_or_None)."""
        # TODO: can I get the wikipedia user if no artist tag?
        # Seems like there are some other author values this isnt returning. 
        # I'd also like to get the "depicts" wikidata property for the caption
        # SOme pages seem to have it listd under Attribution in the licence
    params = {
        "action": "query",
        "titles": f"File:{filename}",
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiurlwidth": width,
        "format": "json",
    }
    headers = {"User-Agent": "floral-world/1.0 (https://github.com/north-ross/floral-world)"}
    try:
        response = requests.get(COMMONS_API_URL, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as e:
        return None, f"request failed: {e}"

    pages = payload.get("query", {}).get("pages", {})
    if not pages:
        return None, "no 'pages' in response"
    page = next(iter(pages.values()))
    if "missing" in page:
        return None, "file missing on Commons (renamed/deleted since Wikidata edit?)"
    if "imageinfo" not in page:
        return None, f"no imageinfo (page keys: {list(page.keys())})"

    info = page["imageinfo"][0]
    if "thumburl" not in info:
        return None, "imageinfo present but no thumburl (non-image file type?)"

    extmeta = info.get("extmetadata", {})
    def clean(field):
        val = extmeta.get(field, {}).get("value")
        # TODO: Clean up the &amp values
        return val if val else None

    return {
        "thumbUrl": info["thumburl"],
        "imageDescription": info['ImageDescription'],
        "descriptionUrl": info["descriptionurl"],
        "author": clean("Artist"),
        "license": clean("LicenseShortName"),
        "licenseUrl": clean("LicenseUrl"), # set this one up as a dict to save space?
        "objectName": clean("ObjectName")
    }, None
#%%

def commons_url_to_filename(image_url):
    """Wikidata P18 gives a Special:FilePath URL; Commons API needs the raw title."""
    if not image_url:
        return None
    encoded_name = urlparse(image_url).path.rsplit("/", 1)[-1]
    return unquote(encoded_name)

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

    # Get info from wikidata
    family_names = species.family.unique()
    wikidata_info = fetch_wikidata_info(family_names)
    # Log taxa with no wikidata page
    taxa_notfound = [x for x in family_names if x not in wikidata_info.keys()]
    if taxa_notfound:
        print(f"Families not found in wikidata query: {sorted(taxa_notfound)}")

    result = {}
    image_failures = []

    for family, group in species.groupby("family", sort=True):
        climates = group.climate_description.dropna()
        modes = climates[climates != ""].mode()
        wd_list = wikidata_info.get(family, [])
        wd = wd_list[0] if wd_list else {}

        img_dict = None
        raw_image = wd.get("image")
        if raw_image:
            filename = commons_url_to_filename(raw_image)
            img_dict, error = fetch_commons_info(filename)
            if error:
                image_failures.append({"family": family, "raw_image": raw_image,
                                        "filename": filename, "error": error})

        result[family] = {
            "sr": {code: int(counts.get((family, code), 0)) for code in sorted(set(area_codes))},
            # WCVP names contains no family-rank records. Species IPNI IDs are
            # not family IDs; leave this unavailable until an authority is added.
            "ipni_id": None,
            "global": int(group.plant_name_id.nunique()),
            "climate": str(modes.iloc[0]) if not modes.empty else None,
            "ids": {
                'inatId': wd.get('inatId', None),
                'colId': wd.get('colId', None),
                'powoId': wd.get('powoId', None)
                },
            "image": img_dict
        }

    if image_failures:
        print(f"Image lookup failed for {len(image_failures)} families:", file=sys.stderr)
        for f in image_failures:
            print(f"  {f['family']}: {f['error']} (filename={f['filename']!r})", file=sys.stderr)
    return result

#%%
def load_archive(archive, area_codes):
    with ZipFile(archive) as zf:
        with zf.open("wcvp_names.csv") as source:
            names = pd.read_csv(source, sep="|", usecols=NAME_COLUMNS, dtype="string")
        with zf.open("wcvp_distribution.csv") as source:
            distributions = pd.read_csv(source, sep="|", usecols=DISTRIBUTION_COLUMNS, dtype="string")
    return build_richness(names, distributions, area_codes)

#%%
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
    with open('src/data/family-area-sr.json', 'w') as outfile:
        json.dump(result, outfile, allow_nan=False, sort_keys=True)
        print("wrote to file")
    sys.stdout.write("\n")
    

if __name__ == "__main__":
    main()
