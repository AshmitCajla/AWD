#         st.info("🔗 Please configure Google Sheets connection to load master data")

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import io
import gspread
from google.oauth2.service_account import Credentials
import json

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

@st.cache_data(ttl=300)  # Cache for 5 minutes
def connect_to_google_sheets(credentials_dict, sheet_url, worksheet_name=None):
    """Connect to Google Sheets and return DataFrame"""
    try:
        # Parse credentials
        if isinstance(credentials_dict, str):
            creds_dict = json.loads(credentials_dict)
        else:
            creds_dict = credentials_dict
        
        # Set up credentials and scope
        scope = ['https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive']
        
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        gc = gspread.authorize(credentials)
        
        # Open the spreadsheet
        if sheet_url.startswith('https://docs.google.com/spreadsheets/d/'):
            # Extract sheet ID from URL
            sheet_id = sheet_url.split('/d/')[1].split('/')[0]
            sheet = gc.open_by_key(sheet_id)
        else:
            # Assume it's a sheet name
            sheet = gc.open(sheet_url)
        
        # Get worksheet
        if worksheet_name:
            worksheet = sheet.worksheet(worksheet_name)
        else:
            worksheet = sheet.get_worksheet(0)  # First worksheet
        
        # Get all data
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        
        st.success(f"✅ Connected to Google Sheets: {len(df)} rows loaded")
        return df
        
    except Exception as e:
        st.error(f"❌ Error connecting to Google Sheets: {str(e)}")
        return None

def get_credentials_from_secrets():
    """Get Google Sheets credentials from Streamlit secrets"""
    try:
        # Get credentials from secrets
        google_secrets = st.secrets["gcp_service_account"]
        
        credentials_dict = {
            "type": google_secrets["type"],
            "project_id": google_secrets["project_id"],
            "private_key_id": google_secrets["private_key_id"],
            "private_key": google_secrets["private_key"],
            "client_email": google_secrets["client_email"],
            "client_id": google_secrets["client_id"],
            "auth_uri": google_secrets["auth_uri"],
            "token_uri": google_secrets["token_uri"],
            "auth_provider_x509_cert_url": google_secrets["auth_provider_x509_cert_url"],
            "client_x509_cert_url": google_secrets["client_x509_cert_url"],
            "universe_domain": google_secrets["universe_domain"]
        }
        
        return credentials_dict
        
    except KeyError as e:
        st.error(f"❌ Missing secret: {str(e)}")
        st.error("Please check your .streamlit/secrets.toml file configuration")
        return None
    except Exception as e:
        st.error(f"❌ Error loading secrets: {str(e)}")
        return None

def get_app_config_from_secrets():
    """Get app configuration from Streamlit secrets"""
    try:
        app_config = st.secrets["app_config"]
        return {
            "sheet_url": app_config["sheet_url"],
            "worksheet_name": app_config["worksheet_name"]
        }
    except KeyError:
        # Return defaults if not in secrets
        return {
            "sheet_url": "",
            "worksheet_name": "Farm details"
        }
    except Exception as e:
        st.error(f"❌ Error loading app config: {str(e)}")
        return {
            "sheet_url": "",
            "worksheet_name": "Farm details"
        }

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
    
    # Check for empty or null-like values - UPDATED: Empty cells = 0
    if str_val in ['', '0', '0.0', 'NO', 'N', 'FALSE', 'F', 'NAN', 'NA', 'NONE']:
        return False
    
    # Check for positive values
    if str_val in ['1', '1.0', 'YES', 'Y', 'TRUE', 'T', 'X']:
        return True
    
    return False

