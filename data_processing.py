import pandas as pd
import numpy as np
from typing import Dict, List, Tuple

def load_data(filepath: str = 'Data/PFF_2025_FULL_Play_Feed.csv') -> pd.DataFrame:
    """
    Load PFF data from CSV file.
    
    Args:
        filepath: Path to the CSV file
        
    Returns:
        DataFrame with raw PFF data
    """
    df = pd.read_csv(filepath)
    return df


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean PFF data by removing special teams, spikes, kneels, etc.
    Only keep plays where pff_RUNPASS is 'P' or 'R'.
    
    Args:
        df: Raw PFF DataFrame
        
    Returns:
        Cleaned DataFrame
    """
    # Filter to only Pass (P) or Run (R) plays
    df_clean = df[df['pff_RUNPASS'].isin(['P', 'R'])].copy()
    
    return df_clean


def parse_clock_to_minutes(clock_str: str) -> int:
    """
    Parse pff_CLOCK string (MM:SS format) to minutes remaining in quarter.
    
    Args:
        clock_str: Time string in MM:SS format (e.g., "14:53")
        
    Returns:
        Minutes as integer
    """
    if pd.isna(clock_str):
        return 0
    
    try:
        parts = str(clock_str).split(':')
        minutes = int(parts[0])
        return minutes
    except:
        return 0


def normalize_formation_group(formation: str) -> str:
    """
    Normalize formation group to have larger number first.
    Examples: 1x3 -> 3x1, 1x2 -> 2x1, 2x2 stays 2x2
    
    Args:
        formation: Formation string (e.g., "1x3")
        
    Returns:
        Normalized formation string
    """
    if pd.isna(formation):
        return formation
    
    # Check if format is NxN
    if 'x' in str(formation):
        parts = str(formation).split('x')
        if len(parts) == 2:
            try:
                num1 = int(parts[0])
                num2 = int(parts[1])
                # Return larger number first
                return f"{max(num1, num2)}x{min(num1, num2)}"
            except:
                return formation
    
    return formation


def add_calculated_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add calculated columns needed for analysis.
    
    Args:
        df: Cleaned DataFrame
        
    Returns:
        DataFrame with additional calculated columns
    """
    df = df.copy()
    
    # Parse clock to seconds
    # Parse clock to minutes
    df['minutes_remaining'] = df['pff_CLOCK'].apply(parse_clock_to_minutes)
    
    # Normalize formation groups
    df['pff_OFFFORMATIONGROUP_NORM'] = df['pff_OFFFORMATIONGROUP'].apply(normalize_formation_group)
    
    # Binary indicators for tendency calculations
    df['is_run'] = (df['pff_RUNPASS'] == 'R').astype(int)
    df['has_motion'] = df['pff_SHIFTMOTION'].notna().astype(int)
    df['is_play_action'] = df['pff_PLAYACTION'].fillna(0).astype(int)
    df['is_standard_dropback'] = (
        (df['pff_DROPBACKTYPE'].isin(['SD', 'SR', 'SL'])) & 
        (df['pff_PLAYACTION'] == 0)
    ).astype(int)

    # Add defensive columns
    df = add_defensive_columns(df)
    
    return df


def filter_data(df: pd.DataFrame, filters: Dict) -> pd.DataFrame:
    """
    Apply user-selected filters to the dataset.
    
    Args:
        df: DataFrame with calculated columns
        filters: Dictionary of filter parameters
        
    Returns:
        Filtered DataFrame
    """
    df_filtered = df.copy()
    
    # Team filter
    if filters.get('team'):
        df_filtered = df_filtered[df_filtered['pff_OFFTEAM'] == filters['team']]
    
   # Week filter
    if filters.get('weeks') and len(filters['weeks']) > 0:
        df_filtered = df_filtered[df_filtered['pff_WEEK'].astype(str).isin(filters['weeks'])]
    
    # Quarter filter
    if filters.get('quarters') and len(filters['quarters']) > 0:
        df_filtered = df_filtered[df_filtered['pff_QUARTER'].isin(filters['quarters'])]
    
    # Time remaining filter
    if filters.get('time_range'):
        min_time, max_time = filters['time_range']
        df_filtered = df_filtered[
            (df_filtered['minutes_remaining'] >= min_time) & 
            (df_filtered['minutes_remaining'] <= max_time)
        ]
    
    # Down filter
    if filters.get('downs') and len(filters['downs']) > 0:
        df_filtered = df_filtered[df_filtered['pff_DOWN'].isin(filters['downs'])]
    
    # Yards to go filter
    if filters.get('yards_to_go_range'):
        min_ytg, max_ytg = filters['yards_to_go_range']
        df_filtered = df_filtered[
            (df_filtered['pff_DISTANCE'] >= min_ytg) & 
            (df_filtered['pff_DISTANCE'] <= max_ytg)
        ]
    
    # Yardline filter
    if filters.get('yardline_range'):
        min_yl, max_yl = filters['yardline_range']
        df_filtered = df_filtered[
            (df_filtered['pff_YARDS_TO_GOAL_LINE'] >= min_yl) & 
            (df_filtered['pff_YARDS_TO_GOAL_LINE'] <= max_yl)
        ]
    
    return df_filtered


