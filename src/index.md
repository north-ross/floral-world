---
title: Vascular Plant Diversity
toc: true
---

```js echo
// DEMO: site is still under construction
// It really does not work on mobile especially
```

# Floral World: ${selectedFam ?? "Vascular Plants"}

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
const wgsrpd = topojson.feature(wgsrpdTopo, wgsrpdTopo.objects.level3)
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
  domain: richnessExtent,
  interpolate: "rgb",
  unknown: "#FFF", // since we replaced null with zero
  label: `Species richness — ${selectedFam ?? "Vascular plants"}`
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
const familyDataSr = selectedFam != null ? sr[selectedFam]['sr'] : totalSrMap;
// Set zeros to null for display purposes
const richnessByArea = new Map(
  Object.entries(familyDataSr).map(([area, val]) => [area, val == 0 ? null : Math.round(val)])
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
        return `${d.properties.LEVEL3_NAM}: ${val ?? 0}`; // show zero for null. In any case where its null it should probably be zero anyways
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
// Set mutable for selected area, separate one for table
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
      // TODO: Set area table value to null
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
        <h1 style="font-family: 'serif';font-weight: normal;">${persistedArea.properties.LEVEL3_NAM}</h1>
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
const topFamiliesNum = areaRanked.filter((d) => d.rank == 1).length
// starter code for number of endemic families
// replace selectedFam with all families. 
// If this country has all the global species, and the second highest country has zero, it's endemic.
// if (sr[selectedFam]['global'] === sr[selectedFam]['sr'][persistedArea.properties.LEVEL3_COD] & famRanked[1] === 0) 

const famTableInput = view(Inputs.table(areaRanked.filter((d) => d.richness>0), {
  columns: ["family", "richness", "rank", "pctAboveAvg"],
  header: {
    family: "Plant Family",
    richness: "Species Richness",
    rank: "Global Rank",
    pctAboveAvg: "% Above Average"
  },
  format: {
    pctAboveAvg: (d) => d == null ? "—" : `${(d).toFixed(1)}%`,
    // display the formatted tie label field instead of average rank
    rank: (d, i) => areaRanked[i]?.tieLabel ?? "—", 
  },
  multiple: false, rows:13.5
}))
```

```js
// Set mutable for selected family
const selectedFam = Mutable(null);
const setSelectedFam = (v) => {selectedFam.value = v;};
```

```js
// Update selected family from table when table clicked
if (famTableInput !== null) setSelectedFam(famTableInput.family);
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
  <input id="famInput" list="famOptions" placeholder="Type a family or common name" style="flex:1;">
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
    setSelectedFam(resolved);
    // TODO: Update table selection?
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
selectedFam == null
  ? html`<p>Select a plant family with the search bar or from the left table.</p>`
  : html`
        <div><h1 style="font-family: 'serif';font-weight: normal;">${selectedFam} ${cmnNamesFiltered[selectedFam]?.[0] ? "\("+cmnNamesFiltered[selectedFam][0]+"\)" : ""}</h1></div>
        `
```

<div>${familySearchBox}<br></div>

<details>
<summary><b>About this family (click here)</b></summary>
<img align="right" src="https://thumb.wikimedia.org/wikipedia/commons/thumb/7/7d/Illustration_Notholaena_marantae.jpg/250px-Illustration_Notholaena_marantae.jpg?utm_source=commons.wikimedia.org&utm_campaign=index&utm_content=thumbnail">

```js
const akaHtml = (cmnNamesFiltered[selectedFam]?.length > 1)
  ? html`<p><strong>Also known as:</strong> ${cmnNamesFiltered[selectedFam].slice(1).join(", ")}.</p>`
  : html` `
```

```js
selectedFam != null
  ? html`${akaHtml}<p><strong>Preferred climate:</strong> ${sr[selectedFam]?.['climate']}</p>
<p>Contains ${sr[selectedFam]?.['global'] ?? "—"} species globally, highest species richness in ${famRanked[0]?.areaName ?? "—"}.</p>
  `
  : html` `
```

Coming soon - this will have text and an image from Wikipedia plus links to iNat, Catalogue of Life, POWO and Paleobio database.
</details>

```js
// Show a table of species richness by area for selected family

// 1. Convert array to lookup object: { "ABT": "Alberta", ... }
const codeToName = Object.fromEntries(
  wgsrpdTopo.objects.level3.geometries.map(feature => [
    feature.properties.LEVEL3_COD,
    feature.properties.LEVEL3_NAM
  ])
)

// 2. Turn the object into an array of rows with a safe fallback
const famEntries = Object.entries(sr[selectedFam]?.['sr'] || {}).map(([areaCode, richness]) => ({
  areaCode,
  areaName: codeToName[areaCode] ?? areaCode,
  richness: Math.round(richness),
  percentGlobal: Math.round(richness / sr[selectedFam]['global'] * 1000) / 10
}));

const famRanked = rankFamily(famEntries);

const areaTableSelect = view(Inputs.table(famEntries.filter((d) => d.richness>0), {
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
<style>
.wide p,
.wide h1,
.wide h2,
.wide h3,
.wide h4,
.wide h5,
.wide h6,
.wide .katex-display {
  max-width: none;
}
</style>
<div class="wide">

## About

The World Checklist for Vascular Plants (WCVP)[^1] divides the world's [vascular plants](https://en.wikipedia.org/wiki/Vascular_plant) into ${Object.keys(sr).length -1} families and aggregates their distributions into "botanical countries". This site is used to explore the number of species in different areas, a useful measure of global biodiversity ([α-diversity](https://en.wikipedia.org/wiki/Alpha_diversity)). 

The data on this site **includes extinct species** and "doubtfully present" locations, while **excluding introduced ranges**, updated weekly from WCVP. The idea is that this will allow us to examine the "natural" patterns of plant diversity. A future version of the site will allow the user to tweak these parameters.

## How to use 
<details><summary>Read more</summary>
You might want to start by clicking on your home area, or one that you're interested in. The table that will show in the bottom left will be sorted by the uniquely high families for this area. Selecting that row in the table will update the map to show its distribution.

Here are a few plant families with interesting distributions you could check out as well:
- Ericaceae, the heather family, is insanely high in the Cape of South Africa. Try turning on the log scale (top right) to see the variation in rest of the world better
  - ${Inputs.button("Select Ericaceae", {reduce: () => setSelectedFam("Ericaceae")})} 
- Polemoniaceae (phlox) is centered on California. Click on California to see all the other plant families that are unusually high here. 
  - ${Inputs.button("Select Polemoniaceae", {reduce: () => setSelectedFam("Polemoniaceae")})}
- The parasitic "vampire-cup" family Cytinaceae has a weird ditribution around Mexico, Madagascar and the mediterranean.
  - ${Inputs.button("Select Cytinaceae", {reduce: () => setSelectedFam("Cytinaceae")})}
- ${Inputs.button("Sarraceniaceae (pitcher plants)", {reduce: () => setSelectedFam("Sarraceniaceae")})}
</details><br>

## What does this map really show?
<details><summary>Read more</summary>

Since the [boundaries used for aggregation](https://www.tdwg.org/standards/wgsrpd/) are somewhat arbitrary, this visualization can't be taken too seriously as representing "true" centers of biodiversity or distribution. See [Sabatini et al. 2022](https://www.nature.com/articles/s41467-022-32063-z)[^2] for a much computational approach, although showing similar patterns, although other studies have used these boundaries for statistical analysis, controlling for area and climatic diversity within the boundaries[^3].
</details><br>

## Why are some areas more diverse than others?
<details><summary>Read more</summary>

This is a central and still unresolved question in biogeography, sometimes called the Latitudinal Diversity Gradient (LDG, [my notes](https://dismal-sariola.vercel.app/ecology-notes/macroecology/latitudinal-diversity-gradient/) ). The general pattern is that species richness tends to be higher around the equator and lower around the poles. It seems to be a relatively recent phenomenon which began after the end of the Cretaceous period, 30 or 40 million years ago. Before this, Earth usually had a much wider tropical band, and species richness was probably not much lower around the poles than at the equator. A planned feature for this site is a chart to visualize this LDG next to the map for each family.

One paper ([Tietje et al. 2022](https://www.researchgate.net/publication/361631933_Global_variation_in_diversification_rate_and_species_richness_are_unlinked_in_plants)[^3]) used this same dataset (filtered to seed plants) to try and explore some different hypotheses on this question. They found that one of the most important factors contributing to an area's plant species richness are temperature and precipitation. However, they also found that the diversification rate was generally lower in these areas and higher in dry, northern areas that experienced more climate change in the past 30 million years. They conclude that the reason why tropical areas have more diverse plants is not because of higher rates of diversification, but that they have conserved more species from the Earth's deep tropical past. Something to consdier when exploring the map!

As for why different families have different distributions than each other - this is a very complex question, but I believe it is related to:
- The LDG - tropical areas tend to be more diverse as a rule
- Environmental diversity or geodiversity of an area 
  - areas with lots of different microclimates, soil types or altitudes will have more diversity
- the evolutionary history of the family and its interactions with continental drift
  - some families evolved quite recently in isolated areas, or have gone extinct everywhere expect for these areas
  - New Caledonia is an example of this, containing a few families of "basal angiosperms" that have gone extinct everywhere else. ${Inputs.button("Select New Caledonia on the map", {reduce: () => setPersistedArea(codeToFeature["NWC"])})} 

I previously assumed the reason why some families are very diverse in one area and present in small numbers in the rest of the world is because their center of diversity is the same as their point of evolutionary origin. However, this seems to not be true in every case. For example:

${Inputs.button("Select Onagraceae on the map", {reduce: () => setSelectedFam("Onagraceae")})}

Onagraceae (the "evening primrose" or fireweed family), is present around the world but extremely diverse in California. However, the earliest fossils we have are from Paleocene Colombia (as per [Paleobiology Database](https://paleobiodb.org)), and its evolutionary history is much more complex, with its most diverse lineages originating in California, but with other genera originating in South America, eastern North America, and *Chamanerion* appearing to originate in the northern temporal zone[^4].

I hope this helps you dive into lots of rabbit holes!

</details><br>

## Source code

This is an open source project. Check out the source and planned features, or make your own fork or contribution on [GitHub](https://github.com/north-ross/floral-world).

</div>

[^1]: Govaerts, R., Nic Lughadha, E. et al. The World Checklist of Vascular Plants, a continuously updated resource for exploring global plant diversity. Sci Data 8, 215 (2021). https://doi.org/10.1038/s41597-021-00997-6

[^2]: Sabatini, F.M., Jiménez-Alfaro, B., Jandt, U. et al. Global patterns of vascular plant alpha diversity. Nat Commun 13, 4683 (2022). https://doi.org/10.1038/s41467-022-32063-z

[^3]: Tietje, Melanie & Antonelli, Alexandre & Baker, William & Govaerts, Rafaël & Smith, Stephen & Eiserhardt, Wolf. (2022). Global variation in diversification rate and species richness are unlinked in plants. Proceedings of the National Academy of Sciences. 119. https://doi.org/10.1073/pnas.2120662119. 

[^4]: Katinas L, Crisci JV, Wagner WL, Hoch PC. Geographical diversification of tribes Epilobieae, Gongylocarpeae, and Onagreae (Onagraceae) in North America, based on parsimony analysis of endemicity and track compatibility analysis. Ann Mo Bot Gard. 2004;91(1):159–85. https://repository.si.edu/server/api/core/bitstreams/8deb0998-cb59-412f-9369-96add8cf4641/content.