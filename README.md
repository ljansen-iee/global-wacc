# Global WACC Calculator for Green PtX and Energy System Modelling

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Streamlit App](https://img.shields.io/badge/Streamlit-App-FF4B4B?logo=streamlit)](https://global-wacc.streamlit.app)

An interactive web application that calculates country-specific **Weighted Average Cost of Capital (WACC)** values for green Power-to-X (PtX) projects and energy system modelling. Country risk premiums and beta factors are sourced live from Aswath Damodaran's publicly available datasets.

---

## Features

- **Global coverage** — WACC computed for ~200 countries using country-specific risk premiums and corporate tax rates
- **Interactive parameter adjustment** — risk-free rate, beta, equity risk premium, capital structure, and inflation via sidebar sliders
- **Real & nominal WACC** — Fisher equation conversion for use in constant-price energy system models
- **Beta re-levering** — Hamada's equation applied per country using country-specific tax rates
- **Geographic visualisation** — choropleth world map of real WACC values
- **Sensitivity & scenario analysis** — tornado charts, heatmaps, and multi-scenario comparison
- **CSV export** — results with full methodology metadata embedded in the file header

---

## Methodology

WACC is calculated as:

$$WACC = k_E \cdot \alpha_e + k_D \cdot (1 - T) \cdot \alpha_d$$

where the cost of equity follows the Capital Asset Pricing Model (CAPM) extended by country risk (Damodaran):

$$k_E = r_f + \beta_L \cdot ERP + CRP$$

Default parameters (adjustable via the sidebar):

| Parameter | Default |
| --------- | ------- |
| Risk-free rate $r_f$ | 3.5 % |
| Unleveraged beta $\beta_U$ (Green & Renewable Energy) | 1.06 |
| Equity risk premium $ERP$ | 6.5 % |
| SWAP rate | 3.0 % |
| Debt spread | 2.0 % |
| Equity ratio $\alpha_e$ | 40 % |
| Inflation rate $\pi$ | 2.0 % |

Country-specific inputs (CRP and corporate tax rate $T$) are downloaded automatically from Damodaran's online databases.

---

## Installation

**Requirements:** Python ≥ 3.10

```bash
git clone https://github.com/ljansen-iee/global-wacc.git
cd global-wacc
pip install -r requirements.txt
```

---

## Usage

### Run the Streamlit app

```bash
streamlit run app.py
```

### Run the WACC calculation script directly

```bash
python scripts/country_waccs.py
```

Results are saved to `data/wacc_per_country_crp.csv`.

### Re-download source data

Set `SKIP_DOWNLOAD = False` in `scripts/country_waccs.py`, or set `RECREATE_COUNTRY_MAP = True` to regenerate the country name mapping after Damodaran updates his data.

---

## Data Sources

- Damodaran, A. (2026). *Country Default Spreads and Risk Premiums.* NYU Stern. [ctryprem.html](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/ctryprem.html)
- Damodaran, A. (2026). *Betas by Sector (US).* NYU Stern. [Betas.html](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/Betas.html)
- Damodaran, A. (2023). *Country Risk: Determinants, Measures and Implications.* [DOI 10.2139/ssrn.4509578](https://doi.org/10.2139/ssrn.4509578)
- Damodaran, A. (2023). *Equity Risk Premiums (ERP).* [DOI 10.2139/ssrn.4398884](https://doi.org/10.2139/ssrn.4398884)
- Brealey, R.A., Myers, S.C. & Allen, F. (2020). *Principles of Corporate Finance* (13th ed.). McGraw-Hill Education.
- Reul, J.; Mpinga, L.; Graul, H.; Häckner, B.; Fetköter, J.; Zink, C.; Nafula, M.; Kosgei, D.; Banda, S. (2025). *Renewable Ammonia: Kenya's Business Case.* H2Global Foundation. [H2Global library](https://h2-global.org/library/renewable-ammonia-kenyas-business-case/)

Full BibTeX references are available in [references.bib](references.bib).

---

## License

This project code is licensed under the [MIT License](LICENSE).
Results are licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

**Author:** Lukas Jansen, Fraunhofer IEE — [lukas.jansen@iee.fraunhofer.de](mailto:lukas.jansen@iee.fraunhofer.de)

