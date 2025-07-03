# st.markdown("*AWD Compliance Analysis Dashboard v9.3 - Fixed Google Sheets Authentication*")
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import io
import gspread
from google.oauth2.service_account import Credentials
import json
import base64
import datetime
import pytz
import time

# Note: Add st.set_page_config() at the very beginning of your main script file if needed
# st.set_page_config(page_title="AWD Compliance Analysis", page_icon="🌾", layout="wide")

st.title("🌾 AWD Compliance Analysis Dashboard")
st.markdown("---")

# Define week periods as per user specification
WEEK_PERIODS = [
    (1, "16 June", "22 June", "2025-06-16", "2025-06-22"),
    (2, "23 June", "29 June", "2025-06-23", "2025-06-29"),
    (3, "30 June", "6 July", "2025-06-30", "2025-07-06"),
    (4, "7 July", "13 July", "2025-07-07", "2025-07-13"),
    (5, "14 July", "20 July", "2025-07-14", "2025-07-20"),
    (6, "21 July", "27 July", "2025-07-21", "2025-07-27"),
    (7, "28 July", "3 August", "2025-07-28", "2025-08-03"),
    (8, "4 August", "10 August", "2025-08-04", "2025-08-10"),
    (9, "11 August", "17 August", "2025-08-11", "2025-08-17"),
    (10, "18 August", "24 August", "2025-08-18", "2025-08-24"),
    (11, "25 August", "31 August", "2025-08-25", "2025-08-31"),
    (12, "1 September", "7 September", "2025-09-01", "2025-09-07"),
    (13, "8 September", "14 September", "2025-09-08", "2025-09-14"),
    (14, "15 September", "21 September", "2025-09-15", "2025-09-21"),
    (15, "22 September", "28 September", "2025-09-22", "2025-09-28"),
    (16, "29 September", "5 October", "2025-09-29", "2025-10-05"),
    (17, "6 October", "12 October", "2025-10-06", "2025-10-12"),
    (18, "13 October", "15 October", "2025-10-13", "2025-10-15")
]

def get_credentials():
    """Get properly formatted credentials"""
    creds_dict = {
        "type": "service_account",
        "project_id": "elevated-apex-360403",
        "private_key_id": "f81bf9bb9d9e589180b639eae32d1c36f526a960",
        # Critical change - properly formatted private key with actual newlines
        "private_key": """-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDQPsw+ss5krgBu
wtNC/KUZ5qqRXNG8fjYFLf89VFVMhX1o6PlK39UXPPxzGuNwDcd15Q0h3z/n+/3B
YObQue9Rqq2CSU5PG4GsNbQgVdEHG9Soix+YWl2vbvWe30dU+3lrv3lq2iVAF2Ul
PiKmyAGMXe7qracqphh3qWKQPVizoO5MgpkrxRG6/ig7H9N9iu1h2N/fcLBVdOib
lrkeHdg7KnsaoCPZK6FhVckby4qBbjesL1Jh4BclzC7J21js+9w2xomRotVC2Rts
+2OCF65rj6edDgyxUCkweGxd0EtCfVEMqjjk4lERHUOPawXsB0rCicmJz2BpsPqk
genHFvBVAgMBAAECggEAK0VNN978G3f7b4hskQABx3DCcvuEOkRIccmVvnbiVYjs
Xur/9/KsKsy5kSpeZYd7cXAjiy0CMLBQEUlTFL5577CFJqwYSUBIMNIk6E4kpbM+
/DmSWlw2mNA32ef/wLUTTRQHhPAoqtlhozw2w4yOI85V6W4lbOt/7IdmC14v6vzu
a6xCAX5i/2wFSlwFJQE9IOfl8bjF5o5CBgsrwYcGI9/AeHPcMXQadpMdrYvjpepK
5ewOrElIWigS2zCnGnKyg54fdFfaCj4Xntpmyk+ooJyaRaYY0WZwTDmoQi9AlMiU
FENgtnU7tJRnBA+452Rf3Nd6d10vkBbCxz3CM5alsQKBgQD/oJZCzCNpmtZSfQCW
z/Nj4jJyc8uoViS0TPBlf1SyKll1ZOo8JBaFJxvXULVGm4346BFma19ufz8ozmui
7D61PL5haKoVLwdi8gDd8hcnQs3H+kbujhSj42/M9kaYDUW3KeFG1ZytqZ6FG6by
MzJDkZfqFCZxKerZUoSFyvUr0QKBgQDQjIaIZJivYYPA2Y7Z7S+5/1BGQoqQjT4j
EoDdMARNIJE/6Fu1oV27etKprDCHSWAdYAIk+UpU8JeUKdUFyeMc4pZB0kFsucFl
cj3JWjWu6y+wqW4vXL0OYBn12ZKH0uZwZRASbg68yofm51QJItIBjVhItW/0yPLl
03xpaBVRRQKBgQD6/lWrvr8iqQq5sc1LR2Hm+CmqYXJdlj+x3T3Jmu2xho2SDAVG
CfUmxpC6qJ9ldcU/2bWEB/eLClwcmBntveOQltUj1d3ysNui1pXtVxBO13QwX9kX
0OAJT37uE/6au6VxRCjTIVkW104zykPw2j4HRESSbTiVsp/KxRAkQnTakQKBgHqc
lCAunMJIH9FLV7xyweOl4wlb5+Gy2Px/zXm92FmMMzmSoBC6bcRjIuYU0XdIwZSj
tL8OPhCQX14B9jdwCfIameLa/hIxaC3/q6ntOrC7n49LHfgEmzaPc9Pidk8axNcB
5CAhytJedOZhzTuN2FCHTId6/Pa7CmvrGjNSuW3NAoGBAMTTcVApBUYxrdNmDBb0
pihcmVWvB/C5iARUyYNQqCbWClEIR6/Tj2TdUphCRxZ4w+oDflzYAJPX1q0vQKmv
uDEkUn9W8yacAdde8VmtkmGAYZSP/E5spwx8axMIDXZ5bvq7Zyj+nqh8U7uHZ5kC
bqNY3Ihy7lm0x+IZQYz+Tbf6
-----END PRIVATE KEY-----""",
        "client_email": "masterdata-950@elevated-apex-360403.iam.gserviceaccount.com",
        "client_id": "109484565593844446221",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/masterdata-950%40elevated-apex-360403.iam.gserviceaccount.com",
        "universe_domain": "googleapis.com"
    }
    return creds_dict

