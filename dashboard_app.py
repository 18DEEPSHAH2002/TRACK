import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- Configuration ---
st.set_page_config(
    page_title="Executive Overview Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Google Sheets Export URLs (Converted for CSV access) ---
# NOTE: These URLs assume the sheets are publicly viewable.
# If loading fails, ensure the sharing settings are "Anyone with the link can view."
URL_PENDING = "https://docs.google.com/spreadsheets/d/1jspebqSTXgEtYyxYAE47_uRn6RQKFlHQhneuQoGiCok/gviz/tq?tqx=out:csv&gid=535674994"
URL_COURT_CASES = "https://docs.google.com/spreadsheets/d/1VUnD7ySFzIkeZlaq8E5XG8r2xXcos6lhIt62QZEeHKs/gviz/tq?tqx=out:csv&gid=0"
URL_PERFORMANCE = "https://docs.google.com/spreadsheets/d/14-idXJHzHKCUQxxaqGZi-6S0G20gvPUhK4G16ci2FwI/gviz/tq?tqx=out:csv&gid=213021534"

# --- Data Loading Function with Caching ---
@st.cache_data(ttl=600) # Cache data for 10 minutes
def load_data(url):
    """
    Loads data from a Google Sheet CSV export URL.
    Converts column names to lowercase and strips whitespace for robust access.
    """
    try:
        df = pd.read_csv(url)
        # 1. Clean column names by stripping whitespace
        df.columns = df.columns.str.strip()
        # 2. Convert column names to lowercase for robust key access in all functions
        df.columns = df.columns.str.lower()
        return df
    except Exception as e:
        st.error(f"Error loading data from sheet ({url[-10:]}): {e}. Please ensure the sheet is publicly accessible.")
        return pd.DataFrame()

# --- 1. Pending Tasks Overview ---
def get_pending_tasks_overview(df):
    """Calculates pending tasks per officer."""
    if df.empty:
        return pd.DataFrame({'Officer': ['N/A'], 'Pending Tasks': [0]})
    
    # Updated required columns based on user input: 'officer name' and 'task status'
    required_cols = ['officer name', 'task status']
    missing_cols = [col for col in required_cols if col not in df.columns]
    officer_col = 'officer name'
    status_col = 'task status'

    if missing_cols:
        # Display explicit error if columns are missing
        st.error(
            f"❌ **Error: Missing Columns in Pending Tasks Sheet** (GID: 535674994)\n\n"
            f"The following required columns were not found: **{', '.join(missing_cols).upper()}**.\n\n"
            f"**Available Columns:** {', '.join(df.columns).upper()}"
        )
        return pd.DataFrame({'Officer': ['ERROR: Check Sheet Columns'], 'Pending Tasks': [0]})

    # Filter using 'task status' column
    pending_df = df[df[status_col].astype(str).str.lower().str.strip() == 'pending'].copy()

    if pending_df.empty:
        return pd.DataFrame({
            'Officer': ['None'],
            'Pending Tasks': [0]
        })

    # Group by 'officer name' column
    summary = pending_df.groupby(officer_col).size().reset_index(name='Pending Tasks')
    summary.rename(columns={officer_col: 'Officer'}, inplace=True) # Rename back for display
    summary = summary.sort_values(by='Pending Tasks', ascending=False)

    return summary

# --- 2. Upcoming Court Cases ---
def get_upcoming_cases(df):
    """Filters court cases for the next 14 days."""
    if df.empty:
        return pd.DataFrame()

    # Check for required column - ***'hearing date' is assumed correct, based on standard date naming***
    required_cols = ['hearing date']
    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        st.error(
            f"❌ **Error: Missing Columns in Court Cases Sheet** (GID: 0)\n\n"
            f"The following required columns were not found: **{', '.join(missing_cols).upper()}**.\n\n"
            f"**Available Columns:** {', '.join(df.columns).upper()}"
        )
        return pd.DataFrame()

    today = datetime.now().date()
    end_date = today + timedelta(days=14)

    # Convert 'hearing date' column to datetime, handling errors
    try:
        # Assuming the sheet uses 'Hearing Date' or similar, which is now 'hearing date'
        df['hearing date'] = pd.to_datetime(df['hearing date'], errors='coerce', dayfirst=True)
    except Exception as e:
        st.warning(f"Could not parse 'hearing date' column due to format issues: {e}. Please check the date format in the sheet.")
        return pd.DataFrame()

    # Filter for upcoming cases (from today up to the next 14 days)
    upcoming_df = df[
        (df['hearing date'].dt.date >= today) &
        (df['hearing date'].dt.date <= end_date)
    ].copy()

    # Select and format basic info
    if not upcoming_df.empty:
        upcoming_df['Hearing Date'] = upcoming_df['hearing date'].dt.strftime('%d-%b-%Y')
        
        # Selecting relevant columns based on typical GSheet column names (now lowercase)
        # We assume 'case no.', 'party name', 'court' are the basic info columns
        cols = ['case no.', 'party name', 'court']
        # Filter for existing columns and map to display names
        cols_to_display = {col: col.replace('.', '').title() for col in cols if col in upcoming_df.columns}
        cols_to_display['Hearing Date'] = 'Hearing Date'
        
        # Ensure the required columns exist before selecting
        final_cols = list(cols_to_display.keys())
        upcoming_df = upcoming_df[[c for c in final_cols if c in upcoming_df.columns]].rename(columns=cols_to_display)
        
        return upcoming_df.sort_values(by='Hearing Date')
    else:
        return pd.DataFrame()

# --- 3. Officer Performance (Star Mark Box) ---
def get_officer_performance(df):
    """Calculates completed and pending tasks for performance dashboard."""
    if df.empty:
        return pd.DataFrame({'Officer': ['N/A'], 'Completed (7 Days)': [0], 'Pending (Total)': [0]})
    
    # Updated required columns based on user input: 'officer name' and 'task status'
    required_cols = ['officer name', 'task status', 'completion date']
    missing_cols = [col for col in required_cols if col not in df.columns]
    officer_col = 'officer name'
    status_col = 'task status'
    completion_date_col = 'completion date'

    if missing_cols:
        st.error(
            f"❌ **Error: Missing Columns in Performance Sheet** (GID: 213021534)\n\n"
            f"The following required columns were not found: **{', '.join(missing_cols).upper()}**.\n\n"
            f"**Available Columns:** {', '.join(df.columns).upper()}"
        )
        return pd.DataFrame({'Officer': ['ERROR: Check Sheet Columns'], 'Completed (7 Days)': [0], 'Pending (Total)': [0]})

    today = datetime.now().date()
    start_date_7_days = today - timedelta(days=7)
    
    # Ensure date columns are in datetime format
    try:
        df[completion_date_col] = pd.to_datetime(df[completion_date_col], errors='coerce', dayfirst=True)
    except Exception as e:
        st.warning(f"Could not parse 'completion date' column due to format issues: {e}. Performance metrics for 7 days may be inaccurate.")
        df[completion_date_col] = pd.NaT


    # 1. Completed in Last 7 Days (using 'task status' and 'completion date')
    completed_7_days = df[
        (df[status_col].astype(str).str.lower().str.strip() == 'complete') &
        (df[completion_date_col].dt.date >= start_date_7_days) &
        (df[completion_date_col].dt.date <= today)
    ]
    completed_counts = completed_7_days.groupby(officer_col).size().reset_index(name='Completed (7 Days)')

    # 2. Total Pending Tasks (using 'task status')
    pending_tasks = df[df[status_col].astype(str).str.lower().str.strip() == 'pending']
    pending_counts = pending_tasks.groupby(officer_col).size().reset_index(name='Pending (Total)')

    # Merge results
    performance_df = pd.merge(completed_counts, pending_counts, on=officer_col, how='outer').fillna(0)

    # Get all unique officers (even those with 0 completed/pending)
    all_officers = df[officer_col].dropna().unique()
    all_officers_df = pd.DataFrame({officer_col: all_officers})

    # Merge with all officers to ensure everyone is listed
    performance_df = pd.merge(all_officers_df, performance_df, on=officer_col, how='left').fillna(0)

    # Rename the officer column back for display
    performance_df.rename(columns={officer_col: 'Officer'}, inplace=True)

    # Ensure columns are integer types for clean display
    performance_df['Completed (7 Days)'] = performance_df['Completed (7 Days)'].astype(int)
    performance_df['Pending (Total)'] = performance_df['Pending (Total)'].astype(int)

    return performance_df.sort_values(by='Completed (7 Days)', ascending=False)

# --- Main Dashboard Layout ---
def main_dashboard():
    st.title("Executive Overview Dashboard")
    st.markdown("---")

    # --- 0. External Links (Using wide columns for efficient space use) ---
    st.header("Quick Access Links")
    link_col1, link_col2, link_col3 = st.columns(3)

    link_col1.markdown(f"""
        <div style="padding: 10px; border: 1px solid #4ade80; border-radius: 8px; background-color: #f0fdf4;">
            <h3 style="margin-top:0; color:#15803d;">FCR Agenda</h3>
            <p style="margin-bottom:0;"><a href='https://Fcragendaldh.streamlit.app/' target='_blank'>
                Go to FCR Agenda App <span style='font-size:1.2em;'>➡️</span>
            </a></p>
        </div>
        """, unsafe_allow_html=True)

    link_col2.markdown(f"""
        <div style="padding: 10px; border: 1px solid #93c5fd; border-radius: 8px; background-color: #eff6ff;">
            <h3 style="margin-top:0; color:#2563eb;">Urban SVAMITRA</h3>
            <p style="margin-bottom:0;"><a href='https://dashboardmcl.streamlit.app' target='_blank'>
                Go to Urban SVAMITRA Dashboard <span style='font-size:1.2em;'>📊</span>
            </a></p>
        </div>
        """, unsafe_allow_html=True)

    # Placeholder for the third link or empty space
    with link_col3:
        st.empty()

    st.markdown("---")
    st.header("Data Overviews")
    st.write("---")

    # --- 1, 2, 3. Three Main Data Boxes (Using st.columns(3) for maximum space) ---
    col_pending, col_court, col_performance = st.columns(3)

    # --- Load all dataframes ---
    df_pending = load_data(URL_PENDING)
    df_court = load_data(URL_COURT_CASES)
    df_performance_data = load_data(URL_PERFORMANCE)

    # --- BOX 1: Pending Tasks Overview ---
    with col_pending:
        st.subheader("👤 Officer Pending Tasks")
        pending_summary = get_pending_tasks_overview(df_pending)

        # Display key metric (Total Pending)
        total_pending = pending_summary['Pending Tasks'].sum() if 'Pending Tasks' in pending_summary.columns else 0
        st.metric(label="Total Pending Tasks Across All Officers", value=f"{total_pending}", delta_color="inverse")
        st.markdown("**List of Officers with Pending Tasks:**")

        # Check if the dataframe contains the required 'Officer' column after processing
        if 'Officer' in pending_summary.columns and 'Pending Tasks' in pending_summary.columns and total_pending > 0:
            st.dataframe(
                pending_summary,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Officer": st.column_config.TextColumn("Officer", help="Name of the assigned officer"),
                    "Pending Tasks": st.column_config.NumberColumn("Pending Tasks", help="Number of tasks with status 'Pending'", format="%d")
                }
            )
        elif total_pending == 0 and 'Officer' in pending_summary.columns:
            st.info("🎉 Great job! No pending tasks found.")
        else:
            # Error was likely displayed by the function itself
            st.warning("Data load/processing failed for Pending Tasks. Check Sheet Columns error above.")


    # --- BOX 2: Upcoming Court Cases (Next 14 Days) ---
    with col_court:
        st.subheader("⚖️ Upcoming Court Cases (14 Days)")
        upcoming_cases_df = get_upcoming_cases(df_court)

        # Display key metric (Number of Upcoming Cases)
        num_cases = len(upcoming_cases_df)
        st.metric(label="Total Upcoming Cases (Next 14 Days)", value=f"{num_cases}", delta_color="off")
        st.markdown("**Basic Info for Upcoming Cases:**")

        if not upcoming_cases_df.empty:
            # Check for the presence of the 'Hearing Date' column which is mandatory for display
            if 'Hearing Date' in upcoming_cases_df.columns:
                st.dataframe(
                    upcoming_cases_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Hearing Date": st.column_config.DateColumn("Hearing Date", format="DD-MMM-YYYY"),
                    }
                )
            else:
                 # This branch is hit if the data loaded but date filtering resulted in 0 cases or column rename failed.
                 st.info("No court cases scheduled in the next 14 days, or column names are unexpected.")
        elif num_cases == 0 and not upcoming_cases_df.empty:
            st.info("No court cases scheduled in the next 14 days.")
        else:
            st.warning("Data load/processing failed for Court Cases. Check Sheet Columns error above.")


    # --- BOX 3: Officer Performance (Star Mark Box) ---
    with col_performance:
        st.subheader("⭐ Officer Performance (Last 7 Days)")
        performance_df = get_officer_performance(df_performance_data)

        # Display key metric (Total Completed)
        total_completed = performance_df['Completed (7 Days)'].sum() if 'Completed (7 Days)' in performance_df.columns else 0
        st.metric(label="Total Tasks Completed (Last 7 Days)", value=f"{total_completed}", delta_color="normal")
        st.markdown("**Performance Metrics:**")

        # Check if the dataframe contains the required 'Officer' column after processing
        if 'Officer' in performance_df.columns and not performance_df.empty:
            st.dataframe(
                performance_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Officer": st.column_config.TextColumn("Officer", help="Name of the officer"),
                    "Completed (7 Days)": st.column_config.NumberColumn("Completed (7 Days)", help="Tasks completed in the last 7 days", format="%d"),
                    "Pending (Total)": st.column_config.NumberColumn("Pending (Total)", help="Total tasks currently pending", format="%d")
                }
            )
        else:
            st.warning("Data load/processing failed for Officer Performance. Check Sheet Columns error above.")


if __name__ == "__main__":
    main_dashboard()
