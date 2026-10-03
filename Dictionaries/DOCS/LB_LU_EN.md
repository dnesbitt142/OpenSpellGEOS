<!-- SPDX-License-Identifier: Apache-2.0 -->

# OpenSpellGEOS: Lëtzebuergesch

## Installation

Close PC/GEOS Ensemble before replacing dictionary files. Extract the package and copy its .DCT, .THS, .HYP and .GDI files into Ensemble/USERDATA/DICTS. In Preferences, select Lëtzebuergesch and restart Ensemble after changing the language.

Keep NOTICES.TXT and LICENSES with redistributed copies. The complete project archive contains the build tools, normalized inputs and technical documentation. This package also includes the matching local-language guide.

## Data files

The maximum is 1000000 decimal bytes (1 MB) for each complete .DCT, .THS or .HYP file. It includes the header, index, padding and payload. The counts below describe the distributed files dated 2026-10-03; BUILD.json records custom rebuild results.

| File | Records | Complete bytes |
| --- | ---: | ---: |
| LB_LU.DCT | 116235 | 933337 |
| LB_LU.THS | 7250 | 337014 |
| LB_LU.HYP | 0 | 64 |

## Coverage

The full normalized Luxembourgish spelling inventory is retained. Spelling and explicit synonym groups come from the CC0 Luxembourgish Online Dictionary (LOD). The word list includes recorded n-rule alternatives but cannot decide which variant fits a sentence. Automatic hyphenation remains unavailable because no suitable verified source was supplied; the .HYP file is an empty no-break fallback.

Suggestions use letter similarity. Sentence-level grammar and meaning are outside the checker’s scope. Vocabulary remains finite.

## Compatibility and licences

These files use the existing OLX1 format and the OpenSpellGEOS library. Lookup uses small caches and reads the files as needed; it does not load a complete dictionary into memory. The library, conversion tools and authored additions are Apache-2.0. The linguistic sources retain their separate Apache-compatible licences or public-domain/CC0 status. Full original legal notices are supplied unchanged in NOTICES.TXT and LICENSES.

## Validation

The host checks decoded every data record, verified complete-file hashes and the 1 MB limits, queried actual files through the C reader, checked the GDI labels and recreated all six spelling dictionaries byte-for-byte. These checks do not constitute new native GEOS GUI testing or independent native-speaker editorial review.
