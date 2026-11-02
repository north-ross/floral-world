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
import time
from datetime import datetime, timezone, timedelta
from zipfile import ZipFile
import pandas as pd
import geopandas as gpd
import numpy as np
import requests


WCVP_URL = "https://sftp.kew.org/pub/data-repositories/WCVP/wcvp.zip"
# Present in the current WCVP archive but absent from the bundled map.
# I updated the map data to re add these, so I've removed all the unmapped codes. I
UNMAPPED_CODES = frozenset({})
MAP_PATH = Path(__file__).with_name("level3.json")
NAME_COLUMNS = ["plant_name_id", "taxon_status", "taxon_rank", "family", "climate_description"]
DISTRIBUTION_COLUMNS = ["plant_name_id", "area_code_l3", "introduced", "extinct"]
WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"
QUERY_PATH = Path(__file__).with_name("wikidata-sparql-query.rq")
COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"
IMAGE_CACHE_PATH = Path(__file__).with_name("commons-image-cache.json")
WIKIDATA_SNAPSHOT_PATH = Path(__file__).with_name("wikidata-info-snapshot.json")
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

def load_image_cache():
    """Load cache of image URL and metadata from wiki commons API query"""
    if IMAGE_CACHE_PATH.exists():
        with open(IMAGE_CACHE_PATH) as f:
            return json.load(f)
    return {}

def save_image_cache(cache):
    """save cache of image URL and metadata"""
    with open(IMAGE_CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2, sort_keys=True)

def get_commons_info_cached(raw_image_url, cache):
    """Read wikimedia commons info from cache"""
    if raw_image_url in cache:
        return cache[raw_image_url], None  # cache hit, no error to report
    filename = commons_url_to_filename(raw_image_url)
    result, error = fetch_commons_info(filename)
    if result is not None:
        cache[raw_image_url] = result  # only cache successes
    return result, error

def save_wikidata_snapshot(wikidata_info):
    payload = {"fetched_at": datetime.now(timezone.utc).isoformat(), "data": wikidata_info}
    with open(WIKIDATA_SNAPSHOT_PATH, "w") as f:
        json.dump(payload, f, sort_keys=True)

def load_fresh_snapshot(max_age=timedelta(days=5)):
    if not WIKIDATA_SNAPSHOT_PATH.exists():
        return None
    with open(WIKIDATA_SNAPSHOT_PATH) as f:
        payload = json.load(f)
    age = datetime.now(timezone.utc) - datetime.fromisoformat(payload["fetched_at"])
    return payload["data"] if age < max_age else None

def load_wikidata_snapshot():
    if WIKIDATA_SNAPSHOT_PATH.exists():
        with open(WIKIDATA_SNAPSHOT_PATH) as f:
            payload = json.load(f)
        print(f"Using Wikidata snapshot from {payload['fetched_at']}", file=sys.stderr)
        return payload["data"]
    return None

def fetch_wikidata_info_with_fallback(family_names, chunk_size=50, delay_between_chunks=2):
    fresh = load_fresh_snapshot()
    if fresh is not None:
        print("Using fresh Wikidata snapshot, skipping query", file=sys.stderr)
        return fresh
    try:
        result = fetch_wikidata_info(family_names, chunk_size, delay_between_chunks)
        save_wikidata_snapshot(result)
        return result
    except (requests.exceptions.ReadTimeout, requests.exceptions.HTTPError) as e:
        print(f"Wikidata fetch failed ({e}); falling back to last snapshot", file=sys.stderr)
        snapshot = load_wikidata_snapshot()
        if snapshot is None:
            raise RuntimeError("Wikidata fetch failed and no prior snapshot exists") from e
        return snapshot

