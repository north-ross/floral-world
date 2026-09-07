---
title: Leaflet Test
---

# FloralWorld

```js
import * as L from "npm:leaflet";
```

```html
<style>
.leaflet-container {
background-color:rgba(255,0,0,0.0);
}
</style>
```

```js
const div = display(document.createElement("div"));
div.style = "height: 400px;";

const map = L.map(div)
  .setView([0, 0], 1);

const geoJsonData = FileAttachment("./data/wgsrpd.geojson").json();
```
```js
L.geoJSON(geoJsonData).addTo(map);


```
