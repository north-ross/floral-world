---
title: Vascular Plant Diversity
toc: false
---

# Floral World: ${persistedFam ?? "Vascular Plants"}

```js
import { rankFamily} from "./rankings.js";
```

```js
// From the WGSRPD shapefile, simplified and converted to topojson with mapshaper
const wgsrpdTopo = FileAttachment('./data/level3.json').json();
const sr = FileAttachment('./data/family-area-sr.json').json();
const cmnNames = FileAttachment('./data/taxa-inat-darwincore.json').json();
// Add a column for "total" for every family, which should display first
// Get data on climate to make a bar chart
const dark = Generators.dark();
```

```js
// Pack into topojson feature
const wgsrpd = topojson.feature(wgsrpdTopo, wgsrpdTopo.objects.mapshaper)
```

```js
// Trigger using log scale to color the map
// removed view() from this so it doesn't draw here (I think)
const logscaleInput = Inputs.toggle({label: "Use log scale", values: ["log", "sequential"]});
```

```js
// The reactive value stream — this is what other cells should depend on
const logscale = Generators.input(logscaleInput);
```

```js
// Define the color scale options once, shared between the plot and the standalone legend
const colorOptions = {
  type: logscale,
  range: ["#FAF7C7", "#688816", "#1C3D28"], // TODO: one day - add white at the start, then a lot of intermdiate colors so it only shows for 0?
  domain: logscale == "log" // transform so log doesn't show 0
            ? [richnessExtent[0]+0.5, richnessExtent[1]]
            : richnessExtent,
  interpolate: "rgb",
  unknown: "var(--theme-foreground-fainter)",
  label: `Species richness — ${persistedFam}`
};
```

```js
// Get total vascular plant sr by family
const totalSrMap = {};

const areaKeys = Object.keys(sr[Object.keys(sr)[0]].sr);

// For each country code, sum the values across all plant families
areaKeys.forEach(area => {
  totalSrMap[area] = Object.values(sr).reduce((sum, family) => {
    return sum + (family.sr[area] || 0);
  }, 0);
});
```

```js
// lookup functions for map 
const familyDataSr = persistedFam != null ? sr[persistedFam]['sr'] : totalSrMap;
const richnessByArea = new Map(
  Object.entries(familyDataSr).map(([area, val]) => [area, Math.round(val)])
);
const richnessExtent = d3.extent(richnessByArea.values());
```

```js
// Map
const mapWidth = 0.8 * width;

const selAreaMap = Plot.plot({
  projection: { type: "equal-earth", domain: wgsrpd },
  width: mapWidth,
  color: { ...colorOptions, legend: false },
  marks: [
    Plot.sphere({fill: "#A8CAD4", fillOpacity: 0.4}),
    Plot.graticule(),
    Plot.geo(wgsrpd, {
      fill: (d) => richnessByArea.get(d.properties.LEVEL3_COD),
      stroke: "#afafaf",
      strokeWidth: 0.5
    }),
    Plot.geo(wgsrpd, Plot.pointer({
      title: (d) => {
        const code = d.properties.LEVEL3_COD;
        const val = richnessByArea.get(code);
        return `${d.properties.LEVEL3_NAM}: ${val ?? "no data"}`;
      },
      stroke: "#662200",
      tip: {fill: "#662200"}
    }))
  ]
});

// Plot sets this explicitly from width + projection aspect ratio —
// available immediately, no need to wait for DOM layout.
const mapHeight = +selAreaMap.getAttribute("height");

// view(selAreaMap)
// console.log("reloaded map")
```

```js
// Lightweight overlay — same width/height/projection domain as the base map,
// Only this updates with persistedArea
const highlightOverlay = Plot.plot({
  projection: { type: "equal-earth", domain: wgsrpd },
  width: mapWidth,
  height: mapHeight,
  marks: [
    Plot.sphere({stroke:"var(--theme-foreground)"}),
    Plot.geo(
      persistedArea ? [persistedArea] : [],
      { stroke: "#662200", strokeWidth: 2.5, fill: "none" }
    )
  ],
  style: { backgroundColor: "transparent" }
});
// console.log("reloaded light map")
```

