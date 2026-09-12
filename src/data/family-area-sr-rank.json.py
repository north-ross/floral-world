"""Data loader for the family-area-sr.json file
Reads from WCVP archive
"""
import json
import sys
from zipfile import ZipFile
from io import BytesIO
from urllib.request import urlopen
import pandas as pd

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

# Rank each family. Average method gives us the average value for a tie 
#   so we can better compare between groups
ranked_df = sr.apply(lambda x: x.rank(method='average', ascending=False))

# And get the dense ranking with number of ties for display
def getTieNumber(x):
    dense = x.rank(method='dense', ascending=False)
    diff = x.rank(method='max') - x.rank(method='min') + 1
    tieformat = pd.Series(
        [f"{int(d_val)} ({int(diff_val)}-way tie)"
            if diff_val > 1 else str(int(d_val))
            for d_val, diff_val in zip(dense, diff)],
        index=x.index)
    return tieformat
ranked_df_ties = sr.apply(getTieNumber)

# also get % above average, remove values <0
pct_above_avg = (sr - sr.mean())/sr.mean()
pct_above_avg[pct_above_avg < 0] = None

# Combine all tables
result = pd.concat([sr, ranked_df, ranked_df_ties, pct_above_avg], axis=1,
    keys=['sr','rank', 'tie', 'pct_above_avg'])

# Swap the levels so family is first, sr/rank/tie is second
result = result.swaplevel(0, 1, axis=1).sort_index(axis=1)

# Add "total" species richness column for each area, no ranking
result[('Vascular Plants', 'sr')] = sr.sum(axis=1)

# Now write directly to the json to add family-level traits
result_dict = json.loads(result.to_json())

# Get global SR by family
global_sr = species.groupby('family').agg(pd.Series.nunique).to_dict()
for family, richness in global_sr.items():
    if family in result_dict:
        result_dict[family]['global_sr'] = richness

# Get most common climate by family
modal_climate = species[['family', 'climate_description']]\
    .groupby('family')\
        .agg(pd.Series.mode).to_dict()

for family, climate in modal_climate.items():
    if family in result_dict:
        result_dict[family]['modal_climate'] = climate

json.dump(result_dict, sys.stdout)
# with open('family-area-sr-rank.json', "w") as f:
#     json.dump(result_dict, f)
