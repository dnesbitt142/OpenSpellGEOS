# OpenSpellGEOS
A Open Source spelling/thesaurus/hyphenation library for PC/GEOS

## How to build (once your SDK is set up):
1. Unpack the `Appl` and `Installed` root level folders to `%ROOT_DIR%`/`$ROOT_DIR`
2. In the terminal, navigate to `Installed/Library/Spell`
3. Then run:
   
`mkmf`

`pmake depend`

`pmake full`

### How to install
1. Copy `spell.geo` (or `spellec.geo for the EC version`) to `<Ensemble root folder>\SYSTEM`
2. Download the [dictionary of your proffered language](https://github.com/dnesbitt142/OpenSpellGEOS/tree/aa1d4bc31e5afb6e3c46e577de94db77137d59f5/Dictionaries) and unpack the *.dct, *.gdi *.hyp and *.ths files to `<Ensemble root folder>\USERDATA\DICTS` (you may need to create the DICTS directory first).
3. Once Ensemble is running, chose the dictionary in Preferences > Text > Choose New Main Dictionary (a restart may be required).

Code is licensed under the Apache License 2.0, see [licenses](https://github.com/dnesbitt142/OpenSpellGEOS/tree/main/Dictionaries/BuildTools/Sources/licenses) for each supplied languages' license.

Python tools for creating your own dictionaries, thesaurus and hyphenation files are included in the Dictionaries > BuildTools folder (untested).

## Issues/outstanding tasks:
* Test and update building tools
* Performance testing on older (pre-Pentium) machines/VMs
* Testing of every language.
* Luxembourgish does not have a pre-set country ID in PC/GEOS, so is set to 0.
* A empty user dictionary is not provided by default (the spellchecker will make one when user wards are added).
* No word accents in .gdi files (used by Preferences).
* Document formats of Dictionary (.dct), Hyphenation (.hyp) and Thesaurus (.ths) files.

## Other notes
* No hyphenation supplied for Luxembourgish
* See [NOTICES.TXT](https://github.com/dnesbitt142/OpenSpellGEOS/blob/main/Dictionaries/NOTICES.TXT) for further limitations.details.
* Dictionary and thesaurus data files are small (around 500KB so do not contain a large word set).
