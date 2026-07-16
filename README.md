# Churn Automation / Predictive Analysis 
Overview: This repository contains a Python-based foreccasting tool made to analyze historical delivered volumes for Liquid Nitrogen (LIN) and Liquid Oxygen (LOX), categorized by "Final Market Centers", "Delivery Point #", or "Ship-To-Name". The script cleans raw delivery data, while identifying customer churn, and using Linear Regression to proect future delivery volumes. This tool acts as an automated early-warning system. In generating descriptive risk labels by comparing historical baseline averages against future predictions, allowing operations and sales teams able to easily at-risk accounts in a Power BI Dashboard view.

Key Features:

Time-Series Linear Regression: Projects a 36-month future delivery forecast using a restricted 36-month histroical memory to prevent pandemic-era weight or outdated information from skewing current momentum.

Automated Churn Detection: Scans delivery cycles and automatically flags accounts as "Churned" if they register zero delivery volume for 6 consecutive months.

Risk Banding & Margins: Calculates the variance between a market center's 36-month historical average and its predicted future volume, assigning tags such as "High", "Risk", "Monitor", "Growth", "High Growth".

Descriptive Outputs for BI: Generates clean, readible text columns (ex. "Between 5% and 20% beloow") to be used directly in Power BI tooltips and matrices

Zero-Floor Safety Net: Constrains mathematical regression to prevent forecasting unattainable/impossible negative delivery volumes

Output Files: When the script finishes running successfully, it generates distinct Excel/CSV files designed to bee imported directely into a Power BI Semantic Model. Split into two categories ->

Model Outputs (Historical Data) 
a. LOX_Model_Output.xlsx & LIN_Model_Output.xlsx 
b. Purpose: The "What Has Happened" files 
c. Contents: Contains all cleaned historical delivery data up to the present day. Included calculated featres such as 3YearAvg, YoY Change, seasonal tags, and the Churn flag based on VolumeZero metric.

Forecast Files (Future Predictions)
a. LOX_Forecast.xlsx & LIN_Forecast.xlsx 
b. Purpose: The "What's Next" files
c. Contents: Contains exactly 36 months of future calendar dates (ForecastDate) and predicted delivery volumes (Forecast Volume)
d. Risk Metrics Include:

Historical Average - Baseline normal volume for that specific market center over the last 3 years

PctDiffFromAvg - Descriptive variance text (ex. "> 20% below")

RiskLabel - Short-hand catergorical tags for conditions formattting (High Risk, Monitor, Stable, Growth, High Growth)

PowerBI Integration Guide: 
This Visual Studio Python code is designed to feed a dual-axis Power BI Dashboard. In order to obtain the seamless historical-to-forecast trendlines and the Risk Matrix working:

1. Import the Data: Load both Model Output and Forecast files into PowerBI, whereever they are saved.

2. Create a Master Calendar Table: Use DAX (CALENDARAUTO()) to generative a continuous Date table, label it as Date Table.

3. Build the Bridge: In the Model View, connect the Data column from the Calendar table to both the historical "Date" column and the future "ForecastDate" column.

4. Visuals: * Trendlines: Use Calendar Date hierarchy as the X-axis to draw a continious, unbroken line showing actuals seamlessly transitioning into the regression forecast

 * Early Warning: Drop the RiskLabel column into Conditional Formatting rules to automatically turn failing accounts red and stable accounts green

EXECUTION: Running script locally

1. Raw excel delivery data is placed in correct working directory
2. Ensure you have the required libraries installed (pandas, numpy, scikit-learn)
3. Run script via terminal or below script "python forecast_script.py"
