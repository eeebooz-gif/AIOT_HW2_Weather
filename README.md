# HW2: Temperature Forecast Web App

This is a Streamlit web application that fetches weather forecasting data from the Central Weather Administration (CWA) API, stores it in an SQLite database, and displays it interactively using charts and tables.

## Development Log
- **Task 1: Setup & API Integration**: Successfully connected to the CWA `F-C0032-001` endpoint to fetch the 36-hour weather forecasts for 22 counties in Taiwan. Extracted Minimum Temperature (MinT) and Maximum Temperature (MaxT).
- **Task 2: Data Aggregation**: Grouped counties into major regions (北部地區, 中部地區, 南部地區, 東部地區, 離島地區) using Python dictionary mapping.
- **Task 3: Database Storage**: Designed an `init_db()` function using `sqlite3` to create the `TemperatureForecasts` table. Processed the raw JSON into Pandas DataFrames, averaged the temperatures by region and date, and loaded them into the SQLite database locally (`data.db`).
- **Task 4: Streamlit UI**: Created an interactive web app featuring:
  - A location-based dropdown menu to select a specific region.
  - A dynamic line chart (`st.line_chart`) to visualize the temperature trends.
  - A data table (`st.dataframe`) summarizing the actual minimum and maximum temperatures.
- **Security Check**: Configured `python-dotenv` to securely source the CWA API from the local environment variables. Ignored `.env` inside `.gitignore` before pushing to GitHub. Streamlit Cloud Secrets management will be used for deploying the live app.

## Running Locally
1. Clone the repository.
2. Install dependencies: `pip install -r requirements.txt`.
3. Create a `.env` file in the root directory and add your CWA API key: `CWA_API_KEY=your_api_key_here`.
4. Run the app: `streamlit run app.py`.

## Cloud Deployment
- Configured repository with `.gitignore`.
- App successfully deployed using Streamlit Community Cloud and configured with GitHub.
