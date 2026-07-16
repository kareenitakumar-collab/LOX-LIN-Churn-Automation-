import pandas as pd
import numpy as np
import os
import subprocess
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

def classify_dp(dp_data, max_dataset_date):
    """Applies the IF-THEN logic tree to classify a Delivery Point based on volume history."""
    
    dp_status = dp_data['DP Mapping Status'].iloc[0]
    if pd.notna(dp_status) and dp_status == False:
        return 'LOST'
    
    dp_data = dp_data.sort_values('Date')
    
    six_months_ago = max_dataset_date - relativedelta(months=5)
    last_6_months = dp_data[dp_data['Date'] >= six_months_ago]
    last_6_vols = last_6_months['Sum of Delivered Quantity (SCF)'].values
    
    if sum(last_6_vols) > 0:
        max_consecutive_zeros = 0
        current_zeros = 0
        for vol in last_6_vols:
            if vol == 0:
                current_zeros += 1
                max_consecutive_zeros = max(max_consecutive_zeros, current_zeros)
            else:
                current_zeros = 0
                
        if max_consecutive_zeros <= 5:
            return 'Active'
    
    all_vols = dp_data['Sum of Delivered Quantity (SCF)'].values
    
    gaps = []
    current_gap = 0
    has_started = False
    
    for vol in all_vols:
        if vol > 0:
            if has_started and current_gap > 0:
                gaps.append(current_gap)
            has_started = True
            current_gap = 0
        elif has_started:
            current_gap += 1
            
    current_volume_gap = current_gap 
    
    historical_start_stop = any(4 <= gap <= 9 for gap in gaps)
    
    if historical_start_stop and current_volume_gap <= 9:
        return 'Active-Seasonal'
    elif not historical_start_stop or current_volume_gap > 9:
        return 'LOST'
    else:
        return 'Active'

def process_product(product_name, vol_filename, map_filename, repo_dir):
    """Executes the data pipeline for a specific product line."""
    print(f"\n--- Starting Processing for {product_name} ---")
    
    vol_path = os.path.join(repo_dir, vol_filename)
    map_path = os.path.join(repo_dir, map_filename)
    
    try:
        print(f"Loading {product_name} Excel datasets from local repository...")
        df_vol = pd.read_excel(vol_path, engine='openpyxl')
        df_map = pd.read_excel(map_path, engine='openpyxl')
    except FileNotFoundError as e:
        print(f"Error: Could not find {vol_filename} or {map_filename} in {repo_dir}.")
        return []

    print(f"Merging data and mapping timelines...")
    
    # ---------------------------------------------------------
    # THE FIX: Clean invisible spaces from all column headers
    # ---------------------------------------------------------
    df_vol.columns = df_vol.columns.str.strip()
    df_map.columns = df_map.columns.str.strip()
    
    # Rename Active? to DP Mapping Status
    if 'Active?' in df_map.columns:
        df_map = df_map.rename(columns={'Active?': 'DP Mapping Status'})
    
    # Merge datasets
    df_merged = pd.merge(df_vol, df_map[['Delivery Point', 'DP Mapping Status']], 
                         on='Delivery Point', how='left')
    
    df_merged['Date'] = pd.to_datetime(df_merged['Period (Year)'].astype(str) + '-' + 
                                       df_merged['Period (Month)'].astype(str) + '-01')
    
    max_dataset_date = df_merged['Date'].max()
    dp_groups = df_merged.groupby('Delivery Point')
    
    churn_statuses = {}
    last_active_months = {}
    
    print(f"Evaluating Churn Logic for {product_name}...")
    for dp, group in dp_groups:
        min_date = group['Date'].min()
        all_months = pd.date_range(start=min_date, end=max_dataset_date, freq='MS')
        
        # --- THE FIX: Aggregate duplicate months by summing their volume ---
        group_agg = group.groupby('Date').agg({
            'Sum of Delivered Quantity (SCF)': 'sum',
            'DP Mapping Status': 'first'
        })
        
        # Now reindex using the safely aggregated data
        group_ts = group_agg.reindex(all_months).reset_index()
        group_ts = group_ts.rename(columns={'index': 'Date'})
        # -------------------------------------------------------------------
        
        group_ts['Sum of Delivered Quantity (SCF)'] = group_ts['Sum of Delivered Quantity (SCF)'].fillna(0)
        group_ts['DP Mapping Status'] = group_ts['DP Mapping Status'].ffill().bfill()
        
        status = classify_dp(group_ts, max_dataset_date)
        churn_statuses[dp] = status
        
        active_months = group_ts[group_ts['Sum of Delivered Quantity (SCF)'] > 0]
        if not active_months.empty:
            last_active_months[dp] = active_months['Date'].max()
        else:
            last_active_months[dp] = pd.NaT

    df_merged['Churn Status'] = df_merged['Delivery Point'].map(churn_statuses)
    
    print(f"Calculating Churn Summaries for {product_name}...")
    
    def tag_volume_category(row):
        if row['Churn Status'] == 'LOST':
            last_active = last_active_months.get(row['Delivery Point'])
            if pd.notna(last_active):
                window_start = last_active - relativedelta(months=11)
                if window_start <= row['Date'] <= last_active:
                    return 'Churn Window'
        return 'Regular Volume'

    df_merged['Volume Category'] = df_merged.apply(tag_volume_category, axis=1)
    
    # OUTPUT 1: Enhanced Dataset CSV
    enhanced_file_name = f'{product_name}_Churn_Dataset_Enhanced.csv'
    output1_path = os.path.join(repo_dir, enhanced_file_name)
    df_merged.drop(columns=['Date']).to_csv(output1_path, index=False)
    print(f"Exported CSV: {enhanced_file_name}")

    # OUTPUT 2: Summary Results CSV
    df_churn = df_merged[df_merged['Volume Category'] == 'Churn Window'].copy()
    
    churn_grouped = df_churn.groupby(['Period (Year)', 'Period (Month)'])['Sum of Delivered Quantity (SCF)'].sum().reset_index()
    churn_grouped = churn_grouped.rename(columns={'Sum of Delivered Quantity (SCF)': 'Churn Volume'})
    
    all_grouped = df_merged.groupby(['Period (Year)', 'Period (Month)'])['Sum of Delivered Quantity (SCF)'].sum().reset_index()
    all_grouped = all_grouped.rename(columns={'Sum of Delivered Quantity (SCF)': 'All Volume'})
    
    summary_monthly = pd.merge(all_grouped, churn_grouped, on=['Period (Year)', 'Period (Month)'], how='left')
    summary_monthly['Churn Volume'] = summary_monthly['Churn Volume'].fillna(0)
    summary_monthly['Monthly Churn %'] = (summary_monthly['Churn Volume'] / summary_monthly['All Volume']).replace([np.inf, -np.inf], 0)
    
    summary_yearly = summary_monthly.groupby('Period (Year)')[['All Volume', 'Churn Volume']].sum().reset_index()
    summary_yearly['Yearly Churn %'] = (summary_yearly['Churn Volume'] / summary_yearly['All Volume']).replace([np.inf, -np.inf], 0)
    
    summary_monthly['Monthly Churn %'] = (summary_monthly['Monthly Churn %'] * 100).round(2).astype(str) + '%'
    summary_yearly['Yearly Churn %'] = (summary_yearly['Yearly Churn %'] * 100).round(2).astype(str) + '%'

    summary_final = pd.concat([summary_monthly, pd.DataFrame(columns=[' | ']), summary_yearly], axis=1)
    
    summary_file_name = f'{product_name}_Churn_Summary_Results.csv'
    output2_path = os.path.join(repo_dir, summary_file_name)
    summary_final.to_csv(output2_path, index=False)
    print(f"Exported CSV: {summary_file_name}")
    
    return [enhanced_file_name, summary_file_name]

