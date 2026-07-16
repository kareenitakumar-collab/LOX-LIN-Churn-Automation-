import pandas as pd
import numpy as np
import os
import subprocess
import warnings
from datetime import datetime
from dateutil.relativedelta import relativedelta
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt

# Suppress warnings for clean terminal output
warnings.filterwarnings('ignore')

def build_logistic_risk_model(enhanced_csv_path, product_name, repo_dir):
    """
    Trains a Logistic Regression model to predict the probability of churn.
    Returns the name of the generated file for Git tracking.
    """
    print(f"\n[{product_name}] Building Logistic Risk Model for Customer Profiling...")
    
    try:
        df = pd.read_csv(enhanced_csv_path)
    except FileNotFoundError:
        print(f"Error: {enhanced_csv_path} not found. Run the churn automation script first.")
        return []

    # Format dates
    df['Date'] = pd.to_datetime(df['Period (Year)'].astype(str) + '-' + df['Period (Month)'].astype(str) + '-01')
    
    max_date = df['Date'].max()
    six_months_ago = max_date - relativedelta(months=5)
    recent_data = df[df['Date'] >= six_months_ago]
    
    features = recent_data.groupby('Delivery Point').agg(
        Avg_6M_Volume=('Sum of Delivered Quantity (SCF)', 'mean'),
        Vol_Std_Dev=('Sum of Delivered Quantity (SCF)', 'std'),
        Zero_Volume_Months=('Sum of Delivered Quantity (SCF)', lambda x: (x == 0).sum())
    ).reset_index()
    
    features['Vol_Std_Dev'] = features['Vol_Std_Dev'].fillna(0)
    
    status_df = df[['Delivery Point', 'Churn Status']].drop_duplicates(subset=['Delivery Point'], keep='last')
    model_data = pd.merge(features, status_df, on='Delivery Point')
    
    model_data['Is_Lost'] = np.where(model_data['Churn Status'] == 'LOST', 1, 0)
    
    X = model_data[['Avg_6M_Volume', 'Vol_Std_Dev', 'Zero_Volume_Months']]
    y = model_data['Is_Lost']
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    log_model = LogisticRegression(class_weight='balanced', random_state=42)
    log_model.fit(X_scaled, y)
    
    active_customers = model_data[model_data['Is_Lost'] == 0].copy()
    X_active = active_customers[['Avg_6M_Volume', 'Vol_Std_Dev', 'Zero_Volume_Months']]
    
    if len(X_active) > 0:
        X_active_scaled = scaler.transform(X_active)
        churn_probs = log_model.predict_proba(X_active_scaled)[:, 1]
        active_customers['Churn_Probability_%'] = (churn_probs * 100).round(2)
        
        def assign_risk_profile(prob):
            if prob >= 75: return 'High Risk (Zone 1/2)'
            elif prob >= 40: return 'Medium Risk (Zone 3/4)'
            else: return 'Low Risk (Zone 5/6)'
            
        active_customers['Risk_Profile'] = active_customers['Churn_Probability_%'].apply(assign_risk_profile)
        
        output_df = active_customers[['Delivery Point', 'Avg_6M_Volume', 'Zero_Volume_Months', 'Churn_Probability_%', 'Risk_Profile']]
        output_df = output_df.sort_values('Churn_Probability_%', ascending=False)
        
        output_filename = f"{product_name}_Customer_Risk_Profiles.csv"
        output_path = os.path.join(repo_dir, output_filename)
        output_df.to_csv(output_path, index=False)
        print(f"Exported Risk Profiles: {output_filename}")
        
        return [output_filename]
    
    return []

