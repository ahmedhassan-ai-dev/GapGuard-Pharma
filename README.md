# GapGuard Pharma

**Numerical Cold-Chain Investigation & Decision Support for Vaccines and Temperature-Sensitive Medicines**

An academic software product built for **MATH 301 – Numerical Computations** at **Pharos University in Alexandria**.

GapGuard Pharma transforms temperature logger CSV readings into product-by-product cold-chain investigations. It identifies missing observations, estimates them with numerical interpolation, detects possible out-of-range events, calculates exposure duration and intensity, and produces evidence reports. It is designed to support quality review, **not to decide whether a vaccine or medicine is safe to use**.

## Features

- **My Icebox:** Add multiple medicines or vaccines and their batch numbers to the same storage box.
- **Product policies:** Set temperature ranges, manufacturer information, official source links, and conditional exposure rules when supported by product documentation.
- **CSV import:** Preview files, map date/temperature columns, infer sampling cadence, and flag missing or invalid evidence.
- **Numerical recovery:** Estimate missing temperature readings with local interpolation, distinguishing estimates from observations.
- **Excursion investigation:** Calculate modeled threshold crossings, excursion start/end, total exposure time and degree-minutes.
- **Per-product analysis:** Analyze the same temperature timeline under each product's configured policy.
- **PDF evidence report:** Export the investigation results with product and policy references.
- **Bilingual interface:** Arabic (RTL) and English, built with React + TypeScript.

> **Evidence limitation:** The built-in reference catalog is not a verified inventory of Egyptian-registered brands or formulations. A temperature range or duration from one presentation must not be assumed valid for another. A configured allowance does not establish product safety or suitability for use; follow the current product insert and qualified quality procedures.

## Technology

| Layer | Technology |
|---|---|
| Frontend | React, TypeScript, Vite |
| Backend | Python, FastAPI |
| Analysis | NumPy, pandas, custom numerical methods |
| Reports | ReportLab (PDF) |
| Tests | pytest |

## Project structure

```text
GapGuard_Next/
├── backend/
│   ├── data/            # Synthetic example CSV data
│   ├── gapguard/        # Import, numerical, exposure and policy logic
│   ├── tests/
│   ├── main.py          # FastAPI application
│   └── requirements.txt
├── frontend/
│   ├── src/             # React UI and styles
│   └── package.json
├── .gitignore
└── README.md
```

## Run locally on Windows

Requirements: Python 3.10+, Node.js LTS and npm.

### 1. Backend

Open PowerShell in the `backend` folder:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
```

API docs: http://127.0.0.1:8000/docs

### 2. Frontend

Open a second PowerShell terminal in the `frontend` folder:

```powershell
npm.cmd install
npm.cmd run dev
```

Open the app at http://localhost:5173

## Demo

1. Open **My Icebox** and add one or more product profiles.
2. Select a sample scenario from **Import & Analyze** or upload a CSV file.
3. Confirm column mapping and run the analysis.
4. Review the separate investigation for each product, including duration and degree-minutes.
5. Export the evidence report.

Example files are available in `backend/data/`.

## Numerical foundation — MATH 301

**Interpolation:** Newton divided differences and Lagrange interpolation estimate missing readings inside short gaps.

$$
P_n(t)=\sum_{i=0}^{n} f[t_0,\ldots,t_i]\prod_{j=0}^{i-1}(t-t_j)
$$

**Root finding:** A threshold crossing solves the following equation. The implemented numerical toolkit includes Bisection, False Position, Secant, and Newton–Raphson; the excursion engine uses Bisection on piecewise-linear segments.

$$
P(t)-T_{\mathrm{limit}}=0
$$

**Exposure duration:**

$$
D=t_{\mathrm{return}}-t_{\mathrm{start}}
$$

**Numerical integration:** The area beyond a temperature limit provides an exposure-severity measure in °C·minutes.

$$
E_{\mathrm{high}}=\int \max(P(t)-T_{\mathrm{upper}},0)\,dt
$$

An interpolated curve and between-sample crossing time are **models, not direct measurements**. A gap can hide an excursion even when surrounding observations are within range.

## Sources

- [CDC Vaccine Storage and Handling](https://www.cdc.gov/vaccines/hcp/storage-handling/)
- [CDC Storage and Handling Toolkit](https://www.cdc.gov/vaccines/hcp/downloads/storage-handling-toolkit.pdf)
- Product-specific rules must be checked against the current manufacturer package insert and applicable local protocols.

## Academic context

**Project:** GapGuard Pharma  
**Course:** MATH 301 – Numerical Computations  
**Initiative:** MATH UNLEASHED — From Equations to Innovation  
**University:** Pharos University in Alexandria  
**Author:** Ahmed Hassan Mohamed Masoud

### Disclaimer

GapGuard Pharma is an **academic prototype** for cold-chain investigation. It is not a medical-device certification, automated vaccine-release system, potency test, or replacement for qualified pharmaceutical judgment.
