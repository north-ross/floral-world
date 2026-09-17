
# Simple query to get all vascular plant families - times out. This proves that filtering by parent taxon is bad
q = """
SELECT ?taxonname WHERE {

  ?item wdt:P31 wd:Q16521 ;
        wdt:P105 wd:Q35409 ;
        wdt:P171* wd:Q27133 ; # parent taxon is vascular plants
        wdt:P225 ?taxonname .
}
"""

# My main query based on the above but getting all the info, filtered to a temp list of plants
qmain = """
SELECT ?item ?taxonname 
    (SAMPLE(?_image) AS ?image)  
    (SAMPLE(?_inatId) AS ?inatId) 
    (SAMPLE(?_colId) AS ?colId) 
    (SAMPLE(?_powoId) AS ?powoId)
    (SAMPLE(?_wikipediaUrl) AS ?wikipediaURL) WHERE {
  VALUES ?taxonname { "Ericaceae" "Poaceae" "Onagraceae" "Fabaceae" "Pinaceae" "Salicaceae"}
  
  ?item wdt:P31 wd:Q16521 ;
        wdt:P105 wd:Q35409 ;
#         wdt:P171* wd:Q27133 ; # filter by parent taxa to vascular plants - causes slowdown
        # is there another way to just filter to plants?
        wdt:P225 ?taxonname .
  OPTIONAL { ?item wdt:P18 ?_image. }
  
  OPTIONAL { ?item wdt:P3151 ?_inatId. } # check if these exist for all results - if so, remove optional
  OPTIONAL { ?item wdt:P10585 ?_colId. }
  OPTIONAL { ?item wdt:P5037 ?_powoId. }
      # add paleobio iD? slows things down and doesnt exist much
  
  OPTIONAL {
    ?_wikipediaUrl schema:about ?item ;
                  schema:isPartOf <https://en.wikipedia.org/> .
  }

  
} 
GROUP BY ?item ?taxonname 
"""