@st.cache_data(ttl=300)  # Cache for 5 minutes
def connect_to_google_sheets(sheet_url, worksheet_name=None):
    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request
        
        # Get credentials without duplicate token_uri
        creds_dict = {
            "type": "service_account",
            "project_id": "elevated-apex-360403",
            "private_key_id": "f81bf9bb9d9e589180b639eae32d1c36f526a960",
            "private_key": """-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDQPsw+ss5krgBu
wtNC/KUZ5qqRXNG8fjYFLf89VFVMhX1o6PlK39UXPPxzGuNwDcd15Q0h3z/n+/3B
YObQue9Rqq2CSU5PG4GsNbQgVdEHG9Soix+YWl2vbvWe30dU+3lrv3lq2iVAF2Ul
PiKmyAGMXe7qracqphh3qWKQPVizoO5MgpkrxRG6/ig7H9N9iu1h2N/fcLBVdOib
lrkeHdg7KnsaoCPZK6FhVckby4qBbjesL1Jh4BclzC7J21js+9w2xomRotVC2Rts
+2OCF65rj6edDgyxUCkweGxd0EtCfVEMqjjk4lERHUOPawXsB0rCicmJz2BpsPqk
genHFvBVAgMBAAECggEAK0VNN978G3f7b4hskQABx3DCcvuEOkRIccmVvnbiVYjs
Xur/9/KsKsy5kSpeZYd7cXAjiy0CMLBQEUlTFL5577CFJqwYSUBIMNIk6E4kpbM+
/DmSWlw2mNA32ef/wLUTTRQHhPAoqtlhozw2w4yOI85V6W4lbOt/7IdmC14v6vzu
a6xCAX5i/2wFSlwFJQE9IOfl8bjF5o5CBgsrwYcGI9/AeHPcMXQadpMdrYvjpepK
5ewOrElIWigS2zCnGnKyg54fdFfaCj4Xntpmyk+ooJyaRaYY0WZwTDmoQi9AlMiU
FENgtnU7tJRnBA+452Rf3Nd6d10vkBbCxz3CM5alsQKBgQD/oJZCzCNpmtZSfQCW
z/Nj4jJyc8uoViS0TPBlf1SyKll1ZOo8JBaFJxvXULVGm4346BFma19ufz8ozmui
7D61PL5haKoVLwdi8gDd8hcnQs3H+kbujhSj42/M9kaYDUW3KeFG1ZytqZ6FG6by
MzJDkZfqFCZxKerZUoSFyvUr0QKBgQDQjIaIZJivYYPA2Y7Z7S+5/1BGQoqQjT4j
EoDdMARNIJE/6Fu1oV27etKprDCHSWAdYAIk+UpU8JeUKdUFyeMc4pZB0kFsucFl
cj3JWjWu6y+wqW4vXL0OYBn12ZKH0uZwZRASbg68yofm51QJItIBjVhItW/0yPLl
03xpaBVRRQKBgQD6/lWrvr8iqQq5sc1LR2Hm+CmqYXJdlj+x3T3Jmu2xho2SDAVG
CfUmxpC6qJ9ldcU/2bWEB/eLClwcmBntveOQltUj1d3ysNui1pXtVxBO13QwX9kX
0OAJT37uE/6au6VxRCjTIVkW104zykPw2j4HRESSbTiVsp/KxRAkQnTakQKBgHqc
lCAunMJIH9FLV7xyweOl4wlb5+Gy2Px/zXm92FmMMzmSoBC6bcRjIuYU0XdIwZSj
tL8OPhCQX14B9jdwCfIameLa/hIxaC3/q6ntOrC7n49LHfgEmzaPc9Pidk8axNcB
5CAhytJedOZhzTuN2FCHTId6/Pa7CmvrGjNSuW3NAoGBAMTTcVApBUYxrdNmDBb0
pihcmVWvB/C5iARUyYNQqCbWClEIR6/Tj2TdUphCRxZ4w+oDflzYAJPX1q0vQKmv
uDEkUn9W8yacAdde8VmtkmGAYZSP/E5spwx8axMIDXZ5bvq7Zyj+nqh8U7uHZ5kC
bqNY3Ihy7lm0x+IZQYz+Tbf6
-----END PRIVATE KEY-----""",
            "client_email": "masterdata-950@elevated-apex-360403.iam.gserviceaccount.com",
            "client_id": "109484565593844446221",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/masterdata-950%40elevated-apex-360403.iam.gserviceaccount.com"
        }
        
        # Define required scopes
        SCOPES = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # Create credentials without duplicate token_uri
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=SCOPES
        )
        
        # Create authorized client
        client = gspread.Client(auth=credentials)
        client.session.timeout = 30
        
        # Extract sheet ID from URL
        if 'spreadsheets/d/' in sheet_url:
            sheet_id = sheet_url.split('/d/')[1].split('/')[0]
            sheet = client.open_by_key(sheet_id)
        else:
            sheet = client.open(sheet_url)
        
        # Get worksheet
        worksheet = sheet.worksheet(worksheet_name) if worksheet_name else sheet.get_worksheet(0)
        
        # Verify access
        try:
            worksheet.row_values(1)  # Test read access
            st.success("✅ Successfully connected to Google Sheets")
            return worksheet
        except Exception as e:
            st.error(f"❌ Worksheet access error: {str(e)}")
            st.info("Please ensure the sheet is shared with: masterdata-950@elevated-apex-360403.iam.gserviceaccount.com")
            return None
            
    except Exception as e:
        st.error(f"❌ Connection failed: {str(e)}")
        return None
        