def push_to_github(repo_dir, generated_files):
    """Stages, commits, and pushes the newly generated CSVs to GitHub."""
    print("\n--- Pushing Results to GitHub ---")
    
    if not generated_files:
        print("No files were generated to push.")
        return

    try:
        for file in generated_files:
            subprocess.run(["git", "add", file], cwd=repo_dir, check=True)
            print(f"Staged: {file}")
            
        status = subprocess.run(["git", "status", "--porcelain"], cwd=repo_dir, capture_output=True, text=True)
        if not status.stdout.strip():
            print("No new data to commit. The CSV files are identical to the last run.")
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        commit_message = f"Automated update: Churn results generated on {timestamp}"
        
        subprocess.run(["git", "commit", "-m", commit_message], cwd=repo_dir, check=True)
        print("Committed successfully.")
        
        print("Pushing to remote repository...")
        subprocess.run(["git", "push"], cwd=repo_dir, check=True)
        print("Successfully pushed to GitHub!")

    except subprocess.CalledProcessError as e:
        print(f"\nGit operation failed. Error: {e}")
        print("Ensure you have push access and your terminal is authenticated with GitHub.")

def main():
    repo_directory = os.path.dirname(os.path.abspath(__file__))
    
    products_to_process = {
        'LIN': ('ALTO_LIN_Volume Data_New (1).xlsx', 'LIN_DP_Mapping.xlsx'),
        'LOX': ('ALTO_LOX_Volume Data.xlsx', 'LOX_DP_Mapping.xlsx')
    }
    
    print(f"Running pipeline in local repository: {repo_directory}")
    
    all_generated_files = []
    
    for product_name, filenames in products_to_process.items():
        files = process_product(
            product_name=product_name,
            vol_filename=filenames[0],
            map_filename=filenames[1],
            repo_dir=repo_directory
        )
        all_generated_files.extend(files)
        
    push_to_github(repo_directory, all_generated_files)

if __name__ == "__main__":
    main()