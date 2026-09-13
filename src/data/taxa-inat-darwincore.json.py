import json
import sys
from zipfile import ZipFile
from io import BytesIO
from urllib.request import urlopen
import pandas as pd
import numpy as np

DWCA_URL = "https://www.inaturalist.org/taxa/inaturalist-taxonomy.dwca.zip"

# Download zip into memory
with urlopen(DWCA_URL) as response:
    zip_data = BytesIO(response.read())

with ZipFile(zip_data) as zf:
    # iNat taxonomy data
    df = pd.read_csv(zf.open('taxa.csv'))
    # English common names
    eng_df = pd.read_csv(zf.open('VernacularNames-english.csv'))

# Filter to vascular plant families
plant_fam = df[(df['phylum']=="Tracheophyta") & (df['taxonRank']=="family")]

# Get list of common names for each family name as json
sciname_id = plant_fam.set_index('scientificName')['id']
sciname_cmnnames_json = sciname_id.apply(
        lambda x: eng_df[eng_df['id']==x]['vernacularName'].to_list()
    ).to_json(sys.stdout)

# Write json to stdout for build
# json.dump(sciname_cmnnames_json, sys.stdout)

# Or: for testing, to disk
# with open('data/taxa-inat-darwincore.json', "w") as f:
#     json.dump(sciname_cmnnames_json, f)