def process_uploaded_file(uploaded_file, file_type):
    """Process uploaded files with error handling"""
    try:
        if uploaded_file.name.endswith('.xlsx'):
            if file_type == 'master':
                df = pd.read_excel(uploaded_file, sheet_name=0)
            else:
                df = pd.read_excel(uploaded_file)
        else:
            df = pd.read_csv(uploaded_file)
        
        st.success(f"✅ File loaded successfully: {len(df)} rows")
        return df
    except Exception as e:
        st.error(f"❌ Error loading file: {str(e)}")
        return None

def find_column(df, keywords, default_name=None):
    """Find column based on keywords with fallback"""
    cols = [col for col in df.columns if any(kw.lower() in col.lower() for kw in keywords)]
    if cols:
        return cols[0]
    return default_name

def is_positive_value(value):
    """Check if a value represents a positive/yes value (1, Y, Yes, etc.)"""
    if pd.isna(value):
        return False
    
    # Convert to string and clean
    str_val = str(value).strip().upper()
    
    # Check for empty or null-like values
    if str_val in ['', '0', '0.0', 'NO', 'N', 'FALSE', 'F', 'NAN', 'NA', 'NONE']:
        return False
    
    # Check for positive values
    if str_val in ['1', '1.0', 'YES', 'Y', 'TRUE', 'T', 'X']:
        return True
    
    return False

