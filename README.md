# Reservoir IoT-GIS-security simulation: code and data

Code and data accompanying the manuscript "A Cyber-Secure IoT-GIS Reference Architecture for Reservoir Monitoring and Control: Design and Multi-Scenario Simulation Study with an Illustrative Case of Ravishankar Sagar" [add journal and DOI after publication].

**All performance and security results come from a software simulation on synthetic reservoir archetypes. They are not field measurements, and no field deployment, real sensor data or penetration test is involved.** The only real data are weekly Central Water Commission (CWC) storage bulletins and NASA POWER (MERRA-2) reanalysis rainfall; they are too coarse to validate the five-minute detectors.

## Contents
| Path | Description |
|---|---|
| `code/testbed_sim.py` | Base simulation: LoRa radio, latency, edge filtering, detectors, attacks, gateway jamming. Writes `results/sim_results.json` |
| `code/testbed_multi.py` | Four synthetic archetypes (Tables 3 and 5). Writes `results/sim_results_multi.json` |
| `code/testbed_area.py` | Level-dependent surface area (Section 6.5, Table 7). Reads `data/gangrel_cwc_weekly.csv`, writes `results/sim_results_area.json` |
| `code/make_figures.py` | Figures 2, 3 and 4 (values copied from the manuscript tables and the CWC data) |
| `code/power_to_daily_rainfall.py` | Converts the NASA POWER CSV to `date,rain_mm` for Figure 4 |
| `results/*.json` | Result files used in the manuscript |
| `data/gangrel_cwc_weekly.csv` | Level and live-storage pairs from CWC bulletins (Table 8, Figure 4) |
| `data/POWER_Point_Daily_20230101_20250531_020d63N_081d57E_LST.csv` | NASA POWER daily rainfall, point 20.63 N, 81.57 E |

## Run
Run all commands from the repository root.
```
pip install -r requirements.txt
python code/testbed_sim.py
python code/testbed_multi.py
python code/testbed_area.py
python code/power_to_daily_rainfall.py data/POWER_Point_Daily_20230101_20250531_020d63N_081d57E_LST.csv daily_rainfall.csv
python code/make_figures.py daily_rainfall.csv
```
Random seeds are fixed in the scripts (`SEED = 2026` in `testbed_sim.py`). Python 3.x, numpy, pandas, matplotlib [add the versions you used]. Running the first three scripts overwrites the files in `results/`; `testbed_multi.py` and `testbed_area.py` take a few minutes. Figures are written to the current directory; without the rainfall CSV, Figure 4 has no rainfall panel.

## Data sources
- Central Water Commission, weekly reservoir storage bulletins (https://cwc.gov.in), entry MAHANADI, Chhattisgarh section, 21 bulletins from 01.02.2024 to 08.05.2025. The CSV is a transcription; the `series` column marks the current-year value or the previous-year column of the same bulletin. The original PDFs are not redistributed.
- NASA Langley Research Center, Prediction of Worldwide Energy Resources (POWER), https://power.larc.nasa.gov, MERRA-2 corrected precipitation (PRECTOTCORR): a reanalysis product, not a rain-gauge record.

## Limits
Simulation parameters are assumptions, not measurements. See Section 8.3 of the manuscript.

## Licence
Code: MIT (see `LICENSE`). Data files are derived from public sources; cite the sources above.

## Citation
[add after publication; a Zenodo DOI is created from a GitHub release]
