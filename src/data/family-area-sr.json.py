"""Data loader for the family-area-sr.json file
Reads from WCVP archive
"""
#%%
import json
import sys
from zipfile import ZipFile
from io import BytesIO
from urllib.request import urlopen
import pandas as pd
import numpy as np

WCVP_URL = "https://sftp.kew.org/pub/data-repositories/WCVP/wcvp.zip"

# Download zip into memory
with urlopen(WCVP_URL) as response:
    zip_data = BytesIO(response.read())

with ZipFile(zip_data) as zf:
    # WCVP dataframe of plant names
    df = pd.read_csv(zf.open("wcvp_names.csv"), sep="|")
    # WCVP dataframe of plant distributions
    ddf = pd.read_csv(zf.open("wcvp_distribution.csv"), sep="|")

# Rank countries based on species richness within each family

# Get list of accepted species in family
species = df.loc[(df['taxon_status']=="Accepted") & (df['taxon_rank']=="Species")]

# Now filter the distributions df to only include native plants from our query
species_ids = species[['plant_name_id', 'family']]
filtered_ddf = ddf.merge(species_ids, on='plant_name_id', how='inner')
# remove introduced species
filtered_ddf = filtered_ddf.loc[filtered_ddf['introduced']==0]

# Group this to just get a count of unique plant_name_ids in each area_code_l3
sr = filtered_ddf[['area_code_l3', 'plant_name_id', 'family']].pivot_table(
    index='area_code_l3',
    columns = 'family',
    values='plant_name_id',
    aggfunc=pd.Series.nunique
    )
sr = sr.fillna(0)

# Add "total" species richness column for each area
# TODO: calculate this in the app instead
# sr['Vascular Plants'] = sr.sum(axis=1)

#%%
# Write to json

# Get global SR by family
global_sr = species.groupby('family').agg(pd.Series.nunique).to_dict()

# Get most common climate by family
modal_climate = species[['family', 'climate_description']]\
    .groupby('family')\
        .agg(pd.Series.mode).to_dict()

sr_dict = {}
def getSrJson(x):
    # Convert modal climate to a scalar or list
    climate_val = modal_climate['climate_description'][x.name]
    if isinstance(climate_val, np.ndarray):
        climate_val = climate_val[0] if len(climate_val) > 0 else None

    sr_dict[x.name] = {
        'sr': x.to_dict(), 
        'global': int(global_sr['plant_name_id'][x.name]),
        'climate': climate_val
        }
sr.apply(lambda x: getSrJson(x))
#%%

json.dump(sr_dict, sys.stdout)
# with open('family-area-sr.json', "w") as f:
#     json.dump(sr_dict, f)

# %%