def clean_master_data(df):
    """Robust cleaning for master data - keeps all farms, treats blanks as 0"""
    try:
        df_clean = df.copy()
        
        # Find columns using flexible matching - updated based on actual sheet structure
        farm_id_col = find_column(df_clean, ['kharif 25 farm id'], 'Farm_ID')
        farmer_name_col = find_column(df_clean, ['Kharif 25 Farmer Name'], 'Farmer_Name')
        village_col = find_column(df_clean, ['Kharif 25 Village'], 'Village')
        acres_col = find_column(df_clean, ['kharif 25 - awd study - acres for incentive', 'kharif 25 acres on earth', 'acres', 'acreage', 'incentive acres'], 'Acres')
        
        # Exact column names as they appear in the actual sheet
        awd_study_col = 'Kharif 25 - AWD Study (Y/N)'
        group_a_col = 'Kharif 25 - AWD Study - Group A - Treatment (Y/N)'
        group_b_col = 'Kharif 25 - AWD Study - Group B -training only (Y/N)'
        group_c_col = 'Kharif 25 - AWD Study - Group C - Control (Y/N)'
        
        # Check if required columns exist and show what was found
        missing_cols = []
        found_cols = []
        
        for col_name, col_var in [
            ('AWD Study', awd_study_col),
            ('Group A', group_a_col), 
            ('Group B', group_b_col),
            ('Group C', group_c_col)
        ]:
            if col_var not in df_clean.columns:
                missing_cols.append(f"{col_name}: '{col_var}'")
            else:
                found_cols.append(f"{col_name}: ✅ Found")
        
        # Show found columns
        if found_cols:
            st.success("Found columns: " + ", ".join(found_cols))
        
        # Show what basic columns were found
        basic_cols_found = []
        if farm_id_col:
            basic_cols_found.append(f"Farm ID: '{farm_id_col}'")
        if farmer_name_col:
            basic_cols_found.append(f"Farmer Name: '{farmer_name_col}'")
        if village_col:
            basic_cols_found.append(f"Village: '{village_col}'")
        if acres_col:
            basic_cols_found.append(f"Acres: '{acres_col}'")
        
        if basic_cols_found:
            st.info("Basic columns found: " + ", ".join(basic_cols_found))
        
        if missing_cols:
            st.error(f"❌ Missing required columns:\n" + "\n".join(missing_cols))
            st.info("Available columns containing 'kharif' or 'awd': " + 
                   ", ".join([col for col in df_clean.columns if 'kharif' in col.lower() or 'awd' in col.lower()]))
            return None
        
        # Standardize basic columns
        df_clean['Farm_ID'] = df_clean[farm_id_col].astype(str).fillna("Unknown_Farm") if farm_id_col else "Unknown_Farm"
        df_clean['Farmer_Name'] = df_clean[farmer_name_col].astype(str).fillna("Unknown_Farmer") if farmer_name_col else "Unknown_Farmer"
        df_clean['Village'] = df_clean[village_col].astype(str).fillna("Unknown_Village") if village_col else "Unknown_Village"
        
        if acres_col:
            df_clean['Acres'] = pd.to_numeric(df_clean[acres_col], errors='coerce')
            df_clean['Acres'] = df_clean['Acres'].fillna(0).clip(lower=0)
        else:
            df_clean['Acres'] = 0
        
        # Create AWD study flag but DON'T filter - keep all farms
        df_clean['awd_study_flag'] = df_clean[awd_study_col].apply(is_positive_value)
        awd_participants = df_clean['awd_study_flag'].sum()
        total_farms = len(df_clean)
        
        st.info(f"📊 AWD Study Status: {awd_participants} participants, {total_farms - awd_participants} non-participants (keeping all {total_farms} farms)")
        
        # Assign groups with hierarchical logic - but keep unassigned farms
        def assign_group_hierarchical(row):
            # Check Group A first
            if is_positive_value(row[group_a_col]):
                return 'A'
            
            # If A is not 1, check Group B
            if is_positive_value(row[group_b_col]):
                return 'B'
            
            # If B is not 1, check Group C
            if is_positive_value(row[group_c_col]):
                return 'C'
            
            # If none are 1, assign as Unassigned instead of removing
            return 'Unassigned'
        
        df_clean['Group'] = df_clean.apply(assign_group_hierarchical, axis=1)
        
        # Show group distribution (no filtering)
        group_counts = df_clean['Group'].value_counts()
        st.success(f"✅ Group Distribution: {group_counts.to_dict()}")
        
        # Show sample of actual values in AWD columns for debugging
        st.info("📊 Sample AWD Column Values:")
        sample_data = df_clean[[farm_id_col, awd_study_col, group_a_col, group_b_col, group_c_col, 'Group']].head(10)
        st.dataframe(sample_data, use_container_width=True)
        
        # Return cleaned data with only necessary columns
        final_df = df_clean[['Farm_ID', 'Farmer_Name', 'Village', 'Acres', 'Group']].copy()
        
        # Only remove rows with completely missing Farm_ID
        final_df = final_df.dropna(subset=['Farm_ID'])
        final_df = final_df[final_df['Farm_ID'] != 'Unknown_Farm']
        
        st.success(f"✅ Final clean data: {len(final_df)} farms ready for analysis")
        
        return final_df
        
    except Exception as e:
        st.error(f"❌ Error cleaning master data: {str(e)}")
        st.exception(e)  # Show full traceback for debugging
        return None

def clean_water_data(df):
    """Robust cleaning for water data"""
    try:
        df_clean = df.copy()
        
        # Find columns
        date_col = find_column(df_clean, ['date'], 'Date')
        farm_id_col = find_column(df_clean, ['farm id', 'farm_id', 'farmid'], 'Farm_ID')
        pipe_id_col = find_column(df_clean, ['pipe id', 'pipe_id', 'pipe code'], 'Pipe_ID')
        water_col = find_column(df_clean, ['water level', 'water_level', 'depth'], 'Water_Level_mm')
        
        # Standardize column names
        df_clean['Date'] = pd.to_datetime(df_clean[date_col], errors='coerce') if date_col else None
        df_clean['Farm_ID'] = df_clean[farm_id_col].astype(str) if farm_id_col else "Unknown_Farm"
        df_clean['Pipe_ID'] = df_clean[pipe_id_col].astype(str) if pipe_id_col else "Unknown_Pipe"
        
        if water_col:
            df_clean['Water_Level_mm'] = pd.to_numeric(df_clean[water_col], errors='coerce')
        else:
            df_clean['Water_Level_mm'] = 0
        
        # Drop rows with missing essential data
        df_clean = df_clean.dropna(subset=['Date', 'Farm_ID', 'Water_Level_mm'])
        
        return df_clean[['Date', 'Farm_ID', 'Pipe_ID', 'Water_Level_mm']]
        
    except Exception as e:
        st.error(f"Error cleaning water data: {str(e)}")
        return None

def get_week_number(date, week_periods):
    """Get week number for a given date"""
    for week_num, start_str, end_str, start_iso, end_iso in week_periods:
        start_date = pd.to_datetime(start_iso)
        end_date = pd.to_datetime(end_iso)
        if start_date <= date <= end_date:
            return week_num
    return None