def calculate_overall_tendencies(df: pd.DataFrame) -> Dict:
    """
    Calculate overall team tendencies for scorecard display.
    
    Args:
        df: Filtered DataFrame for selected team
        
    Returns:
        Dictionary with overall tendency metrics
    """
    total_plays = len(df)
    
    if total_plays == 0:
        return {
            'total_plays': 0,
            'run_pct': 0,
            'pa_pct': 0,
            'db_pct': 0,
            'motion_pct': 0,
            'top_run_concepts': []
        }
    
    # Calculate percentages
    run_pct = (df['is_run'].sum() / total_plays) * 100
    pa_pct = (df['is_play_action'].sum() / total_plays) * 100
    db_pct = (df['is_standard_dropback'].sum() / total_plays) * 100
    motion_pct = (df['has_motion'].sum() / total_plays) * 100
    
    # Get top 3 run concepts
    run_plays = df[df['is_run'] == 1]
    top_run_concepts = []
    
    if len(run_plays) > 0:
        run_concept_counts = run_plays['pff_RUNCONCEPTPRIMARY'].value_counts()
        for concept, count in run_concept_counts.head(3).items():
            pct = (count / len(run_plays)) * 100
            top_run_concepts.append(f"{concept} ({pct:.1f}%)")
    
    return {
        'total_plays': total_plays,
        'run_pct': run_pct,
        'pa_pct': pa_pct,
        'db_pct': db_pct,
        'motion_pct': motion_pct,
        'top_run_concepts': top_run_concepts
    }


def calculate_category_tendencies(df: pd.DataFrame, category_column: str) -> pd.DataFrame:
    """
    Calculate tendencies broken down by a specific category (Personnel, Formation, QB Alignment).
    
    Args:
        df: Filtered DataFrame for selected team
        category_column: Column name to group by (e.g., 'pff_OFFPERSONNELBASIC')
        
    Returns:
        DataFrame with tendency metrics by category
    """
    if len(df) == 0:
        return pd.DataFrame()
    
    total_team_plays = len(df)
    
    # Group by category
    grouped = df.groupby(category_column)
    
    results = []
    
    for category, group in grouped:
        category_plays = len(group)
        
        # Calculate percentages
        usage_pct = (category_plays / total_team_plays) * 100
        run_pct = (group['is_run'].sum() / category_plays) * 100 if category_plays > 0 else 0
        pa_pct = (group['is_play_action'].sum() / category_plays) * 100 if category_plays > 0 else 0
        db_pct = (group['is_standard_dropback'].sum() / category_plays) * 100 if category_plays > 0 else 0
        motion_pct = (group['has_motion'].sum() / category_plays) * 100 if category_plays > 0 else 0
        
        # Get top 3 run concepts for this category
        run_plays = group[group['is_run'] == 1]
        top_run_concepts = []
        
        if len(run_plays) > 0:
            run_concept_counts = run_plays['pff_RUNCONCEPTPRIMARY'].value_counts()
            for concept, count in run_concept_counts.head(3).items():
                pct = (count / len(run_plays)) * 100
                top_run_concepts.append(f"{concept} ({pct:.1f}%)")
        
        results.append({
            'Category': category,
            'Plays': category_plays,
            'Usage_Pct': usage_pct,
            'Run_Pct': run_pct,
            'PA_Pct': pa_pct,
            'DB_Pct': db_pct,
            'Motion_Pct': motion_pct,
            'Top_Run_Concepts': '\n'.join(top_run_concepts) if top_run_concepts else ''
        })
    
    result_df = pd.DataFrame(results)
    
    # Sort by usage percentage (descending)
    result_df = result_df.sort_values('Usage_Pct', ascending=False).reset_index(drop=True)
    
    return result_df


