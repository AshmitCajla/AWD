
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import io

# Configure Streamlit page
st.set_page_config(
    page_title="AWD Compliance Analysis",
    page_icon="🌾",
    layout="wide"
)

st.title("🌾 AWD Compliance Analysis Dashboard")
st.markdown("---")

# Define week periods
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

@st.cache_data
def load_sample_data():
    """Create sample data for testing"""
    # Sample master data
    master_data = {
        'Farm_ID': ['MA_BH_PA_NAVJO_PLT_10028_A', 'MA_BH_PA_NAVJO_PLT_10028_B', 'MA_BH_PA_AJIT_PLT_10000'],
        'Farmer_Name': ['Navjot Singh', 'Navjot Singh', 'Ajit Singh'],
        'Village': ['Manjal Khurd', 'Manjal Khurd', 'Manjal Khurd'],
        'Acres': [7.0, 4.0, 12.0],
        'Group': ['A', 'B', 'A']
    }
    
    # Sample water level data
    water_data = {
        'Date': ['2025-06-17', '2025-06-20', '2025-06-17', '2025-06-19', '2025-06-18', '2025-06-21'],
        'Farm_ID': ['MA_BH_PA_NAVJO_PLT_10028_A', 'MA_BH_PA_NAVJO_PLT_10028_A', 
                   'MA_BH_PA_NAVJO_PLT_10028_B', 'MA_BH_PA_NAVJO_PLT_10028_B',
                   'MA_BH_PA_AJIT_PLT_10000', 'MA_BH_PA_AJIT_PLT_10000'],
        'Pipe_ID': ['10028A1', '10028A1', '10028B1', '10028B1', '100001', '100001'],
        'Water_Level_mm': [180, 90, 250, 120, 150, 80]
    }
    
    master_df = pd.DataFrame(master_data)
    water_df = pd.DataFrame(water_data)
    water_df['Date'] = pd.to_datetime(water_df['Date'])
    
    return master_df, water_df

def process_uploaded_file(uploaded_file, file_type):
    """Process uploaded files with error handling"""
    try:
        if uploaded_file.name.endswith('.xlsx'):
            if file_type == 'master':
                df = pd.read_excel(uploaded_file, sheet_name=0)  # Use first sheet
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

def convert_to_binary(series):
    """Convert any format to binary (0/1) with robust handling"""
    try:
        # Convert to string, strip whitespace, and handle NaN/None
        s = series.astype(str).str.strip().str.upper().replace(['NAN', 'NA', 'NONE', ''], '0')
        
        # Replace common values
        mapping = {
            '1': 1, '1.0': 1, 'YES': 1, 'Y': 1, 'TRUE': 1, 'T': 1, 'X': 1,
            '0': 0, '0.0': 0, 'NO': 0, 'N': 0, 'FALSE': 0, 'F': 0
        }
        
        return s.replace(mapping).fillna(0).astype(int)
    except Exception as e:
        st.error(f"Error converting to binary: {str(e)}")
        return pd.Series([0] * len(series), index=series.index)

