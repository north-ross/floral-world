# Floral World
An app to explore global vascular plant biodiversity using data from the [World Checklist for Vascular Plants](https://www.tdwg.org/standards/wgsrpd/). A map shows the species richness for each "botanical country" (WGSRPD level 3 division) and can be filtered by family. Tables let the user discover the "unique families" of each area, and what percentage of global biodiversity they contain.

This is an [Observable Framework](https://observablehq.com/framework/) app. For more, see <https://observablehq.com/framework/getting-started>.

## About
The World Checklist for Vascular Plants divides the world's [vascular plants](https://en.wikipedia.org/wiki/Vascular_plant) into ${Object.keys(sr).length -1} families and aggregates their distributions into "botanical countries". This site is used to explore the number of species in different areas, a useful measure of global biodiversity ([α-diversity](https://en.wikipedia.org/wiki/Alpha_diversity)). 

Since the boundaries used for aggregation are somewhat arbitrary, this visualization can't be taken too seriously as representing centers of biodiversity. See [this article](https://www.nature.com/articles/s41467-022-32063-z) for a much more scientific approach. However, this approach is much less computationally intensive, and the overall patterns still hold true. I've found it very interesting to explore different families and find the unique "specialty" families from different parts of the world.

## Planned features
### Priority
- [x] Add data loader to keep site up-to-date
  - [x] Test that it work properly
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
- [ ] Adapt the page to have a basic level of functionality on mobile
  - [ ] Map should at least stretch to full page width
  - [ ] Add an area selector dropdown/search bar
  - [ ] Maybe even remove the selected area overlay map for mobile, and set persisted area from a vanilla Observable view() element on the plot
- [ ] Selecting a new family or area updates the table select options
  - [x] Families table
  - [ ] Areas table

### Lower priority
- [ ] Add explanatory tooltips, maybe an intro splash page?
- [ ] Fix the flickering when selecting a country from the map
- [ ] Pan/zoom map and change projection
  - This is probably not possible anymore now that I've built it with two overlaying maps
- [ ] Add some higher-level categories like "ferns", or even all taxonomic levels if it doesn't make things too janky
- [ ] In the family info box, include some "iconic species" (maybe most observed on iNat)
- [ ] Allow the user to apply filters data to include introduced ranges or exclude extinct species
- [ ] Chart of preferred climate for each species by family
- [ ] Line chart of species richness by latitude
- [ ] Number of endemic species to each area
  - [ ] Will need to make small islands more visible with a buffer or outline, since this will be the interesting part here
- [ ] Get a list of species in selected area-family
  - [ ] Perhaps on a separate page, since this will involve querying the entire 200MB WCVP

## Use of AI
The purpose of this project was mostly out of the personal interest of the lead developer (North Ross, myself), but I also hoped to learn more about reactive javascript development and the Observable Framework package/ecosystem. Since I had little experience with this previously, I occasionally relied on an LLM (Claude Sonet 5) to give me advice and feedback on the project, especially for optimization and debugging. I'd hesitate to call this "vibe-coding", since I think I understand everything that's gone into the project, and you can rest assured that any "slop" or "jank" inherent to this app is purely human and the result of my own inexperience.

While I recognize the irony of using a computationally resource-intensive product to make an app highlighting the global biodiversity under threat from such development, I would absolutely not have been able to put this together in the same timeframe if I hadn't used this. Another 40+ hours of my life spent working on this app would certainly incur its own resource costs, which I expect might be higher than the computation costs incurred.

That being said, this is an open source project and some of the contributors may have used AI coding agents more liberally than myself. However, all code from contributors has still been reviewed personally by the author, and I don't plan to commit any code that I don't personally understand.

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
