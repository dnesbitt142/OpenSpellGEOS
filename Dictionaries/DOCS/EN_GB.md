<!-- SPDX-License-Identifier: Apache-2.0 -->

# OpenSpellGEOS: English (British)

## Installation

Close PC/GEOS Ensemble before replacing dictionary files. Extract the package and copy its .DCT, .THS, .HYP and .GDI files into Ensemble/USERDATA/DICTS. In Preferences, select English (British) and restart Ensemble after changing the language.

Keep NOTICES.TXT and LICENSES with redistributed copies. The complete project archive contains the build tools, normalized inputs and technical documentation.

## Data files

The maximum is 1000000 decimal bytes (1 MB) for each complete .DCT, .THS or .HYP file. It includes the header, index, padding and payload. The counts below describe the distributed files dated 2026-10-03; BUILD.json records custom rebuild results.

| File | Records | Complete bytes |
| --- | ---: | ---: |
| EN_GB.DCT | 108778 | 860374 |
| EN_GB.THS | 9303 | 999677 |
| EN_GB.HYP | 75449 | 680689 |

## Coverage

The full normalized British spelling list is retained; this profile uses -ise forms. Synonyms come from WordNet and can include other regional spellings. British hyphenation patterns remain separate from the American patterns.

Suggestions use letter similarity. Sentence-level grammar and meaning are outside the checker’s scope. Vocabulary remains finite.

## Compatibility and licences

These files use the existing OLX1 format and the OpenSpellGEOS library. Lookup uses small caches and reads the files as needed; it does not load a complete dictionary into memory. The library, conversion tools and authored additions are Apache-2.0. The linguistic sources retain their separate Apache-compatible licences or public-domain/CC0 status. Full original legal notices are supplied unchanged in NOTICES.TXT and LICENSES.

## Validation

The host checks decoded every data record, verified complete-file hashes and the 1 MB limits, queried actual files through the C reader, checked the GDI labels and recreated all six spelling dictionaries byte-for-byte. These checks do not constitute new native GEOS GUI testing or independent native-speaker editorial review.