def clean_master_data(df):
    """UPDATED: Robust cleaning for master data with new 6-group logic and filtering"""
    try:
        df_clean = df.copy()
        
        # Find basic columns using flexible matching
        farm_id_col = find_column(df_clean, ['kharif 25 farm id'], 'Farm_ID')
        farmer_name_col = find_column(df_clean, ['Kharif 25 Farmer Name'], 'Farmer_Name')
        village_col = find_column(df_clean, ['Kharif 25 Village'], 'Village')
        
        # Use the specific incentive acres column as requested
        incentive_acres_col = 'Kharif 25 - AWD Study - acres for incentive'
        
        # UPDATED: New column structure for 6-group logic
        awd_study_col = 'Kharif 25 - AWD Study (Y/N)'
        
        # Group A columns
        group_a_col = 'Kharif 25 - AWD Study - Group A - Treatment (Y/N)'
        group_a_complied_col = 'Kharif 25 - AWD Study - Group A - Treatment - complied (Y/N)'
        group_a_non_complied_col = 'Kharif 25 - AWD Study - Group A - Treatment - Non-complied (Y/N)'
        
        # Group B columns
        group_b_col = 'Kharif 25 - AWD Study - Group B -training only (Y/N)'
        group_b_complied_col = 'Kharif 25 - AWD Study - Group B - Complied (Y/N)'
        group_b_non_complied_col = 'Kharif 25 - AWD Study - Group B - Non-complied (Y/N)'
        
        # Group C columns
        group_c_col = 'Kharif 25 - AWD Study - Group C - Control (Y/N)'
        group_c_complied_col = 'Kharif 25 - AWD Study - Group C - Complied (Y/N)'
        group_c_non_complied_col = 'Kharif 25 - AWD Study - Group C - non-complied (Y/N)'
        
        # Check if required columns exist and show what was found
        missing_cols = []
        found_cols = []
        
        all_required_cols = [
            ('AWD Study', awd_study_col),
            ('Group A', group_a_col),
            ('Group A Complied', group_a_complied_col),
            ('Group A Non-Complied', group_a_non_complied_col),
            ('Group B', group_b_col),
            ('Group B Complied', group_b_complied_col),
            ('Group B Non-Complied', group_b_non_complied_col),
            ('Group C', group_c_col),
            ('Group C Complied', group_c_complied_col),
            ('Group C Non-Complied', group_c_non_complied_col),
            ('Incentive Acres', incentive_acres_col)
        ]
        
        for col_name, col_var in all_required_cols:
            if col_var not in df_clean.columns:
                missing_cols.append(f"{col_name}: '{col_var}'")
            else:
                found_cols.append(f"{col_name}: ✅ Found")
        
        if missing_cols:
            st.error(f"❌ Missing required columns:\n" + "\n".join(missing_cols))
            st.info("Available columns containing 'kharif' or 'awd': " + 
                   ", ".join([col for col in df_clean.columns if 'kharif' in col.lower() or 'awd' in col.lower()]))
            return None
        
        # Standardize basic columns
        df_clean['Farm_ID'] = df_clean[farm_id_col].astype(str).fillna("Unknown_Farm") if farm_id_col else "Unknown_Farm"
        df_clean['Farmer_Name'] = df_clean[farmer_name_col].astype(str).fillna("Unknown_Farmer") if farmer_name_col else "Unknown_Farmer"
        df_clean['Village'] = df_clean[village_col].astype(str).fillna("Unknown_Village") if village_col else "Unknown_Village"
        
        # Handle incentive acres column specifically
        if incentive_acres_col in df_clean.columns:
            df_clean['Incentive_Acres'] = pd.to_numeric(df_clean[incentive_acres_col], errors='coerce').fillna(0).clip(lower=0)
        else:
            df_clean['Incentive_Acres'] = 0
            st.warning(f"⚠️ Incentive acres column not found, using 0 for all farms")
        
        # STEP 1: Filter by AWD Study participation
        df_clean['awd_study_flag'] = df_clean[awd_study_col].apply(is_positive_value)
        
        # FILTER OUT farms where AWD Study = 0
        initial_count = len(df_clean)
        df_clean = df_clean[df_clean['awd_study_flag'] == True].copy()
        filtered_count = len(df_clean)
        
        if df_clean.empty:
            st.warning("⚠️ No AWD study participants found after filtering")
            return None
        
        # STEP 2: Assign groups with NEW 6-group logic
        def assign_group_with_compliance(row):
            # Check Group A first
            if is_positive_value(row[group_a_col]):
                # Check compliance sub-groups for A
                if is_positive_value(row[group_a_complied_col]):
                    return 'A Complied'
                elif is_positive_value(row[group_a_non_complied_col]):
                    return 'A Non Complied'
                else:
                    return 'A Unassigned'  # Group A but no compliance status
            
            # Check Group B 
            elif is_positive_value(row[group_b_col]):
                # Check compliance sub-groups for B
                if is_positive_value(row[group_b_complied_col]):
                    return 'B Complied'
                elif is_positive_value(row[group_b_non_complied_col]):
                    return 'B Non Complied'
                else:
                    return 'B Unassigned'  # Group B but no compliance status
            
            # Check Group C
            elif is_positive_value(row[group_c_col]):
                # Check compliance sub-groups for C
                if is_positive_value(row[group_c_complied_col]):
                    return 'C Complied'
                elif is_positive_value(row[group_c_non_complied_col]):
                    return 'C Non Complied'
                else:
                    return 'C Unassigned'  # Group C but no compliance status
            
            # If none of the main groups are 1
            else:
                return 'No Group Assigned'
        
        df_clean['Group'] = df_clean.apply(assign_group_with_compliance, axis=1)
        
        # STEP 3: FILTER OUT unassigned groups as requested
        before_filter = len(df_clean)
        df_clean = df_clean[~df_clean['Group'].isin(['A Unassigned', 'B Unassigned', 'C Unassigned', 'No Group Assigned'])].copy()
        after_filter = len(df_clean)
        
        st.info(f"📊 Removed {before_filter - after_filter} farms with unassigned groups")
        
        if df_clean.empty:
            st.warning("⚠️ No farms remaining after removing unassigned groups")
            return None
        
        # STEP 4: Payment eligibility and incentive calculation
        # Only "A Complied" group is eligible for payments
        df_clean['Payment_Eligible'] = df_clean['Group'] == 'A Complied'
        
        # STEP 5: Add "Incentive to Give" column as requested
        # 0 for A non complied, A unassigned, B (all) and C (all)
        # Only A Complied gets actual incentive calculation
        def calculate_incentive_to_give(row):
            if row['Group'] == 'A Complied':
                return 1  # Will be multiplied by compliance proportion later
            else:
                return 0  # All others get 0
        
        df_clean['Incentive_To_Give'] = df_clean.apply(calculate_incentive_to_give, axis=1)
        
        # Show group distribution and payment eligibility
        group_counts = df_clean['Group'].value_counts()
        payment_eligible_count = df_clean['Payment_Eligible'].sum()
        
        st.success(f"✅ Final Group Distribution: {group_counts.to_dict()}")
        st.success(f"✅ Payment Eligible Farms (A Complied): {payment_eligible_count} farms")
        
        # Return cleaned data with necessary columns
        final_df = df_clean[['Farm_ID', 'Farmer_Name', 'Village', 'Incentive_Acres', 'Group', 'Payment_Eligible', 'Incentive_To_Give']].copy()
        
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
    """UPDATED: Analyze compliance for a single pipe within a week with clearer criteria checking"""
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
    
    # UPDATED: Clear compliance criteria as specified
    # 1. BOTH measurements ≤ 200mm
    both_below_200 = first_value <= 200 and second_value <= 200
    
    # 2. At least one measurement ≤ 100mm
    one_below_100 = first_value <= 100 or second_value <= 100
    
    # 3. At least 3 days gap between measurements
    sufficient_gap = days_gap >= 3
    
    details = f"{first_date} ({first_value}mm), {second_date} ({second_value}mm), {days_gap} days"
    
    # Check all criteria
    if both_below_200 and one_below_100 and sufficient_gap:
        return {
            'status': '🟢 PASS',
            'details': details,
            'days_gap': days_gap,
            'compliant': True,
            'reason': 'All criteria met'
        }
    else:
        # Determine specific failure reason
        failed_criteria = []
        if not both_below_200:
            failed_criteria.append('Both readings must be ≤200mm')
        if not one_below_100:
            failed_criteria.append('At least one reading must be ≤100mm')
        if not sufficient_gap:
            failed_criteria.append('Gap must be ≥3 days')
        
        return {
            'status': '🔴 FAIL',
            'details': details,
            'days_gap': days_gap,
            'compliant': False,
            'reason': '; '.join(failed_criteria)
        }

