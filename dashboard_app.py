import streamlit as st
import pandas as pd
import gspread
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import json
from urllib.parse import urlparse
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
@st.cache_data(ttl=300)  # Cache for 5 minutes
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
    st.markdown("<div class='header-text'>⏳ Officers with Pending Tasks</div>", unsafe_allow_html=True)
    
    if pending_df is not None:
        try:
            # Clean column names
            pending_df.columns = pending_df.columns.str.strip()
            
            # Identify officer and task columns (adjust based on your sheet structure)
            officer_col = [col for col in pending_df.columns if 'officer' in col.lower() or 'name' in col.lower()][0]
            status_col = [col for col in pending_df.columns if 'status' in col.lower() or 'task' in col.lower()][0]
            
            # Filter pending tasks
            pending_data = pending_df[pending_df[status_col].str.lower() == 'pending'].copy()
            
            # Group by officer and count tasks
            officer_pending = pending_data.groupby(officer_col).size().reset_index(name='Pending Tasks')
            officer_pending = officer_pending.sort_values('Pending Tasks', ascending=False)
            
            if len(officer_pending) > 0:
                # Display as compact table
                st.dataframe(
                    officer_pending,
                    hide_index=True,
                    height=300,
                    use_container_width=True
                )
                st.metric("Total Pending Tasks", pending_data.shape[0])
            else:
                st.info("✅ No pending tasks!")
        except Exception as e:
            st.error(f"Error processing pending tasks: {str(e)}")
    else:
        st.warning("Unable to load pending tasks data")

# ============= COLUMN 2: UPCOMING COURT CASES =============
with col2:
    st.markdown("<div class='header-text'>⚖️ Upcoming Court Cases (14 Days)</div>", unsafe_allow_html=True)
    
    if court_df is not None:
        try:
            # Clean column names
            court_df.columns = court_df.columns.str.strip()
            
            # Find date column
            date_col = [col for col in court_df.columns if 'date' in col.lower() or 'hearing' in col.lower()][0]
            
            # Convert to datetime
            court_df[date_col] = pd.to_datetime(court_df[date_col], errors='coerce')
            
            # Filter upcoming cases in next 14 days
            today = datetime.now().date()
            next_14_days = today + timedelta(days=14)
            
            upcoming = court_df[
                (court_df[date_col].dt.date >= today) & 
                (court_df[date_col].dt.date <= next_14_days)
            ].copy()
            
            if len(upcoming) > 0:
                # Select relevant columns to display
                display_cols = [col for col in upcoming.columns if any(
                    x in col.lower() for x in ['case', 'date', 'hearing', 'court', 'judge']
                )][:4]  # Limit to 4 columns
                
                st.dataframe(
                    upcoming[display_cols],
                    hide_index=True,
                    height=300,
                    use_container_width=True
                )
                st.metric("Upcoming Cases", len(upcoming))
            else:
                st.info("📅 No cases scheduled in next 14 days")
        except Exception as e:
            st.error(f"Error processing court cases: {str(e)}")
    else:
        st.warning("Unable to load court cases data")

# ============= COLUMN 3: OFFICER PERFORMANCE (7 DAYS) =============
with col3:
    st.markdown("<div class='header-text'>⭐ Officer Performance (Last 7 Days)</div>", unsafe_allow_html=True)
    
    if performance_df is not None:
        try:
            # Clean column names
            performance_df.columns = performance_df.columns.str.strip()
            
            # Find relevant columns
            officer_col = [col for col in performance_df.columns if 'officer' in col.lower() or 'name' in col.lower()][0]
            
            # Find completion columns
            completed_col = [col for col in performance_df.columns if 'complet' in col.lower() or 'done' in col.lower()]
            pending_col = [col for col in performance_df.columns if 'pending' in col.lower()]
            
            if completed_col and pending_col:
                completed_col = completed_col[0]
                pending_col = pending_col[0]
                
                # Create performance summary
                perf_summary = performance_df[[officer_col, completed_col, pending_col]].copy()
                perf_summary = perf_summary[perf_summary[completed_col] > 0].sort_values(completed_col, ascending=False)
                
                if len(perf_summary) > 0:
                    st.dataframe(
                        perf_summary,
                        hide_index=True,
                        height=300,
                        use_container_width=True
                    )
                    st.metric("Top Performer", perf_summary.iloc[0][officer_col] if len(perf_summary) > 0 else "N/A")
                else:
                    st.info("No performance data available")
            else:
                st.warning("Could not identify completion/pending columns")
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
