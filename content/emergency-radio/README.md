# ARKive Emergency Radio Guide

Original, plain-language emergency radio guide (FRS/GMRS, MURS, marine VHF, NOAA weather radio, ham, CB,
the 3-3-3 listening plan, a disaster checklist and a one-page printable cheat sheet). MIT licensed (see LICENSE).
Frequencies were checked against 47 CFR Parts 95 and 97, NOAA, the USCG Navigation Center and the ARRL band plan.

- `src/`          the static HTML site (edit here)
- `build-zim.sh`  builds `arkive_en_emergency-radio_YYYY-MM.zim` with zimwriterfs (apt install zim-tools)
- `install.sh`    fetch-step hook: rebuilds the ZIM into /srv/archive/zim and registers it in library.xml
