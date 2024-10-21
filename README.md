# Formål

Beregn distancen fra hvert kvadrat i et kvadratnet til nærmeste stoppested. 
Området er som udgangspunkt Region Midtjylland men ethvert andet område kan vælges.


# Data

* Shapefil for befolkningskvadratnet.
    - Skal mindst indeholde kolonnerne geometry og antal_tal
    - F:\Køreplanlægning\Data og Analyse\Grunddata\Befolkning\...\xxx.shp
* CSV for standere med UTM32N koordinater.
    - Skal mindst indeholde kolonnerne: UTM32_Easting, UTM32_Northing, Long name, Kode til stoppunkt og Pos.nr.
* Dobbeltrettet OSM netværk af typen ”all” hentes automatisk. Inkluderer alle typer veje og stier indenfor det definerede område



# Procedure

* Placer kvadratnetsfil (.shp) i mappen Data
* Placer stoppestedsfil (.csv) i mappen Data
* Åben script i VSCode og kør
* Indtast inputs. Default værdi er angivet som [...].
    - Filnavn på stoppested og kvadratnet er påkrævet
    - OSM område er default Region Midtjylland men kan ændres til andre områder f.eks. Aarhus
    - Chunk size kan sænkes fra 500 hvis memory er et problem
* Kør script (ca. 30-35 minutter)
    - Cirka 5 minutter for indlæsning af data
    - Cirka 1-2 minutter per chunk
* Upload resultat til Webgis

Resultatet indeholder:
* Det originale kvadratnet
* Distancen mellem centroiden af kvadratet og gps punkt for nærmeste stander
* Stander navn og standernummer for nærmeste stander


# Dokumentation af løsning

Lavet med inspiration fra notebook 14 i OSMNX eksempler.
Anvender OSMNX og NetworkX til at håndtere OSM netværk.
Anvender igraph, som er bygget i C, til super hurtige udregninger af Dijkstras algoritme. 

* Hent OSM netværk med OSMNX
* Omdan OSM netværket til en igraph graf hvor kanter er vægtet med kantlængde i meter
* Gem en mapping af igraph id til osmid og en mapping af osmid til igraph id
* Find nærmeste OSM node til alle centroider på kvadratnettet og gem distancen
* Find nærmeste OSM node til alle stop og gem distancen
* Fjern stop hvis distancen mellem stop og nærmeste OSM node er > 1000 meter. Det betyder at stoppet er udenfor det angivne område.
* Oversæt OSM nodes til igraph nodes
* Find korteste distance fra hver stop node til alle nodes på grafen
* For hver centroide node, find det stop med kortest distance


## Effektivitet

Umiddelbart er problemet at finde distancen fra hver centroide til det nærmeste stoppested dvs. centroide $\rightarrow$ alle stop. Det er muligt at udregne fugleflugtsdistancen fra hver centroide til alle stops og kun udføre Dijkstras algoritme til de nærmeste K stop.
Problemet er dog, at man er nødt til at gentage beregningerne for hver centroide, og da mange centroider befinder sig tæt på hinanden og har (næsten) samme nærmeste stoppested og sti dertil, betyder det mange repetitive (overflødige) beregninger.

Problemet kan vendes om til stop $\rightarrow$ alle centroider. For at undgå repetitive beregninger kan problemet omformuleres til stop $\rightarrow$ alle nodes på grafen. Det udregner mange unødvendige distancer, dog skal alle beregninger kun udføres én gang og løser problemet stop $\rightarrow$ alle centroider da centroider er en delmængde af alle nodes.
Igraph er et Python interface til en C implementation af Dijkstras algoritme og den paralleliserer udregningerne til flere CPU-kerner via multiprocessing.


# Backlog

Intet