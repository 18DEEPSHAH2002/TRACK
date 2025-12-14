import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re

# Page Config
st.set_page_config(page_title="District Dashboard", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS for compact layout
st.markdown("""
    <style>
    /* Remove default padding and margins */
    .main {
        padding-top: 0.5rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    
    /* Compact headers */
    h1, h2, h3 {
        margin: 0;
        padding: 0.25rem 0;
    }
    
    /* Compact spacing for metric containers */
    [data-testid="metric-container"] {
        margin: 0 !important;
        padding: 0.5rem !important;
    }
    
    /* Compact dataframe styling */
    .dataframe {
        font-size: 12px;
    }
    
    /* Custom card styling */
    .dashboard-card {
        padding: 0.75rem;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        background-color: #f8f9fa;
    }
    
    .header-text {
        font-size: 14px;
        font-weight: 600;
        margin: 0.25rem 0;
    }
    
    .metric-text {
        font-size: 13px;
        margin: 0.1rem 0;
    }
    
    .error-box {
        background-color: #ffe6e6;
        border-left: 4px solid #ff4444;
        padding: 0.75rem;
        border-radius: 4px;
        margin: 0.5rem 0;
        font-size: 12px;
    }
    
    .info-box {
        background-color: #e6f3ff;
        border-left: 4px solid #0066ff;
        padding: 0.75rem;
        border-radius: 4px;
        margin: 0.5rem 0;
        font-size: 12px;
    }
    </style>
    """, unsafe_allow_html=True)

# Function to fetch Google Sheets data via CSV export
def get_sheet_data(sheet_url):
    """Convert Google Sheets URL to CSV export and fetch data"""
    try:
        # Extract sheet ID and GID from URL
        sheet_id = re.search(r'/d/([a-zA-Z0-9-_]+)', sheet_url)
        gid = re.search(r'[#&]gid=([0-9]+)', sheet_url)
        
        if sheet_id and gid:
            sheet_id = sheet_id.group(1)
            gid = gid.group(1)
            csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
            df = pd.read_csv(csv_url)
            return df
        else:
            st.error("Could not parse Google Sheets URL")
            return None
    except Exception as e:
        st.error(f"Error fetching sheet: {str(e)}")
        return None

# Cache data loading
@st.cache_data(ttl=300)
def load_all_data():
    """Load all data from Google Sheets"""
    pending_tasks_url = "https://docs.google.com/spreadsheets/d/1jspebqSTXgEtYyxYAE47_uRn6RQKFlHQhneuQoGiCok/edit?gid=535674994#gid=535674994"
    court_cases_url = "https://docs.google.com/spreadsheets/d/1VUnD7ySFzIkeZlaq8E5XG8r2xXcos6lhIt62QZEeHKs/edit?gid=0#gid=0"
    officer_performance_url = "https://docs.google.com/spreadsheets/d/14-idXJHzHKCUQxxaqGZi-6S0G20gvPUhK4G16ci2FwI/edit?gid=213021534#gid=213021534"
    
    pending_df = get_sheet_data(pending_tasks_url)
    court_df = get_sheet_data(court_cases_url)
    performance_df = get_sheet_data(officer_performance_url)
    
    return pending_df, court_df, performance_df

# Load data
pending_df, court_df, performance_df = load_all_data()

# Dashboard Title
st.markdown("<h1 style='text-align: center; margin: 0; padding: 0.5rem 0;'>📊 District Governance Dashboard</h1>", unsafe_allow_html=True)

# Create three columns for main content
col1, col2, col3 = st.columns([1, 1, 1], gap="small")

# ============= COLUMN 1: PENDING TASKS =============
with col1:
    st.markdown("<div class='header-text'>⏳ XEN Mining Tasks Overview</div>", unsafe_allow_html=True)
    
    if pending_df is not None:
        try:
            # Clean column names
            pending_df.columns = pending_df.columns.str.strip()
            
            # Display available columns for debugging
            available_cols = list(pending_df.columns)
            
            # For XEN Mining sheet: Use SR NO as identifier, REMARKS/SUBJECT as description
            if 'XEN MINING SR NO' in available_cols:
                sr_col = 'XEN MINING SR NO'
                # Get the most recent remarks column
                remarks_cols = [col for col in available_cols if 'REMARKS' in col and 'MEETING' not in col]
                
                if remarks_cols:
                    latest_remarks = remarks_cols[-1]
                    
                    task_data = pending_df[[sr_col, 'SUBJECT', latest_remarks]].copy()
                    task_data = task_data.dropna(subset=[sr_col])
                    
                    if len(task_data) > 0:
                        st.dataframe(
                            task_data.head(10),
                            hide_index=True,
                            height=300,
                            use_container_width=True
                        )
                        st.metric("Total Items", len(task_data))
                    else:
                        st.info("✅ No tasks available!")
                else:
                    st.warning("Could not find remarks columns")
            else:
                st.warning("Could not identify XEN Mining column")
                
        except Exception as e:
            st.error(f"Error processing pending tasks: {str(e)}")
    else:
        st.warning("Unable to load pending tasks data")

# ============= COLUMN 2: UPCOMING COURT CASES =============
with col2:
    st.markdown("<div class='header-text'>⚖️ Upcoming Court Cases (Next 14 Days)</div>", unsafe_allow_html=True)
    
    if court_df is not None:
        try:
            # Clean column names
            court_df.columns = court_df.columns.str.strip()
            
            available_cols = list(court_df.columns)
            
            # Look for date column - "NEXT HEARING DATE" in your sheet
            date_col = None
            if 'NEXT HEARING DATE' in available_cols:
                date_col = 'NEXT HEARING DATE'
            elif 'Hearing Date' in available_cols:
                date_col = 'Hearing Date'
            elif 'HEARING DATE' in available_cols:
                date_col = 'HEARING DATE'
            
            if date_col:
                # Convert to datetime
                court_df[date_col] = pd.to_datetime(court_df[date_col], errors='coerce')
                
                # Filter upcoming cases in next 14 days
                today = datetime.now().date()
                next_14_days = today + timedelta(days=14)
                
                # Remove rows with NaT (invalid dates)
                court_df_valid = court_df.dropna(subset=[date_col])
                
                upcoming = court_df_valid[
                    (court_df_valid[date_col].dt.date >= today) & 
                    (court_df_valid[date_col].dt.date <= next_14_days)
                ].copy()
                
                if len(upcoming) > 0:
                    # Select relevant columns
                    display_cols = ['CASE NO.', 'CASE TITLE', date_col]
                    display_cols = [col for col in display_cols if col in available_cols]
                    
                    st.dataframe(
                        upcoming[display_cols].head(10),
                        hide_index=True,
                        height=300,
                        use_container_width=True
                    )
                    st.metric("Upcoming Cases (Next 14 Days)", len(upcoming))
                else:
                    st.info("📅 No cases scheduled in next 14 days")
            else:
                st.markdown("<div class='error-box'><strong>⚠️ Column Issue:</strong> Could not find date column. Looking for 'NEXT HEARING DATE'.</div>", unsafe_allow_html=True)
                st.info(f"Available columns: {', '.join(available_cols[:5])}...")
                
        except Exception as e:
            st.error(f"Error processing court cases: {str(e)}")
    else:
        st.warning("Unable to load court cases data")

# ============= COLUMN 3: OFFICER PERFORMANCE (7 DAYS) =============
with col3:
    st.markdown("<div class='header-text'>⭐ Officer Tasks Completed (Last 7 Days)</div>", unsafe_allow_html=True)
    
    if performance_df is not None:
        try:
            # Clean column names
            performance_df.columns = performance_df.columns.str.strip()
            
            available_cols = list(performance_df.columns)
            
            # Use the actual columns from the performance sheet
            officer_col = None
            entry_date_col = None
            status_col = None
            
            if 'MARKED TO OFFICER' in available_cols:
                officer_col = 'MARKED TO OFFICER'
            
            if 'ENTRY DATE' in available_cols:
                entry_date_col = 'ENTRY DATE'
            
            if 'STATUS' in available_cols:
                status_col = 'STATUS'
            
            if officer_col and entry_date_col and status_col:
                # Convert entry date to datetime
                performance_df[entry_date_col] = pd.to_datetime(performance_df[entry_date_col], errors='coerce')
                
                # Filter for last 7 days
                today = datetime.now().date()
                last_7_days = today - timedelta(days=7)
                
                # Filter for completed tasks in last 7 days
                last_7_df = performance_df[
                    (performance_df[entry_date_col].dt.date >= last_7_days) & 
                    (performance_df[entry_date_col].dt.date <= today)
                ].copy()
                
                # Filter for completed status
                completed_tasks = last_7_df[last_7_df[status_col].str.lower().str.contains('complet|done|closed', na=False, case=False)].copy()
                
                if len(completed_tasks) > 0:
                    # Group by officer and count completed tasks
                    officer_summary = completed_tasks.groupby(officer_col).size().reset_index(name='Completed Tasks (7 Days)')
                    officer_summary = officer_summary.sort_values('Completed Tasks (7 Days)', ascending=False)
                    
                    st.dataframe(
                        officer_summary.head(10),
                        hide_index=True,
                        height=300,
                        use_container_width=True
                    )
                    st.metric("Total Completed (7 Days)", len(completed_tasks))
                else:
                    st.info("No completed tasks in last 7 days")
            else:
                st.markdown("<div class='error-box'><strong>⚠️ Column Issue:</strong> Looking for 'MARKED TO OFFICER', 'ENTRY DATE', and 'STATUS' columns.</div>", unsafe_allow_html=True)
                st.info(f"Available: {', '.join(available_cols[:5])}...")
                
        except Exception as e:
            st.error(f"Error processing performance data: {str(e)}")
    else:
        st.warning("Unable to load performance data")

# ============= BOTTOM ROW: EXTERNAL LINKS =============
st.divider()

link_col1, link_col2 = st.columns(2, gap="small")

with link_col1:
    st.markdown("""
    <a href="https://Fcragendaldh.streamlit.app/" target="_blank">
        <button style="width: 100%; padding: 10px; background-color: #1f77b4; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold;">
        📋 FCR Agenda
        </button>
    </a>
    """, unsafe_allow_html=True)

with link_col2:
    st.markdown("""
    <a href="https://dashboardmcl.streamlit.app" target="_blank">
        <button style="width: 100%; padding: 10px; background-color: #2ca02c; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold;">
        🏙️ Urban Swamitra
        </button>
    </a>
    """, unsafe_allow_html=True)

# ============= FOOTER =============
st.markdown("""
    <div style='text-align: center; padding: 1rem; color: #666; font-size: 12px;'>
    Last updated: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S IST") + """
    </div>
""", unsafe_allow_html=True)