def analyze_pipe_compliance(pipe_data):
    """Analyze compliance for a single pipe within a week"""
    if len(pipe_data) < 2:
        if len(pipe_data) == 1:
            first_date = pipe_data.iloc[0]['Date'].strftime('%d/%m')
            first_value = int(pipe_data.iloc[0]['Water_Level_mm'])
            return {
                'status': '🔴 Pending',
                'details': f"{first_date} ({first_value}mm), —, —",
                'days_gap': 0,
                'compliant': False,
                'reason': 'Missing 2nd visit'
            }
        else:
            return {
                'status': '🔴 No Data',
                'details': "—, —, —",
                'days_gap': 0,
                'compliant': False,
                'reason': 'No visits'
            }
    
    # Sort by date
    pipe_data = pipe_data.sort_values('Date')
    first_measurement = pipe_data.iloc[0]
    second_measurement = pipe_data.iloc[-1]  # Use last measurement if more than 2
    
    first_date = first_measurement['Date'].strftime('%d/%m')
    first_value = int(first_measurement['Water_Level_mm'])
    second_date = second_measurement['Date'].strftime('%d/%m')
    second_value = int(second_measurement['Water_Level_mm'])
    
    days_gap = (second_measurement['Date'] - first_measurement['Date']).days
    
    # Check compliance criteria
    both_below_200 = first_value <= 200 and second_value <= 200
    one_below_100 = first_value <= 100 or second_value <= 100
    sufficient_gap = days_gap >= 3
    
    details = f"{first_date} ({first_value}mm), {second_date} ({second_value}mm), {days_gap} days"
    
    if both_below_200 and one_below_100 and sufficient_gap:
        return {
            'status': '🟢 OK',
            'details': details,
            'days_gap': days_gap,
            'compliant': True,
            'reason': 'Compliant'
        }
    elif not sufficient_gap:
        return {
            'status': '🔴 Error',
            'details': details,
            'days_gap': days_gap,
            'compliant': False,
            'reason': 'Gap too short'
        }
    elif not both_below_200:
        return {
            'status': '🔴 Error',
            'details': details,
            'days_gap': days_gap,
            'compliant': False,
            'reason': 'Reading >200mm'
        }
    elif not one_below_100:
        return {
            'status': '🔴 Error',
            'details': details,
            'days_gap': days_gap,
            'compliant': False,
            'reason': 'No reading ≤100mm'
        }
    else:
        return {
            'status': '🔴 Error',
            'details': details,
            'days_gap': days_gap,
            'compliant': False,
            'reason': 'Unknown error'
        }

def analyze_weekly_compliance(master_df, water_df, week_periods):
    """Analyze compliance week by week for all farmers"""
    results = []
    
    # Add week number to water data
    water_df['Week'] = water_df['Date'].apply(lambda x: get_week_number(x, week_periods))
    water_df = water_df.dropna(subset=['Week'])
    
    # Get all weeks that have data
    available_weeks = sorted(water_df['Week'].unique())
    
    for week_num in available_weeks:
        week_info = next((w for w in week_periods if w[0] == week_num), None)
        if not week_info:
            continue
            
        week_data = water_df[water_df['Week'] == week_num]
        
        # Group by farm
        for farm_id, farm_master_data in master_df.iterrows():
            farm_water_data = week_data[week_data['Farm_ID'] == farm_master_data['Farm_ID']]
            
            if farm_water_data.empty:
                # No data for this farm this week
                results.append({
                    'Week': int(week_num),
                    'Week_Period': f"{week_info[1]} - {week_info[2]}",
                    'Village': farm_master_data['Village'],
                    'Farm_ID': farm_master_data['Farm_ID'],
                    'Farmer_Name': farm_master_data['Farmer_Name'],
                    'Group': farm_master_data['Group'],
                    'Total_Acres': farm_master_data['Acres'],
                    'Pipes_Installed': 0,
                    'Pipes_Passing': 0,
                    'Non_Compliant_Pipes': '',
                    'Proportion_Passing': 0.0,
                    'Eligible_Acres': 0.0,
                    'Amount_to_Pay_Rs': 0.0,
                    'Pipe_Details': 'No data this week',
                    'Comments': 'No pipe data'
                })
                continue
            
            # Analyze each pipe for this farm in this week
            pipe_details = []
            pipes_installed = 0
            pipes_passing = 0
            non_compliant_pipes = []
            
            for pipe_id, pipe_data in farm_water_data.groupby('Pipe_ID'):
                pipes_installed += 1
                compliance_result = analyze_pipe_compliance(pipe_data)
                
                pipe_detail = f"{pipe_id}: {compliance_result['details']} {compliance_result['status']}"
                pipe_details.append(pipe_detail)
                
                if compliance_result['compliant']:
                    pipes_passing += 1
                else:
                    non_compliant_pipes.append(f"{pipe_id} ({compliance_result['reason']})")
            
            # Calculate metrics
            proportion_passing = pipes_passing / pipes_installed if pipes_installed > 0 else 0
            eligible_acres = proportion_passing * farm_master_data['Acres']
            
            # Payment only for Group A
            if farm_master_data['Group'] == 'A':
                amount_to_pay = eligible_acres * 300
            else:
                amount_to_pay = 0
            
            results.append({
                'Week': int(week_num),
                'Week_Period': f"{week_info[1]} - {week_info[2]}",
                'Village': farm_master_data['Village'],
                'Farm_ID': farm_master_data['Farm_ID'],
                'Farmer_Name': farm_master_data['Farmer_Name'],
                'Group': farm_master_data['Group'],
                'Total_Acres': farm_master_data['Acres'],
                'Pipes_Installed': pipes_installed,
                'Pipes_Passing': pipes_passing,
                'Non_Compliant_Pipes': '; '.join(non_compliant_pipes) if non_compliant_pipes else '',
                'Proportion_Passing': proportion_passing,
                'Eligible_Acres': round(eligible_acres, 2),
                'Amount_to_Pay_Rs': round(amount_to_pay, 0),
                'Pipe_Details': '\n'.join(pipe_details),
                'Comments': f"Week {week_num} analysis"
            })
    
    return pd.DataFrame(results)

