<!-- SPDX-License-Identifier: Apache-2.0 -->

# OpenSpellGEOS: Deutsch (Deutschland)

## Installation

Close PC/GEOS Ensemble before replacing dictionary files. Extract the package and copy its .DCT, .THS, .HYP and .GDI files into Ensemble/USERDATA/DICTS. In Preferences, select Deutsch (Deutschland) and restart Ensemble after changing the language.

Keep NOTICES.TXT and LICENSES with redistributed copies. The complete project archive contains the build tools, normalized inputs and technical documentation. This package also includes the matching local-language guide.

## Data files

The maximum is 1000000 decimal bytes (1 MB) for each complete .DCT, .THS or .HYP file. It includes the header, index, padding and payload. The counts below describe the distributed files dated 2026-10-03; BUILD.json records custom rebuild results.

| File | Records | Complete bytes |
| --- | ---: | ---: |
| DE_DE.DCT | 130396 | 999766 |
| DE_DE.THS | 3744 | 258145 |
| DE_DE.HYP | 115252 | 999766 |

## Coverage

The dictionary retains explicit forms and compounds from the public-domain German source, plus four independently authored E-Mail forms. The 1114 authored everyday spellings (1102 canonical entry keys) are mandatory. The thesaurus covers specialist terminology. German hyphenation is precomputed using the selected reformed-orthography patterns. Compounds absent from the dictionary are outside the current runtime coverage.

Suggestions use letter similarity. Sentence-level grammar and meaning are outside the checker’s scope. Vocabulary remains finite.

## Compatibility and licences

These files use the existing OLX1 format and the OpenSpellGEOS library. Lookup uses small caches and reads the files as needed; it does not load a complete dictionary into memory. The library, conversion tools and authored additions are Apache-2.0. The linguistic sources retain their separate Apache-compatible licences or public-domain/CC0 status. Full original legal notices are supplied unchanged in NOTICES.TXT and LICENSES.

## Validation

The host checks decoded every data record, verified complete-file hashes and the 1 MB limits, queried actual files through the C reader, checked the GDI labels and recreated all six spelling dictionaries byte-for-byte. These checks do not constitute new native GEOS GUI testing or independent native-speaker editorial review.
