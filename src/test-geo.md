---
title: Geo Test
toc: false
---

# Floral World
```js
// From the WGSRPD shapefile, simplified and converted to topojson with mapshaper
const wgsrpdTopo = FileAttachment('./data/level3.json').json();
const sr = FileAttachment('./data/family-area-sr.json').json();
```

```js

const wgsrpd = topojson.feature(wgsrpdTopo, wgsrpdTopo.objects.mapshaper)

const selAreaMap = Plot.plot({
  projection: { type: "equal-earth" },
  width: 1080,
  marks: [
    Plot.sphere(),
    Plot.graticule(),
    Plot.geo(wgsrpd, {fill: "var(--theme-foreground-fainter)"}),
    Plot.geo(wgsrpd, Plot.pointer({
        title: "LEVEL3_NAM", 
        stroke: "var(--theme-foreground-focus)",
        tip: true
        }))
    // Add another mark that activates when a country is selected
  ]
});

view(selAreaMap)

const area = Generators.input(selAreaMap);
// view(wgsrpdTopo.objects.mapshaper.geometries)
// if there are problems with data requesting too fast:
// Only call the table if it's "frozen" as per https://observablehq.com/@mtsvelik/plot-frozen-state-detection
```

<div class="grid grid-cols-2">

<div class="card">
  ${area === null
    ? html`<p>Select a botanical country from the map.</p>`
    : html`
        <h2>${area.properties.LEVEL3_NAM}</h2>
        <p>${area.properties.LEVEL3_NAM} is a very cool place!</p>
      `
  }

```js
// Get species richness by family
// area.properties.LEVEL3_COD

// Transpose: for the chosen area, pull that value out of every family
function transposeForArea(nested, areaCode) {
  return Object.entries(nested).map(([family, values]) => ({
    family,
    richness: Math.round(values[areaCode] ?? 0)
  }));
}

const entries = transposeForArea(sr, area.properties.LEVEL3_COD);

// Sort descending by richness
const areaSorted = [...entries].sort((a, b) => d3.descending(a.richness, b.richness));

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

const ranked = assignRanks(areaSorted);
```

```js 
Inputs.table(ranked, {
  columns: ["family", "richness", "rank"],
  header: {
    family: "Plant Family",
    richness: "Species Richness",
    rank: "Rank"
  },
  sort: "richness",
  reverse: true
})
```
</div>
<div class="card">

```js
const selFamily = view(
  Inputs.search(Object.keys(sr), {
    placeholder: "Choose a family",
    value: "Orchidaceae",
    datalist: Object.keys(sr),
    multiple: false 
    })
);

// TODO: Get global species richness included in sr
```

  ${selFamily.length < 0
    ? html`<p>Choose a family from the search bar</p>`
    : html`
        <h2>${selFamily[0]} (common name)</h2>
        <p>Contains x species, highest species richness in ${famSorted[0].area}.</p>
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
const entries = Object.entries(sr[selFamily[0]]).map(([area, richness]) => ({
  area: codeToName[area],
  richness: Math.round(richness)
}));

// 3. Sort descending by richness
const famSorted = [...entries].sort((a, b) => d3.descending(a.richness, b.richness));
// 4. Show table
const tableSelectedArea = view(Inputs.table(famSorted, {
  columns: ["area", "richness"],
  header: {
    area: "Area",
    richness: "Species Richness"
  },
  select: false 
  //multiple: false// Would be nice if they could select a country here and have it flash on the map, or even change the selection

  // would be n
}))
// Add a thing to update selected area

// Inputs.table(sr[[selFamily[0]]])
```

</div>
</div>

<footer>
Map data adapted from <a href="https://www.tdwg.org/standards/wgsrpd/"> World Geographic System for Recording Plant Distributions </a>
</footer>