def calculate_all_teams_tendencies(df: pd.DataFrame, filters: Dict, category_column: str) -> pd.DataFrame:
    """
    Calculate tendencies for all teams to enable ranking.
    
    Args:
        df: Full dataset (before team filter)
        filters: Filter parameters (excluding team)
        category_column: Column to group by
        
    Returns:
        DataFrame with all teams' tendencies aggregated
    """
    # Apply all filters except team filter
    df_filtered = df.copy()
    
    # Week filter
    if filters.get('weeks') and len(filters['weeks']) > 0:
        df_filtered = df_filtered[df_filtered['pff_WEEK'].astype(str).isin(filters['weeks'])]
    
    # Quarter filter
    if filters.get('quarters') and len(filters['quarters']) > 0:
        df_filtered = df_filtered[df_filtered['pff_QUARTER'].isin(filters['quarters'])]
    
    # Time remaining filter
    if filters.get('time_range'):
        min_time, max_time = filters['time_range']
        df_filtered = df_filtered[
            (df_filtered['minutes_remaining'] >= min_time) & 
            (df_filtered['minutes_remaining'] <= max_time)
        ]
    
    # Down filter
    if filters.get('downs') and len(filters['downs']) > 0:
        df_filtered = df_filtered[df_filtered['pff_DOWN'].isin(filters['downs'])]
    
    # Yards to go filter
    if filters.get('yards_to_go_range'):
        min_ytg, max_ytg = filters['yards_to_go_range']
        df_filtered = df_filtered[
            (df_filtered['pff_DISTANCE'] >= min_ytg) & 
            (df_filtered['pff_DISTANCE'] <= max_ytg)
        ]
    
    # Yardline filter
    if filters.get('yardline_range'):
        min_yl, max_yl = filters['yardline_range']
        df_filtered = df_filtered[
            (df_filtered['pff_YARDS_TO_GOAL_LINE'] >= min_yl) & 
            (df_filtered['pff_YARDS_TO_GOAL_LINE'] <= max_yl)
        ]
    
    # Calculate tendencies for each team
    all_teams_data = []
    
    for team in df_filtered['pff_OFFTEAM'].unique():
        team_df = df_filtered[df_filtered['pff_OFFTEAM'] == team]
        
        if len(team_df) == 0:
            continue
        
        total_plays = len(team_df)
        
        # Overall metrics
        overall_metrics = {
            'Team': team,
            'Total_Plays': total_plays,
            'Run_Pct': (team_df['is_run'].sum() / total_plays) * 100,
            'PA_Pct': (team_df['is_play_action'].sum() / total_plays) * 100,
            'DB_Pct': (team_df['is_standard_dropback'].sum() / total_plays) * 100,
            'Motion_Pct': (team_df['has_motion'].sum() / total_plays) * 100
        }
        
        all_teams_data.append(overall_metrics)
    
    return pd.DataFrame(all_teams_data)


def add_rankings(team_df: pd.DataFrame, all_teams_df: pd.DataFrame, metrics: List[str]) -> pd.DataFrame:
    """
    Add rankings to team's tendency metrics by comparing to all teams.
    
    Args:
        team_df: DataFrame with selected team's tendencies
        all_teams_df: DataFrame with all teams' tendencies
        metrics: List of metric column names to rank
        
    Returns:
        DataFrame with ranking columns added
    """
    df = team_df.copy()
    
    for metric in metrics:
        if metric not in df.columns or metric not in all_teams_df.columns:
            continue
        
        # For each row in team_df, calculate rank
        rankings = []
        
        for idx, row in df.iterrows():
            value = row[metric]
            
            # Count how many teams have higher value (descending rank)
            sorted_values = all_teams_df[metric].sort_values(ascending=False).values
            
            # Find rank (1-indexed)
            rank = np.where(sorted_values == value)[0]
            
            if len(rank) > 0:
                rank_value = rank[0] + 1
                
                # Check for ties
                tied_count = np.sum(sorted_values == value)
                if tied_count > 1:
                    rankings.append(f"t-{rank_value}")
                else:
                    rankings.append(f"{rank_value}")
            else:
                rankings.append("-")
        
        df[f'{metric}_Rank'] = rankings
    
    return df