def fetch_wikidata_chunk(query, headers, retries=4, base_delay=10):
    for attempt in range(retries):
        try:
            response = requests.get(
                WIKIDATA_SPARQL_URL, params={"query": query},
                headers=headers, timeout=60,
            )
            response.raise_for_status()
            return response.json()["results"]["bindings"]
        except (requests.exceptions.ReadTimeout, requests.exceptions.HTTPError) as e:
            is_retryable_status = isinstance(e, requests.exceptions.ReadTimeout) or (
                e.response is not None and e.response.status_code in (502, 503, 504)
            )
            if not is_retryable_status or attempt == retries - 1:
                raise
            wait = base_delay * (2 ** attempt)
            print(f"{type(e).__name__}, retrying in {wait}s (attempt {attempt+1}/{retries})", file=sys.stderr)
            time.sleep(wait)

def fetch_wikidata_info(family_names, chunk_size=50, delay_between_chunks=2):
    headers = {
        "Accept": "application/sparql-results+json",
        "User-Agent": "floral-world/1.0 (https://github.com/north-ross/floral-world)",
    }
    all_bindings = []
    for i in range(0, len(family_names), chunk_size):
        chunk = family_names[i:i + chunk_size]
        values_clause = " ".join(f'"{name}"' for name in chunk)
        query = SPARQL_TEMPLATE.replace("$familiesList$", values_clause)
        # print(f"Requesting wikidata query for families {i} - {i+chunk_size}")
        wd_chunk = fetch_wikidata_chunk(query, headers)
        all_bindings.extend(wd_chunk)
        if i + chunk_size < len(family_names):
            time.sleep(delay_between_chunks)

    return bindings_to_dict(all_bindings)

#%%
def bindings_to_dict(bindings):
    """Group SPARQL rows by family name; each row -> plain dict with missing OPTIONALs as None."""
    result = {}
    for row in bindings:
        family = row["taxonname"]["value"]
        parsed = {var: val["value"] for var, val in row.items() if var != "taxonname"}
        result.setdefault(family, []).append(parsed)
    return result
