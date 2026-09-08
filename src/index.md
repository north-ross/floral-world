---
title: Vascular Plant Diversity
toc: false
---

# Floral World

```js
const persistedArea = Mutable(null);
const setPersistedArea = (v) => {persistedArea.value = v;};
```

```js
// From the WGSRPD shapefile, simplified and converted to topojson with mapshaper
const wgsrpdTopo = FileAttachment('./data/level3.json').json();
const sr = FileAttachment('./data/family-area-sr.json').json();
// Add a column for "total" for every family, which should display first
// Get data on climate to make a bar chart
const dark = Generators.dark();
```


```js
// Trigger using log scale to color the map
const logscale = view(Inputs.toggle({label: "Log scale", values: ["log", "sequential"]}));

const wgsrpd = topojson.feature(wgsrpdTopo, wgsrpdTopo.objects.mapshaper)
```

```js
// lookup functions for map 
// Build a lookup: area code -> richness, for the currently selected family
const familyData = sr[selFamily] ?? {};

const richnessByArea = new Map(
  Object.entries(familyData).map(([area, val]) => [area, Math.round(val)])
);
```

```js
// Map

const selAreaMap = Plot.plot({
  projection: { type: "equal-earth" },
  width: 1080,
  color: {
    type: logscale ,// Add option to replace with log
    scheme: "YlGn", // Adjust color scale so that zero is the theme color
    unknown: "var(--theme-foreground-fainter)",
    legend: true,
    label: `Species richness — ${selFamily}`
  },
  marks: [
    Plot.sphere(),
    Plot.graticule(),
    Plot.geo(wgsrpd, {
      fill: (d) => richnessByArea.get(d.properties.LEVEL3_COD),
      stroke: "#b0b0b0",
      strokeWidth: 0.5
      }),
    Plot.geo(wgsrpd, Plot.pointer({
        title: (d) => {
          const code = d.properties.LEVEL3_COD;
          const val = richnessByArea.get(code);
          return `${d.properties.LEVEL3_NAM}: ${val ?? "no data"}`;
        },
        stroke: "var(--theme-foreground-focus)",
        tip: true
        }))
    // Add another mark that activates when a country is selected
  ]
});

view(selAreaMap)

```

```js
// Generator input for selArea
const selArea = Generators.input(selAreaMap);
```

```js
// Set a persistent area that doesn't get reset when map is reloaded
if (selArea !== null) setPersistedArea(selArea);
```

<div class="grid grid-cols-2">
<div class="card">

  ${persistedArea === null
    ? html`<p>Select a botanical country from the map.</p>`
    : html`
        <h2>${persistedArea.properties.LEVEL3_NAM}</h2>
        <p>The bars are open in beautiful ${persistedArea.properties.LEVEL3_NAM}...</p>
      `
  }

```js
// Get species richness by family
// Transpose: for the chosen area, pull that value out of every family
function transposeForArea(nested, areaCode) {
  return Object.entries(nested).map(([family, values]) => ({
    family,
    richness: Math.round(values[areaCode] ?? 0)
  }));
}

const areaEntries =persistedArea
  ? transposeForArea(sr, persistedArea.properties.LEVEL3_COD)
  : [];

// Sort descending by richness
const areaSorted = [...areaEntries].sort((a, b) => d3.descending(a.richness, b.richness));

// Same average-tie ranking
function assignRanks(sortedRows) {
  const n = sortedRows.length;
  const out = new Array(n);
  let i = 0;
  while (i < n) {
    let j = i;
    while (j < n && sortedRows[j].richness === sortedRows[i].richness) j++;
    const avgRank = (i + 1 + j) / 2;
    for (let k = i; k < j; k++) out[k] = { ...sortedRows[k], rank: avgRank };
    i = j;
  }
  return out;
}

const areaRanked = assignRanks(areaSorted);

const areaTableSel = view(Inputs.table(areaRanked, {
  columns: ["family", "richness", "rank"],
  header: {
    family: "Plant Family",
    richness: "Species Richness",
    rank: "Rank"
  },
  sort: "richness",
  select: false,
  reverse: true
}))
```