def build_multivariable_forecast(summary_csv_path, product_name, repo_dir):
    """
    Trains a Multivariable Linear Regression model to forecast 12 months.
    Returns the names of the generated CSV and Image files for Git tracking.
    """
    print(f"[{product_name}] Building Multivariable Regression Forecast (12-Month Outlook)...")
    
    try:
        df = pd.read_csv(summary_csv_path)
    except FileNotFoundError:
        print(f"Error: {summary_csv_path} not found.")
        return []

    # Clean the summary data
    df = df.dropna(subset=['Period (Month)'])
    df['Monthly Churn %'] = df['Monthly Churn %'].astype(str).str.replace('%', '').astype(float)
    
    # THE FIX: Safely parse dates regardless of if Month is a number ("4") or text ("Apr")
    # 1. Ensure Year is a clean integer string (handles decimals like 2023.0 safely)
    year_str = df['Period (Year)'].astype(float).astype(int).astype(str)
    
    # 2. Treat the month simply as text
    month_str = df['Period (Month)'].astype(str).str.replace('.0', '', regex=False)
    
    # 3. Create the Date column (Pandas automatically understands "2023-Apr-01")
    df['Date'] = pd.to_datetime(year_str + '-' + month_str + '-01')
    
    df = df.sort_values('Date').reset_index(drop=True)
    
    df['Time_Index'] = df.index
    df['Month_Num'] = df['Date'].dt.month
    
    X = df[['Time_Index', 'Month_Num']]
    y = df['Monthly Churn %']
    
    lin_model = LinearRegression()
    lin_model.fit(X, y)
    
    last_date = df['Date'].max()
    future_dates = [last_date + relativedelta(months=i) for i in range(1, 13)]
    
    future_df = pd.DataFrame({'Date': future_dates})
    future_df['Time_Index'] = range(len(df), len(df) + 12)
    future_df['Month_Num'] = future_df['Date'].dt.month
    
    future_X = future_df[['Time_Index', 'Month_Num']]
    future_df['Forecasted_Churn_%'] = lin_model.predict(future_X).round(2)
    future_df['Forecasted_Churn_%'] = future_df['Forecasted_Churn_%'].clip(lower=0)
    
    export_df = future_df[['Date', 'Forecasted_Churn_%']]
    output_filename = f"{product_name}_Churn_Forecast_12M.csv"
    output_path = os.path.join(repo_dir, output_filename)
    export_df.to_csv(output_path, index=False)
    print(f"Exported 12M Forecast: {output_filename}")
    
    # Generate and Save Visual
   # -----------------------------------------
    # Custom Corporate Visual Generation
    # -----------------------------------------
    brand_primary = '#0033A0'    
    brand_secondary = '#E31837'  
    text_color = '#333333'       
    grid_color = '#E0E0E0'       

    # 1. Setup the Canvas Explicitly
    fig, ax = plt.subplots(figsize=(12, 6))
    fig.patch.set_facecolor('white') # Force a solid white background so it never blends in
    ax.set_facecolor('#FAFAFA')      
    
    # 2. Plot the Data (using .values to strip confusing indexes)
    ax.plot(df['Date'].values, df['Monthly Churn %'].values, 
             label='Historical Actuals', marker='o', markersize=6, 
             linewidth=2.5, color=brand_primary)
             
    ax.plot(future_df['Date'].values, future_df['Forecasted_Churn_%'].values, 
             label='Model Forecast', marker='s', markersize=6, 
             linewidth=2.5, linestyle='--', color=brand_secondary)
    
    # 3. Typography and Labels
    ax.set_title(f'{product_name} - 12-Month Multivariable Churn Forecast', 
              fontsize=16, fontweight='bold', color=text_color, pad=20, fontfamily='sans-serif')
    ax.set_xlabel('Timeline', fontsize=12, fontweight='bold', color=text_color, labelpad=10)
    ax.set_ylabel('Monthly Churn Rate (%)', fontsize=12, fontweight='bold', color=text_color, labelpad=10)
    
    # 4. Clean Grid & Borders
    ax.grid(True, axis='y', linestyle='-', alpha=0.7, color=grid_color)
    ax.grid(False, axis='x') 
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(grid_color)
    ax.spines['bottom'].set_color(text_color)
    
    # Clean up the date format on the bottom axis so they don't overlap
    fig.autofmt_xdate()
    
    ax.legend(frameon=True, facecolor='white', edgecolor=grid_color, 
               fontsize=11, loc='upper left', framealpha=1)
    
    # 5. Save Image SAFELY
    img_filename = f"{product_name}_Forecast_Visual.png"
    img_path = os.path.join(repo_dir, img_filename)
    
    # Force the white background to save into the file, regardless of your VS Code theme
    plt.savefig(img_path, facecolor=fig.get_facecolor(), transparent=False, bbox_inches='tight', dpi=300)
    plt.close(fig)
    print(f"Exported High-Res Visual: {img_filename}")
    
    return [output_filename, img_filename]

def push_to_github(repo_dir, generated_files):
    """Stages, commits, and pushes the newly generated files to GitHub."""
    print("\n--- Pushing Forecast Results to GitHub ---")
    
    if not generated_files:
        print("No files were generated to push.")
        return

    try:
        for file in generated_files:
            subprocess.run(["git", "add", file], cwd=repo_dir, check=True)
            print(f"Staged: {file}")
            
        status = subprocess.run(["git", "status", "--porcelain"], cwd=repo_dir, capture_output=True, text=True)
        if not status.stdout.strip():
            print("No new data to commit. The models produced the same output as the last run.")
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        commit_message = f"Automated forecast update: Models and visuals generated on {timestamp}"
        
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
    print(f"Initializing Predictive Modeling Sequence in: {repo_directory}")
    
    products = ['LIN', 'LOX']
    all_generated_files = []
    
    for prod in products:
        enhanced_csv = os.path.join(repo_directory, f"{prod}_Churn_Dataset_Enhanced.csv")
        summary_csv = os.path.join(repo_directory, f"{prod}_Churn_Summary_Results.csv")
        
        # Run models and collect filenames for Git
        risk_files = build_logistic_risk_model(enhanced_csv, prod, repo_directory)
        forecast_files = build_multivariable_forecast(summary_csv, prod, repo_directory)
        
        all_generated_files.extend(risk_files)
        all_generated_files.extend(forecast_files)
        
    print("\nPredictive Modeling Complete. Triggering Git Sync...")
    
    # Push everything to GitHub
    push_to_github(repo_directory, all_generated_files)

if __name__ == "__main__":
    main()