#%%
def fetch_commons_info(filename, width=300):
    """Get thumbnail image and attribution for filename fetched from wikidata
        So it can be displayed properly on the site.
        Returns (info_dict_or_None, error_str_or_None)."""
        # Seems like there are some other author values this isnt returning. 
        # I'd also like to get the "depicts" wikidata property for the caption
        # SOme pages seem to have it listd under Attribution in the licence
    params = {
        "action": "query",
        "titles": f"File:{filename}",
        "prop": "imageinfo|sdc",
        "iiprop": "url|extmetadata|user",
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
        return re.sub("<[^>]+>", "", val).strip().replace("&amp;", "&") if val else None

    artist = clean("Artist")
    uploader = info.get("user")
    if artist:
        credit, credit_kind = artist, "artist"
    elif uploader:
        credit, credit_kind = uploader, "uploader"
    else:
        credit, credit_kind = None, None
    return {
        "thumbUrl": info["thumburl"],
        # "imageDescription": clean('ImageDescription'),
        "descriptionUrl": info["descriptionurl"],
        "author": [credit_kind, credit],
        "license": clean("LicenseShortName"),
        "licenseUrl": clean("LicenseUrl"), # set this one up as a dict to save space?
        # "category0": clean("Categories").split('|')[0]
    }, None
#%%

def commons_url_to_filename(image_url):
    """Wikidata P18 gives a Special:FilePath URL; Commons API needs the raw title."""
    if not image_url:
        return None
    encoded_name = urlparse(image_url).path.rsplit("/", 1)[-1]
    return unquote(encoded_name)

def build_richness(names, distributions, area_codes, gdf, wikidata_fetcher=fetch_wikidata_info_with_fallback):
    """Deterministic aggregation; duplicate localities never inflate species richness."""
    species = names.loc[(names.taxon_status == "Accepted") &
                        (names.taxon_rank == "Species"), NAME_COLUMNS].drop_duplicates()
    if species.empty:
        raise ValueError("No accepted species in WCVP names")
    if species[["plant_name_id", "family"]].isna().any().any():
        raise ValueError("Accepted species must have an ID and family")
    if species.plant_name_id.duplicated().any():
        raise ValueError("Conflicting accepted species records for the same ID")

    # Get counts for native, introduced and extinct species
    d = distributions.merge(species[["plant_name_id", "family"]], on="plant_name_id")
    d = d[d.area_code_l3.notna() & (d.area_code_l3 != "")]

    # Run the unknown-code check here on d.area_code_l3 now, instead of on `native`
    is_intro = (d.introduced == "1").fillna(False).to_numpy()
    is_ext = (d.extinct == "1").fillna(False).to_numpy()
    d["bucket"] = np.select([is_intro, is_ext], ["introduced", "extinct"], default="native")
    d = d.drop_duplicates(["plant_name_id", "area_code_l3", "bucket"])
    counts = (d.groupby(["family", "area_code_l3", "bucket"]).plant_name_id
                .nunique().unstack(fill_value=0))

    # Calculate global count for each bucket
    # For extinct, it needs to be extinct everywhere, meaning .all()
    d['is_intro'] = is_intro
    d['is_ext'] = is_ext
    extinct_plants = (d[['plant_name_id', 'family', 'is_ext']]
                        .groupby(['family', 'plant_name_id']).all())
    extinct_counts = extinct_plants.loc[extinct_plants.is_ext].groupby('family').count()
    # Native (native extant) is the inverse of extinct:
    native_counts = (extinct_plants.loc[~extinct_plants.is_ext]
                        .groupby('family').count().rename(columns={"is_ext": 'native'}))
    # The total introduced means all plants that are introduced somwhere, even if they have a 
    #   native range. Therefore it's not additive with the others
    # And we need to use .any() instead of .all() because of this
    introduced_plants = (d[['plant_name_id', 'family', 'is_intro']]
                            .groupby(['family', 'plant_name_id']).any())
    introduced_counts = introduced_plants.loc[introduced_plants.is_intro].groupby('family').count()
    # Join all of the counts
    global_count = (native_counts.join(introduced_counts, how="outer").join(extinct_counts, how="outer")
                                .fillna(0).astype('int'))
    global_count_lookup = dict(zip(global_count.index, global_count.to_numpy().tolist()))

    # Count endemics
    native = d[d.bucket != "introduced"]
    n_areas = native.groupby("plant_name_id").area_code_l3.transform("nunique")
    endemics = (native[n_areas == 1].groupby(['family', 'area_code_l3'])
                .plant_name_id.nunique().rename("endemic"))
    # Since each endemic is only in one area, we can just sum to get the global count
    endemic_global = endemics.groupby(level="family").sum()

    counts = (counts.join(endemics, how="left")
                    .reindex(columns=["native", "introduced", "extinct", "endemic"], fill_value=0)
                    .fillna(0).astype('int'))
    # get counts as a collection of dicts to better put into the dict later
    counts_lookup = dict(zip(counts.index, counts.to_numpy().tolist()))

    unmapped = set(native.area_code_l3) - set(area_codes)
    unknown = unmapped - UNMAPPED_CODES
    if unknown:
        raise ValueError(f"Unknown WGSRPD level 3 codes: {sorted(unknown)}")
    if unmapped:
        print(f"WCVP areas absent from level3.json (excluded from area counts): {sorted(unmapped)}", file=sys.stderr)

    # Get the list of countries for each latitudinal band from the geodataframe
    # For building the latitudinal diversity gradient (LDGs)
    ldg_areas_dict = {}
    band_size=10
    for i in range(-90, 90, band_size):
        # select countries in bounding box of this latitude band
        ldg_countries = gdf.cx[:, i : i+band_size].LEVEL3_COD
        # key is the lower limit of the band
        ldg_areas_dict[i] = ldg_countries

    # one row per (area, band), built from the bbox logic
    band_map = pd.concat(
        [pd.DataFrame({"area_code_l3": codes.values, "band": i}) for i, codes in ldg_areas_dict.items()]
    )
    ldg_counts = (native.merge(band_map, on="area_code_l3")
                        .groupby(["family", "band"]).plant_name_id.nunique())

    # Get info from wikidata
    family_names = species.family.unique()
    wikidata_info = wikidata_fetcher(family_names)
    # Log taxa with no wikidata page
    taxa_notfound = [x for x in family_names if x not in wikidata_info.keys()]
    if taxa_notfound:
        print(f"Families not found in wikidata query: {sorted(taxa_notfound)}", file=sys.stderr)

    result = {}
    image_cache = load_image_cache()

    image_failures = []

    for family, group in species.groupby("family", sort=True):
        climates = group.climate_description.dropna().str.lower()
        climates_dict = climates.groupby(climates).count().to_dict()
        # Combine the rare "subtropical or tropical" value into "subtropical"
        if climates_dict.get("subtropical or tropical", None):
            climates_dict["subtropical"] += climates_dict["subtropical or tropical"]
            climates_dict.pop("subtropical or tropical", None)
        # And similarly add "temperate, subtropical or tropical" into "temperate"
        if climates_dict.get("temperate, subtropical or tropical", None):
            climates_dict["temperate"] += climates_dict["temperate, subtropical or tropical"]
            climates_dict.pop("subtropical or tropical", None)
        wd_list = wikidata_info.get(family, [])
        wd = wd_list[0] if wd_list else {}

        img_dict = {}
        raw_image = wd.get("image")
        if raw_image:
            img_dict, error = get_commons_info_cached(raw_image, image_cache)
            filename = commons_url_to_filename(raw_image)

            if error:
                image_failures.append({"family": family, "raw_image": raw_image,
                                        "filename": filename, "error": error})

        # Add tag for image depicts label
        img_dict['depicts'] = wd.get('imageDepictsLabel', None)

        result[family] = {
            "sr": {code: counts_lookup[(family, code)]
                    for code in sorted(set(area_codes))
                    if (family, code) in counts_lookup},
            "global": global_count_lookup.get(family),
            "globalEndemic": int(endemic_global.get(family, 0)),
            "climate": climates_dict,
            "ids": {
                'wikidata': wd.get('item', None),
                'inatId': wd.get('inatId', None),
                'colId': wd.get('colId', None),
                'powoId': wd.get('powoId', None)
                },
            "image": img_dict,
            "ldg": {int(b): int(ldg_counts.get((family, b), 0)) for b in ldg_areas_dict}
        }
    save_image_cache(image_cache)

    if image_failures:
        print(f"Image lookup failed for {len(image_failures)} families:", file=sys.stderr)
        for fail in image_failures:
            print(f"  {fail['family']}: {fail['error']} (filename={fail['filename']!r})", file=sys.stderr)
    
    # licenses_set = {x['image']['license'] for x in result.values() if x['image']}
    # print(licenses_set)
    return result

#%%
def load_archive(archive, area_codes, wikidata_fetcher=fetch_wikidata_info_with_fallback):
    with ZipFile(archive) as zf:
        with zf.open("wcvp_names.csv") as source:
            names = pd.read_csv(source, sep="|", usecols=NAME_COLUMNS, dtype="string")
        with zf.open("wcvp_distribution.csv") as source:
            distributions = pd.read_csv(source, sep="|", usecols=DISTRIBUTION_COLUMNS, dtype="string")
    gdf = gpd.read_file(MAP_PATH, layer="level3")
    return build_richness(names, distributions, area_codes, gdf, wikidata_fetcher=wikidata_fetcher)

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
    # with open('src/data/family-area-sr.json', 'w') as outfile:
    #     json.dump(result, outfile, allow_nan=False, sort_keys=True)
    #     print("wrote to file")
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
