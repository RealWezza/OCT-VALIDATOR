import streamlit as st
import pandas as pd
import numpy as np
import re
import gspread
from google.oauth2.service_account import Credentials
from thefuzz import process, fuzz
from deep_translator import GoogleTranslator
from io import BytesIO
from PIL import Image
import os
import time
import base64
import string
import logging

# ----------------------------------------------------------------------------- 
# 1. CONFIGURATION
# -----------------------------------------------------------------------------
page_icon = "🍊"
if os.path.exists("logo.png"):
    page_icon = Image.open("logo.png")

st.set_page_config(
    page_title="OCT VALIDATOR", 
    layout="wide", 
    page_icon=page_icon,
    initial_sidebar_state="expanded"
)

# --- HELPER: IMAGE TO BASE64 ---
def get_img_as_base64(file):
    with open(file, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

logo_base64 = ""
if os.path.exists("logo.png"):
    logo_base64 = f"data:image/png;base64,{get_img_as_base64('logo.png')}"

# ----------------------------------------------------------------------------- 
# 2. CSS STYLING
# -----------------------------------------------------------------------------
st.markdown(f"""
    <style>
    header[data-testid="stHeader"] {{ display: none !important; }}
    .block-container {{ padding-top: 1rem !important; margin-top: 0rem !important; }}
    .stApp {{ background: linear-gradient(180deg, #1B1B7F 0%, #0d0d40 100%); color: #E6A537; }}
    /* ... باقي CSS كما هو ... */
    </style>
""", unsafe_allow_html=True)

st.markdown("""<ul class="circles"><li></li><li></li><li></li><li></li><li></li></ul>""", unsafe_allow_html=True)

# ----------------------------------------------------------------------------- 
# 3. LOGIC & DATA
# -----------------------------------------------------------------------------

def normalize_text(text):
    if not isinstance(text, str): return str(text)
    text = text.translate(str.maketrans('', '', string.punctuation))
    text = re.sub("[إأآا]", "ا", text)
    text = re.sub("ة", "ه", text)
    text = re.sub("ى", "ي", text)
    return text.strip().lower()

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_settings_data():
    logging.basicConfig(level=logging.INFO)
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    empty_res = (False, [], [], [], {}, pd.DataFrame(), [], [])

    try:
        info = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(info, scopes=scope)
        client = gspread.authorize(creds)
        logging.info("✅ Google Sheets client authorized successfully.")
    except Exception as e:
        logging.error(f"❌ Failed to authorize Google Sheets: {e}")
        return empty_res

    SETTINGS_ID = "15YTSsTS7xspjzyfRWI9vVdiKAMxY125sGinpF4NeTD0"
    try:
        sh = client.open_by_key(SETTINGS_ID)
        logging.info(f"✅ Opened Google Sheet: {SETTINGS_ID}")
        
        def get_data(sheet_names, skip_row=False):
            for name in sheet_names:
                try:
                    wks = sh.worksheet(name)
                    rows = wks.get_all_values()
                    if not rows: continue
                    data = rows[1:] if skip_row and len(rows) > 1 else rows
                    clean = [str(cell).strip().lower() for row in data for cell in row if str(cell).strip()]
                    if clean: return clean
                except Exception as e:
                    logging.warning(f"Sheet '{name}' not found or empty: {e}")
            return []

        generic_words = get_data(["Generic_Words", "Generic", "Generic Words"], False)
        ad_words = get_data(["Ad_Words", "Ads", "Ad Words"], False)
        forbidden_words = get_data(["Forbidden_Words", "Forbidden", "Forbidden Words"], True)
        safe_bacon = get_data(["Safe_Bacon", "Safe Bacon"], False)
        safe_curacao = get_data(["Safe_Curacao", "Safe Curacao"], False)

        term_dict = {}
        try:
            raw_term = sh.worksheet("Terminology").get_all_values()
            if len(raw_term) > 2:
                for r in raw_term[2:]:
                    if len(r) >= 2:
                        src, tgt = str(r[0]).strip(), str(r[1]).strip()
                        if src and tgt:
                            term_dict[src.lower()] = tgt
                            term_dict[tgt.lower()] = src
                            term_dict[normalize_text(src)] = tgt
                            term_dict[normalize_text(tgt)] = src
        except Exception as e:
            logging.warning(f"Terminology sheet not found: {e}")

        try:
            raw_lib = sh.worksheet("Description_Library").get_all_values()
            clean_lib = []
            if len(raw_lib) > 1:
                for r in raw_lib[1:]:
                    if len(r) >= 3: clean_lib.append([r[0].strip(), r[1].strip(), r[2].strip()])
                    elif len(r) == 2: clean_lib.append([r[0].strip(), r[1].strip(), ""])
            desc_lib_df = pd.DataFrame(clean_lib, columns=['Item Name', 'Eng Desc', 'Arb Desc'])
        except Exception as e:
            logging.warning(f"Description_Library sheet not found: {e}")
            desc_lib_df = pd.DataFrame(columns=['Item Name', 'Eng Desc', 'Arb Desc'])

        return True, generic_words, forbidden_words, ad_words, term_dict, desc_lib_df, safe_bacon, safe_curacao

    except Exception as e:
        logging.error(f"Failed to open or read Google Sheet: {e}")
        return empty_res

# --- SAFE GOOGLE TRANSLATE ---
def translate_word_safe(word, src_lang, tgt_lang):
    word_clean = word.strip()
    if not word_clean: return ""
    if src_lang == 'ar' and ("توفى" in word_clean or "توفي" in word_clean):
        return "Toffee"
    prompts = [f"Food: {word_clean}", word_clean] if src_lang != 'ar' else [f"Food item: {word_clean}", word_clean]
    for prompt in prompts:
        try:
            tr = GoogleTranslator(source='auto', target=tgt_lang).translate(prompt)
            tr_clean = re.sub(r'^(Food item|Food|طعام)[:\s]*', '', tr, flags=re.IGNORECASE).strip()
            if tr_clean and tr_clean.lower() != word_clean.lower(): return tr_clean
        except: continue
    return word_clean

def translate_text_loop_logic(text, term_dict, source_lang):
    if not text or pd.isna(text): return text, "None"
    text_str = str(text).strip()
    if not text_str: return "", "None"
    words = text_str.split() 
    translated_words = []
    src_code = 'en' if source_lang == 'English' else 'ar'
    tgt_code = 'ar' if source_lang == 'English' else 'en'
    term_keys_norm = list(term_dict.keys())
    for word in words:
        clean_word = word.strip(string.punctuation)
        norm_word = normalize_text(clean_word)
        found_translation = term_dict.get(norm_word)
        if not found_translation and len(norm_word) > 2:
            match = process.extractOne(norm_word, term_keys_norm, scorer=fuzz.ratio)
            if match and match[1] >= 85: found_translation = term_dict[match[0]]
        if not found_translation: found_translation = translate_word_safe(clean_word, src_code, tgt_code)
        translated_words.append(found_translation)
    rough_sentence = " ".join(translated_words)
    final_polished = rough_sentence
    try:
        polished = GoogleTranslator(source='auto', target=tgt_code).translate(rough_sentence)
        if len(polished) > len(rough_sentence) * 0.5: final_polished = polished
    except: pass
    final_polished = re.sub(r'\s+', ' ', final_polished).strip()
    return final_polished, "Loop+Fuzzy+Google"

def validate_item(row, sheet_type, generic_words, forbidden_words, ad_words, desc_lib_df, safe_bacon_list, safe_curacao_list):
    return True, row, "", "Valid", []

# ----------------------------------------------------------------------------- 
# 4. MAIN LAYOUT
# -----------------------------------------------------------------------------
def main():
    if 'processed_data' not in st.session_state: st.session_state.processed_data = None
    if 'first_load' not in st.session_state:
        placeholder = st.empty()
        img_tag = f'<img src="{logo_base64}" class="loading-logo-img"/>' if logo_base64 else '<div style="font-size:4em;">🍊</div>'
        placeholder.markdown(f"""<div id="loading-overlay"><div class="loading-content">{img_tag}<div class="loading-text">Loading...</div></div></div>""", unsafe_allow_html=True)
        conn_status, generic_words, forbidden_words, ad_words, term_dict, desc_lib_df, safe_bacon, safe_curacao = fetch_settings_data()
        time.sleep(1.0)
        placeholder.empty()
        st.session_state.first_load = True
        st.session_state.settings_data = (conn_status, generic_words, forbidden_words, ad_words, term_dict, desc_lib_df, safe_bacon, safe_curacao)
    else:
        conn_status, generic_words, forbidden_words, ad_words, term_dict, desc_lib_df, safe_bacon, safe_curacao = st.session_state.settings_data

    # ... باقي الكود كما هو من Main Layout, Sidebar, Bulk Processor, Manual Item Check ...
    # فقط استبدل fetch_settings_data() في الكود الأصلي بالنسخة المعدلة أعلاه

if __name__ == "__main__":
    main()