```js
// Generator input for selArea
const selArea = Generators.input(selAreaMap);
```

```js
// Set mutable for selected area
const persistedArea = Mutable(null);
const setPersistedArea = (v) => {persistedArea.value = v;};
```

```js
// When map is clicked, update persistent area mutable
selAreaMap.addEventListener(
  "pointerdown",
  (event) => {
    event.stopPropagation(); // stop Plot's own pointerdown (sticky toggle) from running
    requestAnimationFrame(() => requestAnimationFrame(() => { // skip two frames to avoid premature result
      if (selArea !== null) setPersistedArea(selArea);
      // TODO: Reset the areaTableSelect
    }));
  },
  { capture: true }
);
```

```js
// Standalone legend, rendered separately in normal document flow
const colorLegend = Plot.legend({ color: colorOptions });
```

```js
html`<div>
  <div class="grid grid-cols-2">
    <div>${colorLegend}</div> <div>${logscaleInput}</div>
  </div>
  <div style="position: relative; width: ${mapWidth}px; height: ${mapHeight}px;">
    <div style="position: absolute; top: 0; left: 0;">${selAreaMap}</div>
    <div style="position: absolute; top: 0; left: 0; pointer-events: none;">${highlightOverlay}</div>
  </div>
</div>`
```

<div class="grid grid-cols-2">
<div class="card">

  ${persistedArea === null
    ? html`<p>Select a botanical country from the map.</p>`
    : html`
        <h1>${persistedArea.properties.LEVEL3_NAM}</h1>
        <p>Contains ${areaRanked.filter((d) => d.richness>0).length} plant families and ${totalSrMap[persistedArea.properties.LEVEL3_COD]} species.</p>
        ${topFamiliesNum > 0 ? html`<p>Top ranked for ${topFamiliesNum} families!</p>` : html``}
      `
  }

```js
const globalRankCache = new Map();

function getGlobalRanking(family) {
  if (!globalRankCache.has(family)) {
    const entries = Object.entries(sr[family]['sr'] ?? {}).map(([areaCode, richness]) => ({
      areaCode,
      richness: Math.round(richness)
    }));
    globalRankCache.set(family, rankFamily(entries));
  }
  return globalRankCache.get(family);
}

// For the selected area, look up each family's GLOBAL rank at that area's code
function transposeForArea(nested, areaCode) {
  return Object.keys(nested).map((family) => {
    const globalRanked = getGlobalRanking(family);
    const row = globalRanked.find((d) => d.areaCode === areaCode);
    return {
      family,
      richness: row?.richness ?? 0,
      rank: row?.rank ?? null,
      denseRank: row?.denseRank ?? null,
      tieLabel: row?.tieLabel ?? "—",
      pctAboveAvg: row?.pctAboveAvg ?? null
    };
  });
}

const areaEntries = persistedArea
  ? transposeForArea(sr, persistedArea.properties.LEVEL3_COD)
  : [];

// Sort by the family's global rank (best/lowest rank number first)
const areaRanked = [...areaEntries].sort((a, b) => d3.ascending(a.rank, b.rank));

const famTableInput = view(Inputs.table(areaRanked, {
  columns: ["family", "tieLabel", "richness", "pctAboveAvg"],
  header: {
    family: "Plant Family",
    tieLabel: "Global Rank",
    richness: "Species Richness",
    pctAboveAvg: "% Above Average"
  },
  sort: "rank",
  multiple: false,
  reverse: true
}))
const topFamiliesNum = areaRanked.filter((d) => d.rank == 1).length
```

```js
// Set mutable for selected family
const persistedFam = Mutable(null);
const setPersistedFam = (v) => {persistedFam.value = v;};
```

