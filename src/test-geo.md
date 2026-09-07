---
title: Geo Test
theme: dashboard
toc: false
---

# Floral World
```js
const wgsrpd = FileAttachment('./data/wgsrpd.geojson').json();
const sr = FileAttachment('./data/family-area-sr.json').json();
// const selFamily = Mutable(null)
```

```js
// const selArea = Mutable(null)

const selArea = view(Plot.plot({
  projection: { type: "equal-earth" },
  width: 1080,
  marks: [
    Plot.sphere(),
    Plot.graticule(),
    Plot.geo(wgsrpd, {fill: "currentColor"}),
    Plot.geo(wgsrpd, Plot.pointer({
        title: "LEVEL3_NAM", 
        stroke: 'red',
        tip: true
        }))
  ]
}));

// if there are problems with data requesting too fast:
// Only call the table if it's "frozen" as per https://observablehq.com/@mtsvelik/plot-frozen-state-detection
```

<div class="grid grid-cols-2">

<div class="card">

  ${selArea === null
    ? html`<p>Click a mark on the chart to view details.</p>`
    : html`
        <h2>${selArea.properties.LEVEL3_NAM}</h2>
        <p>Additional details go here...</p>
      `
  }
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

  ${selFamily === null 
    ? html`<p>Choose a family from the search bar</p>`
    : html`
        <p>Value: <strong>${selFamily[0]}</strong></p>
        <p>Additional details go here...</p>
      `
  }


</div>
</div>