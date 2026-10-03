<!-- SPDX-License-Identifier: Apache-2.0 -->

# OpenSpellGEOS: Français (France)

## Installation

Close PC/GEOS Ensemble before replacing dictionary files. Extract the package and copy its .DCT, .THS, .HYP and .GDI files into Ensemble/USERDATA/DICTS. In Preferences, select Français (France) and restart Ensemble after changing the language.

Keep NOTICES.TXT and LICENSES with redistributed copies. The complete project archive contains the build tools, normalized inputs and technical documentation. This package also includes the matching local-language guide.

## Data files

The maximum is 1000000 decimal bytes (1 MB) for each complete .DCT, .THS or .HYP file. It includes the header, index, padding and payload. The counts below describe the distributed files dated 2026-10-03; BUILD.json records custom rebuild results.

| File | Records | Complete bytes |
| --- | ---: | ---: |
| FR_FR.DCT | 132192 | 999766 |
| FR_FR.THS | 2443 | 183831 |
| FR_FR.HYP | 115530 | 999766 |

## Coverage

Spelling uses an older public-domain French vocabulary source and retains a compact selection of its explicit forms. It is not a comprehensive current normative French dictionary. The thesaurus covers specialist terminology. French hyphenation is precomputed from the selected patterns and is restricted to retained dictionary words.

Suggestions use letter similarity. Sentence-level grammar and meaning are outside the checker’s scope. Vocabulary remains finite.

## Compatibility and licences

These files use the existing OLX1 format and the OpenSpellGEOS library. Lookup uses small caches and reads the files as needed; it does not load a complete dictionary into memory. The library, conversion tools and authored additions are Apache-2.0. The linguistic sources retain their separate Apache-compatible licences or public-domain/CC0 status. Full original legal notices are supplied unchanged in NOTICES.TXT and LICENSES.

## Validation

The host checks decoded every data record, verified complete-file hashes and the 1 MB limits, queried actual files through the C reader, checked the GDI labels and recreated all six spelling dictionaries byte-for-byte. These checks do not constitute new native GEOS GUI testing or independent native-speaker editorial review.