def create_pipe_readings_table(master_df, water_df, start_date, end_date):
    """Create detailed pipe readings table for the selected date range"""
    try:
        results = []
        
        # For each farm in master data
        for _, farm_data in master_df.iterrows():
            farm_id = farm_data['Farm_ID']
            
            # Get all water data for this farm in the date range
            farm_water_data = water_df[water_df['Farm_ID'] == farm_id].copy()
            
            if farm_water_data.empty:
                # No data for this farm
                pipe_columns = {f'Pipe_{i}': 'No data' for i in range(1, 6)}
                results.append({
                    'Date_Range': f"{start_date} to {end_date}",
                    'Village': farm_data['Village'],
                    'Farm_ID': farm_id,
                    'Farmer_Name': farm_data['Farmer_Name'],
                    'Group': farm_data['Group'],
                    **pipe_columns,
                    'Comments': 'No pipe data available'
                })
                continue
            
            # Group by pipe ID
            pipes_data = {}
            for pipe_id, pipe_readings in farm_water_data.groupby('Pipe_ID'):
                # Sort by date
                pipe_readings = pipe_readings.sort_values('Date')
                
                # Format readings as (date, reading)
                readings_list = []
                for _, reading in pipe_readings.iterrows():
                    date_str = reading['Date'].strftime('%d/%m')
                    reading_val = int(reading['Water_Level_mm'])
                    readings_list.append(f"({date_str}, {reading_val}mm)")
                
                pipes_data[pipe_id] = {
                    'readings_text': f"{pipe_id}: " + ", ".join(readings_list),
                    'readings_data': pipe_readings
                }
            
            # Determine which pipes are non-compliant
            non_compliant_pipes = []
            for pipe_id, pipe_info in pipes_data.items():
                compliance_result = analyze_pipe_compliance(pipe_info['readings_data'])
                if not compliance_result['compliant']:
                    non_compliant_pipes.append(pipe_id)
            
            # Create pipe columns (up to 5 pipes)
            pipe_columns = {}
            pipe_ids = list(pipes_data.keys())
            
            for i in range(1, 6):  # Pipe 1 to Pipe 5
                if i-1 < len(pipe_ids):
                    pipe_id = pipe_ids[i-1]
                    pipe_columns[f'Pipe_{i}'] = pipes_data[pipe_id]['readings_text']
                else:
                    pipe_columns[f'Pipe_{i}'] = 'Not installed'
            
            # Create comments about non-compliant pipes
            if non_compliant_pipes:
                # Map pipe IDs to pipe numbers for comment
                pipe_numbers = []
                for pipe_id in non_compliant_pipes:
                    if pipe_id in pipe_ids:
                        pipe_num = pipe_ids.index(pipe_id) + 1
                        pipe_numbers.append(str(pipe_num))
                
                if pipe_numbers:
                    comments = f"Pipe {','.join(pipe_numbers)} did not follow compliance"
                else:
                    comments = "Some pipes did not follow compliance"
            else:
                if pipes_data:
                    comments = "All pipes compliant"
                else:
                    comments = "No pipe data"
            
            results.append({
                'Date_Range': f"{start_date} to {end_date}",
                'Village': farm_data['Village'],
                'Farm_ID': farm_id,
                'Farmer_Name': farm_data['Farmer_Name'],
                'Group': farm_data['Group'],
                **pipe_columns,
                'Comments': comments
            })
        
        return pd.DataFrame(results)
        
    except Exception as e:
        st.error(f"Error creating pipe readings table: {str(e)}")
        return None

