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
        
        st.success(f"1 Connected to Google Sheets: {len(df)} rows loaded")
        return df
        
    except Exception as e:
        st.error(f"0 Error connecting to Google Sheets: {str(e)}")
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
        st.error(f"0 Missing secret: {str(e)}")
        st.error("Please check your .streamlit/secrets.toml file configuration")
        return None
    except Exception as e:
        st.error(f"0 Error loading secrets: {str(e)}")
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
        st.error(f"0 Error loading app config: {str(e)}")
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
        
        st.success(f"1 File loaded successfully: {len(df)} rows")
        return df
    except Exception as e:
        st.error(f"0 Error loading file: {str(e)}")
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

def extract_pipe_codes(row):
    """Extract pipe codes for a farm from the master data"""
    pipe_codes = []
    for i in range(1, 6):  # Pipes 1-5
        pipe_col = f'Kharif 25 PVC Pipe code - {i}'
        if pipe_col in row.index and pd.notna(row[pipe_col]):
            pipe_code = str(row[pipe_col]).strip()
            if pipe_code and pipe_code != '' and pipe_code.lower() != 'nan':
                pipe_codes.append(pipe_code)
    return pipe_codes

def clean_master_data(df):
    """Enhanced cleaning for master data with pipe mapping"""
    try:
        df_clean = df.copy()
        
        # Find basic columns using exact names
        farm_id_col = 'Kharif 25 Farm ID'
        farmer_name_col = 'Kharif 25 Farmer Name'
        village_col = 'Kharif 25 Village'
        incentive_acres_col = 'Kharif 25 - AWD Study - acres for incentive'
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
        
        # Pipe code columns
        pipe_code_cols = [f'Kharif 25 PVC Pipe code - {i}' for i in range(1, 6)]
        
        # Check if required columns exist
        missing_cols = []
        all_required_cols = [
            farm_id_col, farmer_name_col, village_col, incentive_acres_col, awd_study_col,
            group_a_col, group_a_complied_col, group_a_non_complied_col,
            group_b_col, group_b_complied_col, group_b_non_complied_col,
            group_c_col, group_c_complied_col, group_c_non_complied_col
        ] + pipe_code_cols
        
        for col in all_required_cols:
            if col not in df_clean.columns:
                missing_cols.append(col)
        
        if missing_cols:
            st.error(f"0 Missing required columns: {missing_cols}")
            st.info("Available columns: " + ", ".join(df_clean.columns.tolist()))
            return None, None
        
        # Standardize basic columns
        df_clean['Farm_ID'] = df_clean[farm_id_col].astype(str).fillna("Unknown_Farm")
        df_clean['Farmer_Name'] = df_clean[farmer_name_col].astype(str).fillna("Unknown_Farmer")
        df_clean['Village'] = df_clean[village_col].astype(str).fillna("Unknown_Village")
        
        # Handle incentive acres
        df_clean['Incentive_Acres'] = pd.to_numeric(df_clean[incentive_acres_col], errors='coerce').fillna(0).clip(lower=0)
        
        # Filter by AWD Study participation
        df_clean['awd_study_flag'] = df_clean[awd_study_col].apply(is_positive_value)
        initial_count = len(df_clean)
        df_clean = df_clean[df_clean['awd_study_flag'] == True].copy()
        filtered_count = len(df_clean)
        
        if df_clean.empty:
            st.warning("⚠️ No AWD study participants found after filtering")
            return None, None
        
        st.info(f"📊 Filtered to {filtered_count} AWD study participants from {initial_count} total farms")
        
        # Assign groups with 6-group logic
        def assign_group_with_compliance(row):
            # Check Group A first
            if is_positive_value(row[group_a_col]):
                if is_positive_value(row[group_a_complied_col]):
                    return 'A Complied'
                elif is_positive_value(row[group_a_non_complied_col]):
                    return 'A Non Complied'
                else:
                    return 'A Unassigned'
            
            # Check Group B 
            elif is_positive_value(row[group_b_col]):
                if is_positive_value(row[group_b_complied_col]):
                    return 'B Complied'
                elif is_positive_value(row[group_b_non_complied_col]):
                    return 'B Non Complied'
                else:
                    return 'B Unassigned'
            
            # Check Group C
            elif is_positive_value(row[group_c_col]):
                if is_positive_value(row[group_c_complied_col]):
                    return 'C Complied'
                elif is_positive_value(row[group_c_non_complied_col]):
                    return 'C Non Complied'
                else:
                    return 'C Unassigned'
            
            else:
                return 'No Group Assigned'
        
        df_clean['Group'] = df_clean.apply(assign_group_with_compliance, axis=1)
        
        # Filter out unassigned groups
        before_filter = len(df_clean)
        df_clean = df_clean[~df_clean['Group'].isin(['A Unassigned', 'B Unassigned', 'C Unassigned', 'No Group Assigned'])].copy()
        after_filter = len(df_clean)
        
        st.info(f"📊 Removed {before_filter - after_filter} farms with unassigned groups")
        
        if df_clean.empty:
            st.warning("⚠️ No farms remaining after removing unassigned groups")
            return None, None
        
        # Payment eligibility and incentive calculation
        df_clean['Payment_Eligible'] = df_clean['Group'] == 'A Complied'
        df_clean['Incentive_To_Give'] = df_clean['Group'].apply(lambda x: 1 if x == 'A Complied' else 0)
        
        # Extract pipe codes for each farm
        df_clean['Pipe_Codes'] = df_clean.apply(extract_pipe_codes, axis=1)
        df_clean['Pipe_Count'] = df_clean['Pipe_Codes'].apply(len)
        
        # Create farm-pipe mapping
        farm_pipe_mapping = {}
        all_pipe_codes = set()
        
        for _, row in df_clean.iterrows():
            farm_id = row['Farm_ID']
            pipe_codes = row['Pipe_Codes']
            farm_pipe_mapping[farm_id] = pipe_codes
            all_pipe_codes.update(pipe_codes)
        
        # Show group distribution and pipe statistics
        group_counts = df_clean['Group'].value_counts()
        payment_eligible_count = df_clean['Payment_Eligible'].sum()
        
        st.success(f"1 Final Group Distribution: {group_counts.to_dict()}")
        st.success(f"1 Payment Eligible Farms (A Complied): {payment_eligible_count} farms")
        st.success(f"1 Total Unique Pipe Codes Found: {len(all_pipe_codes)} pipes")
        st.success(f"1 Farms with Pipes: {len(df_clean[df_clean['Pipe_Count'] > 0])} farms")
        
        # Prepare final dataframe
        final_df = df_clean[['Farm_ID', 'Farmer_Name', 'Village', 'Incentive_Acres', 'Group', 
                           'Payment_Eligible', 'Incentive_To_Give', 'Pipe_Codes', 'Pipe_Count']].copy()
        
        # Remove farms with no valid Farm_ID
        final_df = final_df.dropna(subset=['Farm_ID'])
        final_df = final_df[final_df['Farm_ID'] != 'Unknown_Farm']
        
        st.success(f"1 Final clean data: {len(final_df)} farms ready for analysis")
        
        return final_df, farm_pipe_mapping
        
    except Exception as e:
        st.error(f"0 Error cleaning master data: {str(e)}")
        st.exception(e)
        return None, None

def clean_water_data(df, farm_pipe_mapping):
    """Enhanced cleaning for water data with pipe mapping validation"""
    try:
        df_clean = df.copy()
        
        # Find columns
        date_col = find_column(df_clean, ['date'], 'Date')
        pipe_id_col = find_column(df_clean, ['pipe id', 'pipe_id', 'pipe code', 'pipeid'], 'Pipe_ID')
        water_col = find_column(df_clean, ['water level', 'water_level', 'depth'], 'Water_Level_mm')
        
        if not all([date_col, pipe_id_col, water_col]):
            st.error(f"0 Missing essential columns in water data. Found: Date={date_col}, Pipe_ID={pipe_id_col}, Water_Level={water_col}")
            return None
        
        # Standardize column names
        df_clean['Date'] = pd.to_datetime(df_clean[date_col], errors='coerce')
        df_clean['Pipe_ID'] = df_clean[pipe_id_col].astype(str).str.strip()
        df_clean['Water_Level_mm'] = pd.to_numeric(df_clean[water_col], errors='coerce')
        
        # Drop rows with missing essential data
        initial_count = len(df_clean)
        df_clean = df_clean.dropna(subset=['Date', 'Pipe_ID', 'Water_Level_mm'])
        after_drop = len(df_clean)
        
        if after_drop < initial_count:
            st.info(f"📊 Removed {initial_count - after_drop} rows with missing data")
        
        # Get all valid pipe codes from master data
        all_valid_pipes = set()
        for pipe_codes in farm_pipe_mapping.values():
            all_valid_pipes.update(pipe_codes)
        
        # Filter water data to only include pipes from master data
        before_filter = len(df_clean)
        df_clean = df_clean[df_clean['Pipe_ID'].isin(all_valid_pipes)].copy()
        after_filter = len(df_clean)
        
        # Add Farm_ID based on pipe mapping
        def get_farm_id_for_pipe(pipe_id):
            for farm_id, pipe_codes in farm_pipe_mapping.items():
                if pipe_id in pipe_codes:
                    return farm_id
            return None
        
        df_clean['Farm_ID'] = df_clean['Pipe_ID'].apply(get_farm_id_for_pipe)
        
        # Remove readings for pipes not mapped to any farm
        df_clean = df_clean.dropna(subset=['Farm_ID'])
        final_count = len(df_clean)
        
        st.info(f"📊 Water data filtering results:")
        st.info(f"   - Total valid pipes in master: {len(all_valid_pipes)}")
        st.info(f"   - Before pipe filtering: {before_filter} readings")
        st.info(f"   - After pipe filtering: {after_filter} readings")
        st.info(f"   - Final mapped readings: {final_count} readings")
        
        if df_clean.empty:
            st.warning("⚠️ No water data matches the pipes from master data")
            return None
        
        # Show pipe coverage statistics
        unique_pipes_in_water = df_clean['Pipe_ID'].nunique()
        unique_farms_in_water = df_clean['Farm_ID'].nunique()
        
        st.success(f"1 Water data summary:")
        st.success(f"   - Unique pipes with data: {unique_pipes_in_water}")
        st.success(f"   - Unique farms with data: {unique_farms_in_water}")
        st.success(f"   - Date range: {df_clean['Date'].min().date()} to {df_clean['Date'].max().date()}")
        
        return df_clean[['Date', 'Farm_ID', 'Pipe_ID', 'Water_Level_mm']]
        
    except Exception as e:
        st.error(f"0 Error cleaning water data: {str(e)}")
        st.exception(e)
        return None

