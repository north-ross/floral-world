---
title: Geo Test
toc: false
---

# Floral World
```js
const wgsrpdTopo = FileAttachment('./data/level3.json').json();
const sr = FileAttachment('./data/family-area-sr.json').json();
```

```js

const wgsrpdmesh = topojson.feature(wgsrpdTopo, wgsrpdTopo.objects.mapshaper)

const selAreaMap = view(Plot.plot({
  projection: { type: "equal-earth" },
  width: 1080,
  marks: [
    Plot.sphere(),
    Plot.graticule(),
    Plot.geo(wgsrpdmesh, {fill: "var(--theme-foreground-fainter)"}),
    Plot.geo(wgsrpdmesh, Plot.pointer({
        title: "LEVEL3_NAM", 
        stroke: "var(--theme-foreground-focus)",
        tip: true
        }))
    // Add another mark that activates when a different country is selected. It should also reset th tip selector
  ]
}));

// if there are problems with data requesting too fast:
// Only call the table if it's "frozen" as per https://observablehq.com/@mtsvelik/plot-frozen-state-detection
```

<div class="grid grid-cols-2">

<div class="card">
  ${selAreaMap === null
    ? html`<p>Click a mark on the chart to view details.</p>`
    : html`
        <h2>${selAreaMap.properties.LEVEL3_NAM}</h2>
        <p>${selAreaMap.properties.LEVEL3_NAM} is a very cool place!</p>
      `
  }

```js
selAreaMap.properties.LEVEL3_COD
// Inputs.table(sr[[selFamily[0]]])
```
</div>
<div class="card">

```js
const selFamily = view(
  Inputs.search(Object.keys(sr), {
    placeholder: "Choose a family",
    datalist: Object.keys(sr),
    required: false
  })
);
```

  ${selFamily.length < 0
    ? html`<p>Choose a family from the search bar</p>`
    : html`
        <h2>${selFamily[0]} (common name)</h2>
        <p>Contains x species, highest species richness in ${sorted[0].area}.</p>
      `
  }
```js
// 1. Turn the object into an array of rows
const entries = Object.entries(sr[selFamily[0]]).map(([area, richness]) => ({
  area,
  richness: Math.round(richness)
}));

// 2. Sort descending by richness (this determines rank order)
const sorted = [...entries].sort((a, b) => d3.descending(a.richness, b.richness));

const tableSelectedArea = view(Inputs.table(sorted, {
  columns: ["area", "richness"],
  header: {
    area: "Area",
    richness: "Species Richness"
  },
  sort: "richness",
  reverse: true,
  multiple: false
}))
// Add a thing to update selected area

// Inputs.table(sr[[selFamily[0]]])
```

</div>
</div>