# Main App Interface
st.sidebar.header("🔗 Google Sheets Configuration")

# Google Sheets Configuration
with st.sidebar.expander("🔑 Google Sheets Setup", expanded=True):
    st.markdown("""
    **Setup Instructions:**
    1. ✅ Service Account: `masterdata-950@elevated-apex-360403.iam.gserviceaccount.com`
    2. Share your Google Sheet with the email above (Editor access)
    3. Enter your Google Sheets URL below
    
    **For deployment issues:**
    - Use Streamlit Secrets for credentials (recommended)
    - Or set GOOGLE_CREDENTIALS environment variable
    """)
    
    sheet_url = st.text_input(
        "Google Sheets URL",
        value='https://docs.google.com/spreadsheets/d/10_bnGF7WBZ0J3aSvl8riufNbZjXAxB7wcnN3545fGzw/',
        help="Full URL of your Google Sheet"
    )
    
    worksheet_name = st.text_input(
        "Worksheet Name",
        value="Farm details",
        help="Name of the specific worksheet to read"
    )
    
    refresh_data = st.button("🔄 Refresh Master Data", help="Reload data from Google Sheets")

st.sidebar.header("📁 Water Data Upload")

# Water file upload (keeping this as file upload)
water_file = st.sidebar.file_uploader(
    "Upload Water Level Data", 
    type=['xlsx'],
    help="Upload Excel/CSV file with water measurements"
)

master_df = None
water_df = None

# Load master data from Google Sheets
if sheet_url and (refresh_data or 'master_df_cache' not in st.session_state):
    with st.spinner("Connecting to Google Sheets..."):
        raw_master = connect_to_google_sheets(sheet_url, worksheet_name)
    
    if raw_master is not None:
        master_df = clean_master_data(raw_master)
        if master_df is not None:
            st.session_state['master_df_cache'] = master_df
            st.sidebar.success(f"✅ Master data loaded: {len(master_df)} farms")
            st.sidebar.write(f"Groups distribution: {master_df['Group'].value_counts().to_dict()}")
        else:
            st.sidebar.error("❌ Failed to process master data")
elif 'master_df_cache' in st.session_state:
    master_df = st.session_state['master_df_cache']
    st.sidebar.success(f"✅ Using cached master data: {len(master_df)} farms")

# Load water data from file upload
if water_file:
    raw_water = process_uploaded_file(water_file, 'water')
    if raw_water is not None:
        water_df = clean_water_data(raw_water)
        if water_df is not None:
            st.sidebar.success(f"✅ Water data processed: {len(water_df)} measurements")

