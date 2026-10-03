<!-- SPDX-License-Identifier: Apache-2.0 -->

# OpenSpellGEOS: Français (France)

## Installation

Fermez PC/GEOS Ensemble avant de remplacer les fichiers du dictionnaire. Décompressez le paquet et copiez les fichiers .DCT, .THS, .HYP et .GDI dans Ensemble/USERDATA/DICTS. Dans les préférences (Preferences), choisissez Français (France) et redémarrez Ensemble après un changement de langue.

Conservez NOTICES.TXT et LICENSES avec les copies redistribuées. L’archive complète du projet contient les outils de génération, les données d’entrée normalisées et la documentation technique. Ce paquet comprend également le guide correspondant en anglais.

## Fichiers de données

Chaque fichier complet .DCT, .THS ou .HYP est limité à 1000000 octets (1 Mo). L’en-tête, l’index, les octets de remplissage et les données sont compris dans cette limite. Les valeurs ci-dessous concernent les fichiers distribués du 03/10/2026 ; BUILD.json décrit les résultats d’une génération personnalisée.

| Fichier | Entrées | Taille totale en octets |
| --- | ---: | ---: |
| FR_FR.DCT | 132192 | 999766 |
| FR_FR.THS | 2443 | 183831 |
| FR_FR.HYP | 115530 | 999766 |

## Couverture linguistique

L’orthographe s’appuie sur une ancienne liste française du domaine public, dont une sélection compacte de formes explicites est conservée. Il ne s’agit pas d’un dictionnaire normatif complet du français actuel. Le thésaurus couvre une terminologie spécialisée. La césure française est précalculée à partir des motifs sélectionnés et se limite aux mots conservés dans le dictionnaire.

Les suggestions reposent sur la ressemblance des lettres. La grammaire et le sens des phrases entières ne sont pas analysés. Le vocabulaire reste limité.

## Compatibilité et licences

Ces fichiers utilisent le format OLX1 existant et la bibliothèque OpenSpellGEOS. La recherche utilise de petits caches et lit les données au besoin ; le dictionnaire entier n’est pas chargé en mémoire. La bibliothèque, les outils de conversion et les ajouts rédigés pour le projet sont sous Apache-2.0. Les sources linguistiques conservent leurs licences distinctes compatibles avec Apache, ou leur statut de domaine public/CC0. Les mentions légales originales complètes sont fournies sans modification dans NOTICES.TXT et LICENSES.

## Validation

Les vérifications sur l’ordinateur de compilation ont décodé toutes les entrées, vérifié les empreintes des fichiers et les limites de 1 Mo, interrogé les fichiers réels avec le lecteur C, contrôlé les libellés GDI et reproduit les six dictionnaires orthographiques octet pour octet. Elles ne constituent ni un nouveau test de l’interface GEOS ni une révision linguistique indépendante par des francophones.
