<!-- SPDX-License-Identifier: Apache-2.0 -->

# OpenSpellGEOS: Svenska

## Installation

Stäng PC/GEOS Ensemble innan du ersätter ordboksfiler. Packa upp paketet och kopiera filerna .DCT, .THS, .HYP och .GDI till Ensemble/USERDATA/DICTS. Välj Svenska i inställningarna (Preferences) och starta om Ensemble efter ett språkbyte.

Behåll NOTICES.TXT och LICENSES tillsammans med kopior som distribueras vidare. Det fullständiga projektarkivet innehåller byggverktyg, normaliserade indata och teknisk dokumentation. Paketet innehåller även motsvarande engelska handledning.

## Datafiler

Varje fullständig .DCT-, .THS- eller .HYP-fil får vara högst 1000000 byte (1 MB). Filhuvud, index, utfyllnad och innehåll ingår i gränsen. Uppgifterna nedan gäller de distribuerade filerna från 2026-10-03; BUILD.json redovisar resultatet av egna byggen.

| Fil | Poster | Total storlek i byte |
| --- | ---: | ---: |
| SV_SE.DCT | 113629 | 999766 |
| SV_SE.THS | 8922 | 723565 |
| SV_SE.HYP | 41780 | 417151 |

## Språklig täckning

Stavningsordlistan bygger på det svenska uttalslexikonet från NST och ett separat tillägg som tagits fram för projektet. De 990 särskilt valda vardagsformerna måste finnas kvar, däribland både hej och heja. Källan innehåller vissa automatiskt genererade former. Synonymordlistan innehåller fackterminologi och behåller alla tillgängliga uppslagsord som kan kodas. Avstavningen omfattar endast uttryckliga gränser mellan sammansättningsled; brytpunkter inom enkla ord eller enskilda sammansättningsled saknas fortfarande.

Förslagen bygger på likheten mellan bokstäverna. Grammatik och betydelse i hela meningar analyseras inte. Ordförrådet är begränsat.

## Kompatibilitet och licenser

Filerna använder det befintliga OLX1-formatet och OpenSpellGEOS-biblioteket. Sökningen använder små cacheminnen och läser data vid behov; hela ordboken läses inte in i minnet. Biblioteket, konverteringsverktygen och projektets egna tillägg omfattas av Apache-2.0. Språkkällorna behåller sina separata Apache-kompatibla licenser eller sin status som allmän egendom/CC0. De fullständiga ursprungliga juridiska texterna finns oförändrade i NOTICES.TXT och LICENSES.

## Validering

Kontrollerna på byggdatorn har avkodat varje datapost, verifierat filernas kontrollsummor och gränserna på 1 MB, slagit upp ord i de verkliga filerna med C-läsaren, kontrollerat GDI-namnen och återskapat alla sex stavningsordlistor byte för byte. Detta är varken ett nytt test av GEOS-gränssnittet eller en oberoende språkgranskning av personer med språket som modersmål.