def format_percentage_with_rank(value: float, rank: str) -> str:
    """
    Format percentage with rank for display.
    
    Args:
        value: Percentage value
        rank: Rank string (e.g., "12" or "t-12")
        
    Returns:
        Formatted string like "45.2% (12th)"
    """
    if pd.isna(value):
        return "-"
    
    # Add ordinal suffix
    if rank == "-":
        return f"{value:.1f}%"
    
    rank_num = rank.replace('t-', '')
    
    if rank.startswith('t-'):
        return f"{value:.1f}% (t-{rank_num}th)"
    else:
        # Add ordinal suffix (st, nd, rd, th)
        if rank_num.endswith('1') and rank_num != '11':
            suffix = 'st'
        elif rank_num.endswith('2') and rank_num != '12':
            suffix = 'nd'
        elif rank_num.endswith('3') and rank_num != '13':
            suffix = 'rd'
        else:
            suffix = 'th'
        
        return f"{value:.1f}% ({rank_num}{suffix})"
    
def parse_pass_rushers(rushers_str: str) -> int:
    """
    Parse pff_PASSRUSHPLAYERS to extract number of pass rushers.
    Format: "4; PHI 53 (LILB); PHI 90 (NRT); PHI 94 (RE); PHI 97 (DLT)"
    
    Args:
        rushers_str: String with number of rushers and player details
        
    Returns:
        Number of pass rushers as integer
    """
    if pd.isna(rushers_str):
        return 0
    
    try:
        # Split by semicolon and get first element
        parts = str(rushers_str).split(';')
        num_rushers = int(parts[0].strip())
        return num_rushers
    except:
        return 0


def is_man_coverage(coverage: str) -> bool:
    """
    Determine if coverage is Man coverage based on pff_PASS_COVERAGE_BASIC.
    
    Args:
        coverage: Coverage type string
        
    Returns:
        True if Man coverage, False otherwise
    """
    if pd.isna(coverage):
        return False
    
    man_coverages = ['COVER 0', 'COVER 1', 'COVER 1 DOUBLE', 'COVER 2 MAN']
    return str(coverage).strip().upper() in man_coverages

def normalize_coverage(coverage: str) -> str:
    """
    Normalize coverage names by combining variants into base coverage.
    
    Args:
        coverage: Coverage type string
        
    Returns:
        Normalized coverage string
    """
    if pd.isna(coverage):
        return coverage
    
    coverage_str = str(coverage).strip().upper()
    
    # Combine Cover 3 variants
    if coverage_str in ['COVER 3 CLOUD', 'COVER 3 DBL CLOUD', 'COVER 3 SEAM']:
        return 'COVER 3'
    
    return coverage_str