def analyze_weekly_compliance(master_df, water_df, week_periods):
    """UPDATED: Analyze compliance week by week for all farmers with enhanced output"""
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
                    'Payment_Eligible': farm_master_data['Payment_Eligible'],
                    'Incentive_To_Give': farm_master_data['Incentive_To_Give'],
                    'Total_Incentive_Acres': farm_master_data['Incentive_Acres'],
                    'All_Pipe_IDs': 'No data',
                    'Pipes_Installed': 0,
                    'Pipes_Passing': 0,
                    'Non_Compliant_Pipe_IDs': '',
                    'Proportion_Passing': 0.0,
                    'Eligible_Acres': 0.0,
                    'Amount_to_Pay_Rs': 0.0,
                    'Final_Incentive_Amount': 0.0,
                    'Pipe_Details': 'No data this week',
                    'Comments': 'No pipe data'
                })
                continue
            
            # UPDATED: Analyze each pipe for this farm in this week with detailed tracking
            pipe_details = []
            pipes_installed = 0
            pipes_passing = 0
            non_compliant_pipe_ids = []
            all_pipe_ids = []
            
            for pipe_id, pipe_data in farm_water_data.groupby('Pipe_ID'):
                pipes_installed += 1
                all_pipe_ids.append(pipe_id)
                compliance_result = analyze_pipe_compliance(pipe_data)
                
                pipe_detail = f"{pipe_id}: {compliance_result['details']} {compliance_result['status']}"
                pipe_details.append(pipe_detail)
                
                if compliance_result['compliant']:
                    pipes_passing += 1
                else:
                    non_compliant_pipe_ids.append(pipe_id)
            
            # Calculate metrics
            proportion_passing = pipes_passing / pipes_installed if pipes_installed > 0 else 0
            eligible_acres = proportion_passing * farm_master_data['Incentive_Acres']
            
            # UPDATED: Payment calculation based on Payment_Eligible status
            if farm_master_data['Payment_Eligible']:
                amount_to_pay = eligible_acres * 300
            else:
                amount_to_pay = 0
            
            # UPDATED: Final incentive amount based on Incentive_To_Give flag
            final_incentive = farm_master_data['Incentive_To_Give'] * amount_to_pay
            
            results.append({
                'Week': int(week_num),
                'Week_Period': f"{week_info[1]} - {week_info[2]}",
                'Village': farm_master_data['Village'],
                'Farm_ID': farm_master_data['Farm_ID'],
                'Farmer_Name': farm_master_data['Farmer_Name'],
                'Group': farm_master_data['Group'],
                'Payment_Eligible': farm_master_data['Payment_Eligible'],
                'Incentive_To_Give': farm_master_data['Incentive_To_Give'],
                'Total_Incentive_Acres': farm_master_data['Incentive_Acres'],
                'All_Pipe_IDs': ', '.join(all_pipe_ids),
                'Pipes_Installed': pipes_installed,
                'Pipes_Passing': pipes_passing,
                'Non_Compliant_Pipe_IDs': ', '.join(non_compliant_pipe_ids) if non_compliant_pipe_ids else '',
                'Proportion_Passing': proportion_passing,
                'Eligible_Acres': round(eligible_acres, 2),
                'Amount_to_Pay_Rs': round(amount_to_pay, 0),
                'Final_Incentive_Amount': round(final_incentive, 0),
                'Pipe_Details': '\n'.join(pipe_details),
                'Comments': f"Week {week_num} analysis"
            })
    
    return pd.DataFrame(results)

