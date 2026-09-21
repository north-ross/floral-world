---
title: Vascular Plant Diversity
toc: true
---

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
@media (max-width: 640px) {
  .grid.grid-cols-2 {
    display: block;
  }
  .grid.grid-cols-2 > .card {
    margin-bottom: 1rem; /* grid-gap doesn't apply in block mode, so add spacing manually */
  }
}
.inputs-3a86ea-input {
  display: flex;
  align-items: center;
  width: 100%;
}
</style>

# Floral World: ${selectedFam ?? "Vascular Plants"}

```js
import { rankFamily} from "./rankings.js";
```

```js
// From the WGSRPD shapefile, simplified and converted to topojson with mapshaper
const wgsrpdTopo = FileAttachment('./data/level3.json').json();
const sr = FileAttachment('./data/family-area-sr.json').json();
const cmnNames = FileAttachment('./data/taxa-inat-darwincore.json').json();
const colorMap = FileAttachment('./data/climate-colors-map.json').json();
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
  range: ["#FAF7C7", "#688816", "#1C3D28"], 
  domain: richnessExtent,
  interpolate: "rgb",
  unknown: "#f5f4e8", // since we replaced null with zero
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
// set width min 900px, max 1200 px, or 80% of width in between
// Mayb add a slider to let the user pick the map width?
const mapWidth = (width < 800) ? 800 : Math.min(width, 1000); 

const selAreaMap = Plot.plot({
  projection: { type: "equal-earth", domain: wgsrpd },
  width: mapWidth,
  color: { ...colorOptions, legend: false },
  marks: [
    Plot.sphere({fill: "#8db3be", fillOpacity: 0.7}),
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
      strokeWidth: 2,
      tip: {fill: dark ? "#662200" : "var(--theme-background)",}
    })),
    // Overlay updated based on table selection
    Plot.geo(
      codeToFeature[mutAreaTableSelection] ?? [],
      { stroke: "#662200", strokeWidth: 2, fill: "none"}
      // Give this a tip label as well?
    )
  ]
});

// Plot sets this explicitly from width + projection aspect ratio —
// available immediately, no need to wait for DOM layout.

// console.log("reloaded main map")
```
```js
const mapHeight = +selAreaMap.getAttribute("height");
```

```js
// Set mutable for selected area, separate one for table
const persistedArea = Mutable(null);
const setPersistedArea = (v) => {persistedArea.value = v;};
```
```js
// Reset signal for table select
const mutAreaTableSelection = Mutable(null);
const setMutAreaTableSelection = (v) => {mutAreaTableSelection.value = v;}
```

```js
// On map input, set table select to none
const selArea = Generators.observe((notify) => {
  let lastCode = undefined; // plain closure var — NOT reactive, just local bookkeeping
  const inputted = () => {
    // console.log("input")
    const current = selAreaMap.value;
    notify(current);
    const currentCode = current?.properties?.LEVEL3_COD;
    if (currentCode !== lastCode) {
      lastCode = currentCode;
      // Only touch the Mutable when the hovered area actually changes,
      // and only if something is even selected in the table right now
      if (mutAreaTableSelection !== null) setMutAreaTableSelection(null);
    }
  };
  inputted();
  selAreaMap.addEventListener("input", inputted, {capture: true});
  return () => selAreaMap.removeEventListener("input", inputted, {capture: true});
});
```
```js
if (selArea !== null) setPersistedArea(selArea);
```


```js
// Standalone legend, rendered separately in normal document flow
const colorLegend = Plot.legend({ color: colorOptions });
```

```js
// TODO: Align to center, add LDG plot on the right
html`<div>
  <div class="grid grid-cols-2" >
    <div>${colorLegend}</div> <div>${logscaleInput}</div>
  </div>
  <div style="position: relative; width: ${mapWidth}px; height: ${mapHeight}px;">
    <div style="position: absolute; top: 0; left: 0;">${selAreaMap}</div>
  </div>
</div>`
```

<div class="grid grid-cols-2" style="grid-auto-rows: auto;">
<div class="card">

${persistedArea === null
  ? html`
    <h1 style="font-family: 'serif';font-weight: normal;">Global Vascular Plant Families</h1>
    `
  : html`
      <h1 style="font-family: 'serif';font-weight: normal;">${persistedArea.properties.LEVEL3_NAM}</h1>
    `
}

