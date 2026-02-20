import streamlit as st
import pandas as pd
import numpy as np
from data_processing import (
    load_data,
    clean_data,
    add_calculated_columns,
    filter_data,
    calculate_overall_tendencies,
    calculate_category_tendencies,
    calculate_all_teams_tendencies,
    add_rankings,
    format_percentage_with_rank,
    calculate_defensive_overall_tendencies,
    calculate_defensive_category_tendencies,
    calculate_all_teams_defensive_tendencies
)

# Page configuration
st.set_page_config(
    page_title="2025 NFL Tendency Dashboard",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
def load_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

load_css('styles.css')

# Title
st.title("NFL Tendency Dashboard")
st.markdown("---")

# Load and process data
@st.cache_data
def load_and_process_data():
    """Load and prepare data with caching"""
    import os
    if os.path.exists('Data/PFF_2025_FULL_Play_Feed.csv'):
        df = load_data('Data/PFF_2025_FULL_Play_Feed.csv')
    else:
        df = load_data()
    df = clean_data(df)
    df = add_calculated_columns(df)
    return df

# Load data
try:
    df = load_and_process_data()
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# Get unique values for filters
all_teams = sorted(df['pff_OFFTEAM'].dropna().unique())
all_quarters = sorted(df['pff_QUARTER'].dropna().astype(int).unique())
all_downs = sorted(df['pff_DOWN'].dropna().astype(int).unique())

# Custom sort for weeks: 1-18, then WC, DP, CC, SB
def sort_weeks(week_list):
    numeric_weeks = []
    playoff_weeks = []
    playoff_order = ['WC', 'DP', 'CC', 'SB']
    
    for week in week_list:
        if week.isdigit():
            numeric_weeks.append(int(week))
        else:
            playoff_weeks.append(week)
    
    # Sort numeric weeks
    numeric_weeks.sort()
    
    # Sort playoff weeks by defined order
    playoff_weeks_sorted = [w for w in playoff_order if w in playoff_weeks]
    
    # Combine: numeric first, then playoffs
    return [str(w) for w in numeric_weeks] + playoff_weeks_sorted

all_weeks = sort_weeks(df['pff_WEEK'].dropna().astype(str).unique().tolist())
min_time = int(df['minutes_remaining'].min())
max_time = int(df['minutes_remaining'].max())
min_ytg = int(df['pff_DISTANCE'].min())
max_ytg = int(df['pff_DISTANCE'].max())
min_yl = int(df['pff_YARDS_TO_GOAL_LINE'].min())
max_yl = int(df['pff_YARDS_TO_GOAL_LINE'].max())

# Team filter (single select) - with session state
if 'selected_team' not in st.session_state:
    st.session_state['selected_team'] = all_teams[0] if len(all_teams) > 0 else None

# Sidebar filters
st.sidebar.header("Select Team")
selected_team = st.sidebar.selectbox(
    "Select Team",
    options=all_teams,
    index=all_teams.index(st.session_state['selected_team']) if st.session_state['selected_team'] in all_teams else 0,
    key='team_select'
)

# Update session state when team changes
if selected_team != st.session_state.get('selected_team'):
    st.session_state['selected_team'] = selected_team

# Check if reset was triggered
if st.session_state.get('reset_filters', False):
    # Reset all filter states
    st.session_state['weeks_multiselect'] = all_weeks
    st.session_state['quarters_multiselect'] = all_quarters
    st.session_state['time_slider'] = (min_time, max_time)
    st.session_state['downs_multiselect'] = all_downs
    st.session_state['ytg_slider'] = (min_ytg, max_ytg)
    st.session_state['yardline_slider'] = (min_yl, max_yl)
    # Clear the reset flag
    st.session_state['reset_filters'] = False

st.sidebar.header("Situational Filters")

# Week filter (multi-select)
if 'weeks_multiselect' not in st.session_state:
    st.session_state['weeks_multiselect'] = all_weeks

selected_weeks = st.sidebar.multiselect(
    "Select Week(s)",
    options=all_weeks,
    key='weeks_multiselect'
)

# Quarter filter (multi-select)
if 'quarters_multiselect' not in st.session_state:
    st.session_state['quarters_multiselect'] = all_quarters

selected_quarters = st.sidebar.multiselect(
    "Select Quarter(s)",
    options=all_quarters,
    key='quarters_multiselect'
)

# Time remaining filter
st.sidebar.subheader("Time Remaining in Quarter")
if 'time_slider' not in st.session_state:
    st.session_state['time_slider'] = (min_time, max_time)

time_range = st.sidebar.slider(
    "Minutes Remaining",
    min_value=min_time,
    max_value=max_time,
    step=1,
    key='time_slider'
)

# Down filter (multi-select)
if 'downs_multiselect' not in st.session_state:
    st.session_state['downs_multiselect'] = all_downs

selected_downs = st.sidebar.multiselect(
    "Select Down(s)",
    options=all_downs,
    key='downs_multiselect'
)

# Yards to go filter
st.sidebar.subheader("Yards to Go")
if 'ytg_slider' not in st.session_state:
    st.session_state['ytg_slider'] = (min_ytg, max_ytg)

yards_to_go_range = st.sidebar.slider(
    "Distance",
    min_value=min_ytg,
    max_value=max_ytg,
    step=1,
    key='ytg_slider'
)

# Yardline filter
st.sidebar.subheader("Yardline (Yards to Goal)")
if 'yardline_slider' not in st.session_state:
    st.session_state['yardline_slider'] = (min_yl, max_yl)

yardline_range = st.sidebar.slider(
    "Yards to Goal Line",
    min_value=min_yl,
    max_value=max_yl,
    step=1,
    key='yardline_slider'
)

# Reset Filters Button at the bottom
st.sidebar.markdown("---")
if st.sidebar.button("Reset Situational Filters", use_container_width=True):
    st.session_state['reset_filters'] = True
    st.rerun()
    
# Create filters dictionary
filters = {
    'team': selected_team,
    'weeks': selected_weeks,
    'quarters': selected_quarters,
    'time_range': time_range,
    'downs': selected_downs,
    'yards_to_go_range': yards_to_go_range,
    'yardline_range': yardline_range
}

# Filter data for selected team
df_filtered = filter_data(df, filters)

# Calculate all teams' tendencies for ranking (without team filter)
filters_for_ranking = filters.copy()
filters_for_ranking['team'] = None
all_teams_tendencies = calculate_all_teams_tendencies(df, filters_for_ranking, None)

# Tabs
tab1, tab2 = st.tabs(["Offense", "Defense"])

with tab1:
    st.header(f"{selected_team} Offensive Tendencies")
    
    # Check if data exists
    if len(df_filtered) == 0:
        st.warning("No data available for selected filters.")
    else:
        # Calculate overall tendencies
        overall = calculate_overall_tendencies(df_filtered)
        
        # Calculate rankings for overall metrics
        team_overall = all_teams_tendencies[all_teams_tendencies['Team'] == selected_team].iloc[0] if len(all_teams_tendencies[all_teams_tendencies['Team'] == selected_team]) > 0 else None
        
        # Function to get rank for a metric
        def get_rank(metric_name, value):
            if team_overall is None:
                return "-"
            sorted_values = all_teams_tendencies[metric_name].sort_values(ascending=False).values
            rank = np.where(sorted_values == value)[0]
            if len(rank) > 0:
                rank_value = rank[0] + 1
                tied_count = np.sum(sorted_values == value)
                if tied_count > 1:
                    return f"t-{rank_value}"
                else:
                    return str(rank_value)
            return "-"
        
        # Display overall scorecards
        st.subheader("Overall Offensive Tendencies")
        
        cols = st.columns(6)
        
        # Total Plays
        with cols[0]:
            st.markdown(f"""
                <div class="scorecard">
                    <div class="scorecard-value">{overall['total_plays']}</div>
                    <div class="scorecard-label">Total Plays</div>
                </div>
            """, unsafe_allow_html=True)
        
        # Run %
        with cols[1]:
            run_rank = get_rank('Run_Pct', team_overall['Run_Pct']) if team_overall is not None else "-"
            rank_display = f"({run_rank})" if run_rank != "-" else ""
            st.markdown(f"""
                <div class="scorecard">
                    <div class="scorecard-value">{overall['run_pct']:.1f}%</div>
                    <div class="scorecard-label">Run %</div>
                    <div class="scorecard-rank">{rank_display}</div>
                </div>
            """, unsafe_allow_html=True)
        
        # PA %
        with cols[2]:
            pa_rank = get_rank('PA_Pct', team_overall['PA_Pct']) if team_overall is not None else "-"
            rank_display = f"({pa_rank})" if run_rank != "-" else ""
            st.markdown(f"""
                <div class="scorecard">
                    <div class="scorecard-value">{overall['pa_pct']:.1f}%</div>
                    <div class="scorecard-label">PA %</div>
                    <div class="scorecard-rank">{rank_display}</div>
                </div>
            """, unsafe_allow_html=True)
        
        # DB %
        with cols[3]:
            db_rank = get_rank('DB_Pct', team_overall['DB_Pct']) if team_overall is not None else "-"
            rank_display = f"({db_rank})" if run_rank != "-" else ""
            st.markdown(f"""
                <div class="scorecard">
                    <div class="scorecard-value">{overall['db_pct']:.1f}%</div>
                    <div class="scorecard-label">Std DB %</div>
                    <div class="scorecard-rank">{rank_display}</div>
                </div>
            """, unsafe_allow_html=True)
        
        # Motion %
        with cols[4]:
            motion_rank = get_rank('Motion_Pct', team_overall['Motion_Pct']) if team_overall is not None else "-"
            rank_display = f"({motion_rank})" if run_rank != "-" else ""
            st.markdown(f"""
                <div class="scorecard">
                    <div class="scorecard-value">{overall['motion_pct']:.1f}%</div>
                    <div class="scorecard-label">Motion %</div>
                    <div class="scorecard-rank">{rank_display}</div>
                </div>
            """, unsafe_allow_html=True)
        
        # Top Run Concepts
        with cols[5]:
            concepts_display = "<br>".join(overall['top_run_concepts'][:3]) if overall['top_run_concepts'] else "N/A"
            st.markdown(f"""
                <div class="scorecard">
                    <div class="scorecard-label" style="margin-bottom: 10px;">Top Run Concepts</div>
                    <div style="font-size: 12px; line-height: 1.6; color: #333; margin-top: 5px;">{concepts_display}</div>
                </div>
            """, unsafe_allow_html=True)
                
        st.markdown("---")
        
        # Tendency Tables
        st.subheader("Detailed Tendency Breakdown")
        
        # Table 1: Personnel
        st.markdown("### Personnel Groupings")
        personnel_df = calculate_category_tendencies(df_filtered, 'pff_OFF_PERSONNEL_GROUP')
        
        if len(personnel_df) > 0:
            # Add rankings (simplified for now - would need all teams data by category)
            # For MVP, we'll add placeholder rankings
            personnel_df['Usage_Display'] = personnel_df.apply(
                lambda row: f"{row['Usage_Pct']:.1f}%", axis=1
            )
            personnel_df['Run_Display'] = personnel_df.apply(
                lambda row: f"{row['Run_Pct']:.1f}%", axis=1
            )
            personnel_df['PA_Display'] = personnel_df.apply(
                lambda row: f"{row['PA_Pct']:.1f}%", axis=1
            )
            personnel_df['DB_Display'] = personnel_df.apply(
                lambda row: f"{row['DB_Pct']:.1f}%", axis=1
            )
            personnel_df['Motion_Display'] = personnel_df.apply(
                lambda row: f"{row['Motion_Pct']:.1f}%", axis=1
            )
            
            # Display table
            display_df = personnel_df[[
                'Category', 'Plays', 'Usage_Display', 'Run_Display', 
                'PA_Display', 'DB_Display', 'Motion_Display', 'Top_Run_Concepts'
            ]].rename(columns={
                'Category': 'Personnel',
                'Usage_Display': 'Usage %',
                'Run_Display': 'Run %',
                'PA_Display': 'PA %',
                'DB_Display': 'DB %',
                'Motion_Display': 'Motion %',
                'Top_Run_Concepts': 'Top Run Concepts'
            })
            
            display_df_formatted = display_df.copy()
            display_df_formatted['Top Run Concepts'] = display_df_formatted['Top Run Concepts'].str.replace('\n', ' | ')

            st.dataframe(
                display_df_formatted,
                use_container_width=True,
                hide_index=True
            )
        
        st.markdown("---")
        
        # Table 2: Formation Group
        st.markdown("### Formation Groups")
        formation_df = calculate_category_tendencies(df_filtered, 'pff_OFFFORMATIONGROUP_NORM')
        
        if len(formation_df) > 0:
            formation_df['Usage_Display'] = formation_df.apply(
                lambda row: f"{row['Usage_Pct']:.1f}%", axis=1
            )
            formation_df['Run_Display'] = formation_df.apply(
                lambda row: f"{row['Run_Pct']:.1f}%", axis=1
            )
            formation_df['PA_Display'] = formation_df.apply(
                lambda row: f"{row['PA_Pct']:.1f}%", axis=1
            )
            formation_df['DB_Display'] = formation_df.apply(
                lambda row: f"{row['DB_Pct']:.1f}%", axis=1
            )
            formation_df['Motion_Display'] = formation_df.apply(
                lambda row: f"{row['Motion_Pct']:.1f}%", axis=1
            )
            
            display_df = formation_df[[
                'Category', 'Plays', 'Usage_Display', 'Run_Display', 
                'PA_Display', 'DB_Display', 'Motion_Display', 'Top_Run_Concepts'
            ]].rename(columns={
                'Category': 'Formation',
                'Usage_Display': 'Usage %',
                'Run_Display': 'Run %',
                'PA_Display': 'PA %',
                'DB_Display': 'DB %',
                'Motion_Display': 'Motion %',
                'Top_Run_Concepts': 'Top Run Concepts'
            })
            
            display_df_formatted = display_df.copy()
            display_df_formatted['Top Run Concepts'] = display_df_formatted['Top Run Concepts'].str.replace('\n', ' | ')

            st.dataframe(
                display_df_formatted,
                use_container_width=True,
                hide_index=True
            )
        
        st.markdown("---")
        
        # Table 3: QB Alignment
        st.markdown("### QB Alignment")
        
       # Create QB alignment category: Shotgun vs Under Center
        df_filtered_qb = df_filtered.copy()
        df_filtered_qb['QB_Alignment'] = df_filtered_qb['pff_SHOTGUN'].apply(
            lambda x: 'Shotgun' if x == 'S' else 'Under Center'
        )

        qb_df = calculate_category_tendencies(df_filtered_qb, 'QB_Alignment')
        
        if len(qb_df) > 0:
            qb_df['Usage_Display'] = qb_df.apply(
                lambda row: f"{row['Usage_Pct']:.1f}%", axis=1
            )
            qb_df['Run_Display'] = qb_df.apply(
                lambda row: f"{row['Run_Pct']:.1f}%", axis=1
            )
            qb_df['PA_Display'] = qb_df.apply(
                lambda row: f"{row['PA_Pct']:.1f}%", axis=1
            )
            qb_df['DB_Display'] = qb_df.apply(
                lambda row: f"{row['DB_Pct']:.1f}%", axis=1
            )
            qb_df['Motion_Display'] = qb_df.apply(
                lambda row: f"{row['Motion_Pct']:.1f}%", axis=1
            )
            
            display_df = qb_df[[
                'Category', 'Plays', 'Usage_Display', 'Run_Display', 
                'PA_Display', 'DB_Display', 'Motion_Display', 'Top_Run_Concepts'
            ]].rename(columns={
                'Category': 'QB Alignment',
                'Usage_Display': 'Usage %',
                'Run_Display': 'Run %',
                'PA_Display': 'PA %',
                'DB_Display': 'DB %',
                'Motion_Display': 'Motion %',
                'Top_Run_Concepts': 'Top Run Concepts'
            })
            
            # Convert newlines to HTML breaks for display
            display_df_formatted = display_df.copy()
            display_df_formatted['Top Run Concepts'] = display_df_formatted['Top Run Concepts'].str.replace('\n', ' | ')

            st.dataframe(
                display_df_formatted,
                use_container_width=True,
                hide_index=True
            )
        
        st.markdown("---")
        st.markdown("### Metric Definitions")
        
        with st.expander("Click to view offensive metric explanations"):
            st.markdown("""
            **Usage %** - Percentage of team's total plays using this category
            
            **Run %** - Percentage of plays in this category that are runs
            
            **PA %** - Play Action percentage: plays with play action / total plays in category
            
            **DB %** - Standard Dropback percentage: dropbacks where QB drops straight back (SD/SR/SL) with no play action / total plays in category
            
            **Motion %** - Percentage of plays in this category that use pre-snap motion or shifts
            
            **Top Run Concepts** - Most common run concepts within this category, shown as percentage of run plays
            - *Outside Zone* - Outside zone blocking scheme
            - *Inside Zone* - Inside zone blocking scheme  
            - *Man* - Man/gap blocking scheme
            - *Power* - Power blocking scheme
            - *Counter* - Counter run concept
            
            **Rankings** - Rank among all 32 teams with same filters applied (t- indicates tie)
            """)

with tab2:
    st.header(f"{selected_team} Defensive Tendencies")
    
    # Filter data for defense (team as DEFTEAM)
    filters_defense = filters.copy()
    df_defense = df.copy()
    
    # Apply filters with team as DEFTEAM
    df_defense_filtered = df_defense[df_defense['pff_DEFTEAM'] == selected_team]
    
    # Apply other filters
    if filters.get('weeks') and len(filters['weeks']) > 0:
        df_defense_filtered = df_defense_filtered[df_defense_filtered['pff_WEEK'].astype(str).isin(filters['weeks'])]
    
    if filters.get('quarters') and len(filters['quarters']) > 0:
        df_defense_filtered = df_defense_filtered[df_defense_filtered['pff_QUARTER'].isin(filters['quarters'])]
    
    if filters.get('time_range'):
        min_time, max_time = filters['time_range']
        df_defense_filtered = df_defense_filtered[
            (df_defense_filtered['minutes_remaining'] >= min_time) & 
            (df_defense_filtered['minutes_remaining'] <= max_time)
        ]
    
    if filters.get('downs') and len(filters['downs']) > 0:
        df_defense_filtered = df_defense_filtered[df_defense_filtered['pff_DOWN'].isin(filters['downs'])]
    
    if filters.get('yards_to_go_range'):
        min_ytg, max_ytg = filters['yards_to_go_range']
        df_defense_filtered = df_defense_filtered[
            (df_defense_filtered['pff_DISTANCE'] >= min_ytg) & 
            (df_defense_filtered['pff_DISTANCE'] <= max_ytg)
        ]
    
    if filters.get('yardline_range'):
        min_yl, max_yl = filters['yardline_range']
        df_defense_filtered = df_defense_filtered[
            (df_defense_filtered['pff_YARDS_TO_GOAL_LINE'] >= min_yl) & 
            (df_defense_filtered['pff_YARDS_TO_GOAL_LINE'] <= max_yl)
        ]
    
    # Calculate all teams' defensive tendencies for ranking
    all_teams_def_tendencies = calculate_all_teams_defensive_tendencies(df, filters_defense)
    
    # Check if data exists
    if len(df_defense_filtered) == 0:
        st.warning("No defensive data available for selected filters.")
    else:
        # Calculate overall defensive tendencies
        overall_def = calculate_defensive_overall_tendencies(df_defense_filtered)
        
        # Calculate rankings for overall metrics
        team_def_overall = all_teams_def_tendencies[all_teams_def_tendencies['Team'] == selected_team].iloc[0] if len(all_teams_def_tendencies[all_teams_def_tendencies['Team'] == selected_team]) > 0 else None
        
        # Function to get rank for a metric
        def get_def_rank(metric_name, value):
            if team_def_overall is None:
                return "-"
            sorted_values = all_teams_def_tendencies[metric_name].sort_values(ascending=False).values
            rank = np.where(sorted_values == value)[0]
            if len(rank) > 0:
                rank_value = rank[0] + 1
                tied_count = np.sum(sorted_values == value)
                if tied_count > 1:
                    return f"t-{rank_value}"
                else:
                    return str(rank_value)
            return "-"
        
        # Display defensive scorecards
        st.subheader("Overall Defensive Tendencies")
        
        cols = st.columns(6)
        
        # Total Plays
        with cols[0]:
            st.markdown(f"""
                <div class="scorecard">
                    <div class="scorecard-value">{overall_def['total_plays']}</div>
                    <div class="scorecard-label">Total Plays</div>
                </div>
            """, unsafe_allow_html=True)
        
        # Blitz %
        with cols[1]:
            blitz_rank = get_def_rank('Blitz_Pct', team_def_overall['Blitz_Pct']) if team_def_overall is not None else "-"
            rank_display = f"({blitz_rank})" if blitz_rank != "-" else ""
            st.markdown(f"""
                <div class="scorecard">
                    <div class="scorecard-value">{overall_def['blitz_pct']:.1f}%</div>
                    <div class="scorecard-label">Blitz %</div>
                    <div class="scorecard-rank">{rank_display}</div>
                </div>
            """, unsafe_allow_html=True)
        
        # Man %
        with cols[2]:
            man_rank = get_def_rank('Man_Pct', team_def_overall['Man_Pct']) if team_def_overall is not None else "-"
            rank_display = f"({man_rank})" if man_rank != "-" else ""
            st.markdown(f"""
                <div class="scorecard">
                    <div class="scorecard-value">{overall_def['man_pct']:.1f}%</div>
                    <div class="scorecard-label">Man %</div>
                    <div class="scorecard-rank">{rank_display}</div>
                </div>
            """, unsafe_allow_html=True)
        
        # MOFO %
        with cols[3]:
            mofo_rank = get_def_rank('MOFO_Pct', team_def_overall['MOFO_Pct']) if team_def_overall is not None else "-"
            rank_display = f"({mofo_rank})" if mofo_rank != "-" else ""
            st.markdown(f"""
                <div class="scorecard">
                    <div class="scorecard-value">{overall_def['mofo_pct']:.1f}%</div>
                    <div class="scorecard-label">MOFO %</div>
                    <div class="scorecard-rank">{rank_display}</div>
                </div>
            """, unsafe_allow_html=True)
        
        # Disguise %
        with cols[4]:
            disguise_rank = get_def_rank('Disguise_Pct', team_def_overall['Disguise_Pct']) if team_def_overall is not None else "-"
            rank_display = f"({disguise_rank})" if disguise_rank != "-" else ""
            st.markdown(f"""
                <div class="scorecard">
                    <div class="scorecard-value">{overall_def['disguise_pct']:.1f}%</div>
                    <div class="scorecard-label">Disguise %</div>
                    <div class="scorecard-rank">{rank_display}</div>
                </div>
            """, unsafe_allow_html=True)
        
        # Top Coverages
        with cols[5]:
            coverages_display = "<br>".join(overall_def['top_coverages'][:3]) if overall_def['top_coverages'] else "N/A"
            st.markdown(f"""
                <div class="scorecard">
                    <div class="scorecard-label" style="margin-bottom: 10px;">Top Coverages</div>
                    <div style="font-size: 12px; line-height: 1.6; color: #333; margin-top: 5px;">{coverages_display}</div>
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Defensive Tables
        st.subheader("Detailed Defensive Breakdown")
        
        # Table 1: By Defensive Package
        st.markdown("### Defensive Package Tendencies")
        def_package_df = calculate_defensive_category_tendencies(df_defense_filtered, 'pff_DEF_PACKAGE')
        
        if len(def_package_df) > 0:
            def_package_df['Usage_Display'] = def_package_df.apply(
                lambda row: f"{row['Usage_Pct']:.1f}%", axis=1
            )
            def_package_df['Blitz_Display'] = def_package_df.apply(
                lambda row: f"{row['Blitz_Pct']:.1f}%", axis=1
            )
            def_package_df['Man_Display'] = def_package_df.apply(
                lambda row: f"{row['Man_Pct']:.1f}%", axis=1
            )
            def_package_df['MOFO_Display'] = def_package_df.apply(
                lambda row: f"{row['MOFO_Pct']:.1f}%", axis=1
            )
            def_package_df['Disguise_Display'] = def_package_df.apply(
                lambda row: f"{row['Disguise_Pct']:.1f}%", axis=1
            )
            
            display_df = def_package_df[[
                'Category', 'Plays', 'Usage_Display', 'Blitz_Display', 
                'Man_Display', 'MOFO_Display', 'Disguise_Display', 'Top_Coverages'
            ]].rename(columns={
                'Category': 'Defensive Package',
                'Usage_Display': 'Usage %',
                'Blitz_Display': 'Blitz %',
                'Man_Display': 'Man %',
                'MOFO_Display': 'MOFO %',
                'Disguise_Display': 'Disguise %',
                'Top_Coverages': 'Top Coverages'
            })
            
            # Replace newlines with separator for display
            display_df_formatted = display_df.copy()
            display_df_formatted['Top Coverages'] = display_df_formatted['Top Coverages'].str.replace('\n', ' | ')
            
            st.dataframe(
                display_df_formatted,
                use_container_width=True,
                hide_index=True
            )
        
        st.markdown("---")
        
        # Table 2: Defensive Package vs Offensive Personnel
        st.markdown("### Defensive Package vs Offensive Personnel")
        
        # Get all offensive personnel options (convert to string for consistency)
        all_off_personnel = sorted(df_defense_filtered['pff_OFF_PERSONNEL_GROUP'].dropna().astype(str).unique())

        # Default to "11" if available, otherwise first option
        default_personnel = "11" if "11" in all_off_personnel else (all_off_personnel[0] if len(all_off_personnel) > 0 else None)
        
        if default_personnel:
            selected_off_personnel = st.selectbox(
                "Select Offensive Personnel to Analyze Against",
                options=all_off_personnel,
                index=all_off_personnel.index(default_personnel) if default_personnel in all_off_personnel else 0
            )
            
            # Filter to only plays vs selected offensive personnel
            df_vs_personnel = df_defense_filtered[df_defense_filtered['pff_OFF_PERSONNEL_GROUP'].astype(str) == selected_off_personnel]
            
            if len(df_vs_personnel) > 0:
                def_vs_personnel_df = calculate_defensive_category_tendencies(df_vs_personnel, 'pff_DEF_PACKAGE')
                
                if len(def_vs_personnel_df) > 0:
                    def_vs_personnel_df['Usage_Display'] = def_vs_personnel_df.apply(
                        lambda row: f"{row['Usage_Pct']:.1f}%", axis=1
                    )
                    def_vs_personnel_df['Blitz_Display'] = def_vs_personnel_df.apply(
                        lambda row: f"{row['Blitz_Pct']:.1f}%", axis=1
                    )
                    def_vs_personnel_df['Man_Display'] = def_vs_personnel_df.apply(
                        lambda row: f"{row['Man_Pct']:.1f}%", axis=1
                    )
                    def_vs_personnel_df['MOFO_Display'] = def_vs_personnel_df.apply(
                        lambda row: f"{row['MOFO_Pct']:.1f}%", axis=1
                    )
                    def_vs_personnel_df['Disguise_Display'] = def_vs_personnel_df.apply(
                        lambda row: f"{row['Disguise_Pct']:.1f}%", axis=1
                    )
                    
                    display_df_vs = def_vs_personnel_df[[
                        'Category', 'Plays', 'Usage_Display', 'Blitz_Display', 
                        'Man_Display', 'MOFO_Display', 'Disguise_Display', 'Top_Coverages'
                    ]].rename(columns={
                        'Category': 'Defensive Package',
                        'Usage_Display': 'Usage %',
                        'Blitz_Display': 'Blitz %',
                        'Man_Display': 'Man %',
                        'MOFO_Display': 'MOFO %',
                        'Disguise_Display': 'Disguise %',
                        'Top_Coverages': 'Top Coverages'
                    })
                    
                    # Replace newlines with separator for display
                    display_df_vs_formatted = display_df_vs.copy()
                    display_df_vs_formatted['Top Coverages'] = display_df_vs_formatted['Top Coverages'].str.replace('\n', ' | ')
                    
                    st.dataframe(
                        display_df_vs_formatted,
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info(f"No defensive package data vs {selected_off_personnel}")
            else:
                st.info(f"No plays found vs {selected_off_personnel}")
        else:
            st.info("No offensive personnel data available")

        st.markdown("---")
        st.markdown("### Metric Definitions")
        
        with st.expander("Click to view defensive metric explanations"):
            st.markdown("""
            **Usage %** - Percentage of defensive plays using this package
            
            **Blitz %** - Percentage of pass plays where defense blitzed / total pass plays
            
            **Man %** - Percentage of pass plays using man coverage / total pass plays
            - *Man coverages include:* Cover 0, Cover 1, Cover 1 Double, Cover 2 Man
            
            **MOFO %** - Middle of Field Open percentage: pass plays with middle of the field open look / total pass plays
            
            **Disguise %** - Percentage of pass plays where pre-snap look (MOFO shown) differed from post-snap coverage (MOFO played) / pass plays
            
            **Top Coverages** - Most common coverage schemes within this category, shown as percentage of pass plays
            - *Cover 0* - Man coverage, no deep safety help
            - *Cover 1* - Man coverage with single-high safety
            - *Cover 2* - Two-deep zone coverage
            - *Cover 3* - Three-deep zone coverage (includes Cloud, Seam, and Double Cloud variants)
            - *Cover 4* - Quarters coverage (four-deep zones)
            - *Cover 6* - Half-field quarters, half-field Cover 2
            
            **Rankings** - Rank among all 32 teams with same filters applied (t- indicates tie)
            
            **Table 2 Filter** - Shows defensive tendencies specifically against the selected offensive personnel grouping
            """)

# Footer
st.markdown("---")
st.markdown("*Data: PFF 2025 Season Play Feed*")