# UPDATED: Cleaner Main App Interface
st.sidebar.header("⚙️ Configuration")

# Google Sheets Configuration
with st.sidebar.expander("🔑 Google Sheets Setup", expanded=False):
    # Get configuration from secrets
    app_config = get_app_config_from_secrets()
    credentials_dict = get_credentials_from_secrets()
    
    if credentials_dict is None:
        st.error("❌ Failed to load credentials from secrets.toml")
        st.stop()
    else:
        st.success("✅ Credentials loaded")
    
    sheet_url = app_config["sheet_url"]
    worksheet_name = app_config["worksheet_name"]
    
    if not sheet_url:
        st.warning("⚠️ No Google Sheets URL configured")
    
    refresh_data = st.button("🔄 Refresh Master Data")

# Water file upload
st.sidebar.header("📁 Water Data Upload")
water_file = st.sidebar.file_uploader(
    "Upload Water Level Data", 
    type=['xlsx'],
    help="Upload Excel file with water measurements"
)

# Data loading section
master_df = None
water_df = None

# Load master data from Google Sheets
if sheet_url and (refresh_data or 'master_df_cache' not in st.session_state):
    with st.spinner("Connecting to Google Sheets..."):
        raw_master = connect_to_google_sheets(credentials_dict, sheet_url, worksheet_name)
    
    if raw_master is not None:
        master_df = clean_master_data(raw_master)
        if master_df is not None:
            st.session_state['master_df_cache'] = master_df
        else:
            st.sidebar.error("❌ Failed to process master data")
