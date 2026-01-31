import streamlit as st
import pandas as pd
import numpy as np
import re
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from thefuzz import process, fuzz
from deep_translator import GoogleTranslator
from io import BytesIO
from PIL import Image
import os
import time
import base64
import string
import unicodedata

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
    
    .circles {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; overflow: hidden; z-index: 0; pointer-events: none; }}
    .circles li {{ position: absolute; display: block; list-style: none; width: 20px; height: 20px; background: rgba(255, 255, 255, 0.05); animation: animate 25s linear infinite; bottom: -150px; border-radius: 50%; }}
    .circles li:nth-child(1) {{ left: 25%; width: 80px; height: 80px; animation-delay: 0s; }}
    .circles li:nth-child(2) {{ left: 10%; width: 20px; height: 20px; animation-delay: 2s; animation-duration: 12s; }}
    .circles li:nth-child(3) {{ left: 70%; width: 20px; height: 20px; animation-delay: 4s; }}
    .circles li:nth-child(4) {{ left: 40%; width: 60px; height: 60px; animation-delay: 0s; animation-duration: 18s; }}
    .circles li:nth-child(5) {{ left: 65%; width: 20px; height: 20px; animation-delay: 0s; }}
    @keyframes animate {{ 0% {{ transform: translateY(0) rotate(0deg); opacity: 1; }} 100% {{ transform: translateY(-1000px) rotate(720deg); opacity: 0; }} }}

    section[data-testid="stSidebar"] {{ background-color: #E6A537 !important; border-right: 3px solid #111111; width: 350px !important; min-width: 350px !important; z-index: 1; }}
    section[data-testid="stSidebar"] * {{ color: #111111 !important; }}
    
    div.stButton > button[kind="secondary"] {{ background-color: #FFFFFF !important; color: #1B1B7F !important; border: 2px solid #1B1B7F !important; border-radius: 8px; padding: 6px 15px; width: 100%; font-weight: bold; }}
    div.stButton > button[kind="secondary"]:hover {{ background-color: #f0f0f0 !important; }}
    
    [data-testid="stFileUploader"] section {{ background-color: #FFFFFF !important; border: 2px dashed #1B1B7F; border-radius: 10px; }}
    [data-testid="stFileUploader"] section > div, [data-testid="stFileUploader"] section span {{ color: #000000 !important; }}
    [data-testid="stFileUploader"] button {{ background-color: #E6A537 !important; color: #111111 !important; border: 1px solid #111; }}
    
    .manual-card, .right-tools-box {{ background: rgba(255, 255, 255, 0.05); padding: 20px; border-radius: 15px; border: 1px solid rgba(230, 165, 55, 0.3); margin-bottom: 20px; backdrop-filter: blur(5px); }}
    .manual-card h3, .manual-card label, .right-tools-box div {{ color: #E6A537 !important; }}
    
    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div {{ background-color: #FFFFFF !important; color: #111111 !important; border: 2px solid #1B1B7F !important; font-weight: bold; }}
    
    div.stButton > button[kind="primary"] {{ background-color: #E6A537 !important; color: #FFFFFF !important; font-weight: 900 !important; border: 2px solid #FFFFFF; border-radius: 8px; width: 100%; text-shadow: 1px 1px #111; }}
    div.stButton > button[kind="primary"]:hover {{ background-color: #111111 !important; color: #E6A537 !important; border-color: #E6A537; }}
    
    #loading-overlay {{ position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background-color: #1B1B7F; z-index: 9999999; display: flex; flex-direction: column; justify-content: center; align-items: center; }}
    #action-overlay {{ position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(27, 27, 127, 0.7); backdrop-filter: blur(8px); z-index: 9999999; display: flex; flex-direction: column; justify-content: center; align-items: center; }}
    .loading-content {{ text-align: center; display: flex; flex-direction: column; align-items: center; justify-content: center; }}
    .loading-text {{ color: #E6A537 !important; font-weight: 900; font-size: 1.8rem; margin-top: 15px; text-shadow: 2px 2px #000; text-align: center; font-family: sans-serif; }}
    .loading-logo-img {{ width: 140px; animation: pulse 1.5s infinite; }}
    .action-logo-spin {{ width: 140px; animation: spin 3s linear infinite; }}
    
    @keyframes pulse {{ 0% {{ opacity: 1; transform: scale(1); }} 50% {{ opacity: 0.8; transform: scale(1.1); }} 100% {{ opacity: 1; transform: scale(1); }} }}
    @keyframes spin {{ 100% {{ transform: rotate(360deg); }} }}

    .header-wrapper {{ display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; margin-bottom: 30px; width: 100%; z-index: 1; position: relative; }}
    .header-logo {{ width: 120px; height: auto; margin-bottom: 10px; }}
    .header-title {{ font-family: sans-serif; font-weight: 900; font-size: 3.5em; line-height: 1; text-shadow: 4px 4px 0px #111111; }}
    .title-oct {{ color: #E6A537; }}
    .title-val {{ color: #E6A537; }}
    footer {{ visibility: hidden; }}
    </style>
""", unsafe_allow_html=True)

st.markdown("""<ul class="circles"><li></li><li></li><li></li><li></li><li></li></ul>""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. LOGIC & DATA
# -----------------------------------------------------------------------------

def normalize_text(text):
    if not isinstance(text, str): return str(text)
    text = unicodedata.normalize('NFKC', text)
    text = text.lower()
    text = re.sub(r'[\u064B-\u065F\u0640]', '', text) 
    text = re.sub("[إأآا]", "ا", text)
    text = re.sub("ة", "ه", text)
    text = re.sub("ى", "ي", text)
    text = re.sub(r'[^\w\s\u0600-\u06FF]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def strip_text(text):
    if not isinstance(text, str): return str(text)
    norm = normalize_text(text)
    return re.sub(r'\s+', '', norm)

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_settings_data():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = None
    try: creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
    except:
        try: creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
        except: pass

    empty_res = (False, [], [], [], {}, {}, {}, pd.DataFrame(), [], [])
    if not creds: return empty_res

    client = gspread.authorize(creds)
    SETTINGS_ID = "15YTSsTS7xspjzyfRWI9vVdiKAMxY125sGinpF4NeTD0" 
    
    try:
        sh = client.open_by_key(SETTINGS_ID)
        
        def find_worksheet_case_insensitive(sheet_name):
            all_sheets = sh.worksheets()
            for ws in all_sheets:
                if ws.title.strip().lower() == sheet_name.strip().lower(): return ws
            return None

        def get_data(sheet_names_list, skip_row=False):
            wks = None
            for name in sheet_names_list:
                wks = find_worksheet_case_insensitive(name)
                if wks: break
            if not wks: return []
            rows = wks.get_all_values()
            if not rows: return []
            data = rows[1:] if skip_row and len(rows) > 1 else rows
            clean = [str(cell).strip().lower() for row in data for cell in row if str(cell).strip()]
            return clean

        generic_words = get_data(["Generic_Words", "Generic"], False)
        ad_words_raw = get_data(["Ad_Words", "Ads"], False)
        ad_words = set([normalize_text(w) for w in ad_words_raw])
        forbidden_words = get_data(["Forbidden_Words", "Forbidden"], True)
        safe_bacon = get_data(["Safe_Bacon", "Safe Bacon"], False) 
        safe_curacao = get_data(["Safe_Curacao", "Safe Curacao"], False)

        term_dict = {}
        stripped_term_dict = {}
        debug_table = []
        
        term_wks = find_worksheet_case_insensitive("Terminology")
        if term_wks:
            raw_term = term_wks.get_all_values()
            if len(raw_term) > 1:
                # Column A = English, Column B = Arabic
                for r in raw_term[1:]: 
                    if len(r) >= 2:
                        src, tgt = str(r[0]), str(r[1])
                        if src.strip() and tgt.strip():
                            n_src = normalize_text(src)
                            n_tgt = normalize_text(tgt)
                            s_src = strip_text(src)
                            s_tgt = strip_text(tgt)
                            
                            term_dict[n_src] = tgt.strip()
                            term_dict[n_tgt] = src.strip()
                            stripped_term_dict[s_src] = tgt.strip()
                            stripped_term_dict[s_tgt] = src.strip()
                            
                            debug_table.append({"En": src, "Ar": tgt})

        desc_lib_df = pd.DataFrame(columns=['Item Name', 'Eng Desc', 'Arb Desc'])
        lib_wks = find_worksheet_case_insensitive("Description_Library")
        if lib_wks:
            raw_lib = lib_wks.get_all_values()
            clean_lib = []
            if len(raw_lib) > 1:
                for r in raw_lib[1:]:
                    if len(r) >= 3: clean_lib.append([r[0].strip(), r[1].strip(), r[2].strip()])
                    elif len(r) == 2: clean_lib.append([r[0].strip(), r[1].strip(), ""])
            if clean_lib:
                desc_lib_df = pd.DataFrame(clean_lib, columns=['Item Name', 'Eng Desc', 'Arb Desc'])

        return True, debug_table, generic_words, forbidden_words, ad_words, term_dict, stripped_term_dict, desc_lib_df, safe_bacon, safe_curacao

    except Exception as e: 
        return False, [], [], [], {}, {}, {}, pd.DataFrame(), [], []

# --- TRANSLATION HELPER (THE FIX IS HERE) ---
def translate_word_safe(word, src_lang, tgt_lang):
    word_clean = word.strip()
    if not word_clean: return ""
    prompts = [f"Food: {word_clean}", word_clean]
    if src_lang == 'ar': prompts = [f"Food item: {word_clean}", word_clean]
    for prompt in prompts:
        try:
            tr = GoogleTranslator(source='auto', target=tgt_lang).translate(prompt)
            # CRITICAL FIX: AGGRESSIVE CLEANING OF "FOOD:" PREFIXES IN ARABIC & ENGLISH
            tr_clean = re.sub(r'^(Food item|Food|Dish|Item|طعام|الطعام|غذاء|الغذاء|الأكل|وجبة|صنف)[:\s\-\.]*', '', tr, flags=re.IGNORECASE).strip()
            return tr_clean
        except: continue
    return word_clean

# --- SEARCH LOGIC (Token-wise) ---
def search_token_wise_core(input_word, term_dict, stripped_term_dict, allow_google, source_lang):
    if not input_word: return "", ""
    
    norm_input = normalize_text(input_word)
    stripped = strip_text(input_word)
    
    # 1. Exact & Stripped
    if norm_input in term_dict: return term_dict[norm_input], "Terminology (Exact)"
    if stripped in stripped_term_dict: return stripped_term_dict[stripped], "Terminology (Stripped)"
    
    # 2. Singular/Plural
    if norm_input.endswith('s') and len(norm_input) > 3:
        sing = norm_input[:-1]
        if sing in term_dict: return term_dict[sing], "Terminology (Singular)"
    
    # 3. Token-wise Fuzzy
    best_match_val = None
    best_match_score = 0
    for key, val in term_dict.items():
        key_tokens = key.split()
        for token in key_tokens:
            score = fuzz.ratio(norm_input, token)
            if score >= 90: return val, "Terminology (Token Match)"
            if score > best_match_score:
                best_match_score = score
                best_match_val = val

    # 4. Fuzzy
    if best_match_score >= 85: return best_match_val, "Terminology (Fuzzy)"

    # 5. Google
    if allow_google:
        tgt = 'ar' if source_lang == 'English' else 'en'
        try:
            # Use the SAFE translate function to strip "Food:"
            res = translate_word_safe(input_word, source_lang, tgt)
            return res, "Google"
        except:
            return "Error", "Connection"
    else:
        return input_word, "Not Found"

# --- BULK TRANSLATION ---
def translate_text_with_priority(text, term_dict, stripped_term_dict, source_lang):
    if not text or pd.isna(text): return text, "None"
    text_str = str(text).strip()
    norm = normalize_text(text_str)
    
    # 1. Full Sentence Check
    if norm in term_dict: return term_dict[norm], "Terminology"
    if strip_text(text_str) in stripped_term_dict: return stripped_term_dict[strip_text(text_str)], "Terminology"
    
    # 2. Squeeze Algorithm
    all_keys = sorted(term_dict.keys(), key=len, reverse=True)
    placeholders = {}
    counter = 1000
    used_terminology = False
    
    processing_text = norm 
    
    for key in all_keys:
        if len(key) < 3: continue 
        if key in processing_text:
            token = f" __{counter}__ "
            placeholders[token.strip()] = term_dict[key]
            processing_text = processing_text.replace(key, token)
            counter += 1
            used_terminology = True
            
    chunks = processing_text.split()
    final_output_parts = []
    
    tgt_code = 'ar' if source_lang == 'English' else 'en'
    src_code = 'en' if source_lang == 'English' else 'ar'
    used_google = False
    
    for chunk in chunks:
        if re.match(r'^__\d+__$', chunk):
            if chunk in placeholders:
                final_output_parts.append(placeholders[chunk])
            else:
                final_output_parts.append(chunk)
        else:
            if len(chunk) < 2 and not chunk.isdigit(): continue
            try:
                # Use SAFE translate here too
                tr = translate_word_safe(chunk, src_code, tgt_code)
                final_output_parts.append(tr)
                used_google = True
            except:
                final_output_parts.append(chunk)
            
    final_text = " ".join(final_output_parts)
    final_text = re.sub(r'\s+', ' ', final_text).strip()
    
    return final_text, "Terminology + Google" if used_google else "Terminology"

# --- VALIDATION ---
def check_mismatch(name, desc):
    n = name.lower()
    d = desc.lower()
    conflicts = [
        (['chicken', 'poultry'], ['beef', 'meat', 'lamb', 'fish', 'seafood', 'prawn', 'shrimp']),
        (['beef', 'meat', 'lamb', 'steak'], ['chicken', 'poultry', 'fish', 'seafood', 'prawn', 'shrimp']),
        (['fish', 'seafood', 'prawn', 'shrimp', 'salmon', 'tuna'], ['chicken', 'poultry', 'beef', 'meat', 'lamb']),
        (['vegetable', 'veggie', 'vegan'], ['chicken', 'beef', 'meat', 'lamb', 'fish', 'bacon', 'prawn']),
        (['hot', 'warm', 'steamed', 'grilled'], ['iced', 'cold', 'frozen', 'chilled', 'frosty']),
        (['iced', 'cold', 'frozen', 'chilled'], ['hot', 'warm', 'steamed']),
        (['mocha', 'latte', 'coffee', 'espresso', 'cappuccino', 'frappe', 'macchiato'], 
         ['beef', 'chicken', 'meat', 'lamb', 'burger', 'steak', 'fish', 'prawn', 'rice', 'pasta', 'sandwich'])
    ]
    for set_a, set_b in conflicts:
        has_a_name = any(x in n for x in set_a)
        has_b_desc = any(x in d for x in set_b)
        if has_a_name and has_b_desc:
            if 'bacon' in d and ('beef' in d or 'turkey' in d): continue
            return True, f"Mismatch: Name implies '{set_a[0]}' but Desc implies '{set_b[0]}'"
    return False, ""

def validate_item(row, sheet_type, generic_words, forbidden_words, ad_words, desc_lib_df, safe_bacon_list, safe_curacao_list):
    item_name = str(row.get('Item Name', '')).strip()
    description = str(row.get('Description', '')).strip()
    desc_raw_lower = description.lower()
    name_norm = normalize_text(item_name)
    desc_norm = normalize_text(description)
    combined_text = (name_norm + " " + desc_norm).lower()
    
    default_safe_bacon = ['beef', 'turkey', 'veal', 'halal', 'chicken', 'lamb']
    default_safe_curacao = ['syrup', 'flavor', 'flavour', 'mix', 'mocktail', 'virgin']
    final_safe_bacon = list(set(safe_bacon_list + default_safe_bacon)) if safe_bacon_list else default_safe_bacon
    final_safe_curacao = list(set(safe_curacao_list + default_safe_curacao)) if safe_curacao_list else default_safe_curacao

    def get_suggestions(itm_name):
        if desc_lib_df.empty: return []
        match = process.extractOne(itm_name, desc_lib_df['Item Name'].astype(str).unique(), scorer=fuzz.token_sort_ratio)
        if match and match[1] >= 90:
            matches = desc_lib_df[desc_lib_df['Item Name'] == match[0]]
            if not matches.empty:
                return [f"🇬🇧 {r['Eng Desc']}\n\n🇸🇦 {r['Arb Desc']}" for _, r in matches.iterrows()]
        return []

    # 1. FORBIDDEN
    check_forbidden = forbidden_words + ['pig', 'ham', 'naughty', 'dirty', 'fucking']
    bacon_is_safe = False
    if 'bacon' in combined_text:
        if any(safe in combined_text for safe in final_safe_bacon): bacon_is_safe = True
    curacao_is_safe = False
    if 'curacao' in combined_text:
        if any(safe in combined_text for safe in final_safe_curacao): curacao_is_safe = True

    for word in check_forbidden:
        w_clean = normalize_text(word)
        if not w_clean: continue
        if w_clean in name_norm:
             if w_clean == 'bacon' and bacon_is_safe: continue
             if (w_clean == 'blue curacao' or w_clean == 'curacao') and curacao_is_safe: continue
             return False, row, f"Forbidden in Name: {word}", "Delete Item", []
        if w_clean in desc_norm:
             if w_clean == 'bacon' and bacon_is_safe: continue
             if (w_clean == 'blue curacao' or w_clean == 'curacao') and curacao_is_safe: continue
             return False, row, f"Forbidden in Desc: {word}", "Delete Desc & Replace", get_suggestions(item_name)

    # 2. CHOICES
    choice_separators = ['/', '\\', ' or ', ' OR ']
    has_separator = any(s in desc_raw_lower for s in choice_separators)
    choice_indicators = ['choice of', 'choice between', 'choose', 'your choice']
    has_indicator = any(i in desc_norm for i in choice_indicators)
    is_between_and = ('between' in desc_norm and 'and' in desc_norm)
    name_has_option_keyword = any(x in item_name.lower() for x in [' or ', '/', ' & '])
    set_score = fuzz.token_set_ratio(name_norm, desc_norm)
    is_valid_choice = (set_score >= 80) or (name_has_option_keyword and set_score >= 60)
    
    if (has_indicator or has_separator or is_between_and) and not is_valid_choice:
         if sheet_type == "Main Menu":
             if (has_indicator or is_between_and) and not has_separator:
                 return False, row, "Undefined Choice", "Delete Item", []
         else:
             return False, row, "Choices in SEP", "Delete Description", []

    # 3. MISMATCH & GENERIC
    is_mismatch, mis_msg = check_mismatch(name_norm, desc_norm)
    if is_mismatch:
        if sheet_type == "Main Menu": return False, row, mis_msg, "Delete Item", []
        else: return False, row, mis_msg, "Delete Desc & Replace", get_suggestions(item_name)

    for word in generic_words:
        w_clean = normalize_text(word)
        if w_clean and w_clean in combined_text:
            if sheet_type == "Main Menu": return False, row, f"Generic: {word}", "Delete Item", []
            else: return False, row, f"Generic: {word}", "Delete Desc & Replace", get_suggestions(item_name)

    # 4. VALUE ADDED
    name_tokens = set(name_norm.split())
    desc_tokens = set(desc_norm.split())
    extra_words = desc_tokens - name_tokens
    
    common_fillers = {'delicious', 'tasty', 'yummy', 'amazing', 'great', 'best', 'famous', 'signature', 'special', 
                      'fresh', 'hot', 'cold', 'served', 'with', 'dish', 'plate', 'platter', 'bowl', 'cup', 'glass', 'our'}
    junk_fillers = common_fillers - ad_words
    
    if extra_words:
        all_extras_are_junk = True
        for w in extra_words:
            if w not in junk_fillers:
                all_extras_are_junk = False
                break
        if all_extras_are_junk:
             return False, row, "No Value Added", "Delete Desc & Replace", get_suggestions(item_name)
    else:
        if fuzz.ratio(name_norm, desc_norm) > 90 and len(desc_norm) > 5:
             return False, row, "Identical to Name", "Delete Desc & Replace", get_suggestions(item_name)

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
        
        settings_res = fetch_settings_data()
        time.sleep(1.0)
        placeholder.empty()
        st.session_state.first_load = True
        st.session_state.settings_data = settings_res
    else:
        settings_res = st.session_state.settings_data

    if settings_res[0] == False:
        conn_status = False
        conn_msg = settings_res[1]
        debug_table, generic_words, forbidden_words, ad_words, term_dict, stripped_term_dict, desc_lib_df, safe_bacon, safe_curacao = [], [], [], set(), {}, {}, pd.DataFrame(), [], []
    else:
        conn_status = True
        conn_msg = "Connected"
        debug_table, generic_words, forbidden_words, ad_words, term_dict, stripped_term_dict, desc_lib_df, safe_bacon, safe_curacao = settings_res[1:]

    with st.sidebar:
        col_res, col_tit = st.columns([0.3, 0.7])
        with col_res:
            if st.button("Reset", key="reset_btn", type="secondary"):
                st.session_state.processed_data = None
                st.rerun()
        
        st.markdown("### ⚙️ Bulk Operations")
        if st.button("🔄 Update Data", key="update_btn", type="secondary"):
            st.cache_data.clear()
            st.rerun()
            
        sidebar_menu_type = st.radio("Sheet Type", ["Main Menu", "Sep Sheet"], key="bk_type")
        uploaded_file = st.file_uploader("Upload Menu", type=['xlsx', 'csv'])
        
        col_name_mapped = 'Item Name'
        col_desc_mapped = 'Description'
        selected_sheet = 0
        all_cols = []
        
        if uploaded_file:
            try:
                uploaded_file.seek(0)
                if uploaded_file.name.endswith(('.xlsx', '.xls')):
                    xl_file = pd.ExcelFile(uploaded_file)
                    sheet_names = xl_file.sheet_names
                    st.markdown("---")
                    selected_sheet = st.selectbox("📑 Select Sheet:", range(len(sheet_names)), format_func=lambda x: sheet_names[x])
                
                uploaded_file.seek(0)
                if uploaded_file.name.endswith('.csv'): 
                    df_preview = pd.read_csv(uploaded_file, nrows=5)
                else: 
                    df_preview = pd.read_excel(uploaded_file, sheet_name=selected_sheet, nrows=5)
                
                all_cols = df_preview.columns.tolist()
                st.markdown("---")
                st.markdown("**📂 Map Columns**")
                idx_n, idx_d = 0, 0
                for i, col in enumerate(all_cols):
                    c_lower = str(col).lower()
                    if 'item' in c_lower or 'name' in c_lower: idx_n = i
                    if 'desc' in c_lower: idx_d = i
                col_name_sel = st.selectbox("Item Name:", all_cols, index=idx_n)
                col_desc_sel = st.selectbox("Description:", all_cols, index=idx_d)
                col_name_mapped = col_name_sel
                col_desc_mapped = col_desc_sel
                st.markdown("---")
            except Exception as e: st.error(f"Error: {e}")

        action_mode = st.radio("Action", ["Check Errors Only", "Translate Only", "Check & Translate"])
        
        source_lang = "English"
        target_name_col = "Name (Arb)"
        target_desc_col = "Desc (Arb)"
        
        if "Translate" in action_mode:
            st.markdown("#### 🌐 Translation Settings")
            source_lang = st.radio("Source Language:", ["English", "Arabic"])
            st.caption("Select Target Columns (Overwrite):")
            
            opts = ["(Create New Column)"] + all_cols
            sel_target_name = st.selectbox("Target Name Col:", opts, index=0)
            sel_target_desc = st.selectbox("Target Desc Col:", opts, index=0)
            target_name_col = sel_target_name if sel_target_name != "(Create New Column)" else "Name (Translated)"
            target_desc_col = sel_target_desc if sel_target_desc != "(Create New Column)" else "Desc (Translated)"

        if st.button("Run Bulk Processor", type="primary"):
            if uploaded_file and conn_status:
                spin_html = f'<div class="loading-content"><img src="{logo_base64}" class="action-logo-spin"/><div class="loading-text">Processing...</div></div>' if logo_base64 else '🍊'
                spin_ph = st.empty()
                spin_ph.markdown(f'<div id="action-overlay">{spin_html}</div>', unsafe_allow_html=True)
                
                try:
                    uploaded_file.seek(0)
                    if uploaded_file.name.endswith('.csv'): 
                        df = pd.read_csv(uploaded_file)
                        all_sheets = { "Sheet1": df }
                        current_sheet_name = "Sheet1"
                    else: 
                        all_sheets = pd.read_excel(uploaded_file, sheet_name=None)
                        sheet_keys = list(all_sheets.keys())
                        current_sheet_name = sheet_keys[selected_sheet]
                        df = all_sheets[current_sheet_name]
                    
                    df.rename(columns={col_name_mapped: 'Item Name', col_desc_mapped: 'Description'}, inplace=True)
                    
                    if 'Item Name' not in df.columns: st.error("Error mapping columns.")
                    else:
                        result_df = df.copy()
                        
                        if "Check" in action_mode:
                            result_df['Status'] = 'Valid'; result_df['Error'] = ''; result_df['Action'] = ''
                            for idx, row in result_df.iterrows():
                                valid, mod_row, err, act, _ = validate_item(row, sidebar_menu_type, generic_words, forbidden_words, ad_words, desc_lib_df, safe_bacon, safe_curacao)
                                if not valid:
                                    result_df.at[idx, 'Status'] = 'Issue'
                                    result_df.at[idx, 'Error'] = err
                                    result_df.at[idx, 'Action'] = act

                        if "Translate" in action_mode:
                            if target_name_col not in result_df.columns: result_df[target_name_col] = ''
                            if target_desc_col not in result_df.columns: result_df[target_desc_col] = ''
                            result_df['Name Source'] = ''
                            result_df['Desc Source'] = ''
                            
                            for idx, row in result_df.iterrows():
                                t_name, src_n = translate_text_with_priority(row['Item Name'], term_dict, stripped_term_dict, source_lang)
                                t_desc, src_d = translate_text_with_priority(row['Description'], term_dict, stripped_term_dict, source_lang)
                                
                                result_df.at[idx, target_name_col] = t_name
                                result_df.at[idx, target_desc_col] = t_desc
                                result_df.at[idx, 'Name Source'] = src_n
                                result_df.at[idx, 'Desc Source'] = src_d
                        
                        display_df = result_df.copy()
                        display_df.rename(columns={'Item Name': col_name_mapped, 'Description': col_desc_mapped}, inplace=True)
                        all_sheets[current_sheet_name] = display_df
                        st.session_state.processed_data = display_df
                        st.session_state.all_sheets_data = all_sheets
                        st.success("Done!")
                finally:
                    spin_ph.empty() 

    if logo_base64: header_html = f"""<div class="header-wrapper"><img src="data:image/png;base64,{get_img_as_base64('logo.png')}" class="header-logo"/><div class="header-title"><span class="title-oct">OCT</span> <span class="title-val">VALIDATOR</span></div></div>"""
    else: header_html = """<div class="header-wrapper"><div style="font-size:4em;">🍊</div><div class="header-title">OCTVALIDATOR</div></div>"""
    st.markdown(header_html, unsafe_allow_html=True)

    col_main, col_right = st.columns([0.65, 0.35], gap="large")

    with col_main:
        st.markdown("<div class='manual-card'>", unsafe_allow_html=True)
        st.markdown("<h3>Manual Item Check</h3>", unsafe_allow_html=True)
        with st.form("manual_form"):
            manual_menu_type = st.radio("Select Type:", ["Main Menu", "Sep Sheet"], horizontal=True, key="man_type")
            st.markdown("---")
            man_name = st.text_input("Item Name", placeholder="e.g. Chicken Burger")
            man_desc = st.text_area("Description", placeholder="e.g. Delicious beef burger")
            submitted = st.form_submit_button("Validate Item", type="primary")
            if submitted:
                spin_html = f'<div class="loading-content"><img src="{logo_base64}" class="action-logo-spin"/><div class="loading-text">Checking...</div></div>'
                spin_ph = st.empty()
                spin_ph.markdown(f'<div id="action-overlay">{spin_html}</div>', unsafe_allow_html=True)
                time.sleep(0.5) 
                if not conn_status: st.error("Connection Error.")
                elif not man_name: st.warning("Enter item name.")
                else:
                    row = {'Item Name': man_name, 'Description': man_desc}
                    valid, mod_row, err, act, suggestions = validate_item(row, manual_menu_type, generic_words, forbidden_words, ad_words, desc_lib_df, safe_bacon, safe_curacao)
                    spin_ph.empty()
                    if valid and not err: st.markdown(f"<div class='success-box' style='color:#111; background:#e8f5e9; padding:10px; border-radius:5px;'>✅ <b>Item is Valid</b></div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div class='error-box' style='color:#c62828; background:#ffebee; padding:10px; border-radius:5px;'>❌ <b>{err}</b><br>Action: {act}</div>", unsafe_allow_html=True)
                        if act != "Delete Item" and suggestions:
                            st.markdown("<br><b style='color:#111;'>Library Suggestions:</b>", unsafe_allow_html=True)
                            for s in suggestions: st.code(s, language="text")
                        elif act != "Delete Item": st.warning("No suggestions found.")
                spin_ph.empty()
        st.markdown("</div>", unsafe_allow_html=True)

    with col_right:
        st.markdown('<div class="right-tools-box">', unsafe_allow_html=True)
        with st.expander("🔤 OCT-TERMO", expanded=True):
             st.markdown('<div style="color:#111;">', unsafe_allow_html=True)
             
             # GOOGLE KILLER SWITCH
             allow_google = st.checkbox("Allow Google Fallback?", value=True)
             
             termo_input = st.text_input("Search Term:", key="float_termo")
             if termo_input:
                 spin_html = f'<img src="{logo_base64}" class="action-logo-spin"/>' if logo_base64 else '🍊'
                 spin_ph = st.empty()
                 spin_ph.markdown(f'<div id="action-overlay">{spin_html}</div>', unsafe_allow_html=True)
                 time.sleep(0.5)
                 
                 src_lang_detect = "English"
                 if re.search(r'[\u0600-\u06FF]', termo_input): src_lang_detect = "Arabic"
                 
                 res, src = search_token_wise_core(termo_input, term_dict, stripped_term_dict, allow_google, src_lang_detect) 
                 
                 spin_ph.empty()
                 # CLEAN RESULT DISPLAY
                 st.markdown(f"<b style='color:#111; font-size:1.5em;'>{res}</b>", unsafe_allow_html=True)
                 st.caption(f"{src}")
                 
             st.markdown('</div>', unsafe_allow_html=True)

        # HIDDEN FOR ADMIN
        # with st.expander("🔌 OCT-DATA", expanded=False): ...
        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.processed_data is not None:
        st.markdown("---")
        st.subheader("📊 Bulk Results")
        def highlight_rows(row):
            if 'Status' in row and row['Status'] == 'Issue': return ['background-color: #ffe6e6; color: black'] * len(row)
            return ['color: black'] * len(row)
        edited_df = st.data_editor(st.session_state.processed_data.style.apply(highlight_rows, axis=1), num_rows="fixed", use_container_width=True)
        c1, c2, c3 = st.columns([1, 1, 1])
        with c2:
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                if 'all_sheets_data' in st.session_state:
                    sheets_dict = st.session_state.all_sheets_data
                    for s_name, s_df in sheets_dict.items():
                        clean_df = s_df.copy()
                        cols_to_remove = ['Status', 'Error', 'Action', 'Name Source', 'Desc Source']
                        clean_df = clean_df.drop(columns=[c for c in cols_to_remove if c in clean_df.columns])
                        clean_df.to_excel(writer, sheet_name=s_name, index=False)
                else:
                    clean_df = edited_df.data.copy() if hasattr(edited_df, "data") else edited_df.copy()
                    cols_to_remove = ['Status', 'Error', 'Action', 'Name Source', 'Desc Source']
                    clean_df = clean_df.drop(columns=[c for c in cols_to_remove if c in clean_df.columns])
                    clean_df.to_excel(writer, index=False)
            
            st.download_button("📥 Download Excel", data=output.getvalue(), file_name="Processed_Menu.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if __name__ == "__main__":
    main()