def clean_master_data(df):
    """Robust cleaning for master data with better error handling"""
    try:
        # Create a copy to avoid modifying original
        df_clean = df.copy()
        
        # Find columns using flexible matching
        farm_id_col = find_column(df_clean, ['farm id', 'farm_id', 'farmid'], 'Farm_ID')
        farmer_name_col = find_column(df_clean, ['farmer name', 'farmer_name'], 'Farmer_Name')
        village_col = find_column(df_clean, ['village'], 'Village')
        acres_col = find_column(df_clean, ['acres', 'acreage', 'incentive acres'], 'Acres')
        
        # Group columns - specific to your data structure
        group_a_col = find_column(df_clean, ['group a - treatment', 'awd study - group a'])
        group_b_col = find_column(df_clean, ['group b - training', 'awd study - group b'])
        group_c_col = find_column(df_clean, ['group c - control', 'awd study - group c'])
        
        # Debug output
        debug_info = {
            "Farm ID Column": farm_id_col,
            "Farmer Name Column": farmer_name_col,
            "Village Column": village_col,
            "Acres Column": acres_col,
            "Group A Column": group_a_col,
            "Group B Column": group_b_col,
            "Group C Column": group_c_col
        }
        
        # st.sidebar.subheader("🔍 Detected Columns")
        # st.sidebar.json(debug_info)
        
        # Standardize column names with null checks
        df_clean['Farm_ID'] = df_clean[farm_id_col].astype(str).fillna("Unknown_Farm") if farm_id_col else "Unknown_Farm"
        df_clean['Farmer_Name'] = df_clean[farmer_name_col].astype(str).fillna("Unknown_Farmer") if farmer_name_col else "Unknown_Farmer"
        df_clean['Village'] = df_clean[village_col].astype(str).fillna("Unknown_Village") if village_col else "Unknown_Village"
        
        # Handle acres - convert to numeric with better error handling
        if acres_col:
            df_clean['Acres'] = pd.to_numeric(df_clean[acres_col], errors='coerce')
            df_clean['Acres'] = df_clean['Acres'].fillna(0).clip(lower=0)  # Ensure non-negative
        else:
            df_clean['Acres'] = 0
        
        # Handle group assignments with null checks
        if group_a_col:
            df_clean[group_a_col] = df_clean[group_a_col].fillna(0)
            df_clean['Group_A'] = convert_to_binary(df_clean[group_a_col])
        else:
            df_clean['Group_A'] = 0
            
        if group_b_col:
            df_clean[group_b_col] = df_clean[group_b_col].fillna(0)
            df_clean['Group_B'] = convert_to_binary(df_clean[group_b_col])
        else:
            df_clean['Group_B'] = 0
            
        if group_c_col:
            df_clean[group_c_col] = df_clean[group_c_col].fillna(0)
            df_clean['Group_C'] = convert_to_binary(df_clean[group_c_col])
        else:
            df_clean['Group_C'] = 0
        
        # Assign group based on flags with priority (A > B > C)
        def assign_group(row):
            if row['Group_A'] == 1:
                return 'A'
            elif row['Group_B'] == 1:
                return 'B'
            elif row['Group_C'] == 1:
                return 'C'
            return 'Unknown'
        
        df_clean['Group'] = df_clean.apply(assign_group, axis=1)
        
        # Keep only essential columns
        return df_clean[['Farm_ID', 'Farmer_Name', 'Village', 'Acres', 'Group']].dropna(subset=['Farm_ID'])
        
    except Exception as e:
        st.error(f"Error cleaning master data: {str(e)}")
        st.error("Please check your input data format and try again.")
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
        
        # Debug output
        debug_info = {
            "Date Column": date_col,
            "Farm ID Column": farm_id_col,
            "Pipe ID Column": pipe_id_col,
            "Water Level Column": water_col
        }
        
        # st.sidebar.subheader("💧 Detected Water Columns")
        # st.sidebar.json(debug_info)
        
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

def assign_week(date):
    """Assign week number based on date"""
    if pd.isna(date):
        return None
    
    date_obj = date.date() if hasattr(date, 'date') else date
    
    for week_num, _, _, start_date, end_date in WEEK_PERIODS:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        if start <= date_obj <= end:
            return week_num
    return None

