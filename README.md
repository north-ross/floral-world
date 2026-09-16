# Floral World
An app to explore global vascular plant biodiversity using data from the [World Checklist for Vascular Plants](https://www.tdwg.org/standards/wgsrpd/). A map shows the species richness for each "botanical country" (WGSRPD level 3 division) and can be filtered by family. Tables let the user discover the "unique families" of each area, and what percentage of global biodiversity they contain.


This is an [Observable Framework](https://observablehq.com/framework/) app. For more, see <https://observablehq.com/framework/getting-started>.

## About
The World Checklist for Vascular Plants divides the world's [vascular plants](https://en.wikipedia.org/wiki/Vascular_plant) into ${Object.keys(sr).length -1} families and aggregates their distributions into "botanical countries". This site is used to explore the number of species in different areas, a useful measure of global biodiversity ([α-diversity](https://en.wikipedia.org/wiki/Alpha_diversity)). 

Since the boundaries used for aggregation are somewhat arbitrary, this visualization can't be taken too seriously as representing centers of biodiversity. See [this article](https://www.nature.com/articles/s41467-022-32063-z) for a much more scientific approach. However, this approach is much less computationally intensive, and the overall patterns still hold true. I've found it very interesting to explore different families and find the unique "specialty" families from different parts of the world.

## Planned features
### Priority
- [ ] Add data loader to keep site up-to-date
  - [ ] Test that it work properly
  - [x] Fix it so it builds json correctly, and write code to get derived values (ties etc) in js
  - [x] Add data loader for common names
- [x] Get common names for families (from [iNat taxonomy DarwinCore archive](https://www.inaturalist.org/pages/developers))
  - [ ] Maybe replace this with the more complete dataset from [Catalogue of Life API](https://www.checklistbank.org/about/formats#data-content)
- [ ] Query Wikidata to add links to wikipedia, iNat, CoL paleobio database. 
  - [ ] Embed an image from wikidata, and maybe the heading of the Wikipedia page in a collapsable summary box
- [ ] Add some text about the "specialty" family for each area
  - [ ] From the country-wise (global) ranking for families, get the highest ranked for this (using averages for ties), excluding absent taxa (i.e. in Antarctica)
  - [x] How does this taxa compare to global average? Maybe pick the family with the largest % difference between here and average.
  - [x] For countries that have multiple families where they're #1, include the number of them
- [x] Selecting a family from the countries table updates the selected family reactively
- [ ] Selecting a new family or area updates the table select options

### Lower priority
- [ ] Add explanatory tooltips, maybe an intro splash page?
- [ ] Fix the flickering when selecting a country from the map
- [ ] Pan/zoom map and change projection
  - (This is probably not possible anymore now that I've built it with two overlaying maps)
- [ ] Add some higher-level categories like "ferns"
- [ ] In the family info box, include some "iconic species" (maybe most observed on iNat)
- [ ] Filter data to include introduced ranges or exclude extinct species
- [ ] Chart of preferred climate for each species by family
- [ ] Line chart of species richness by latitude
- [ ] Show a list of species in selected area-family
- [ ] Number of endemic species to each area
  - [ ] Will need to make small islands more visible

## Development and validation

Install Node.js 20+ and Python 3.12+, then install dependencies in a virtual environment:

```sh
npm ci
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
npm test
python -m unittest discover -s tests -v
npm run build
```

The tests use small, offline fixtures and run on pushes and pull requests. The
WCVP loader runs during builds; do not commit `src/data/family-area-sr.json`, as
an existing file takes precedence over the Observable loader. Observable caches
loader output; use `npm run clean` before a fresh data build.

To validate a downloaded current WCVP archive without downloading it again:

```sh
python src/data/family-area-sr.json.py --archive /path/to/wcvp.zip > /tmp/family-area-sr.json
WCVP_ARCHIVE=/path/to/wcvp.zip python -m unittest discover -s tests -v
```

Without `--archive`, the loader downloads Kew's current archive. It counts unique
accepted species with native distributions (`introduced == 0`), retaining the
existing treatment of extinct and doubtful localities. Global counts include
all accepted species, including those without native distribution records.
Localities recorded only at continent or region level have no level 3 code and
are excluded from area counts, while their species remain in global counts.
Every family contains integer richness for every code in `level3.json`, with
zero for absent species. Twenty WCVP codes are absent from the bundled map; the
loader explicitly lists these in `UNMAPPED_CODES`, reports them on stderr, and
excludes their localities from area counts without affecting global counts.
Updating the map is a separate task. Other unknown native distribution codes or
conflicting accepted species records fail the build instead of silently changing counts.
Climate is the most frequent nonempty description; ties use the first value
alphabetically, and missing climates become `null`.

The current WCVP names archive contains no family-rank records, so `ipni_id` is
`null`. Species or genus IPNI identifiers must not be used as family identifiers;
family IDs require a separate authoritative source in a future enrichment change.
All-zero family rankings likewise use `null` for the undefined percentage above
the mean, consistent with the existing nullable percentage field.
