import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

try:
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
    client = gspread.authorize(creds)
    sh = client.open_by_key("15YTSsTS7xspjzyfRWI9vVdiKAMxY125sGinpF4NeTD0")
    worksheet = sh.sheet1
    data = worksheet.get_all_values()
    st.success("✅ Connection successful!")
    st.write("First 5 rows:", data[:5])
except Exception as e:
    st.error(f"❌ Connection failed: {e}")
