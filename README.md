# Floral World
An app to explore global vascular plant biodiversity using data from the [World Checklist for Vascular Plants](https://www.tdwg.org/standards/wgsrpd/). A map shows the species richness for each "botanical country" (WGSRPD level 3 division) and can be filtered by family. Tables let the user discover the "unique families" of each area, and what percentage of global biodiversity they contain.


This is an [Observable Framework](https://observablehq.com/framework/) app. For more, see <https://observablehq.com/framework/getting-started>.

## About
The World Checklist for Vascular Plants divides the world's [vascular plants](https://en.wikipedia.org/wiki/Vascular_plant) into ${Object.keys(sr).length -1} families and aggregates their distributions into "botanical countries". This site is used to explore the number of species in different areas, a useful measure of global biodiversity ([α-diversity](https://en.wikipedia.org/wiki/Alpha_diversity)). 

Since the boundaries used for aggregation are somewhat arbitrary, this visualization can't be taken too seriously as representing centers of biodiversity. See [this article](https://www.nature.com/articles/s41467-022-32063-z) for a much more scientific approach. However, this approach is much less computationally intensive, and the overall patterns still hold true. I've found it very interesting to explore different families and find the unique "specialty" families from different parts of the world.