def get_week_number_dynamic(date, start_date):
    """Get week number based on dynamic start date (day 1)"""
    days_diff = (date.date() - start_date).days
    week_number = (days_diff // 7) + 1
    return max(1, week_number)

def analyze_pipe_compliance(pipe_data):
    """Check if a pipe meets compliance criteria (UPDATED: Single reading ≤200 is compliant)"""
    if len(pipe_data) == 0:
        return {'compliant': False, 'reason': 'No readings available'}
    
    # Sort readings by date
    pipe_data = pipe_data.sort_values('Date')
    
    # Get all readings for compliance check
    readings = pipe_data['Water_Level_mm'].tolist()
    
    # Special case: Single reading ≤200mm = compliant
    if len(pipe_data) == 1:
        single_reading = readings[0]
        if single_reading <= 200:
            return {
                'compliant': True,
                'reason': 'Single reading ≤200mm (compliant)'
            }
        else:
            return {
                'compliant': False,
                'reason': 'Single reading >200mm (non-compliant)'
            }
    
    # Multiple readings (≥2): All ≤200mm + at least one ≤100mm
    if len(pipe_data) >= 2:
        # Compliance checks (NO GAP CONSTRAINT)
        both_below_200 = all(reading <= 200 for reading in readings)
        one_below_100 = any(reading <= 100 for reading in readings)
        
        compliant = both_below_200 and one_below_100
        
        if compliant:
            return {
                'compliant': True,
                'reason': 'All criteria met'
            }
        else:
            failed_criteria = []
            if not both_below_200:
                failed_criteria.append('All readings must be ≤200mm')
            if not one_below_100:
                failed_criteria.append('At least one reading must be ≤100mm')
            
            return {
                'compliant': False,
                'reason': '; '.join(failed_criteria)
            }
    
    # This should never be reached
    return {'compliant': False, 'reason': 'Unknown error'}

def validate_compliance_logic():
    """Test function to validate that compliance logic is working correctly"""
    test_results = []
    
    # Test 1: Single reading ≤200mm should be compliant
    test_data_1 = pd.DataFrame({
        'Date': [pd.Timestamp('2025-01-01')],
        'Water_Level_mm': [150]
    })
    result_1 = analyze_pipe_compliance(test_data_1)
    test_results.append(f"Test 1 - Single reading 150mm: {'1 PASS' if result_1['compliant'] else '0 FAIL'}")
    
    # Test 2: Single reading >200mm should be non-compliant
    test_data_2 = pd.DataFrame({
        'Date': [pd.Timestamp('2025-01-01')],
        'Water_Level_mm': [250]
    })
    result_2 = analyze_pipe_compliance(test_data_2)
    test_results.append(f"Test 2 - Single reading 250mm: {'0 FAIL (Expected)' if not result_2['compliant'] else '1 UNEXPECTED PASS'}")
    
    # Test 3: Multiple readings, all ≤200mm with one ≤100mm should be compliant
    test_data_3 = pd.DataFrame({
        'Date': [pd.Timestamp('2025-01-01'), pd.Timestamp('2025-01-02')],
        'Water_Level_mm': [80, 150]
    })
    result_3 = analyze_pipe_compliance(test_data_3)
    test_results.append(f"Test 3 - Multiple readings [80, 150]: {'1 PASS' if result_3['compliant'] else '0 FAIL'}")

    # Test 4: Multiple readings, all ≤200mm but none ≤100mm should be non-compliant
    test_data_4 = pd.DataFrame({
        'Date': [pd.Timestamp('2025-01-01'), pd.Timestamp('2025-01-02')],
        'Water_Level_mm': [150, 180]
    })
    result_4 = analyze_pipe_compliance(test_data_4)
    test_results.append(f"Test 4 - Multiple readings [150, 180]: {'0 FAIL (Expected)' if not result_4['compliant'] else '1 UNEXPECTED PASS'}")

    return test_results

def analyze_farm_compliance(master_df, water_df, farm_pipe_mapping, start_date, end_date):
    """Analyze compliance for each farm using ONLY pipes with ≥2 readings as denominator (FIXED)"""
    try:
        results = []
        
        # Filter water data to date range
        water_df_filtered = water_df[
            (water_df['Date'].dt.date >= start_date) & 
            (water_df['Date'].dt.date <= end_date)
        ].copy()
        
        for _, farm_data in master_df.iterrows():
            farm_id = farm_data['Farm_ID']
            farm_pipe_codes = farm_data['Pipe_Codes']
            
            # Get water data for this farm in the date range
            farm_water_data = water_df_filtered[water_df_filtered['Farm_ID'] == farm_id].copy()
            
            # Initialize counters
            valid_pipes = 0      # Pipes with ≥1 readings (VALID PIPE DEFINITION)
            pipes_passing = 0     # Pipes meeting compliance criteria
            compliant_pipe_ids = []
            non_compliant_pipe_ids = []
            pipe_readings_details = []
            
            # Analyze each pipe assigned to this farm
            for pipe_id in farm_pipe_codes:
                pipe_data = farm_water_data[farm_water_data['Pipe_ID'] == pipe_id]
                
                # PIPE VALIDITY: ≥1 reading makes a pipe valid
                if len(pipe_data) >= 1:  
                    valid_pipes += 1  # Count as valid pipe
                    compliance_result = analyze_pipe_compliance(pipe_data)
                    
                    # Format readings for output
                    readings_str = ", ".join([
                        f"({row['Date'].strftime('%d/%m')}, {int(row['Water_Level_mm'])}mm)" 
                        for _, row in pipe_data.sort_values('Date').iterrows()
                    ])
                    
                    # Add compliance result to the details
                    if len(pipe_data) == 1:
                        pipe_readings_details.append(f"{pipe_id}: {readings_str} - Single reading")
                    else:
                        pipe_readings_details.append(f"{pipe_id}: {readings_str}")
                    
                    # COMPLIANCE CHECK: Apply the compliance rules
                    if compliance_result['compliant']:
                        pipes_passing += 1
                        compliant_pipe_ids.append(pipe_id)
                    else:
                        non_compliant_pipe_ids.append(pipe_id)
                else:
                    # Pipe has no readings - not valid
                    pipe_readings_details.append(f"{pipe_id}: No readings in period")
            
            # FARM COMPLIANCE CALCULATION: Use valid pipes (≥1 readings) as denominator
            if valid_pipes > 0:
                proportion_passing = pipes_passing / valid_pipes  
            else:
                proportion_passing = 0  # No valid pipes → 0% compliance
            
            # Calculate eligible acres and payment
            eligible_acres = proportion_passing * farm_data['Incentive_Acres']
            final_incentive_amount = eligible_acres * 300 if farm_data['Payment_Eligible'] else 0
            
            # FARM VALIDITY: Farm is valid if it has ≥1 pipe with ≥1 readings
            is_valid_farm = valid_pipes > 0
            
            results.append({
                'Village': farm_data['Village'],
                'Farm_ID': farm_id,
                'Farmer_Name': farm_data['Farmer_Name'],
                'Group': farm_data['Group'],
                'Valid_Farm': '1' if is_valid_farm else '0',  # NEW: Valid farm indicator
                'Total_Incentive_Acres': farm_data['Incentive_Acres'],
                'All_Pipe_IDs': ', '.join(farm_pipe_codes) if farm_pipe_codes else 'None',
                'Total_Assigned_Pipes': len(farm_pipe_codes),  # NEW: Total assigned
                'Valid_Pipes_Count': valid_pipes,  # UPDATED: Pipes with ≥1 readings
                'Pipes_Passing': pipes_passing,
                'Pipes_Read': '\n'.join(pipe_readings_details),
                'Compliant_Pipe_IDs': ', '.join(compliant_pipe_ids) if compliant_pipe_ids else 'None',
                'Non_Compliant_Pipe_IDs': ', '.join(non_compliant_pipe_ids) if non_compliant_pipe_ids else 'None',
                'Farm_Proportion_Passing': proportion_passing,  # UPDATED: Now based on pipes with ≥1 readings
                'Eligible_Acres': round(eligible_acres, 2),
                'Final_Incentive_Amount': round(final_incentive_amount, 0)
            })
        
        return pd.DataFrame(results)
        
    except Exception as e:
        st.error(f"0 Error analyzing farm compliance: {str(e)}")
        st.exception(e)
        return None

def analyze_weekly_compliance(master_df, water_df, farm_pipe_mapping, start_date, end_date):
    """Analyze compliance week by week within the selected date range (FIXED)"""
    try:
        results = []
        
        # Generate week periods based on start_date
        current_date = start_date
        week_number = 1
        
        while current_date <= end_date:
            week_end = min(current_date + timedelta(days=6), end_date)
            
            # Filter water data for this week
            week_water_data = water_df[
                (water_df['Date'].dt.date >= current_date) & 
                (water_df['Date'].dt.date <= week_end)
            ].copy()
            
            # Analyze each farm for this week
            for _, farm_data in master_df.iterrows():
                farm_id = farm_data['Farm_ID']
                farm_pipe_codes = farm_data['Pipe_Codes']
                
                # Get water data for this farm this week
                farm_water_data = week_water_data[week_water_data['Farm_ID'] == farm_id]
                
                # Initialize pipe analysis
                pipe_details = []
                total_assigned_pipes = len(farm_pipe_codes)
                valid_pipes = 0  # Pipes with ≥1 readings this week (UPDATED)
                pipes_passing = 0
                non_compliant_pipe_ids = []
                
                for pipe_id in farm_pipe_codes:
                    pipe_data = farm_water_data[farm_water_data['Pipe_ID'] == pipe_id]
                    
                    if len(pipe_data) >= 1:  # UPDATED: Consider pipes with ≥1 readings
                        valid_pipes += 1
                        compliance_result = analyze_pipe_compliance(pipe_data)
                        
                        # Format readings
                        readings_str = ", ".join([
                            f"{row['Date'].strftime('%d/%m')} ({int(row['Water_Level_mm'])}mm)"
                            for _, row in pipe_data.sort_values('Date').iterrows()
                        ])
                        
                        if compliance_result['compliant']:
                            pipes_passing += 1
                            if len(pipe_data) == 1:
                                pipe_detail = f"{pipe_id}: {readings_str} 🟢 PASS (Single reading ≤200mm)"
                            else:
                                pipe_detail = f"{pipe_id}: {readings_str} 🟢 PASS"
                        else:
                            non_compliant_pipe_ids.append(pipe_id)
                            if len(pipe_data) == 1:
                                pipe_detail = f"{pipe_id}: {readings_str} 🔴 FAIL (Single reading >200mm)"
                            else:
                                pipe_detail = f"{pipe_id}: {readings_str} � FAIL"
                        
                        pipe_details.append(pipe_detail)
                    else:
                        # No readings for this pipe
                        pipe_detail = f"{pipe_id}: No data this week 🔴"
                        pipe_details.append(pipe_detail)
                        non_compliant_pipe_ids.append(pipe_id)
                
                # FIXED CALCULATION: Use valid pipes as denominator
                if valid_pipes > 0:
                    proportion_passing = pipes_passing / valid_pipes
                else:
                    proportion_passing = 0
                
                eligible_acres = proportion_passing * farm_data['Incentive_Acres']
                
                # Payment calculation
                if farm_data['Payment_Eligible']:
                    amount_to_pay = eligible_acres * 300
                else:
                    amount_to_pay = 0
                
                final_incentive = farm_data['Incentive_To_Give'] * amount_to_pay
                
                # Determine if farm is valid (has at least 1 pipe with ≥1 readings)
                is_valid_farm = valid_pipes > 0
                
                results.append({
                    'Week': week_number,
                    'Week_Period': f"{current_date.strftime('%d/%m')} - {week_end.strftime('%d/%m')}",
                    'Village': farm_data['Village'],
                    'Farm_ID': farm_id,
                    'Farmer_Name': farm_data['Farmer_Name'],
                    'Group': farm_data['Group'],
                    'Valid_Farm': '1' if is_valid_farm else '0',  # NEW: Valid farm indicator
                    'Payment_Eligible': farm_data['Payment_Eligible'],
                    'Total_Incentive_Acres': farm_data['Incentive_Acres'],
                    'Assigned_Pipe_IDs': ', '.join(farm_pipe_codes),
                    'Total_Assigned_Pipes': total_assigned_pipes,
                    'Valid_Pipes_Count': valid_pipes,  # UPDATED: Pipes with ≥1 readings
                    'Pipes_Passing': pipes_passing,
                    'Non_Compliant_Pipe_IDs': ', '.join(non_compliant_pipe_ids) if non_compliant_pipe_ids else '',
                    'Proportion_Passing': proportion_passing,  # UPDATED: Based on valid pipes (≥1 readings)
                    'Eligible_Acres': round(eligible_acres, 2),
                    'Final_Incentive_Amount': round(final_incentive, 0),
                    'Pipe_Details': '\n'.join(pipe_details),
                    'Comments': f"Week {week_number} analysis - {valid_pipes}/{total_assigned_pipes} pipes valid (≥1 reading)"
                })
            
            # Move to next week
            current_date = week_end + timedelta(days=1)
            week_number += 1
        
        return pd.DataFrame(results)
        
    except Exception as e:
        st.error(f"0 Error analyzing weekly compliance: {str(e)}")
        st.exception(e)
        return None

def create_pipe_readings_table(master_df, water_df, farm_pipe_mapping, start_date, end_date):
    """Create detailed pipe readings table (FIXED)"""
    try:
        results = []
        
        # Filter water data to date range
        water_df_filtered = water_df[
            (water_df['Date'].dt.date >= start_date) & 
            (water_df['Date'].dt.date <= end_date)
        ].copy()
        
        for _, farm_data in master_df.iterrows():
            farm_id = farm_data['Farm_ID']
            farm_pipe_codes = farm_data['Pipe_Codes']
            
            # Get water data for this farm in the date range
            farm_water_data = water_df_filtered[water_df_filtered['Farm_ID'] == farm_id].copy()
            
            # Initialize pipe columns
            pipe_columns = {}
            
            # Process each pipe assigned to this farm (up to 5)
            for i in range(5):
                pipe_col = f'Pipe_{i+1}'
                
                if i < len(farm_pipe_codes):
                    pipe_id = farm_pipe_codes[i]
                    pipe_data = farm_water_data[farm_water_data['Pipe_ID'] == pipe_id]
                    
                    if pipe_data.empty:
                        pipe_columns[pipe_col] = f"{pipe_id}: No data"
                    else:
                        # Format readings
                        readings_list = []
                        for _, reading in pipe_data.sort_values('Date').iterrows():
                            date_str = reading['Date'].strftime('%d/%m')
                            reading_val = int(reading['Water_Level_mm'])
                            readings_list.append(f"({date_str}, {reading_val}mm)")
                        
                        pipe_columns[pipe_col] = f"{pipe_id}: " + ", ".join(readings_list)
                else:
                    pipe_columns[pipe_col] = 'Not assigned'
            
            # Determine non-compliant pipes (UPDATED: Consider pipes with ≥1 readings)
            non_compliant_pipes = []
            for pipe_id in farm_pipe_codes:
                pipe_data = farm_water_data[farm_water_data['Pipe_ID'] == pipe_id]
                if len(pipe_data) >= 1:  # UPDATED: Evaluate pipes with ≥1 reading
                    compliance_result = analyze_pipe_compliance(pipe_data)
                    if not compliance_result['compliant']:
                        # Find pipe number for this pipe_id
                        pipe_num = farm_pipe_codes.index(pipe_id) + 1
                        if len(pipe_data) == 1:
                            non_compliant_pipes.append(f"{pipe_num}(single reading >200mm)")
                        else:
                            non_compliant_pipes.append(str(pipe_num))
                else:
                    # Pipes with no data
                    pipe_num = farm_pipe_codes.index(pipe_id) + 1
                    non_compliant_pipes.append(f"{pipe_num}(no data)")
            
            # Create comments (UPDATED)
            if non_compliant_pipes:
                comments = f"Pipe {','.join(non_compliant_pipes)} did not follow compliance"
            elif farm_pipe_codes and not farm_water_data.empty:
                # Check if any pipes have ≥1 readings
                pipes_with_data = [
                    pipe_id for pipe_id in farm_pipe_codes 
                    if len(farm_water_data[farm_water_data['Pipe_ID'] == pipe_id]) >= 1
                ]
                if pipes_with_data:
                    comments = "All evaluated pipes compliant"
                else:
                    comments = "No pipes have any data"
            else:
                comments = "No pipe data"
            
            # Determine if farm is valid (has at least 1 pipe with ≥1 readings)
            pipes_with_data = [
                pipe_id for pipe_id in farm_pipe_codes 
                if len(farm_water_data[farm_water_data['Pipe_ID'] == pipe_id]) >= 1
            ]
            is_valid_farm = len(pipes_with_data) > 0
            
            results.append({
                'Date_Range': f"{start_date} to {end_date}",
                'Village': farm_data['Village'],
                'Farm_ID': farm_id,
                'Farmer_Name': farm_data['Farmer_Name'],
                'Group': farm_data['Group'],
                'Valid_Farm': '1' if is_valid_farm else '0',  # NEW: Valid farm indicator
                **pipe_columns,
                'Comments': comments
            })
        
        return pd.DataFrame(results)
        
    except Exception as e:
        st.error(f"0 Error creating pipe readings table: {str(e)}")
        return None

def create_pipe_summary_table(master_df, water_df, farm_pipe_mapping, start_date, end_date):
    """Create pipe summary table with new column structure including dates and readings count"""
    try:
        results = []
        
        # Filter water data to date range
        water_df_filtered = water_df[
            (water_df['Date'].dt.date >= start_date) & 
            (water_df['Date'].dt.date <= end_date)
        ].copy()
        
        for _, farm_data in master_df.iterrows():
            farm_id = farm_data['Farm_ID']
            farm_pipe_codes = farm_data['Pipe_Codes']
            farmer_name = farm_data['Farmer_Name']
            group = farm_data['Group']
            
            # Get water data for this farm in the date range
            farm_water_data = water_df_filtered[water_df_filtered['Farm_ID'] == farm_id].copy()
            
            # Determine if farm is valid (has at least 1 pipe with ≥1 readings)
            pipes_with_data = [
                pipe_id for pipe_id in farm_pipe_codes 
                if len(farm_water_data[farm_water_data['Pipe_ID'] == pipe_id]) >= 1
            ]
            is_valid_farm = len(pipes_with_data) > 0
            farm_valid_status = '1' if is_valid_farm else '0'
            
            # Process each pipe assigned to this farm
            for pipe_id in farm_pipe_codes:
                pipe_data = farm_water_data[farm_water_data['Pipe_ID'] == pipe_id].copy()
                
                # Initialize reading columns (up to 6 readings)
                reading_data = {
                    'Reading_1_mm': '',
                    'Reading_1_Date': '',
                    'Reading_2_mm': '',
                    'Reading_2_Date': '',
                    'Reading_3_mm': '',
                    'Reading_3_Date': '',
                    'Reading_4_mm': '',
                    'Reading_4_Date': '',
                    'Reading_5_mm': '',
                    'Reading_5_Date': '',
                    'Reading_6_mm': '',
                    'Reading_6_Date': ''
                }
                
                total_readings = len(pipe_data)
                
                if not pipe_data.empty:
                    # Sort by date and get up to 6 readings
                    pipe_data_sorted = pipe_data.sort_values('Date')
                    for i, (_, reading) in enumerate(pipe_data_sorted.iterrows()):
                        if i < 6:  # Only take first 6 readings
                            reading_data[f'Reading_{i+1}_mm'] = int(reading['Water_Level_mm'])
                            reading_data[f'Reading_{i+1}_Date'] = reading['Date'].strftime('%d/%m/%Y')
                
                # Determine if pipe is valid (has at least 1 reading)
                valid_pipe_status = '1' if total_readings >= 1 else '0'

                # Determine compliance for this pipe
                compliance_status = "No Data"
                if len(pipe_data) >= 1:
                    compliance_result = analyze_pipe_compliance(pipe_data)
                    if compliance_result['compliant']:
                        compliance_status = 1
                    else:
                        compliance_status = 0
                
                # Add row for this pipe
                results.append({
                    'Farm_ID': farm_id,
                    'Pipe_ID': pipe_id,
                    'Farm_Valid': farm_valid_status,
                    'Valid_pipe': valid_pipe_status,
                    'Farmer_Name': farmer_name,
                    'Group': group,
                    'Abiding_AWD_method': compliance_status,
                    **reading_data,
                    'Total_number_of_readings': total_readings
                })
        
        return pd.DataFrame(results)
        
    except Exception as e:
        st.error(f"0 Error creating pipe summary table: {str(e)}")
        return None

def create_village_summary(results_df):
    """Create village-wise summary"""
    try:
        # Filter to only valid farms for compliance calculations
        valid_farms_df = results_df[results_df['Valid_Farm'] == '1']
        
        village_summary = results_df.groupby('Village').agg({
            'Farm_ID': 'count',
            'Final_Incentive_Amount': 'sum',
            'Pipes_Passing': 'sum',
            'Valid_Pipes_Count': 'sum',  # FIXED: Use valid pipes instead
            'Total_Assigned_Pipes': 'sum'  # NEW: Also show total assigned
        }).rename(columns={
            'Farm_ID': 'Total_Farms',
            'Final_Incentive_Amount': 'Total_Village_Incentive',
            'Pipes_Passing': 'Total_Compliant_Pipes',
            'Valid_Pipes_Count': 'Total_Valid_Pipes',
            'Total_Assigned_Pipes': 'Total_Assigned_Pipes'
        })
        
        # Add valid farms count and avg compliance (only for valid farms)
        valid_farms_summary = valid_farms_df.groupby('Village').agg({
            'Farm_ID': 'count',
            'Farm_Proportion_Passing': 'mean'
        }).rename(columns={
            'Farm_ID': 'Valid_Farms',
            'Farm_Proportion_Passing': 'Avg_Compliance_Rate_Valid_Farms'
        })
        
        # Merge the summaries
        village_summary = village_summary.merge(valid_farms_summary, left_index=True, right_index=True, how='left')
        village_summary['Valid_Farms'] = village_summary['Valid_Farms'].fillna(0).astype(int)
        village_summary['Avg_Compliance_Rate_Valid_Farms'] = village_summary['Avg_Compliance_Rate_Valid_Farms'].fillna(0)
        
        # Reorder columns
        village_summary = village_summary[['Total_Farms', 'Valid_Farms', 'Avg_Compliance_Rate_Valid_Farms', 
                                         'Total_Village_Incentive', 'Total_Compliant_Pipes', 'Total_Valid_Pipes', 
                                         'Total_Assigned_Pipes']]
        
        village_summary = village_summary.round(2)
        return village_summary
        
    except Exception as e:
        st.error(f"0 Error creating village summary: {str(e)}")
        return None

def create_payment_summary(results_df):
    """Create payment summary table"""
    try:
        payment_farms = results_df[results_df['Final_Incentive_Amount'] > 0].copy()
        
        if payment_farms.empty:
            return pd.DataFrame()
        
        payment_summary = payment_farms[['Village', 'Farm_ID', 'Farmer_Name', 'Group', 'Valid_Farm',
                                       'Total_Incentive_Acres', 'Valid_Pipes_Count',  # FIXED: Show valid pipes
                                       'Pipes_Passing', 'Eligible_Acres', 
                                       'Farm_Proportion_Passing', 'Final_Incentive_Amount']].copy()
        
        payment_summary = payment_summary.sort_values('Final_Incentive_Amount', ascending=False)
        return payment_summary
        
    except Exception as e:
        st.error(f"0 Error creating payment summary: {str(e)}")
        return None

# Main App Interface
st.sidebar.header("⚙️ Configuration")

# Google Sheets Configuration
with st.sidebar.expander("🔑 Google Sheets Setup", expanded=False):
    app_config = get_app_config_from_secrets()
    credentials_dict = get_credentials_from_secrets()
    
    if credentials_dict is None:
        st.error("0 Failed to load credentials from secrets.toml")
        st.stop()
    else:
        st.success("1 Credentials loaded")
    
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
farm_pipe_mapping = None

# Load master data from Google Sheets
if sheet_url and (refresh_data or 'master_df_cache' not in st.session_state):
    with st.spinner("Connecting to Google Sheets..."):
        raw_master = connect_to_google_sheets(credentials_dict, sheet_url, worksheet_name)
    
    if raw_master is not None:
        master_df, farm_pipe_mapping = clean_master_data(raw_master)
        if master_df is not None and farm_pipe_mapping is not None:
            st.session_state['master_df_cache'] = master_df
            st.session_state['farm_pipe_mapping_cache'] = farm_pipe_mapping
        else:
            st.sidebar.error("0 Failed to process master data")
elif 'master_df_cache' in st.session_state:
    master_df = st.session_state['master_df_cache']
    farm_pipe_mapping = st.session_state['farm_pipe_mapping_cache']

# Display master data status
if master_df is not None:
    with st.sidebar:
        st.success(f"1 Master: {len(master_df)} farms")
        group_dist = master_df['Group'].value_counts()
        st.write("**Groups:**")
        for group, count in group_dist.items():
            st.write(f"• {group}: {count}")
        
        # Show pipe statistics
        total_pipes = sum(len(pipes) for pipes in farm_pipe_mapping.values())
        st.write(f"**Pipes:** {total_pipes} total assigned")

# Load water data from file upload
if water_file and farm_pipe_mapping is not None:
    raw_water = process_uploaded_file(water_file, 'water')
    if raw_water is not None:
        water_df = clean_water_data(raw_water, farm_pipe_mapping)
        if water_df is not None:
            st.sidebar.success(f"1 Water: {len(water_df)} measurements")

# Main Analysis Section
if master_df is not None and water_df is not None and farm_pipe_mapping is not None:
    
    # Filters in sidebar
    st.sidebar.header("🔍 Analysis Filters")
    
    # Date Range Filter
    min_date = water_df['Date'].min().date()
    max_date = water_df['Date'].max().date()
    
    date_range = st.sidebar.date_input(
        "📅 Analysis Date Range (Start date = Day 1)",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        help="Start date will be treated as Day 1 of the analysis period"
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
    if st.button("🚀 Run Compliance Analysis", type="primary", use_container_width=True):
        
        # Validate date range
        if len(date_range) != 2:
            st.error("Please select both start and end dates")
        else:
            start_date, end_date = date_range
            
            with st.spinner("🔄 Analyzing farm compliance..."):
                results_df = analyze_farm_compliance(master_df, water_df, farm_pipe_mapping, start_date, end_date)
            
            if results_df is not None and not results_df.empty:
                # Apply filters
                if selected_groups:
                    results_df = results_df[results_df['Group'].isin(selected_groups)]
                if selected_villages:
                    results_df = results_df[results_df['Village'].isin(selected_villages)]
                
                if results_df.empty:
                    st.warning("⚠️ No data matches the selected filters.")
                else:
                    # Display results
                    st.header("📊 AWD Compliance Analysis Results")
                    st.info(f"📅 Analysis Period: {start_date} to {end_date} ({(end_date - start_date).days + 1} days)")
                    
                    # Key metrics
                    col1, col2, col3, col4, col5 = st.columns(5)
                    
                    with col1:
                        total_farmers = len(results_df)
                        st.metric("🧑‍🌾 Total Farmers", total_farmers)
                    
                    with col2:
                        valid_farmers = len(results_df[results_df['Valid_Farm'] == '1'])
                        st.metric("1 Valid Farms", f"{valid_farmers}/{total_farmers}")
                    
                    with col3:
                        payment_eligible = len(results_df[results_df['Final_Incentive_Amount'] > 0])
                        st.metric("💰 Getting Payment", payment_eligible)
                    
                    with col4:
                        total_incentive = results_df['Final_Incentive_Amount'].sum()
                        st.metric("💵 Total Incentive (₹)", f"{total_incentive:,.0f}")
                    
                    with col5:
                        # Calculate avg compliance only for valid farms
                        valid_farms_df = results_df[results_df['Valid_Farm'] == '1']
                        if len(valid_farms_df) > 0:
                            avg_compliance = valid_farms_df['Farm_Proportion_Passing'].mean()
                            st.metric("📈 Avg Compliance (Valid)", f"{avg_compliance:.1%}")
                        else:
                            st.metric("📈 Avg Compliance (Valid)", "N/A")
                    
                    # FIXED: Show the logic being used
                    st.info("🔧 **UPDATED LOGIC:** Farm compliance = (Pipes passing ÷ Pipes with ≥1 readings) × 100%. Single reading ≤200mm = compliant. Only Valid Farms (≥1 pipe with 1+ readings) included in averages.")
                    
                    # Main results table - FIXED TO INCLUDE ALL REQUIRED COLUMNS
                    st.subheader("📋 Farm Compliance Analysis")
                    
                    # Format display dataframe
                    display_df = results_df.copy()
                    display_df['Farm_Proportion_Passing'] = (display_df['Farm_Proportion_Passing'] * 100).round(1).astype(str) + '%'
                    # Remove rupee sign, keep only numeric value
                    display_df['Final_Incentive_Amount'] = display_df['Final_Incentive_Amount'].round(0).astype(int)
                    
                    # ALL REQUIRED COLUMNS - FIXED
                    required_columns = [
                        'Village', 'Farm_ID', 'Farmer_Name', 'Group', 'Valid_Farm', 'Total_Incentive_Acres', 
                        'All_Pipe_IDs', 'Pipes_Read', 'Pipes_Passing', 'Compliant_Pipe_IDs', 
                        'Non_Compliant_Pipe_IDs', 'Farm_Proportion_Passing', 'Eligible_Acres', 
                        'Final_Incentive_Amount'
                    ]
                    
                    st.dataframe(display_df[required_columns], use_container_width=True, height=400)
                    
                    # NEW: Home Screen Summary Table
                    st.subheader("📋 Farm Summary Overview")
                    
                    # Create home screen summary table with requested columns
                    home_summary_df = results_df.copy()
                    home_summary_df['Farm_Proportion_Passing'] = (home_summary_df['Farm_Proportion_Passing'] * 100).round(1).astype(str) + '%'
                    # Remove rupee sign, keep only numeric value
                    home_summary_df['Final_Incentive_Amount'] = home_summary_df['Final_Incentive_Amount'].round(0).astype(int)
                    
                    # Select and rename columns for home screen table
                    home_columns = [
                        'Village', 'Farm_ID', 'Farmer_Name', 'Group', 'Total_Incentive_Acres', 
                        'Valid_Farm', 'Valid_Pipes_Count', 'Pipes_Read', 'Pipes_Passing', 
                        'Farm_Proportion_Passing', 'Eligible_Acres', 'Final_Incentive_Amount'
                    ]
                    
                    # Rename columns to match user request
                    home_display_df = home_summary_df[home_columns].copy()
                    home_display_df = home_display_df.rename(columns={
                        'Valid_Farm': 'Valid farm',
                        'Valid_Pipes_Count': 'Valid pipes',
                        'Final_Incentive_Amount': 'Incentive_Amount'
                    })
                    
                    st.dataframe(home_display_df, use_container_width=True, height=400)
                    
                    # Summary by group
                    st.subheader("📊 Summary by Group")
                    
                    # Filter to only valid farms for compliance calculations
                    valid_farms_df = results_df[results_df['Valid_Farm'] == '1']
                    
                    summary_df = results_df.groupby('Group').agg({
                        'Farm_ID': 'count',
                        'Total_Assigned_Pipes': 'sum',
                        'Valid_Pipes_Count': 'sum',
                        'Pipes_Passing': 'sum',
                        'Final_Incentive_Amount': 'sum'
                    }).rename(columns={
                        'Farm_ID': 'Total_Farms',
                        'Total_Assigned_Pipes': 'Total_Assigned_Pipes',
                        'Valid_Pipes_Count': 'Valid_Pipes_Total',
                        'Pipes_Passing': 'Pipes_Passing_Total',
                        'Final_Incentive_Amount': 'Total_Incentive_Amount'
                    })
                    
                    # Add valid farms count and avg compliance (only for valid farms)
                    valid_farms_summary = valid_farms_df.groupby('Group').agg({
                        'Farm_ID': 'count',
                        'Farm_Proportion_Passing': 'mean'
                    }).rename(columns={
                        'Farm_ID': 'Valid_Farms',
                        'Farm_Proportion_Passing': 'Avg_Compliance_Rate_Valid_Farms'
                    })
                    
                    # Add compliant farms count (farms with 100% compliance)
                    compliant_farms_df = valid_farms_df[valid_farms_df['Farm_Proportion_Passing'] > 0]
                    compliant_farms_summary = compliant_farms_df.groupby('Group').agg({
                        'Farm_ID': 'count'
                    }).rename(columns={
                        'Farm_ID': 'Compliant_Farms'
                    })
                    
                    # Merge the summaries
                    summary_df = summary_df.merge(valid_farms_summary, left_index=True, right_index=True, how='left')
                    summary_df = summary_df.merge(compliant_farms_summary, left_index=True, right_index=True, how='left')
                    summary_df['Valid_Farms'] = summary_df['Valid_Farms'].fillna(0).astype(int)
                    summary_df['Compliant_Farms'] = summary_df['Compliant_Farms'].fillna(0).astype(int)
                    summary_df['Avg_Compliance_Rate_Valid_Farms'] = summary_df['Avg_Compliance_Rate_Valid_Farms'].fillna(0)
                    
                    # Calculate percentage of compliant farms
                    summary_df['Percent_Compliant_Farms'] = (summary_df['Compliant_Farms'] / summary_df['Valid_Farms'] * 100).fillna(0)
                    
                    # Reorder columns
                    summary_df = summary_df[['Total_Farms', 'Valid_Farms', 'Compliant_Farms', 'Percent_Compliant_Farms', 
                                           'Total_Assigned_Pipes', 'Valid_Pipes_Total', 'Pipes_Passing_Total', 
                                           'Avg_Compliance_Rate_Valid_Farms', 'Total_Incentive_Amount']]
                    
                    summary_df['Avg_Compliance_Rate_Valid_Farms'] = (summary_df['Avg_Compliance_Rate_Valid_Farms'] * 100).round(1).astype(str) + '%'
                    summary_df['Percent_Compliant_Farms'] = summary_df['Percent_Compliant_Farms'].round(1).astype(str) + '%'
                    # Remove rupee sign, keep only numeric value
                    summary_df['Total_Incentive_Amount'] = summary_df['Total_Incentive_Amount'].round(0).astype(int)
                    
                    st.dataframe(summary_df, use_container_width=True)
                    
                    # Weekly Analysis
                    with st.expander("📅 Weekly Breakdown Analysis", expanded=False):
                        st.subheader("📊 Week-by-Week Compliance")
                        weekly_results = analyze_weekly_compliance(master_df, water_df, farm_pipe_mapping, start_date, end_date)
                        
                        if weekly_results is not None and not weekly_results.empty:
                            # Apply same filters
                            if selected_groups:
                                weekly_results = weekly_results[weekly_results['Group'].isin(selected_groups)]
                            if selected_villages:
                                weekly_results = weekly_results[weekly_results['Village'].isin(selected_villages)]
                            
                            # Format weekly display
                            weekly_display = weekly_results.copy()
                            weekly_display['Proportion_Passing'] = (weekly_display['Proportion_Passing'] * 100).round(1).astype(str) + '%'
                            # Remove rupee sign, keep only numeric value
                            weekly_display['Final_Incentive_Amount'] = weekly_display['Final_Incentive_Amount'].round(0).astype(int)
                            weekly_display['Payment_Eligible'] = weekly_display['Payment_Eligible'].apply(lambda x: "1" if x else "0")
                            
                            # Select columns for display (FIXED: Include new columns)
                            weekly_display_cols = [
                                'Week', 'Week_Period', 'Village', 'Farm_ID', 'Farmer_Name', 'Group', 'Valid_Farm',
                                'Payment_Eligible', 'Total_Incentive_Acres', 'Assigned_Pipe_IDs', 
                                'Total_Assigned_Pipes', 'Valid_Pipes_Count', 'Pipes_Passing', 
                                'Proportion_Passing', 'Eligible_Acres', 'Final_Incentive_Amount'
                            ]
                            
                            st.dataframe(weekly_display[weekly_display_cols], use_container_width=True, height=400)
                            
                            # Weekly summary
                            weekly_summary = weekly_results.groupby('Week').agg({
                                'Farm_ID': 'count',
                                'Total_Assigned_Pipes': 'sum',
                                'Valid_Pipes_Count': 'sum',
                                'Pipes_Passing': 'sum',
                                'Proportion_Passing': 'mean',
                                'Final_Incentive_Amount': 'sum'
                            }).rename(columns={
                                'Farm_ID': 'Farms_Analyzed',
                                'Total_Assigned_Pipes': 'Total_Assigned',
                                'Valid_Pipes_Count': 'Valid_Pipes',
                                'Pipes_Passing': 'Pipes_Passing',
                                'Proportion_Passing': 'Avg_Compliance',
                                'Final_Incentive_Amount': 'Week_Total_Incentive'
                            })
                            
                            st.subheader("📈 Weekly Summary")
                            weekly_summary['Avg_Compliance'] = (weekly_summary['Avg_Compliance'] * 100).round(1).astype(str) + '%'
                            # Remove rupee sign, keep only numeric value
                            weekly_summary['Week_Total_Incentive'] = weekly_summary['Week_Total_Incentive'].round(0).astype(int)
                            st.dataframe(weekly_summary, use_container_width=True)
                            
                            # Download weekly data
                            weekly_csv = weekly_results.to_csv(index=False)
                            st.download_button(
                                "📥 Download Weekly Analysis",
                                weekly_csv,
                                f"awd_weekly_analysis_{start_date}_to_{end_date}.csv",
                                "text/csv",
                                use_container_width=True
                            )
                    
                    # Pipe Readings Detail Table
                    with st.expander("🔍 Detailed Pipe Readings Table", expanded=False):
                        st.subheader("📊 Pipe-by-Pipe Reading Details")
                        pipe_readings_df = create_pipe_readings_table(master_df, water_df, farm_pipe_mapping, start_date, end_date)
                        
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
                    
                    # New Pipe Summary Table
                    with st.expander("📊 Pipe Summary Table", expanded=False):
                        st.subheader("🔍 Individual Pipe Analysis")
                        pipe_summary_df = create_pipe_summary_table(master_df, water_df, farm_pipe_mapping, start_date, end_date)
                        
                        if pipe_summary_df is not None and not pipe_summary_df.empty:
                            # Apply same filters
                            if selected_groups:
                                pipe_summary_df = pipe_summary_df[pipe_summary_df['Group'].isin(selected_groups)]
                            if selected_villages:
                                # Filter by villages (need to get village info from master_df)
                                farm_village_map = master_df.set_index('Farm_ID')['Village'].to_dict()
                                pipe_summary_df['Village'] = pipe_summary_df['Farm_ID'].map(farm_village_map)
                                pipe_summary_df = pipe_summary_df[pipe_summary_df['Village'].isin(selected_villages)]
                                pipe_summary_df = pipe_summary_df.drop('Village', axis=1)  # Remove temporary column
                            
                            st.dataframe(pipe_summary_df, use_container_width=True, height=400)
                            
                            # Summary statistics for the pipe summary table
                            col1, col2, col3, col4 = st.columns(4)
                            
                            with col1:
                                total_pipes = len(pipe_summary_df)
                                st.metric("📏 Total Pipes", total_pipes)
                            
                            with col2:
                                compliant_pipes = len(pipe_summary_df[pipe_summary_df['Abiding_AWD_method'] == 1])
                                st.metric("1 Abiding AWD", f"{compliant_pipes}/{total_pipes}")
                            
                            with col3:
                                no_data_pipes = len(pipe_summary_df[pipe_summary_df['Abiding_AWD_method'] == 'No Data'])
                                st.metric("⚠️ No Data", no_data_pipes)
                            
                            with col4:
                                if total_pipes > 0:
                                    compliance_rate = (compliant_pipes / total_pipes * 100)
                                    st.metric("📈 AWD Compliance Rate", f"{compliance_rate:.1f}%")
                                else:
                                    st.metric("📈 AWD Compliance Rate", "N/A")
                            
                            # Download pipe summary table
                            pipe_summary_csv = pipe_summary_df.to_csv(index=False)
                            st.download_button(
                                "📊 Download Pipe Summary Table",
                                pipe_summary_csv,
                                f"awd_pipe_summary_{start_date}_to_{end_date}.csv",
                                "text/csv",
                                use_container_width=True
                            )
                        else:
                            st.warning("No pipe summary data available for the selected filters")
                    
                    # Village Summary
                    with st.expander("🏘️ Village-wise Performance", expanded=False):
                        st.subheader("📊 Village Summary")
                        village_summary = create_village_summary(results_df)
                        
                        if village_summary is not None and not village_summary.empty:
                            # Apply village filter
                            if selected_villages:
                                village_summary = village_summary[village_summary.index.isin(selected_villages)]
                            
                            # Format village summary
                            village_display = village_summary.copy()
                            village_display['Avg_Compliance_Rate_Valid_Farms'] = (village_display['Avg_Compliance_Rate_Valid_Farms'] * 100).round(1).astype(str) + '%'
                            # Remove rupee sign, keep only numeric value
                            village_display['Total_Village_Incentive'] = village_display['Total_Village_Incentive'].round(0).astype(int)
                            
                            st.dataframe(village_display, use_container_width=True)
                            
                            # Village performance chart
                            col1, col2 = st.columns(2)
                            with col1:
                                st.subheader("Village Compliance Rates (Valid Farms Only)")
                                chart_data = village_summary['Avg_Compliance_Rate_Valid_Farms'].reset_index()
                                st.bar_chart(chart_data.set_index('Village')['Avg_Compliance_Rate_Valid_Farms'])
                            
                            with col2:
                                st.subheader("Total Incentive by Village")
                                incentive_data = village_summary['Total_Village_Incentive'].reset_index()
                                st.bar_chart(incentive_data.set_index('Village')['Total_Village_Incentive'])
                    
                    # Payment Summary
                    with st.expander("💰 Payment Summary", expanded=False):
                        st.subheader("💵 Farms Receiving Payments")
                        payment_summary = create_payment_summary(results_df)
                        
                        if payment_summary is not None and not payment_summary.empty:
                            # Apply filters
                            if selected_groups:
                                payment_summary = payment_summary[payment_summary['Group'].isin(selected_groups)]
                            if selected_villages:
                                payment_summary = payment_summary[payment_summary['Village'].isin(selected_villages)]
                            
                            # Format payment summary
                            payment_display = payment_summary.copy()
                            payment_display['Farm_Proportion_Passing'] = (payment_display['Farm_Proportion_Passing'] * 100).round(1).astype(str) + '%'
                            # Remove rupee sign, keep only numeric value
                            payment_display['Final_Incentive_Amount'] = payment_display['Final_Incentive_Amount'].round(0).astype(int)
                            
                            st.dataframe(payment_display, use_container_width=True)
                            
                            # Payment statistics
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("💰 Farms Getting Paid", len(payment_summary))
                            with col2:
                                st.metric("📊 Avg Payment (₹)", f"{payment_summary['Final_Incentive_Amount'].mean():,.0f}")
                            with col3:
                                st.metric("🏆 Highest Payment (₹)", f"{payment_summary['Final_Incentive_Amount'].max():,.0f}")
                            
                            # Download payment summary
                            payment_csv = payment_summary.to_csv(index=False)
                            st.download_button(
                                "💰 Download Payment Summary",
                                payment_csv,
                                f"awd_payment_summary_{start_date}_to_{end_date}.csv",
                                "text/csv",
                                use_container_width=True
                            )
                        else:
                            st.info("No farms are receiving payments with the current filters")
                    
                    # Download options
                    st.subheader("📥 Download Options")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        csv = results_df.to_csv(index=False)
                        st.download_button(
                            "📊 Download Farm Analysis",
                            csv,
                            f"awd_farm_analysis_{start_date}_to_{end_date}.csv",
                            "text/csv",
                            use_container_width=True
                        )
                    
                    with col2:
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
                        else:
                            st.button("💰 No Payment Records", disabled=True, use_container_width=True)
                    
                    with col3:
                        summary_csv = summary_df.to_csv()
                        st.download_button(
                            "📋 Download Group Summary",
                            summary_csv,
                            f"awd_group_summary_{start_date}_to_{end_date}.csv",
                            "text/csv",
                            use_container_width=True
                        )
                    
                    # Detailed analysis for top farms
                    with st.expander("🔍 Detailed Farm Analysis", expanded=False):
                        st.subheader("🎯 Top Performing Farms")
                        
                        # Sort by compliance rate and show top farms
                        top_farms = results_df.nlargest(10, 'Farm_Proportion_Passing')
                        
                        for _, row in top_farms.iterrows():
                            st.write(f"**🏆 {row['Farm_ID']} - {row['Farmer_Name']} ({row['Village']})**")
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.write(f"**Group:** {row['Group']}")
                                st.write(f"**Total Acres:** {row['Total_Incentive_Acres']}")
                                st.write(f"**Assigned Pipes:** {row['All_Pipe_IDs']}")
                            
                            with col2:
                                st.write(f"**Compliance Rate:** {row['Farm_Proportion_Passing']:.1%}")
                                st.write(f"**Valid Pipes:** {row['Valid_Pipes_Count']}/{row['Total_Assigned_Pipes']}")  # FIXED
                                st.write(f"**Pipes Passing:** {row['Pipes_Passing']}")
                                st.write(f"**Eligible Acres:** {row['Eligible_Acres']}")
                            
                            with col3:
                                st.write(f"**Final Incentive (₹):** {row['Final_Incentive_Amount']:,.0f}")
                                if row['Non_Compliant_Pipe_IDs'] != 'None':
                                    st.error(f"**Failed Pipes:** {row['Non_Compliant_Pipe_IDs']}")
                                else:
                                    st.success("**All valid pipes compliant!**")
                            
                            # Show pipe reading details
                            st.write("**📊 Pipe Reading Details:**")
                            st.code(row['Pipes_Read'], language=None)
                            
                            st.markdown("---")
                        
                        # Poor performing farms
                        st.subheader("⚠️ Farms Needing Attention")
                        poor_farms = results_df[results_df['Farm_Proportion_Passing'] < 0.5].nsmallest(5, 'Farm_Proportion_Passing')
                        
                        if not poor_farms.empty:
                            for _, row in poor_farms.iterrows():
                                st.write(f"**⚠️ {row['Farm_ID']} - {row['Farmer_Name']} ({row['Village']})**")
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.write(f"Compliance Rate: {row['Farm_Proportion_Passing']:.1%}")
                                    st.write(f"Group: {row['Group']}")
                                    st.write(f"Valid Pipes: {row['Valid_Pipes_Count']}/{row['Total_Assigned_Pipes']}")  # FIXED
                                with col2:
                                    st.write(f"Failed Pipes: {row['Non_Compliant_Pipe_IDs']}")
                                    st.write(f"Potential Loss (₹): {(row['Total_Incentive_Acres'] * 300) - row['Final_Incentive_Amount']:,.0f}")
                                st.markdown("---")
                        else:
                            st.success("🎉 All farms are performing well (≥50% compliance)!")
                        
                        # Farm search functionality
                        st.subheader("🔎 Search Specific Farm")
                        search_farm = st.selectbox(
                            "Select a farm to view details:",
                            options=[''] + results_df['Farm_ID'].tolist(),
                            index=0
                        )
                        
                        if search_farm:
                            farm_detail = results_df[results_df['Farm_ID'] == search_farm].iloc[0]
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.info(f"""
                                **Farm Details:**
                                - **ID:** {farm_detail['Farm_ID']}
                                - **Farmer:** {farm_detail['Farmer_Name']}
                                - **Village:** {farm_detail['Village']}
                                - **Group:** {farm_detail['Group']}
                                - **Total Acres:** {farm_detail['Total_Incentive_Acres']}
                                """)
                            
                            with col2:
                                st.info(f"""
                                **Performance:**
                                - **Compliance Rate:** {farm_detail['Farm_Proportion_Passing']:.1%}
                                - **Valid Pipes:** {farm_detail['Valid_Pipes_Count']}/{farm_detail['Total_Assigned_Pipes']}
                                - **Pipes Passing:** {farm_detail['Pipes_Passing']}
                                - **Eligible Acres:** {farm_detail['Eligible_Acres']}
                                - **Final Incentive (₹):** {farm_detail['Final_Incentive_Amount']:,.0f}
                                """)
                            
                            st.subheader("📊 Pipe Reading Details")
                            st.code(farm_detail['Pipes_Read'], language=None)
                            
                            if farm_detail['Non_Compliant_Pipe_IDs'] != 'None':
                                st.error(f"⚠️ Non-compliant pipes: {farm_detail['Non_Compliant_Pipe_IDs']}")
                            else:
                                st.success("1 All valid pipes are compliant!")
                    
                    # Data Quality Analysis
                    with st.expander("📈 Data Quality & Coverage Analysis", expanded=False):
                        st.subheader("📊 Data Coverage Statistics")
                        
                        # Filter water data to date range for coverage analysis
                        water_df_filtered = water_df[
                            (water_df['Date'].dt.date >= start_date) & 
                            (water_df['Date'].dt.date <= end_date)
                        ].copy()
                        
                        # Calculate coverage metrics (FIXED)
                        total_farms = len(master_df)
                        farms_with_valid_pipes = len(results_df[results_df['Valid_Pipes_Count'] > 0])
                        total_assigned_pipes = results_df['Total_Assigned_Pipes'].sum()
                        total_valid_pipes = results_df['Valid_Pipes_Count'].sum()
                        pipes_with_data = water_df_filtered['Pipe_ID'].nunique()
                        
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("🏢 Farms w/ Valid Pipes", f"{farms_with_valid_pipes}/{total_farms}", f"{farms_with_valid_pipes/total_farms:.1%}")
                        with col2:
                            st.metric("📏 Valid Pipe Rate", f"{total_valid_pipes}/{total_assigned_pipes}", f"{total_valid_pipes/total_assigned_pipes:.1%}")
                        with col3:
                            total_readings = len(water_df_filtered)
                            st.metric("📊 Total Readings", total_readings)
                        with col4:
                            days_covered = (end_date - start_date).days + 1
                            avg_readings_per_day = total_readings / days_covered if days_covered > 0 else 0
                            st.metric("📅 Avg Daily Readings", f"{avg_readings_per_day:.1f}")
                        
                        # Missing data analysis (FIXED)
                        st.subheader("⚠️ Missing Data Analysis")
                        
                        # Farms with no valid pipes
                        farms_no_valid_pipes = results_df[results_df['Valid_Pipes_Count'] == 0]
                        if not farms_no_valid_pipes.empty:
                            st.error(f"**{len(farms_no_valid_pipes)} farms have NO valid pipes (≥2 readings):**")
                            st.dataframe(farms_no_valid_pipes[['Village', 'Farm_ID', 'Farmer_Name', 'Group', 'All_Pipe_IDs', 'Total_Assigned_Pipes']], use_container_width=True)
                        else:
                            st.success("1 All farms have at least one valid pipe!")
                        
                        # Farms with partial data
                        farms_partial_data = results_df[
                            (results_df['Valid_Pipes_Count'] > 0) & 
                            (results_df['Farm_Proportion_Passing'] < 1.0) & 
                            (results_df['Non_Compliant_Pipe_IDs'] != 'None')
                        ]
                        
                        if not farms_partial_data.empty:
                            st.warning(f"**{len(farms_partial_data)} farms have incomplete/non-compliant data:**")
                            partial_display = farms_partial_data[['Village', 'Farm_ID', 'Farmer_Name', 'Group', 'Valid_Pipes_Count', 'Total_Assigned_Pipes', 'Farm_Proportion_Passing', 'Non_Compliant_Pipe_IDs']].copy()
                            partial_display['Farm_Proportion_Passing'] = (partial_display['Farm_Proportion_Passing'] * 100).round(1).astype(str) + '%'
                            st.dataframe(partial_display, use_container_width=True)
                        
                        # Daily reading distribution
                        st.subheader("📅 Daily Reading Distribution")
                        daily_readings = water_df_filtered.groupby(water_df_filtered['Date'].dt.date).size().reset_index()
                        daily_readings.columns = ['Date', 'Number_of_Readings']
                        
                        # Create a simple chart
                        st.line_chart(daily_readings.set_index('Date')['Number_of_Readings'])
                        
                        # Show days with low readings
                        avg_daily = daily_readings['Number_of_Readings'].mean()
                        low_reading_days = daily_readings[daily_readings['Number_of_Readings'] < avg_daily * 0.5]
                        
                        if not low_reading_days.empty:
                            st.warning("⚠️ Days with unusually low readings:")
                            st.dataframe(low_reading_days, use_container_width=True)
                        
                        # Group performance comparison (FIXED)
                        st.subheader("👥 Group Performance Comparison")
                        group_performance = results_df.groupby('Group').agg({
                            'Farm_ID': 'count',
                            'Total_Assigned_Pipes': 'sum',
                            'Valid_Pipes_Count': 'sum',
                            'Pipes_Passing': 'sum',
                            'Farm_Proportion_Passing': ['mean', 'std'],
                            'Final_Incentive_Amount': ['sum', 'mean']
                        }).round(2)
                        
                        # Flatten column names
                        group_performance.columns = ['Total_Farms', 'Total_Assigned', 'Total_Valid', 'Total_Passing', 'Avg_Compliance', 'Compliance_StdDev', 'Total_Incentive', 'Avg_Incentive_per_Farm']
                        group_performance['Avg_Compliance'] = (group_performance['Avg_Compliance'] * 100).round(1).astype(str) + '%'
                        group_performance['Compliance_StdDev'] = (group_performance['Compliance_StdDev'] * 100).round(1).astype(str) + '%'
                        # Remove rupee sign, keep only numeric value
                        group_performance['Total_Incentive'] = group_performance['Total_Incentive'].round(0).astype(int)
                        group_performance['Avg_Incentive_per_Farm'] = group_performance['Avg_Incentive_per_Farm'].round(0).astype(int)
                        
                        st.dataframe(group_performance, use_container_width=True)
            else:
                st.error("0 No results generated. Please check your data.")

else:
    if master_df is None or farm_pipe_mapping is None:
        st.info("🔗 Please configure Google Sheets connection to load master data with pipe mapping")
    if water_df is None:
        st.info("📁 Please upload water level data to begin analysis")

# Information sections (UPDATED)
with st.expander("📏 Compliance Criteria (UPDATED)", expanded=False):
    st.markdown("""
    ### 1 **UPDATED** Pipe Compliance Requirements:
    
    **For Multiple Readings (≥2 measurements):**
    1. **All readings ≤ 200mm**
    2. **At least one reading ≤ 100mm** 
    3. **~~No gap constraint~~** 0 (REMOVED)
    
    **🆕 For Single Reading (1 measurement):**
    1. **Reading ≤ 200mm** (automatically compliant)
    
    ### 🆕 **UPDATED** Valid Farm & Pipe Definition:
    - **Valid Pipe**: Pipe with ≥1 reading in the period
    - **Valid Farm**: Farm with ≥1 pipe having ≥1 reading in the period
    - **Display**: 1 for valid farms/pipes, 0 for invalid
    - **Compliance Averages**: Calculated ONLY on valid farms
    
    ### 💰 **UPDATED** Payment Logic:
    - **Payment Eligible**: Only "A Complied" group
    - **Farm Compliance**: **(Compliant Pipes ÷ Valid Pipes)** ← UPDATED
    - **Valid Pipes**: Pipes with ≥1 reading in period ← UPDATED  
    - **Eligible Acres**: Farm Compliance × Total Incentive Acres
    - **Final Incentive**: Eligible Acres × ₹300 (only for A Complied group)
    
    ### 🔧 **Key Updates**:
    **1. Single Reading Rule**: Single reading ≤200mm is now compliant  
    **2. Valid Pipe Definition**: Changed from ≥2 to ≥1 readings  
    **3. Compliance Calculation**: Compliant Pipes ÷ **Valid Pipes (≥1 readings)**  
    **4. Valid Farm Filter**: Only farms with ≥1 valid pipe shown as valid
    
    **Example**: Farm with 5 assigned pipes, 3 pipes have ≥1 reading, 2 compliant  
    - **Compliance**: 2/3 = 66.7% 1
    - **Valid Farm**: 1 (has valid pipes)
    - **Included in averages**: Yes
    """)

with st.expander("👥 Group Assignment Logic", expanded=False):
    st.markdown("""
    ### 🔄 Processing Steps:
    1. **Filter**: Keep only farms where "AWD Study" = 1
    2. **Assign Groups**: Based on group flags and compliance status
    3. **Remove**: All "Unassigned" and "No Group" farms
    4. **Extract Pipes**: Read pipe codes 1-5 from master data
    5. **Map Water Data**: Link water readings to farms via pipe assignments
    
    ### 📊 Final Groups:
    - **A Complied** → Payment Eligible 1
    - **A Non Complied** → No Payment 0
    - **B Complied** → No Payment 0
    - **B Non Complied** → No Payment 0
    - **C Complied** → No Payment 0
    - **C Non Complied** → No Payment 0
    """)

with st.expander("📊 Analysis Features & Tables (UPDATED)", expanded=False):
    st.markdown("""
    ### 🎯 **Main Farm Analysis Table** (FIXED):
    - **Village, Farm_ID, Farmer_Name, Group**: Basic farm information
    - **Total_Incentive_Acres**: Acres eligible for incentive  
    - **All_Pipe_IDs**: All pipes assigned to farm ← ADDED
    - **Pipes_Read**: Detailed readings for each pipe ← ADDED
    - **Pipes_Passing**: Pipes meeting compliance criteria
    - **Compliant_Pipe_IDs**: IDs of compliant pipes ← ADDED
    - **Non_Compliant_Pipe_IDs**: IDs of non-compliant pipes ← ADDED
    - **Farm_Proportion_Passing**: **FIXED** = Pipes_Passing ÷ Valid_Pipes_Count
    - **Eligible_Acres, Final_Incentive_Amount**: Payment calculations
    
    ### 📅 **Weekly Breakdown Analysis** (FIXED):
    - Week-by-week compliance using fixed logic
    - Shows Valid_Pipes_Count vs Total_Assigned_Pipes
    - Comments include valid pipe ratios
    
    ### 🔍 **Detailed Pipe Readings Table** (UPDATED):
    - Comments now distinguish between insufficient data vs non-compliance
    - Now evaluates pipes with ≥1 readings for compliance (including single readings)
    
    ### 📊 **Pipe Summary Table** (UPDATED):
    - **Farm_ID, Pipe_ID**: Individual pipe identification
    - **Farm_Valid**: Whether farm has ≥1 pipe with 1+ readings
    - **Valid_pipe**: Whether individual pipe has ≥1 reading
    - **Farmer_Name, Group**: Farm details
    - **Abiding_AWD_method**: 1/0 compliance status (1=compliant, 0=non-compliant)
    - **Reading_1_mm to Reading_6_mm**: Water level values (up to 6 readings)
    - **Reading_1_Date to Reading_6_Date**: Corresponding dates
    - **Total_number_of_readings**: Count of readings for this pipe
    
    ### 🏘️ **Village Summary** (UPDATED):
    - Now includes Total_Valid_Pipes and Total_Assigned_Pipes
    - Compliance rates based on fixed logic
    
    ### 💰 **Payment Summary** (UPDATED):
    - Shows Valid_Pipes_Count for transparency
    - All calculations use fixed compliance logic
    """)

with st.expander("🎯 Dynamic Date Range System", expanded=False):
    st.markdown("""
    ### 📅 **Flexible Analysis Period**:
    - **No Fixed Weeks**: Select any start and end date
    - **Day 1 Logic**: Your start date becomes "Day 1" of analysis
    - **Full Period Analysis**: Main table analyzes entire selected range
    - **Weekly Breakdown**: Optional week-by-week view within your range
    
    ### ⏰ **How It Works**:
    1. **Select Date Range**: Choose any period (days, weeks, months)
    2. **Farm Analysis**: Each farm analyzed across entire period
    3. **Compliance Check**: All readings within period used for compliance
    4. **Weekly Optional**: Additional breakdown by 7-day weeks if needed
    
    ### 🎨 **Use Cases**:
    - **Short Term**: Analyze specific problematic days/weeks
    - **Long Term**: Season-long compliance assessment  
    - **Custom Periods**: Match your field visit schedules
    - **Flexible Reporting**: Any reporting period needed
    """)

st.markdown("---")
st.markdown("*AWD Compliance Analysis Dashboard v20.0 - **SINGLE READING COMPLIANCE** - Single Reading ≤200mm = Compliant & Updated Pipe Summary Table*")