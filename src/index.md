---
title: Vascular Plant Diversity
toc: false
---

```js echo
// DEMO: site is still under construction
// It really does not work on mobile especially
```

# Floral World: ${persistedFam ?? "Vascular Plants"}

```js
import { rankFamily} from "./rankings.js";
```


```js
// From the WGSRPD shapefile, simplified and converted to topojson with mapshaper
const wgsrpdTopo = FileAttachment('./data/level3.json').json();
const sr = FileAttachment('./data/family-area-sr.json').json();
const cmnNames = FileAttachment('./data/taxa-inat-darwincore.json').json();
const dark = Generators.dark();
```

```js
// Restrict common names to only families actually present in sr
// (iNat taxonomy includes families WCVP doesn't recognize / has merged / renamed)
const cmnNamesFiltered = Object.fromEntries(
  Object.entries(cmnNames).filter(([fam]) => fam in sr)
);
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
      tip: {fill: dark ? "#662200" : "var(--theme-background)",}
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
// TODO: Align to center, maybe limit height to a fraction of the screen?
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
    ? html`<p>Select a botanical country from the map or right table.</p>`
    : html`
        <h1 style="font-family: 'serif';">${persistedArea.properties.LEVEL3_NAM}</h1>
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

// starter code for number of endemic families
// replace persistedFam with all families. 
// If this country has all the global species, and the second highest country has zero, it's endemic.
// if (sr[persistedFam]['global'] === sr[persistedFam]['sr'][persistedArea.properties.LEVEL3_COD] & famRanked[1] === 0) 
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
// For the search bar, build search term -> family lookup
// Python: {name: fam for fam, names in cmnNamesFiltered.items() for name in [fam, *names]}
const familyLookup = new Map();
for (const [fam, commonNames] of Object.entries(cmnNamesFiltered)) {
  familyLookup.set(fam.toLowerCase(), fam);
  for (const cname of commonNames) {
    familyLookup.set(cname.toLowerCase(), fam);
  }
}

// Flat list of display strings for the datalist
const searchOptions = Array.from(familyLookup.keys());
```

```js
const familySearchBox = html`<div style="display:flex; gap:4px;">
  <input id="famInput" list="famOptions" placeholder="Type a family or common name and press enter" style="flex:1;">
  <datalist id="famOptions">
    ${searchOptions.map(name => html`<option value="${name}">`)}
  </datalist>
  <button id="famSubmit">Go</button>
</div>`;

const inputEl = familySearchBox.querySelector("#famInput");
const buttonEl = familySearchBox.querySelector("#famSubmit");

function commitFamily() {
  const raw = inputEl.value.trim().toLowerCase();
  const resolved = familyLookup.get(raw);
  if (resolved) {
    setPersistedFam(resolved);
  }
  // else: optionally flash an "not found" state — up to you
}

buttonEl.addEventListener("click", commitFamily);
inputEl.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    commitFamily();
  }
});
// TODO: reset the table selection
```
</div>



<div class="card">

```js
persistedFam == null
  ? html`<p>Select a plant family with the search bar or from the left table.</p>`
  : html`
        <div><h1 style="font-family: 'serif';">${persistedFam} ${cmnNamesFiltered[persistedFam]?.[0] ? "\("+cmnNamesFiltered[persistedFam][0]+"\)" : ""}</h1></div>
        `
```

<div>${familySearchBox}</div>

```js
const akaHtml = (cmnNamesFiltered[persistedFam]?.length > 1)
  ? html`<p><strong>Also known as:</strong> ${cmnNamesFiltered[persistedFam].slice(1).join(", ")}.</p>`
  : html` `
```

```js
persistedFam != null
  ? html`${akaHtml}<p><strong>Preferred climate:</strong> ${sr[persistedFam]?.['climate']}</p>
<p>Contains ${sr[persistedFam]?.['global']} species globally, highest species richness in ${famRanked[0]?.areaName ?? "—"}.</p>
  <details>
  <summary>About</summary>
  <img align="right" src="https://thumb.wikimedia.org/wikipedia/commons/thumb/7/7d/Illustration_Notholaena_marantae.jpg/250px-Illustration_Notholaena_marantae.jpg?utm_source=commons.wikimedia.org&utm_campaign=index&utm_content=thumbnail">
  Coming soon - this will have text and an image from Wikipedia plus links to iNat, Catalogue of Life, POWO and Paleobio database.
  </details>
  `
  : html` `
```


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

The World Checklist for Vascular Plants[^1] divides the world's [vascular plants](https://en.wikipedia.org/wiki/Vascular_plant) into ${Object.keys(sr).length -1} families and aggregates their distributions into "botanical countries". This site is used to explore the number of species in different areas, a useful measure of global biodiversity ([α-diversity](https://en.wikipedia.org/wiki/Alpha_diversity)). 


<details><summary>What does this map really show?</summary>

Since the [boundaries used for aggregation](https://www.tdwg.org/standards/wgsrpd/) are somewhat arbitrary, this visualization can't be taken too seriously as representing centers of biodiversity. See [Sabatini et al. 2022](https://www.nature.com/articles/s41467-022-32063-z)[^2] for a much more scientific approach. However, my approach is much less computationally intensive, and the overall patterns still hold true. I've found it very interesting to explore different families and find the unique "specialty" families from different parts of the world.

</details>
<br>

## What should I look at?
You might want to start by clicking on your home area, or one that you're interested in. The table that will show in the bottom left will be sorted by the uniquely high families for this area. Selecting that row in the table will update the map to show its distribution.

Here are a few plant families with interesting distributions you could check out as well:
- Ericaceae, the heather family, is insanely high in the Cape of South Africa. Try turning on the log scale (top right) to see the rest of the world
  - ${Inputs.button("Select Ericaceae", {reduce: () => setPersistedFam("Ericaceae")})} 
- Polemoniaceae (phlox) is centered on California. Click on California to see all the other plant families that are unusually high here. 
  - ${Inputs.button("Select Polemoniaceae", {reduce: () => setPersistedFam("Polemoniaceae")})}
- The parasitic "vampire-cup" family Cytinaceae has a weird ditribution around Mexico, Madagascar and the mediterranean.
  - ${Inputs.button("Select Cytinaceae", {reduce: () => setPersistedFam("Cytinaceae")})}
- ${Inputs.button("Sarraceniaceae (pitcher plants)", {reduce: () => setPersistedFam("Sarraceniaceae")})}
- Roussaceae, a New Caledonian family with a cool distribution
  - ${Inputs.button("Rousseaceae", {reduce: () => setPersistedFam("Rousseaceae")})}


## Source

This is an open source project. Check out the source and planned features, or make your own fork or contribution on [GitHub](https://github.com/north-ross/floral-world).

[^1]: Govaerts, R., Nic Lughadha, E. et al. The World Checklist of Vascular Plants, a continuously updated resource for exploring global plant diversity. Sci Data 8, 215 (2021). [https://doi.org/10.1038/s41597-021-00997-6]

[^2]: Sabatini, F.M., Jiménez-Alfaro, B., Jandt, U. et al. Global patterns of vascular plant alpha diversity. Nat Commun 13, 4683 (2022). https://doi.org/10.1038/s41467-022-32063-z


