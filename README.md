# Floral World
An app to explore global vascular plant biodiversity using data from the [World Checklist for Vascular Plants](https://www.tdwg.org/standards/wgsrpd/). A map shows the species richness for each "botanical country" (WGSRPD level 3 division) and can be filtered by family. Tables let the user discover the "unique families" of each area, and what percentage of global biodiversity they contain.

This is an [Observable Framework](https://observablehq.com/framework/) app. For more, see <https://observablehq.com/framework/getting-started>.

## About
The World Checklist for Vascular Plants divides the world's [vascular plants](https://en.wikipedia.org/wiki/Vascular_plant) into about 400 families and aggregates their distributions into "botanical countries". This site is used to explore the number of species in different areas, a useful measure of global biodiversity ([α-diversity](https://en.wikipedia.org/wiki/Alpha_diversity)). 

Since the boundaries used for aggregation are somewhat arbitrary, this visualization can't be taken too seriously as representing centers of biodiversity. See [this article](https://www.nature.com/articles/s41467-022-32063-z) for a much more scientific approach. However, this approach is much less computationally intensive, and the overall patterns still hold true. I've found it very interesting to explore different families and find the unique "specialty" families from different parts of the world.

Based on an earlier simple project to generate static maps of plant diversity: [Plant Family Mapping](https://github.com/north-ross/PlantFamilyMapping)

## Planned features
### Priority
- [x] Add data loader to keep site up-to-date
- [x] Get common names for families (from [iNat taxonomy DarwinCore archive](https://www.inaturalist.org/pages/developers))
- [x] Selecting a family from the countries table updates the selected family reactively
- [x] Query Wikidata to add links to wikipedia, iNat, CoL paleobio database. 
  - [x] Embed an image from wikidata
- [ ] When no area is selected, show a table of global SR by plant families (no global rank or % above avg)
- [ ] Add some text about the "specialty" family for each area
  - [ ] From the country-wise (global) ranking for families, get the highest ranked for this (using averages for ties)
- [ ] Adapt the page to have a basic level of functionality on mobile
  - [x] Map should at least stretch to full page width
  - [ ] Add an area selector dropdown/search bar
  - [ ] Grid cards should not match height on mobile
  - [ ] Maybe even remove the selected area overlay map for mobile, and set persisted area from a vanilla Observable view() element on the plot

### Lower priority
- [ ] Add explanatory tooltips, maybe an intro splash page?
- [ ] Fix the flickering when selecting a country from the map
- [ ] Add option to change map projection, maybe pan/zoom d3 style if possible
- [ ] Add some higher-level categories like "ferns", or even all taxonomic levels if it doesn't make things too janky
- [ ] In the family info box, include some "iconic species" (maybe most observed on iNat)
- [ ] Allow the user to apply filters data to include introduced ranges or exclude extinct species
- [ ] Chart of preferred climate for each species by family
- [ ] Line chart of species richness by latitude (LDG)
- [ ] Map number of endemic species to each area
  - [ ] Will need to make small islands more visible with a buffer or outline, since this will be the interesting part here
- [ ] Get a list of species in selected area-family
  - [ ] Perhaps on a separate page, since this will involve querying the entire 200MB WCVP
- [ ] Embed wikipedia text

## Use of AI
The purpose of this project was mostly out of my personal interest, but I also hoped to learn more about reactive javascript development and the Observable Framework package/ecosystem. Since I had little experience with this previously, I occasionally relied on an LLM (Claude Sonet 5) to give me advice and feedback on the project, especially for optimization and debugging. I'd hesitate to call this "vibe-coding", since I think I understood all the code that's gone into the project on some level, and you can rest assured that any "slop" or "jank" inherent to this app is purely human and the result of my own inexperience.

No AI was used in my original [simpler code](https://github.com/north-ross/PlantFamilyMapping) to generate static maps, only after I added a lot of complexity and made it into this web app.

While I recognize the irony of using a computationally resource-intensive product to make an app highlighting the global biodiversity under threat from such development, I would absolutely not have been able to put this together in the same timeframe if I hadn't used it. Another 40+ hours of my life spent working on this app would certainly incur its own resource costs, which I expect might be higher than the computation costs.

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