def add_defensive_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add defensive-specific calculated columns.
    
    Args:
        df: DataFrame with offensive columns already added
        
    Returns:
        DataFrame with defensive columns added
    """
    df = df.copy()

    # Normalize coverage names
    df['pff_PASS_COVERAGE_NORMALIZED'] = df['pff_PASS_COVERAGE_BASIC'].apply(normalize_coverage)
    
    # Parse number of pass rushers
    df['num_pass_rushers'] = df['pff_PASSRUSHPLAYERS'].apply(parse_pass_rushers)
    
    # Parse number of pass rushers (keep for potential future use)
    df['num_pass_rushers'] = df['pff_PASSRUSHPLAYERS'].apply(parse_pass_rushers)
    
    # Binary: Is blitz (from pff_BLITZDOG column, only on pass plays)
    df['is_blitz'] = (df['pff_BLITZDOG'] == 1).astype(int)
    
    # Binary: Is man coverage
    df['is_man_coverage'] = df['pff_PASS_COVERAGE_BASIC'].apply(is_man_coverage).astype(int)
    
    # Binary: Is MOFO (Middle of Field Open)
    df['is_mofo'] = (df['pff_MOFOCPLAYED'] == 'O').astype(int)
    
    # Binary: Is disguise (MOFOCSHOWN != MOFOCPLAYED, both not null)
    df['is_disguise'] = (
        (df['pff_MOFOCSHOWN'].notna()) & 
        (df['pff_MOFOCPLAYED'].notna()) & 
        (df['pff_MOFOCSHOWN'] != df['pff_MOFOCPLAYED'])
    ).astype(int)
    
    # Binary: Has valid MOFO data (for disguise denominator)
    df['has_mofo_data'] = (
        (df['pff_MOFOCSHOWN'].notna()) & 
        (df['pff_MOFOCPLAYED'].notna())
    ).astype(int)
    
    return df


def calculate_defensive_overall_tendencies(df: pd.DataFrame) -> Dict:
    """
    Calculate overall defensive team tendencies for scorecard display.
    Metrics calculated against pass plays only.
    
    Args:
        df: Filtered DataFrame for selected team (defensive perspective)
        
    Returns:
        Dictionary with overall defensive tendency metrics
    """
    total_plays = len(df)
    pass_plays = df[df['pff_RUNPASS'] == 'P']
    total_pass_plays = len(pass_plays)
    
    if total_pass_plays == 0:
        return {
            'total_plays': total_plays,
            'blitz_pct': 0,
            'man_pct': 0,
            'mofo_pct': 0,
            'disguise_pct': 0,
            'top_coverages': []
        }
    
    # Calculate percentages (all against pass plays)
    blitz_pct = (pass_plays['is_blitz'].sum() / total_pass_plays) * 100
    man_pct = (pass_plays['is_man_coverage'].sum() / total_pass_plays) * 100
    mofo_pct = (pass_plays['is_mofo'].sum() / total_pass_plays) * 100
    
    # Disguise: only count plays with valid MOFO data
    pass_plays_with_mofo = pass_plays[pass_plays['has_mofo_data'] == 1]
    if len(pass_plays_with_mofo) > 0:
        disguise_pct = (pass_plays_with_mofo['is_disguise'].sum() / len(pass_plays_with_mofo)) * 100
    else:
        disguise_pct = 0
    
    # Get top 3 coverages
    top_coverages = []
    if total_pass_plays > 0:
        coverage_counts = pass_plays['pff_PASS_COVERAGE_NORMALIZED'].value_counts()
        for coverage, count in coverage_counts.head(3).items():
            pct = (count / total_pass_plays) * 100
            top_coverages.append(f"{coverage} ({pct:.1f}%)")
    
    return {
        'total_plays': total_plays,
        'blitz_pct': blitz_pct,
        'man_pct': man_pct,
        'mofo_pct': mofo_pct,
        'disguise_pct': disguise_pct,
        'top_coverages': top_coverages
    }


def calculate_defensive_category_tendencies(df: pd.DataFrame, category_column: str) -> pd.DataFrame:
    """
    Calculate defensive tendencies broken down by category (e.g., Defensive Package).
    
    Args:
        df: Filtered DataFrame for selected team
        category_column: Column name to group by (e.g., 'pff_DEF_PACKAGE')
        
    Returns:
        DataFrame with defensive tendency metrics by category
    """
    if len(df) == 0:
        return pd.DataFrame()
    
    total_team_plays = len(df)
    
    # Group by category
    grouped = df.groupby(category_column)
    
    results = []
    
    for category, group in grouped:
        category_plays = len(group)
        pass_plays = group[group['pff_RUNPASS'] == 'P']
        total_pass_plays = len(pass_plays)
        
        # Calculate percentages
        usage_pct = (category_plays / total_team_plays) * 100
        
        if total_pass_plays > 0:
            blitz_pct = (pass_plays['is_blitz'].sum() / total_pass_plays) * 100
            man_pct = (pass_plays['is_man_coverage'].sum() / total_pass_plays) * 100
            mofo_pct = (pass_plays['is_mofo'].sum() / total_pass_plays) * 100
            
            # Disguise: only count plays with valid MOFO data
            pass_plays_with_mofo = pass_plays[pass_plays['has_mofo_data'] == 1]
            if len(pass_plays_with_mofo) > 0:
                disguise_pct = (pass_plays_with_mofo['is_disguise'].sum() / len(pass_plays_with_mofo)) * 100
            else:
                disguise_pct = 0
        else:
            blitz_pct = 0
            man_pct = 0
            mofo_pct = 0
            disguise_pct = 0
        
        # Get top 3 coverages for this category
        top_coverages = []
        if total_pass_plays > 0:
            coverage_counts = pass_plays['pff_PASS_COVERAGE_NORMALIZED'].value_counts()
            for coverage, count in coverage_counts.head(3).items():
                pct = (count / total_pass_plays) * 100
                top_coverages.append(f"{coverage} ({pct:.1f}%)")
        
        results.append({
            'Category': category,
            'Plays': category_plays,
            'Usage_Pct': usage_pct,
            'Blitz_Pct': blitz_pct,
            'Man_Pct': man_pct,
            'MOFO_Pct': mofo_pct,
            'Disguise_Pct': disguise_pct,
            'Top_Coverages': '\n'.join(top_coverages) if top_coverages else ''
        })
    
    result_df = pd.DataFrame(results)
    
    # Sort by usage percentage (descending)
    result_df = result_df.sort_values('Usage_Pct', ascending=False).reset_index(drop=True)
    
    return result_df


def calculate_all_teams_defensive_tendencies(df: pd.DataFrame, filters: Dict) -> pd.DataFrame:
    """
    Calculate defensive tendencies for all teams to enable ranking.
    
    Args:
        df: Full dataset (before team filter)
        filters: Filter parameters (excluding team)
        
    Returns:
        DataFrame with all teams' defensive tendencies aggregated
    """
    # Apply all filters except team filter
    df_filtered = df.copy()
    
    if filters.get('weeks') and len(filters['weeks']) > 0:
        df_filtered = df_filtered[df_filtered['pff_WEEK'].astype(str).isin(filters['weeks'])]
    
    if filters.get('quarters') and len(filters['quarters']) > 0:
        df_filtered = df_filtered[df_filtered['pff_QUARTER'].isin(filters['quarters'])]
    
    if filters.get('time_range'):
        min_time, max_time = filters['time_range']
        df_filtered = df_filtered[
            (df_filtered['minutes_remaining'] >= min_time) & 
            (df_filtered['minutes_remaining'] <= max_time)
        ]
    
    if filters.get('downs') and len(filters['downs']) > 0:
        df_filtered = df_filtered[df_filtered['pff_DOWN'].isin(filters['downs'])]
    
    if filters.get('yards_to_go_range'):
        min_ytg, max_ytg = filters['yards_to_go_range']
        df_filtered = df_filtered[
            (df_filtered['pff_DISTANCE'] >= min_ytg) & 
            (df_filtered['pff_DISTANCE'] <= max_ytg)
        ]
    
    if filters.get('yardline_range'):
        min_yl, max_yl = filters['yardline_range']
        df_filtered = df_filtered[
            (df_filtered['pff_YARDS_TO_GOAL_LINE'] >= min_yl) & 
            (df_filtered['pff_YARDS_TO_GOAL_LINE'] <= max_yl)
        ]
    
    # Calculate defensive tendencies for each team
    all_teams_data = []
    
    for team in df_filtered['pff_DEFTEAM'].unique():
        team_df = df_filtered[df_filtered['pff_DEFTEAM'] == team]
        
        if len(team_df) == 0:
            continue
        
        total_plays = len(team_df)
        pass_plays = team_df[team_df['pff_RUNPASS'] == 'P']
        total_pass_plays = len(pass_plays)
        
        if total_pass_plays == 0:
            continue
        
        # Overall metrics
        blitz_pct = (pass_plays['is_blitz'].sum() / total_pass_plays) * 100
        man_pct = (pass_plays['is_man_coverage'].sum() / total_pass_plays) * 100
        mofo_pct = (pass_plays['is_mofo'].sum() / total_pass_plays) * 100
        
        # Disguise
        pass_plays_with_mofo = pass_plays[pass_plays['has_mofo_data'] == 1]
        if len(pass_plays_with_mofo) > 0:
            disguise_pct = (pass_plays_with_mofo['is_disguise'].sum() / len(pass_plays_with_mofo)) * 100
        else:
            disguise_pct = 0
        
        all_teams_data.append({
            'Team': team,
            'Total_Plays': total_plays,
            'Blitz_Pct': blitz_pct,
            'Man_Pct': man_pct,
            'MOFO_Pct': mofo_pct,
            'Disguise_Pct': disguise_pct
        })
    
    return pd.DataFrame(all_teams_data)