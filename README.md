# OCT VALIDATOR - Technical Documentation

## Overview
OCT VALIDATOR is a secure, web-based Python application designed to automate the validation and translation of restaurant menus (specifically for Talabat integration). It leverages the **Streamlit** framework for the interface and **Pandas** for high-performance data manipulation.

## Architecture
- **Frontend:** Streamlit (React-based wrapper).
- **Backend:** Python 3.9+.
- **Data Integration:** Google Sheets API (gspread) for real-time fetching of configuration (Forbidden words, Terminology).
- **Translation:** Hybrid engine using `thefuzz` (Fuzzy String Matching) for glossary lookups and `deep_translator` (Google Translate API) for fallback.

## Security Features
1. **Secrets Management:** - Sensitive API keys and Google Service Account credentials are NOT hardcoded. They are managed via `st.secrets` (environment variables), ensuring no credentials leak into the source code repository.
2. **Ephemeral Data:** - Uploaded files are processed in RAM (memory) and are not persistently stored on the server's disk. Once the browser session ends, the data is wiped.
3. **Authentication:** - Google API connectivity uses OAuth2 Service Account credentials with read-only access scopes limited to the specific Configuration Sheets defined in the code.

## Updates & Maintenance
- **Logic Updates:** The core business logic (validation rules) is modularized in `app.py`.
- **Data Updates:** The application fetches "Forbidden Words," "Terminology," etc., dynamically from the linked Google Sheets. Users do not need to update code to change validation rules; they simply update the Google Sheet.

## Installation & Deployment
1. **Repository:** Host on GitHub.
2. **Environment:** - Install dependencies: `pip install -r requirements.txt`
   - Configure `.streamlit/secrets.toml` with the GCP Service Account JSON.
3. **Run:** `streamlit run app.py`

## User Workflow
1. **Upload:** User uploads Excel/CSV.
2. **Validate:** System checks against specific business logic (Generic terms, Mismatches, Forbidden items).
3. **Translate:** System utilizes Terminology sheet (Exact + 95% Fuzzy Match) before falling back to Machine Translation.
4. **Export:** User downloads the cleaned Dataframe or the formatted "Bulk Sheet" for direct import.