# Main Analysis
if master_df is not None and water_df is not None:
    
    # Show data preview
    st.header("📋 Data Preview")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Master Data (Google Sheets)")
        st.dataframe(master_df.head(), use_container_width=True)
        st.write(f"Total farms: {len(master_df)}")
        st.write("Group distribution:")
        st.write(master_df['Group'].value_counts())
    
    with col2:
        st.subheader("Water Level Data (Upload)")
        st.dataframe(water_df.head(), use_container_width=True)
        st.write(f"Total measurements: {len(water_df)}")
        
        # Show date range in data
        min_date = water_df['Date'].min()
        max_date = water_df['Date'].max()
        st.write(f"Date range: {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}")
    
    # Filters
    st.sidebar.header("🔍 Filters")
    
    # Date Range Filter
    st.sidebar.subheader("📅 Date Range Filter")
    
    # Get available date range from water data
    min_date = water_df['Date'].min().date()
    max_date = water_df['Date'].max().date()
    
    # Date range selector
    date_range = st.sidebar.date_input(
        "Select Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        help="Filter water level data by date range"
    )
    
    # Handle single date selection or range
    if len(date_range) == 2:
        start_date, end_date = date_range
        # Filter water data by date range
        water_df_filtered = water_df[
            (water_df['Date'].dt.date >= start_date) & 
            (water_df['Date'].dt.date <= end_date)
        ].copy()
        st.sidebar.success(f"📅 Date range: {start_date} to {end_date}")
        st.sidebar.info(f"Filtered measurements: {len(water_df_filtered)}")
    else:
        # Single date or no selection
        water_df_filtered = water_df.copy()
        st.sidebar.warning("Please select both start and end dates")
    
    # Week filter (based on filtered data)
    water_df_temp = water_df_filtered.copy()
    water_df_temp['Week'] = water_df_temp['Date'].apply(lambda x: get_week_number(x, WEEK_PERIODS))
    available_weeks = sorted([w for w in water_df_temp['Week'].unique() if pd.notna(w)])
    
    selected_weeks = st.sidebar.multiselect(
        "Select Weeks",
        available_weeks,
        default=available_weeks,
        format_func=lambda x: f"Week {int(x)}"
    )
    
    # Group filter
    available_groups = sorted(master_df['Group'].unique())
    selected_groups = st.sidebar.multiselect(
        "Select Groups",
        available_groups,
        default=available_groups
    )
    
    # Village filter
    available_villages = sorted(master_df['Village'].unique())
    selected_villages = st.sidebar.multiselect(
        "Select Villages",
        available_villages,
        default=available_villages
    )
    
    # Status filter
    status_options = ['All', 'Compliant Farms Only', 'Non-Compliant Farms Only', 'Group A Only']
    selected_status = st.sidebar.selectbox("Status Filter", status_options)
    
    # Generate Analysis
    if st.button("📊 Analyze Weekly Compliance", type="primary", use_container_width=True):
        with st.spinner("Analyzing weekly compliance..."):
            # Use the date-filtered water data for analysis
            results_df = analyze_weekly_compliance(master_df, water_df_filtered, WEEK_PERIODS)
        
        if results_df is not None and not results_df.empty:
            # Apply filters
            if selected_weeks:
                results_df = results_df[results_df['Week'].isin(selected_weeks)]
            if selected_groups:
                results_df = results_df[results_df['Group'].isin(selected_groups)]
            if selected_villages:
                results_df = results_df[results_df['Village'].isin(selected_villages)]
            
            # Apply status filter
            if selected_status == 'Compliant Farms Only':
                results_df = results_df[results_df['Proportion_Passing'] == 1.0]
            elif selected_status == 'Non-Compliant Farms Only':
                results_df = results_df[results_df['Proportion_Passing'] < 1.0]
            elif selected_status == 'Group A Only':
                results_df = results_df[results_df['Group'] == 'A']
            
            if results_df.empty:
                st.warning("No data matches the selected filters.")
            else:
                # Display results
                st.header("📊 Weekly Compliance Analysis")
                st.caption(f"Showing {len(results_df)} records")
                
                # Show applied date filter
                if len(date_range) == 2:
                    st.info(f"📅 Analysis based on data from {start_date} to {end_date}")
                
                # Summary metrics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    total_farmers = results_df['Farm_ID'].nunique()
                    st.metric("Total Farmers", total_farmers)
                
                with col2:
                    group_a_farmers = results_df[results_df['Group'] == 'A']['Farm_ID'].nunique()
                    st.metric("Group A Farmers", group_a_farmers)
                
                with col3:
                    total_payment = results_df[results_df['Group'] == 'A']['Amount_to_Pay_Rs'].sum()
                    st.metric("Total Payment (Group A)", f"₹{total_payment:,.0f}")
                
                with col4:
                    avg_compliance = results_df[results_df['Pipes_Installed'] > 0]['Proportion_Passing'].mean()
                    st.metric("Avg Compliance Rate", f"{avg_compliance:.1%}" if pd.notna(avg_compliance) else "N/A")
                
                # Display main table
                st.subheader("📋 Weekly Compliance Table")
                
                # Format display dataframe
                display_df = results_df.copy()
                display_df['Proportion_Passing'] = (display_df['Proportion_Passing'] * 100).round(1).astype(str) + '%'
                display_df['Amount_to_Pay_Rs'] = display_df['Amount_to_Pay_Rs'].apply(lambda x: f"₹{x:,.0f}" if x > 0 else "N/A")
                
                # Select columns for display
                display_columns = [
                    'Week', 'Week_Period', 'Village', 'Farm_ID', 'Farmer_Name', 'Group',
                    'Total_Acres', 'Pipes_Installed', 'Pipes_Passing', 'Non_Compliant_Pipes',
                    'Proportion_Passing', 'Eligible_Acres', 'Amount_to_Pay_Rs', 'Comments'
                ]
                
                st.dataframe(display_df[display_columns], use_container_width=True)
                
                # Pipe details section
                st.subheader("🔍 Detailed Pipe Analysis")
                for _, row in results_df.iterrows():
                    with st.expander(f"Week {row['Week']} - {row['Farm_ID']} ({row['Farmer_Name']})"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Village:** {row['Village']}")
                            st.write(f"**Group:** {row['Group']}")
                            st.write(f"**Total Acres:** {row['Total_Acres']}")
                            st.write(f"**Pipes Installed:** {row['Pipes_Installed']}")
                        with col2:
                            st.write(f"**Pipes Passing:** {row['Pipes_Passing']}")
                            st.write(f"**Proportion Passing:** {row['Proportion_Passing']:.1%}")
                            st.write(f"**Eligible Acres:** {row['Eligible_Acres']}")
                            st.write(f"**Payment:** ₹{row['Amount_to_Pay_Rs']:,.0f}")
                        
                        st.write("**Pipe Details:**")
                        if row['Non_Compliant_Pipes']:
                            st.error(f"**Non-Compliant Pipes:** {row['Non_Compliant_Pipes']}")
                        st.text(row['Pipe_Details'])
                
                # Download option
                csv = results_df.to_csv(index=False)
                st.download_button(
                    "📥 Download Complete Results",
                    csv,
                    f"awd_weekly_compliance_analysis_{start_date}_to_{end_date}.csv",
                    "text/csv",
                    use_container_width=True
                )
                
                # Payment summary for Group A
                group_a_data = results_df[results_df['Group'] == 'A']
                if not group_a_data.empty:
                    st.subheader("💰 Payment Summary (Group A Only)")
                    payment_summary = group_a_data.groupby(['Farm_ID', 'Farmer_Name', 'Village']).agg({
                        'Total_Acres': 'first',
                        'Eligible_Acres': 'sum',
                        'Amount_to_Pay_Rs': 'sum'
                    }).reset_index()
                    
                    payment_summary['Amount_to_Pay_Rs'] = payment_summary['Amount_to_Pay_Rs'].apply(lambda x: f"₹{x:,.0f}")
                    
                    st.dataframe(payment_summary, use_container_width=True)
                    
                    payment_csv = payment_summary.to_csv(index=False)
                    st.download_button(
                        "📥 Download Payment Summary",
                        payment_csv,
                        f"awd_payment_summary_{start_date}_to_{end_date}.csv",
                        "text/csv",
                        use_container_width=True
                    )
        else:
            st.warning("No results generated. Please check your data.")

else:
    st.info("👆 Please configure Google Sheets connection and upload water data to begin analysis.")

# Show troubleshooting guide
with st.expander("🔧 Troubleshooting Google Sheets Connection"):
    st.markdown("""
    **Common Issues and Solutions:**
    
    **1. "Invalid JWT Signature" Error:**
    - This usually means there's an issue with the service account credentials
    - **Solution for Streamlit Cloud:** Use Streamlit Secrets (see setup below)
    - **Solution for other deployments:** Set environment variables properly
    
    **2. Streamlit Secrets Setup (Recommended for deployment):**
    
    Create a `.streamlit/secrets.toml` file in your project:
    ```toml
    [gcp_service_account]
    type = "service_account"
    project_id = "your-project-id"
    private_key_id = "your-private-key-id"
    private_key = "-----BEGIN PRIVATE KEY-----\\nYOUR_PRIVATE_KEY\\n-----END PRIVATE KEY-----\\n"
    client_email = "your-service-account@your-project.iam.gserviceaccount.com"
    client_id = "your-client-id"
    auth_uri = "https://accounts.google.com/o/oauth2/auth"
    token_uri = "https://oauth2.googleapis.com/token"
    auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
    client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40your-project.iam.gserviceaccount.com"
    universe_domain = "googleapis.com"
    ```
    
    **3. Environment Variable Setup:**
    - Set `GOOGLE_CREDENTIALS` with the full JSON credentials
    - Or set `GOOGLE_CREDENTIALS_B64` with base64-encoded credentials
    
    **4. Sheet Sharing:**
    - Make sure your Google Sheet is shared with: `masterdata-950@elevated-apex-360403.iam.gserviceaccount.com`
    - Give "Editor" permissions
    
    **5. Generate New Service Account Key:**
    - Go to Google Cloud Console → IAM & Admin → Service Accounts
    - Find your service account and create a new key
    - Download the JSON file and update your credentials
    """)

# Show expected format
with st.expander("📋 Expected Data Format"):
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Master Data (Google Sheets) - Required columns:**")
        st.code("""
Required Columns (exact names):
- Kharif 25 Farm ID
- Kharif 25 Farmer Name  
- Kharif 25 Village
- Kharif 25 - AWD Study - acres for incentive
- Kharif 25 - AWD Study (Y/N)
- Kharif 25 - AWD Study - Group A - Treatment (Y/N)
- Kharif 25 - AWD Study - Group B -training only (Y/N)
- Kharif 25 - AWD Study - Group C - Control (Y/N)
        """)
    
    with col2:
        st.write("**Water Level Data (Upload):**")
        st.code("""
Required Columns:
- Date (YYYY-MM-DD format)
- Farm_ID (matches master data)
- Pipe_ID (unique pipe identifier)
- Water_Level_mm (numeric)
        """)

# Show week schedule
with st.expander("📅 Study Week Schedule"):
    week_schedule = pd.DataFrame(WEEK_PERIODS, columns=['Week', 'Start', 'End', 'Start_ISO', 'End_ISO'])
    st.dataframe(week_schedule[['Week', 'Start', 'End']], use_container_width=True)

# Show compliance criteria
with st.expander("📏 Compliance Criteria"):
    st.write("""
    **For a pipe to be compliant in a week:**
    1. **Two measurements required** within the week period
    2. **Both readings ≤ 200mm**
    3. **At least one reading ≤ 100mm**
    4. **At least 3 days gap** between measurements
    
    **Status Indicators:**
    - 🟢 **OK**: All criteria met
    - 🔴 **Pending**: Missing second measurement
    - 🔴 **Error**: Criteria not met (gap too short, readings too high, etc.)
    
    **Payment Calculation (Group A only):**
    - Eligible Acres = (Compliant Pipes / Total Pipes) × Total Acres
    - Payment = Eligible Acres × ₹300
    """)

st.markdown("---")
st.markdown("*AWD Compliance Analysis Dashboard v9.3 - Fixed Google Sheets Authentication*")