elif 'master_df_cache' in st.session_state:
    master_df = st.session_state['master_df_cache']

# Display master data status
if master_df is not None:
    with st.sidebar:
        st.success(f"✅ Master: {len(master_df)} farms")
        group_dist = master_df['Group'].value_counts()
        st.write("**Groups:**")
        for group, count in group_dist.items():
            st.write(f"• {group}: {count}")

# Load water data from file upload
if water_file:
    raw_water = process_uploaded_file(water_file, 'water')
    if raw_water is not None:
        water_df = clean_water_data(raw_water)
        if water_df is not None:
            st.sidebar.success(f"✅ Water: {len(water_df)} measurements")

# UPDATED: Main Analysis Section
if master_df is not None and water_df is not None:
    
    # Filters in sidebar
    st.sidebar.header("🔍 Analysis Filters")
    
    # Date Range Filter
    min_date = water_df['Date'].min().date()
    max_date = water_df['Date'].max().date()
    
    date_range = st.sidebar.date_input(
        "📅 Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    
    # Group filter
    available_groups = sorted(master_df['Group'].unique())
    selected_groups = st.sidebar.multiselect(
        "👥 Groups",
        available_groups,
        default=available_groups
    )
    
    # Village filter
    available_villages = sorted(master_df['Village'].unique())
    selected_villages = st.sidebar.multiselect(
        "🏘️ Villages",
        available_villages,
        default=available_villages
    )
    
    # Generate Analysis
    if st.button("🚀 Run Weekly Compliance Analysis", type="primary", use_container_width=True):
        
        # Apply date filter
        if len(date_range) == 2:
            start_date, end_date = date_range
            water_df_filtered = water_df[
                (water_df['Date'].dt.date >= start_date) & 
                (water_df['Date'].dt.date <= end_date)
            ].copy()
        else:
            water_df_filtered = water_df.copy()
            st.warning("Please select both start and end dates")
        
        with st.spinner("🔄 Analyzing weekly compliance..."):
            results_df = analyze_weekly_compliance(master_df, water_df_filtered, WEEK_PERIODS)
        
        if results_df is not None and not results_df.empty:
            # Apply filters
            if selected_groups:
                results_df = results_df[results_df['Group'].isin(selected_groups)]
            if selected_villages:
                results_df = results_df[results_df['Village'].isin(selected_villages)]
            
            if results_df.empty:
                st.warning("⚠️ No data matches the selected filters.")
            else:
                # UPDATED: Clean results display
                st.header("📊 AWD Weekly Compliance Results")
                
                # Key metrics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    total_farmers = results_df['Farm_ID'].nunique()
                    st.metric("🧑‍🌾 Total Farmers", total_farmers)
                
                with col2:
                    payment_eligible = results_df[results_df['Payment_Eligible'] == True]['Farm_ID'].nunique()
                    st.metric("💰 Payment Eligible", payment_eligible)
                
                with col3:
                    total_incentive = results_df['Final_Incentive_Amount'].sum()
                    st.metric("💵 Total Incentive", f"₹{total_incentive:,.0f}")
                
                with col4:
                    avg_compliance = results_df[results_df['Pipes_Installed'] > 0]['Proportion_Passing'].mean()
                    st.metric("📈 Avg Compliance", f"{avg_compliance:.1%}" if pd.notna(avg_compliance) else "N/A")
                
                # Main results table
                st.subheader("📋 Detailed Results")
                
                # Format display dataframe
                display_df = results_df.copy()
                display_df['Proportion_Passing'] = (display_df['Proportion_Passing'] * 100).round(1).astype(str) + '%'
                display_df['Amount_to_Pay_Rs'] = display_df['Amount_to_Pay_Rs'].apply(lambda x: f"₹{x:,.0f}")
                display_df['Final_Incentive_Amount'] = display_df['Final_Incentive_Amount'].apply(lambda x: f"₹{x:,.0f}")
                display_df['Payment_Eligible'] = display_df['Payment_Eligible'].apply(lambda x: "✅" if x else "❌")
                display_df['Incentive_To_Give'] = display_df['Incentive_To_Give'].apply(lambda x: "✅" if x else "❌")
                
                # UPDATED: Enhanced column selection for display
                display_columns = [
                    'Week', 'Week_Period', 'Village', 'Farm_ID', 'Farmer_Name', 'Group',
                    'Payment_Eligible', 'Incentive_To_Give', 'Total_Incentive_Acres',
                    'All_Pipe_IDs', 'Pipes_Installed', 'Pipes_Passing', 'Non_Compliant_Pipe_IDs',
                    'Proportion_Passing', 'Eligible_Acres', 'Final_Incentive_Amount'
                ]
                
                st.dataframe(display_df[display_columns], use_container_width=True, height=400)
                
                # Download options
                col1, col2 = st.columns(2)
                with col1:
                    csv = results_df.to_csv(index=False)
                    st.download_button(
                        "📥 Download Full Results",
                        csv,
                        f"awd_compliance_analysis_{start_date}_to_{end_date}.csv",
                        "text/csv",
                        use_container_width=True
                    )
                
                with col2:
                    # Payment summary for eligible farms only
                    payment_data = results_df[results_df['Final_Incentive_Amount'] > 0]
                    if not payment_data.empty:
                        payment_csv = payment_data.to_csv(index=False)
                        st.download_button(
                            "💰 Download Payment Records",
                            payment_csv,
                            f"awd_payments_{start_date}_to_{end_date}.csv",
                            "text/csv",
                            use_container_width=True
                        )
                
                # NEW: Pipe Readings Detail Table
                st.subheader("📊 Pipe Readings Detail Table")
                if len(date_range) == 2:
                    pipe_readings_df = create_pipe_readings_table(master_df, water_df_filtered, start_date, end_date)
                    if pipe_readings_df is not None and not pipe_readings_df.empty:
                        # Apply same filters
                        if selected_groups:
                            pipe_readings_df = pipe_readings_df[pipe_readings_df['Group'].isin(selected_groups)]
                        if selected_villages:
                            pipe_readings_df = pipe_readings_df[pipe_readings_df['Village'].isin(selected_villages)]
                        
                        st.dataframe(pipe_readings_df, use_container_width=True, height=400)
                        
                        # Download pipe readings table
                        pipe_csv = pipe_readings_df.to_csv(index=False)
                        st.download_button(
                            "📋 Download Pipe Readings Table",
                            pipe_csv,
                            f"awd_pipe_readings_{start_date}_to_{end_date}.csv",
                            "text/csv",
                            use_container_width=True
                        )
                    else:
                        st.warning("No pipe readings data available for the selected filters")
                else:
                    st.warning("Please select a valid date range to generate pipe readings table")
                
                # Detailed pipe analysis
                with st.expander("🔍 Detailed Pipe Analysis", expanded=False):
                    for _, row in results_df.head(10).iterrows():  # Show first 10 for performance
                        st.write(f"**Week {row['Week']} - {row['Farm_ID']} ({row['Farmer_Name']})**")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"Group: {row['Group']}")
                            st.write(f"All Pipes: {row['All_Pipe_IDs']}")
                            st.write(f"Passing: {row['Pipes_Passing']}/{row['Pipes_Installed']}")
                        with col2:
                            st.write(f"Compliance: {row['Proportion_Passing']:.1%}")
                            if row['Non_Compliant_Pipe_IDs']:
                                st.error(f"Failed Pipes: {row['Non_Compliant_Pipe_IDs']}")
                            st.write(f"Final Incentive: ₹{row['Final_Incentive_Amount']:,.0f}")
                        
                        st.text(row['Pipe_Details'])
                        st.markdown("---")
        else:
            st.error("❌ No results generated. Please check your data.")