</div>
<div class="card">

```js
const selFamilySearch = view(
  Inputs.search(Object.keys(sr), {
    placeholder: "Choose a family",
    query: "Total",
    required: false,
    datalist: Object.keys(sr),
    multiple: false 
    })
);
// TODO: Get global species richness for species included in sr
```

```js
// Get first family from search
// Make this a mutable or generator so it can be overwritten by clicking a family name elsewhere
const selFamily = selFamilySearch[0]
```

${selFamily === null
  ? html`<p>Choose a family from the search bar</p>`
  : html`
      <h2>${selFamily} (common name)</h2>
      <p>Contains x species, highest species richness in ${famSorted[0]?.area ?? "—"}.</p>
    `
}

```js
// Show a table of species richness by area for selected family

// 1. Convert array to lookup object: { "ABT": "Alberta", ... }
const codeToName = Object.fromEntries(
  wgsrpdTopo.objects.mapshaper.geometries.map(feature => [
    feature.properties.LEVEL3_COD,
    feature.properties.LEVEL3_NAM
  ])
)

// 2. Turn the object into an array of rows
const famEntries = Object.entries(sr[selFamily]).map(([area, richness]) => ({
  area: codeToName[area], // Fix some missing areas
  richness: Math.round(richness)
}));

// 3. Sort descending by richness
const famSorted = [...famEntries].sort((a, b) => d3.descending(a.richness, b.richness));
// 4. Show table
const tableSelectedArea = view(Inputs.table(famSorted, {
  columns: ["area", "richness"],
  header: {
    area: "Area",
    richness: "Species Richness"
  },
  select: false 
  //multiple: false// Would be nice if they could select a country here and have it flash on the map, or even change the selection
}))
```

</div>
</div>

## About

<details>
<summary>About</summary>

The World Checklist for Vascular Plants divides the world's [vascular plants](https://en.wikipedia.org/wiki/Vascular_plant) into ${Object.keys(sr).length -1} families and aggregates their distributions into "botanical countries". This site is used to explore the number of species in different areas, a useful measure of global biodiversity ([α-diversity](https://en.wikipedia.org/wiki/Alpha_diversity)). 

Since the boundaries used for aggregation are somewhat arbitrary, this visualization can't be taken too seriously as representing centers of biodiversity. See [this article](https://www.nature.com/articles/s41467-022-32063-z) for a much more scientific approach. However, this approach is much less computationally intensive, and the overall patterns still hold true. I've found it very interesting to explore different families and find the unique "specialty" families from different parts of the world.

</details>

## Planned features
### Priority
- Get common names for families (from [iNat taxonomy DarwinCore archive](https://www.inaturalist.org/pages/developers))
  - Find the common name that contains "family" and use that
  - Let the search bar search this too
- Get an image and link to the family Wikipedia page (and iNat)
- Add data loader to keep site up-to-date - also update common names
- Determine the "specialty" family for each area
  - From the country-wise (global) ranking for families, get the highest ranked for this (using averages for ties)
  - Excluding zero-species taxa (replace with NA for this purpose)
  - How does this taxa compare to global average? Maybe pick the family with the largest % difference between here and average.
  - For countries that have multiple families where they're #1, include the number of them
- Selecting a family from the countries table updates the selected family reactively
  - Maybe I can make this work with the country too, but it seems difficult

### Low priority
- Pan/zoom map and change projection
- Add some higher-level categories like "ferns"
- In the family info box, include an "iconic species" (maybe most observed on iNat)
- Filter data to include introduced ranges or exclude extinct species
- Chart of preferred climate for each species by family
- Line chart of species richness by latitude
- Show a list of species in selected area-family
- Number of endemic species to each area
  - Will need to make small islands more visible


Map data adapted from [World Geographic System for Recording Plant Distributions](https://www.tdwg.org/standards/wgsrpd/), with species distributions from the [World Checklist of Vascular Plants](https://powo.science.kew.org/about-wcvp).
