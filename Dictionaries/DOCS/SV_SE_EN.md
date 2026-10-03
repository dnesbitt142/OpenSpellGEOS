<!-- SPDX-License-Identifier: Apache-2.0 -->

# OpenSpellGEOS: Svenska

## Installation

Close PC/GEOS Ensemble before replacing dictionary files. Extract the package and copy its .DCT, .THS, .HYP and .GDI files into Ensemble/USERDATA/DICTS. In Preferences, select Svenska and restart Ensemble after changing the language.

Keep NOTICES.TXT and LICENSES with redistributed copies. The complete project archive contains the build tools, normalized inputs and technical documentation. This package also includes the matching local-language guide.

## Data files

The maximum is 1000000 decimal bytes (1 MB) for each complete .DCT, .THS or .HYP file. It includes the header, index, padding and payload. The counts below describe the distributed files dated 2026-10-03; BUILD.json records custom rebuild results.

| File | Records | Complete bytes |
| --- | ---: | ---: |
| SV_SE.DCT | 113629 | 999766 |
| SV_SE.THS | 8922 | 723565 |
| SV_SE.HYP | 41780 | 417151 |

## Coverage

Spelling uses the Swedish NST pronunciation lexicon and an authored supplement. The 990 authored everyday forms are mandatory, including both hej and heja. The source contains some automatically generated forms. The thesaurus covers specialist terminology and retains all available encoded headwords. Hyphenation covers explicit compound boundaries only; breaks within simple words or compound components remain unavailable.

Suggestions use letter similarity. Sentence-level grammar and meaning are outside the checker’s scope. Vocabulary remains finite.

## Compatibility and licences

These files use the existing OLX1 format and the OpenSpellGEOS library. Lookup uses small caches and reads the files as needed; it does not load a complete dictionary into memory. The library, conversion tools and authored additions are Apache-2.0. The linguistic sources retain their separate Apache-compatible licences or public-domain/CC0 status. Full original legal notices are supplied unchanged in NOTICES.TXT and LICENSES.

## Validation

The host checks decoded every data record, verified complete-file hashes and the 1 MB limits, queried actual files through the C reader, checked the GDI labels and recreated all six spelling dictionaries byte-for-byte. These checks do not constitute new native GEOS GUI testing or independent native-speaker editorial review.