```js
// TODO: Set input to null when something else changes
const areaNameToFeature = Object.fromEntries(
  wgsrpd.features.map(feature => [
    feature.properties.LEVEL3_NAM,
    feature
  ])
)
```
```js
const areaSelectDropdownInput = Inputs.select([null].concat(Object.keys(areaNameToFeature)),{
  label: "Select area from list",
  value: null,
  width: 260
});

const areaClearButtonInput = Inputs.button("Clear", {reduce: () => setPersistedArea(null)});
```
```js
const areaSelectDropdown = Generators.input(areaSelectDropdownInput);
const areaClearButton = Generators.input(areaClearButtonInput);
```
```js
// Set persistent area from table
if (areaSelectDropdown !== null) {
  const areaSelFeature = areaNameToFeature[areaSelectDropdown]
  setPersistedArea(areaSelFeature);
  setMutAreaTableSelection(areaSelFeature.properties.LEVEL3_COD);
};
```

<div style="display:flex; gap:4px; align-items:center;">
  ${areaSelectDropdownInput}
  ${areaClearButtonInput}
</div>

${persistedArea === null
  ? html`
    <p>Select a family from the table below, or a botanical country from the map or right table.</p>
    `
  : html`
      <p>Contains ${areaRanked.length.toLocaleString()} plant families and ${totalSrMap[persistedArea.properties.LEVEL3_COD].toLocaleString()} species.</p>
      ${topFamiliesNum > 0 ? html`<p>Top ranked for ${topFamiliesNum} families!</p>` : html``}
    `
}