def analyze_compliance(master_df, water_df):
    """Analyze compliance for all farms and generate both payment and monitoring tables"""
    try:
        # Add week to water data
        water_df['Week'] = water_df['Date'].apply(assign_week)
        water_df = water_df.dropna(subset=['Week'])
        
        # Merge data
        merged_df = water_df.merge(master_df, on='Farm_ID', how='inner')
        
        payment_results = []
        monitoring_results = []
        
        # Group by Farm and Week
        for (farm_id, week), group_data in merged_df.groupby(['Farm_ID', 'Week']):
            farm_info = group_data.iloc[0]
            week_num = int(week)
            
            # Get week display string
            week_display = next((f"{start} to {end}" for w, start, end, _, _ in WEEK_PERIODS if w == week_num), "")
            
            # Analyze each pipe
            pipe_summaries = []
            comments = []
            total_pipes = 0
            compliant_pipes = 0
            
            for pipe_id, pipe_data in group_data.groupby('Pipe_ID'):
                if pd.isna(pipe_id) or pipe_id == "Unknown_Pipe":
                    continue
                    
                total_pipes += 1
                pipe_data = pipe_data.sort_values('Date')
                measurements = pipe_data['Water_Level_mm'].tolist()
                dates = pipe_data['Date'].dt.strftime('%m/%d').tolist()
                
                # Create measurement summary
                measurement_pairs = []
                for d, m in zip(dates, measurements):
                    measurement_pairs.append(f"{d}({int(m)}mm)")
                
                # Calculate gap in days if we have multiple dates
                gap_str = ""
                gap_days = 0
                if len(pipe_data) >= 2:
                    date_objs = sorted(pipe_data['Date'])
                    gap_days = (date_objs[-1] - date_objs[0]).days
                    gap_str = f" [{gap_days}d gap]"
                
                # Check compliance
                compliance_status = "❌"
                if len(measurements) >= 2:
                    all_below_200 = all(m <= 200 for m in measurements)
                    any_below_100 = any(m <= 100 for m in measurements)
                    sufficient_gap = gap_days >= 3
                    
                    if all_below_200 and any_below_100 and sufficient_gap:
                        compliance_status = "✅"
                        compliant_pipes += 1
                    else:
                        # Add specific comments
                        if not all_below_200:
                            comments.append(f"P{pipe_id}: >200mm reading")
                        elif not any_below_100:
                            comments.append(f"P{pipe_id}: no <100mm reading")
                        elif not sufficient_gap:
                            comments.append(f"P{pipe_id}: insufficient gap")
                else:
                    if len(measurements) == 0:
                        comments.append(f"P{pipe_id}: no measurements")
                    else:
                        comments.append(f"P{pipe_id}: only 1 measurement")
                
                # Create pipe summary
                measurements_str = ", ".join(measurement_pairs)
                pipe_summary = f"P{pipe_id}: {measurements_str}{gap_str} {compliance_status}"
                pipe_summaries.append(pipe_summary)
            
            # Join pipe summaries
            pipe_details_str = " | ".join(pipe_summaries)
            comments_str = "; ".join(comments) if comments else "All compliant"
            
            # Calculate metrics for payment table
            if total_pipes > 0:
                compliance_rate = compliant_pipes / total_pipes
                eligible_acres = compliance_rate * farm_info['Acres']
                payment = eligible_acres * 300
            else:
                compliance_rate = 0
                eligible_acres = 0
                payment = 0
            
            # Add to payment results
            payment_results.append({
                'Week': week_num,
                'Village': farm_info['Village'],
                'Farm_ID': farm_id,
                'Farmer_Name': farm_info['Farmer_Name'],
                'Group': farm_info['Group'],
                'Total_Acres': farm_info['Acres'],
                'Total_Pipes': total_pipes,
                'Compliant_Pipes': compliant_pipes,
                'Compliance_Rate': compliance_rate,
                'Eligible_Acres': eligible_acres,
                'Payment_Rs': payment
            })
            
            # Add to monitoring results
            monitoring_results.append({
                'Week': week_display,
                'Village': farm_info['Village'],
                'Farmer_ID': farm_id,
                'Farmer_Name': farm_info['Farmer_Name'],
                'Group': farm_info['Group'],
                'Acres': farm_info['Acres'],
                'Pipe_Details': pipe_details_str,
                'Comments': comments_str
            })
        
        return (
            pd.DataFrame(payment_results), 
            pd.DataFrame(monitoring_results)
        )
        
    except Exception as e:
        st.error(f"Error analyzing compliance: {str(e)}")
        return None, None

# Main App Interface
st.sidebar.header("📁 Data Upload")

# Option to use sample data
use_sample = st.sidebar.checkbox("Use Sample Data for Testing", value=True)

if use_sample:
    st.info("Using sample data for demonstration")
    master_df, water_df = load_sample_data()
    st.sidebar.success("✅ Sample data loaded")