else:
    # UPDATED: Cleaner startup message
    if master_df is None:
        st.info("🔗 Please configure Google Sheets connection to load master data")
    if water_df is None:
        st.info("📁 Please upload water level data to begin analysis")

# UPDATED: Cleaner information sections
with st.expander("📅 Study Week Schedule", expanded=False):
    week_df = pd.DataFrame(WEEK_PERIODS, columns=['Week', 'Start', 'End', 'Start_ISO', 'End_ISO'])
    st.dataframe(week_df[['Week', 'Start', 'End']], use_container_width=True)

with st.expander("📊 Output Tables Explained", expanded=False):
    st.markdown("""
    ### 📋 **Weekly Compliance Results Table**
    Main analysis showing week-by-week compliance for each farm with payment calculations.
    
    ### 📊 **Pipe Readings Detail Table** 
    Shows detailed pipe readings for each farm within the selected date range:
    - **Date Range**: Selected analysis period
    - **Farm ID**: Unique farm identifier  
    - **Pipe 1-5**: Each pipe's ID and all readings in format: "PipeID: (date, reading), (date, reading)"
    - **Comments**: Lists which pipes failed compliance (e.g., "Pipe 1,2 did not follow")
    
    **Example Pipe Column**: 
    `P001: (16/06, 150mm), (19/06, 80mm), (22/06, 200mm)`
    """)