```js
// Get global SR by family
const globalFamilyEntries = Object.keys(sr).map((family) => {
  return {
    family, 
    cmnName: cmnNamesFiltered[family]?.[0],
    globalSr: sr[family]['global'],
    nAreas: Object.values(sr[family]['sr']).filter((d) => d > 0).length
  }
});
// Get total global species richness
const globalSrSum = globalFamilyEntries.reduce(
  (a,b) => a + b['globalSr'], 0
);
```

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
const areaRanked = [...areaEntries].sort((a, b) => d3.ascending(a.rank, b.rank)).filter((d) => d.richness>0);
const topFamiliesNum = areaRanked.filter((d) => d.rank == 1).length
// starter code for number of endemic families
// replace selectedFam with all families. 
// If this country has all the global species, and the second highest country has zero, it's endemic.
// if (sr[selectedFam]['global'] === sr[selectedFam]['sr'][persistedArea.properties.LEVEL3_COD] & famRanked[1] === 0) 
```

```js
const famTableInput = (persistedArea != null)
  ? view(Inputs.table(areaRanked, {
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
  : view(Inputs.table(globalFamilyEntries, {
    columns: ["family", "cmnName", "globalSr", "nAreas"],
    header: {
      family: "Plant Family", 
      cmnName: "Common Name",
      globalSr: "Species Richness",
      nAreas: "Areas present"
      },
    sort: "globalSr", reverse: true,
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
if (famTableInput !== null) {
  setSelectedFam(famTableInput.family);
  // Set mutTableArea to the current selected family so it persists on map reload
  if (mutAreaTableSelection == null && persistedArea != null) setMutAreaTableSelection(persistedArea.properties.LEVEL3_COD);
  // TODO: Now reset the search bar text
}

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
  <button id="clearFamSelection">Clear selection</button>
</div>`;

const inputEl = familySearchBox.querySelector("#famInput");
const goButtonEl = familySearchBox.querySelector("#famSubmit");
const clButtonEl = familySearchBox.querySelector("#clearFamSelection");

function commitFamily() {
  const raw = inputEl.value.trim().toLowerCase();
  const resolved = familyLookup.get(raw);
  if (resolved) {
    setSelectedFam(resolved);
    // TODO: Clear table selection?
  }
  // else: optionally flash an "not found" state
}

goButtonEl.addEventListener("click", commitFamily);
clButtonEl.addEventListener("click", () => setSelectedFam(null));
inputEl.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    commitFamily();
  }
});
inputEl.addEventListener("input", () => {
  if (familyLookup.has(inputEl.value.trim().toLowerCase())) {
    commitFamily();
  }
});
```
</div>



<div class="card">

```js
selectedFam == null
  ? html`<p>Select a plant family with the search bar or from the left table.</p>`
  : html`
        <div><h1 style="font-family: 'serif';font-weight: normal;">
          <a href="https://en.wikipedia.org/wiki/${selectedFam}" target="_blank">${selectedFam}</a>
        </h1><h2 style="font-family: 'serif';">${cmnNamesFiltered[selectedFam]?.[0] ? " "+cmnNamesFiltered[selectedFam][0]+" " : ""}</h2>
        </div>
        `
```

<div>${familySearchBox}<br></div>

```js
// TODO: fix wide images not showing?
const imgUrl = sr[selectedFam]?.['image']?.['thumbUrl'] ?? null
const imgSrcUrl = sr[selectedFam]?.['image']?.['descriptionUrl'] ?? null

const imgAuthor =  sr[selectedFam]?.['image']?.['author'] ?? null 
const imgAuthorText = 
  (imgAuthor?.[0] === "uploader") 
  ? "Uploader: " + imgAuthor[1] + " | "  
  : imgAuthor?.[1] + " | " ?? null

const depicts = sr[selectedFam]?.['image']?.['depicts']
const depictsHtml = depicts 
  ? html`<a href="https://en.wikipedia.org/wiki/${depicts?.replace(" ","_")}" target="_blank"><i>${depicts}</i></a><br>`
  : html``
const akaHtml = (cmnNamesFiltered[selectedFam]?.length > 1)
  ? html`<p><strong>Also known as:</strong> ${cmnNamesFiltered[selectedFam].slice(1).join(", ")}.</p>`
  : html` `
const licenseUrl = sr[selectedFam]?.['image']?.['licenseUrl']
const licenseHtml = licenseUrl != null
    ? html`<a href="${licenseUrl}", target="_blank">${sr[selectedFam]?.['image']?.['license']}</a>. `
    : html`${sr[selectedFam]?.['image']?.['license']}. `
const wikiUrl = "https://en.wikipedia.org/wiki/" + selectedFam ?? "";
const inatUrl = "https://www.inaturalist.org/taxa/" + sr[selectedFam]?.['ids']['inatId'] ?? "";
const colUrl = "https://www.catalogueoflife.org/data/taxon/" + sr[selectedFam]?.['ids']['colId'] ?? "";
const powoUrl = "https://powo.science.kew.org/taxon/" + sr[selectedFam]?.['ids']['powoId'] ?? "";
```

<details open><summary><b>About this family</b></summary>

```js
selectedFam != null
  ? html`
  ${imgUrl != null 
    ? html`<figure style="
        float: right;
        width: 220px;
        margin: 0 0 1em 1.5em;
        border: 1px solid var(--theme-foreground-fainter);
        background: var(--theme-background);
        padding: 0.4em;
        font-size: 0.85em;
        text-align: center;
      ">
      <a href="${imgSrcUrl}"  target="_blank">
      <img src="${imgUrl}" alt="Representative image from Wikimedia Commons." style="width: 100%; height: auto; display: block;"></a>
      <figcaption style="padding-top: 0.4em; color: var(--theme-foreground-muted);">
        ${depictsHtml}
        ${imgAuthorText}
        ${licenseHtml}</figcaption>
      </figure>`
    : html`<p>No images available. Consider adding one on <a href="https://www.wikidata.org/wiki/${sr[selectedFam]?.['ids']['wikidata'] ?? ""}" target="_blank">Wikidata</a>?</p>`
  }
  ${akaHtml}
  <!--<p><strong>Preferred climate:</strong> ${Object.keys(sr[selectedFam]?.['climate'])[0]}</p> -->
  <p>Contains ${sr[selectedFam]?.['global'].toLocaleString() ?? "—"} species in ${Object.values(sr[selectedFam]?.['sr']).filter((d) => d > 0).length} countries, highest species richness in ${famRanked[0]?.areaName ?? "—"}.</p>
  <p><b>Read more: </b><a href="${wikiUrl}" target="_blank">Wikipedia</a> | <a href="${inatUrl}" target="_blank">iNaturalist</a> | <a href="${colUrl}" target="_blank">Catalogue of Life</a> | <a href="${powoUrl}" target="_blank">POWO</a> </p>
  `
  : html` `
```

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
// Lookup feature from country code
const codeToFeature = Object.fromEntries(
  wgsrpd.features.map(feature => [
    feature.properties.LEVEL3_COD,
    feature
  ])
)
```
```js
// Set persistent area from table
if (areaTableSelect !== null) {
  setPersistedArea(
    codeToFeature[areaTableSelect.areaCode]
  );
  // selAreaMap.value = null;
  // selAreaMap.dispatchEvent(new Event("input", {bubbles: true}));
  setMutAreaTableSelection(areaTableSelect.areaCode);
};
```



</div>
<div class="card"><h1>Diversity and Distribution</h1>

Comparison of the distribution (number of areas, *x*) with global species richness (log scale, *y*) for each family. ${selectedFam ? html`Selected family is <mark style="background-color: #688816;">highlighted</mark>.`: html` `}

```js
const globalSrPlot = view(Plot.plot({
  x: {label: "number of areas present"},
  y: {type: "log", label: "Species richness"},
  marks: [
    Plot.dot(globalFamilyEntries.filter((d) => d.family == selectedFam), {x: "nAreas", y: "globalSr", fill: "#688816", r: 8}),
    Plot.dot(globalFamilyEntries, {x: "nAreas", y: "globalSr", opacity: 0.6}),
    Plot.tip(globalFamilyEntries, Plot.pointer({x: "nAreas", y: "globalSr", title: (d) => [d.family, d.cmnName].join("\n")}))
  ]
}));
// const globalSrPlotInput = Generators.input(globalSrPlot)
// TODO: Add another select on click tip so you can change selected family from here
// Actually setting selectedFam from this view() would be too intense, so only on click
```

</div>

<div class="card"><h1>Diversity and Climate</h1>
For the selected family, breakdown of the species richness by climate.

```js
const climateEntries = selectedFam 
  ? Object.entries(sr[selectedFam]['climate']).map(
      ([climate, species]) => ({
        climate: climate, 
        species: Math.round(species)
      })
    )
  : null;

if (selectedFam != null) {view(Plot.plot({
      marginBottom: 80,
    x: {
      label: null,
      lineWidth: 1,
      tickRotate: -30,
      domain: Object.keys(colorMap) //.filter(d => climateEntries.some(entry => entry.climate === d))
    },
    y: {label: "Species richness"},
    color: {
      type: "categorical",
      domain: Object.keys(colorMap),
      range: Object.values(colorMap),
      unknown: "var(--theme-foreground)"
      },
    marks: [
      Plot.barY(climateEntries, {
          x: "climate", 
          y: "species", 
          fill: "climate"
        }),
      Plot.tip(climateEntries, Plot.pointerX({x: "climate", y: "species", title: "species"}))
      ]
    }))
}else{
  display(html`<p><i>Select a plant family from the table or search bar.</i></p>`)
}

```
</div>
</div>

<div class="wide">

## About

The World Checklist for Vascular Plants (WCVP)[^1] classifies the world's [vascular plants](https://en.wikipedia.org/wiki/Vascular_plant) into ${globalSrSum.toLocaleString()} species in ${Object.keys(sr).length} families. It also tracks their distributions into ${wgsrpd.features.length} "botanical countries". This site is used to explore the number of species in different areas, a useful measure of global biodiversity ([α-diversity](https://en.wikipedia.org/wiki/Alpha_diversity)). 

The data on this site **includes** extinct species, hybrids and "doubtfully present" locations, while **excluding** introduced ranges. Data is updated weekly from WCVP's [data repository](https://sftp.kew.org/pub/data-repositories/WCVP/). The idea is that this will allow us to examine the "natural" patterns of plant diversity. A future version of the site will allow the user to tweak these parameters.

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
- Sarraceniaceae (new world pitcher plants) are a cool family with an interesting distribution, highest around Florida and Venezuela.
  - ${Inputs.button("Select Sarraceniaceae", {reduce: () => setSelectedFam("Sarraceniaceae")})}
- The gentian family has an interesting climate breakdown, the majority of species are found in "subalpine or subarctic" climate, which is very unusual.
  - ${Inputs.button("Select Gentianaceae", {reduce: () => setSelectedFam("Gentianaceae")})}
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