else:
    # File uploads
    master_file = st.sidebar.file_uploader(
        "Upload Master Farm Data",
        type=['csv', 'xlsx'],
        help="Upload Excel/CSV file with farm details"
    )
    
    water_file = st.sidebar.file_uploader(
        "Upload Water Level Data", 
        type=['csv', 'xlsx'],
        help="Upload Excel/CSV file with water measurements"
    )
    
    master_df = None
    water_df = None
    
    if master_file:
        raw_master = process_uploaded_file(master_file, 'master')
        if raw_master is not None:
            master_df = clean_master_data(raw_master)
            if master_df is not None:
                st.sidebar.success(f"✅ Master data processed: {len(master_df)} farms")
    
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
        st.subheader("Master Data")
        st.dataframe(master_df.head(), use_container_width=True)
    
    with col2:
        st.subheader("Water Level Data")
        st.dataframe(water_df.head(), use_container_width=True)
    
    # Filters
    st.sidebar.header("🔍 Filters")
    
    # Week filter
    available_weeks = list(range(1, 19))
    selected_weeks = st.sidebar.multiselect(
        "Select Weeks",
        available_weeks,
        default=available_weeks[:4]
    )
    
    # Group filter
    available_groups = sorted(master_df['Group'].unique())
    selected_groups = st.sidebar.multiselect(
        "Select Groups",
        available_groups,
        default=available_groups
    )
    
    # Generate Analysis
    if st.button("📊 Analyze Compliance", type="primary", use_container_width=True):
        with st.spinner("Analyzing compliance..."):
            payment_df, monitoring_df = analyze_compliance(master_df, water_df)
        
        if payment_df is not None and monitoring_df is not None and not payment_df.empty:
            # Apply filters
            if selected_weeks:
                payment_df = payment_df[payment_df['Week'].isin(selected_weeks)]
                # Fixed monitoring filter to properly match week numbers
                monitoring_df = monitoring_df[monitoring_df['Week'].apply(lambda x: 
                    any(str(w) in x for w in selected_weeks) if isinstance(x, str) else False)]
            if selected_groups:
                payment_df = payment_df[payment_df['Group'].isin(selected_groups)]
                monitoring_df = monitoring_df[monitoring_df['Group'].isin(selected_groups)]
            
            # Display payment results
            st.header("💰 Payment Analysis Results")
            
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Farmers", payment_df['Farm_ID'].nunique())
            
            with col2:
                avg_compliance = payment_df['Compliance_Rate'].mean()
                st.metric("Avg Compliance", f"{avg_compliance:.1%}")
            
            with col3:
                total_payment = payment_df['Payment_Rs'].sum()
                st.metric("Total Payment", f"₹{total_payment:,.0f}")
            
            with col4:
                total_acres = payment_df['Eligible_Acres'].sum()
                st.metric("Eligible Acres", f"{total_acres:.1f}")
            
            # Detailed payment table
            st.subheader("Payment Details")
            
            # Format for display
            display_df = payment_df.copy()
            display_df['Compliance_Rate'] = display_df['Compliance_Rate'].apply(lambda x: f"{x:.1%}")
            display_df['Eligible_Acres'] = display_df['Eligible_Acres'].round(1)
            display_df['Payment_Rs'] = display_df['Payment_Rs'].apply(lambda x: f"₹{x:,.0f}")
            
            st.dataframe(display_df, use_container_width=True)
            
            # Download option for payment data
            payment_csv = payment_df.to_csv(index=False)
            st.download_button(
                "📥 Download Payment Results",
                payment_csv,
                "awd_payment_results.csv",
                "text/csv",
                use_container_width=True
            )
            
            # Display monitoring table
            st.header("📋 Field Monitoring Report")
            st.caption("Each row shows compliance details for one farmer during one week")
            
            # Display monitoring table with better formatting
            if not monitoring_df.empty:
                st.dataframe(monitoring_df, use_container_width=True)
                
                # Download option for monitoring report
                monitoring_csv = monitoring_df.to_csv(index=False)
                st.download_button(
                    "📥 Download Monitoring Report",
                    monitoring_csv,
                    "awd_monitoring_report.csv",
                    "text/csv",
                    use_container_width=True
                )
            else:
                st.warning("No monitoring data to display after applying filters.")
        
        else:
            st.warning("No results generated. Please check your data.")

else:
    st.info("👆 Please upload data files or enable sample data to begin analysis.")
    
    # Show expected format
    st.subheader("📋 Expected Data Format")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Master Data should contain:**")
        st.code("""
- Farm ID column
- Farmer Name column  
- Village column
- Acres column (for incentives)
- Group columns (A, B, C)
        """)
    
    with col2:
        st.write("**Water Level Data should contain:**")
        st.code("""
- Date column
- Farm ID column
- Pipe ID/Code column
- Water Level (mm) column
        """)

# Show week schedule
with st.expander("📅 Study Week Schedule"):
    week_schedule = pd.DataFrame(WEEK_PERIODS, columns=['Week', 'Start', 'End', 'Start_ISO', 'End_ISO'])
    st.dataframe(week_schedule[['Week', 'Start', 'End']], use_container_width=True)

st.markdown("---")
st.markdown("*AWD Compliance Analysis Dashboard v4.1*")