with st.expander("📏 Compliance Criteria", expanded=False):
    st.markdown("""
    ### ✅ Pipe Compliance Requirements (Per Week):
    1. **Two measurements** within the week period
    2. **Both readings ≤ 200mm**
    3. **At least one reading ≤ 100mm** 
    4. **Minimum 3 days gap** between measurements
    
    ### 💰 Payment Logic:
    - **Payment Eligible**: Only "A Complied" group
    - **Incentive Calculation**: 
      - Eligible Acres = (Compliant Pipes ÷ Total Pipes) × Incentive Acres
      - Payment = Eligible Acres × ₹300
    - **Final Incentive**: 
      - A Complied: Full calculated payment
      - All others: ₹0
    """)

with st.expander("👥 Group Assignment Logic", expanded=False):
    st.markdown("""
    ### 🔄 Processing Steps:
    1. **Filter**: Keep only farms where "AWD Study" = 1
    2. **Assign Groups**: Based on group flags and compliance status
    3. **Remove**: All "Unassigned" and "No Group" farms
    4. **Payment**: Only "A Complied" group eligible
    
    ### 📊 Final Groups:
    - **A Complied** → Payment Eligible ✅
    - **A Non Complied** → No Payment ❌
    - **B Complied** → No Payment ❌
    - **B Non Complied** → No Payment ❌
    - **C Complied** → No Payment ❌
    - **C Non Complied** → No Payment ❌
    """)

st.markdown("---")
st.markdown("*AsWD Compliance Analysis Dashboard v14.0 - Enhanced with Unassigned Filtering & Incentive Logic*")