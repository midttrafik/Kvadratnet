# Formål

Beregn distancen fra hvert kvadrat i et kvadratnet til nærmeste stoppested.\\
Området er som udgangspunkt Region Midtjylland, men ethvert administrativt område fra OpenStreetMap kan anvendes.\\


# Data

* Shapefil for kvadratnet.
    - Skal mindst indeholde kolonnerne geometry og antal_tal
    - F:\Køreplanlægning\Data og Analyse\Grunddata\Befolkning\...\xxx.shp
* CSV for standere med UTM32N koordinater.
    - Skal mindst indeholde kolonnerne: UTM32_Easting, UTM32_Northing, Long name, Kode til stoppunkt og Pos.nr.
* Dobbeltrettet OSM netværk af typen ”all” hentes automatisk. Inkluderer alle typer veje og stier indenfor det administrative område.


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
* Evt. slet cache

Resultatet indeholder:
* Det originale kvadratnet
* Navn og nummer på nærmeste stander til hver kvadrat
* Den totale distance mellem centroiden af kvadratet og gps punkt for nærmeste stander (summen af de tre næste distancer)
* Distance fra centroide af kvadratnet til nærmeste OSM knude
* Distance fra standerens gps punkt til nærmeste OSM knude
* Distance mellem centroidens OSM knude og standerens OSM knude
![screenshot](Ressourcer/Resultat_eksempel.png)


[!IMPORTANT]
Alle beregningerne indeholder en usikkerhed da centroider og standere tildeles OSM knuder.

Vej- og stinettet fra OpenStreetMap er en graf som består af et sæt knuder og kanter.\\
Selvom Region Midtjylland har over 1 million knuder, findes der ikke én knude som er præcist placeret ved centroiden af et kvadrat.\\
I enkelte tilfælde betyder det at et kvadrat har en højere distance sammenlignet med nabokvadraterne.\\
![screenshot](Ressourcer/Kvadrat_usikkerhed.png)


# Dokumentation af løsning

Python [OSMNX](https://osmnx.readthedocs.io/en/stable/) og [NetworkX](https://networkx.org/) til at håndtere OSM grafen.\\
Python [igraph](https://github.com/igraph/python-igraph) (Python interface til C bibliotek) anvendes til højeffektive udregninger af grafteori bl.a. ved parallelisering på flere CPU-kerner.\\
Koblingen mellem Pytohn og igraph er lavet med inspiration i Notebook 14 fra [OSMNX Notebooks](https://github.com/gboeing/osmnx-examples)\\

Kerne-algoritmen udregner korteste distance fra et punkt i inputfilen til nærmeste punkt i hjælpefilen.\\
Programmets overordnet struktur:
* Indlæs kvadratnet
* Indlæs standere og anvend filtre
* Hent OSM netværk med OSMNX
* Omdan OSM netværket til en igraph graf hvor kanter er vægtet med kantlængde i meter
* Gem en mapping af igraph id til osmid og en mapping af osmid til igraph id
* Find nærmeste OSM knude til alle centroider på kvadratnettet og gem distancen
* Find nærmeste OSM knude til alle stop og gem distancen
* Fjern stop hvis distancen mellem stop og nærmeste OSM knude er > 1000 meter. Det betyder at stoppet er udenfor det angivne område.
* Oversæt OSM knuder til igraph nodes
* Find korteste distance fra hver stop knude til alle knuder på grafen
* For hver centroide knude, find det stop med kortest distance


## Effektivitet

Umiddelbart er problemet at finde distancen fra hver centroide til det nærmeste stoppested dvs. *centroide* $\rightarrow$ *alle stop*.\\
Det er muligt at udregne fugleflugtsdistancen fra hver centroide til alle stops og kun udføre Dijkstras algoritme til de nærmeste K stop.\\
Problemet ved denne tilgang er, at beregningerne skal gentages for hver centroide. Da mange centroider befinder sig tæt på hinanden og har (næsten) samme nærmeste stoppested og sti dertil, betyder det mange repetitive (overflødige) beregninger.\\

Problemet kan vendes om til *stop* $\rightarrow$ *alle centroider*.\\
For at undgå repetitive beregninger kan problemet omformuleres til *stop* $\rightarrow$ *alle knuder på grafen*.\\
Denne tilgang udregner mange unødvendige distancer, dog skal alle beregninger kun udføres én gang pr. stop.\\
Denne tilgang løser problemet *stop* $\rightarrow$ *alle centroider* da centroider er en delmængde af alle nodes.\\
Denne tilgang kan nemt paralleliseres i igraph og udnytter effekterne ved multiprocessing.\\


# Backlog

* Bedre input data abstraktion. Gør kompatible med vilkårligt punkt eller polygon data i input og hjælpefil.