```js
// Update selected family from table when table clicked
if (famTableInput !== null) setPersistedFam(famTableInput.family);
// TODO: Now reset the search bar
```

```js
// TODO: Replace this with a generic html search box with an enter button to stop it resetting all the time
// + let the datalist also search common names
const selFamilySearchInput = Inputs.search(
  Object.keys(sr), {
    placeholder: "Choose a family",
    // query: "Acanthaceae",
    required: false,
    datalist: Object.keys(sr),
    multiple: false 
  }
);
```

```js
const selFamilySearch = Generators.input(selFamilySearchInput);
```

```js
// Set first result from search as persistent family
if (selFamilySearch[0] != null) setPersistedFam(selFamilySearch[0]);
// TODO: reset the table selection
```
</div>



<div class="card">
${persistedFam == null
  ? html`${selFamilySearchInput}<p>Choose a family from the search bar</p>`
  : html`
        <div><h1>${persistedFam} ${cmnNames[persistedFam]?.[0] ? "\("+cmnNames[persistedFam][0]+"\)" : ""}</h1></div>
        <div>${selFamilySearchInput}</div>
      ${cmnNames[persistedFam]?.length > 1 ? html`<p><strong>Also known as:</strong> ${cmnNames[persistedFam].slice(1).join(", ")}.</p>`:html``}
      <p><strong>Modal preferred climate:</strong> ${sr[persistedFam]['climate']}</p>
      <p>Contains ${sr[persistedFam]['global']} species globally, highest species richness in ${famRanked[0]?.areaName ?? "—"}.</p>
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

// 2. Turn the object into an array of rows with a safe fallback
const famEntries = Object.entries(sr[persistedFam]?.['sr'] || {}).map(([areaCode, richness]) => ({
  areaCode,
  areaName: codeToName[areaCode] ?? areaCode,
  richness: Math.round(richness),
  percentGlobal: Math.round(richness / sr[persistedFam]['global'] * 1000) / 10
}));

const famRanked = rankFamily(famEntries);

const areaTableSelect = view(Inputs.table(famEntries, {
  columns: ["areaName", "richness", "percentGlobal"],
  header: {
    areaName: "Area",
    richness: "Species Richness",
    percentGlobal: "% of Global"
  },
  multiple: false,
  sort: "richness", reverse: true
  
}))
```

```js
// Set persistent area based on table selection
// Lookup feature from country code
const codeToFeature = Object.fromEntries(
  wgsrpd.features.map(feature => [
    feature.properties.LEVEL3_COD,
    feature
  ])
)
// Set persistent area
if (areaTableSelect !== null) setPersistedArea(
  codeToFeature[areaTableSelect.areaCode]
);

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
- Fix the search bar so it doesn't reload after every press
- Add data loader to keep site up-to-date
  - Test it
  - ~~Fix it so it builds json correctly, and write code to get derived values (ties etc) in js~~
  - ~~Add data loader for common names~~
- Get common names for families (from [iNat taxonomy DarwinCore archive](https://www.inaturalist.org/pages/developers))
  - Let the search bar search this too
- Lookup Wikidata page to add links to wikipedia, iNat, CoL paleobio database
- Determine the "specialty" family for each area
  - From the country-wise (global) ranking for families, get the highest ranked for this (using averages for ties)
  - Excluding zero-species taxa (replace with NA for this purpose)
  - ~~How does this taxa compare to global average? Maybe pick the family with the largest % difference between here and average.~~
  - ~~For countries that have multiple families where they're #1, include the number of them~~

- 🗹 ~~Selecting a family from the countries table updates the selected family reactively~~

### Low priority
- Pan/zoom map and change projection
  - Probably not possible anymore
- Add some higher-level categories like "ferns"
- In the family info box, include an "iconic species" (maybe most observed on iNat)
- Filter data to include introduced ranges or exclude extinct species
- Chart of preferred climate for each species by family
- Line chart of species richness by latitude
- Show a list of species in selected area-family
- Number of endemic species to each area
  - Will need to make small islands more visible



