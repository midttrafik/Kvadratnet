# Formål

Beregn distancen fra hvert geometrisk punkt (f.eks. befolkningskvadratnet, arbejdspladser, uddannelsesinstitutioner) til nærmeste stoppested.<br/>
Området er som udgangspunkt Region Midtjylland, men ethvert administrativt område fra OpenStreetMap kan anvendes.<br/>

<br/>
<br/>


# Data

* Geometrisk inputfil som shapefil
    - Skal indeholde en geometrikolonne med navnet geom
    - Kan f.eks. være Befolkningskvadratnet, Arbejdspladser, Udannelsesinstitutioner mv.
    - F:\Køreplanlægning\Data og Analyse\Grunddata\Befolkning\...\xxx.shp
* Standerfil som CSV med UTM32N koordinater.
    - Skal indeholde kolonnerne: UTM32_Easting, UTM32_Northing, Long name, Kode til stoppunkt og Pos.nr.
* Dobbeltrettet OSM netværk af typen ”all” hentes automatisk. Inkluderer alle typer veje og stier indenfor det administrative område.

<br/>
<br/>


# Procedure

* Placer geometrisk inputfil (.shp) i mappen Data
* Placer stoppestedsfil (.csv) i mappen Data
* Åben script i VSCode og kør
* Indtast inputs. Default værdi er angivet som [...].
    - Filnavnet for standerfilen og geometrisk inputfil er påkrævet
    - OSM område er default Region Midtjylland men kan ændres til andre administrative områder f.eks. Aarhus
    - Stander chunk size kan sænkes fra 500 hvis memory er et problem
* Kør script (ca. 30-35 minutter)
    - Cirka 5 minutter for indlæsning af data
    - Cirka 1-2 minutter for Dijkstras algoritme per stander chunk
* Outputtet ligger i mappen Resultater
* Upload resultat til Webgis
* Evt. slet cache

Resultatet indeholder:
* Alle kolonner og geometrien fra input filen
* Navn og nummer på nærmeste stander til hver geometriske punkt
* (dist\_total) Den totale distance mellem centroiden af kvadratet og gps punkt for nærmeste stander (summen af de tre næste distancer)
* (d\_centroid) Distance fra geometrisk punkt til nærmeste OSM knude
* (d\_stop) Distance fra standerens gps punkt til nærmeste OSM knude
* (dist\_path) Distance mellem det geometriske punkts OSM knude og standerens OSM knude

![screenshot](Ressourcer/Resultat_eksempel.png)

<br/>

**_Vigtigt:_**<br/>
Alle beregningerne indeholder en usikkerhed da geometriske punkter og standere tildeles OSM knuder.<br/>
Vej- og stinettet fra OpenStreetMap er en graf som består af et sæt knuder og kanter.<br/>
Selvom Region Midtjylland har over 1 million knuder, findes der ikke én knude som er præcist placeret ved det geometriske punkt.<br/>
I enkelte tilfælde betyder det at et kvadrat har en højere distance sammenlignet med nabokvadraterne, hvis den nærmeste OSM knude er langt væk.<br/>
![screenshot](Ressourcer/Kvadrat_usikkerhed.png)

<br/>
<br/>


# Dokumentation af løsning

Python [OSMNX](https://osmnx.readthedocs.io/en/stable/) og [NetworkX](https://networkx.org/) til at håndtere OSM grafen.<br/>
Python [igraph](https://github.com/igraph/python-igraph) (Python interface til C bibliotek) anvendes til højeffektive udregninger af grafteori bl.a. ved parallelisering på flere CPU-kerner.<br/>
Koblingen mellem Python og igraph er lavet med inspiration i Notebook 14 fra [OSMNX Notebooks](https://github.com/gboeing/osmnx-examples)<br/>

Kerne-algoritmen udregner korteste distance fra et punkt i inputfilen til nærmeste punkt i hjælpefilen.<br/>

Programmets overordnet struktur:
* Indlæs geometrisk inputfil
* Indlæs standere og anvend filtre
* Hent OSM netværk med OSMNX
* Omdan OSM netværket til en igraph graf hvor kanter er vægtet med kantlængde i meter
* Gem en mapping af igraph id til osmid og en mapping af osmid til igraph id
* Find nærmeste OSM knude til alle geometriske punkter og gem distancen
* Find nærmeste OSM knude til alle stop og gem distancen
* Fjern stop hvis distancen mellem stop og nærmeste OSM knude er > 1000 meter. Det betyder at stoppet er udenfor det angivne område.
* Oversæt OSM knuder til igraph nodes
* Find korteste distance fra hver stop knude til alle knuder på grafen
* For hver geometrisk punkts knude, find det stop med kortest distance

<br/>
<br/>


## Effektivitet

Umiddelbart er problemet at finde distancen fra hver centroide til det nærmeste stoppested dvs. *punkt* $\rightarrow$ *alle stop*.<br/>
Det er muligt at udregne fugleflugtsdistancen fra hver centroide til alle stops og kun udføre Dijkstras algoritme til de nærmeste K stop.<br/>
Problemet ved denne tilgang er, at beregningerne skal gentages for hvert geometrisk punkt. Da mange geometriske punkter befinder sig tæt på hinanden og har (næsten) samme nærmeste stoppested og sti dertil, betyder det mange repetitive (overflødige) beregninger.<br/>

Problemet kan vendes om til *stop* $\rightarrow$ *alle punkter*.<br/>
For at undgå repetitive beregninger kan problemet omformuleres til *stop* $\rightarrow$ *alle knuder på grafen*.<br/>
Denne tilgang udregner mange unødvendige distancer, dog skal alle beregninger kun udføres én gang pr. stop.<br/>
Denne tilgang løser problemet *stop* $\rightarrow$ *alle punkter* da alle geometriske punkter er en delmængde af alle OSM knuder.<br/>
Denne tilgang kan nemt paralleliseres i igraph og udnytter effekterne ved multiprocessing.<br/>

<br/>
<br/>


# Backlog

* Bedre input data abstraktion. Gør kompatible med vilkårligt punkt eller polygon data i input og hjælpefil.
