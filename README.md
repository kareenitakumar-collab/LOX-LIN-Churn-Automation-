# (LIN/LOX) Customer Churn Automation & Predictive Analysis 
Overview: This repository contains the automated data pipeline and machine learning forecasting models for the LIN and LOX bulk gas business. The system is designed to transition our account management from reactive observation to proactive intervention by automatically classifying delivery points, calculation historical churn, and prediction future volume decay using regression algorithms. This tool acts as an automated early-warning system. In generating descriptive risk labels by comparing historical baseline averages against future predictions, allowing operations and sales teams able to easily at-risk accounts in a Power BI Dashboard view.

*All outputs are structured for seamless integration into interactive Power BI dashboards* 

1. **The Automation Pipeline**
   This script handles the raw data extraction, cleaning, and historical classification.
   
   * Smart Cleaning:
                   Automatically sanitizes raw Excel data, stipping invisible characters and dynamically mapping columns regardless of slight naming variations
     
   * Volume Aggregation:
                   Safely aggregates multiple deliveries within a single month to build a continuous, accurate time-series for every Delivery Point
     
   * Behavioral Logic:
                   Distinguishes between permanent churn and normal seasonality by analying historical "Start-Stop-Start" delivery patterns
     
   * Git Automation:
                   Automatically commits and pushes newly processed datasets directly into this repository 

2. **The Predictive Model**
   This script ingests the cleaned historical data and applies two advanced machine learning models:
     1. Multivariable Linear Regression:
         * Forecasts the overall business churn percentage for the next 12 months, outputting both a dataset and a corporate-branded trendline visual
    2. Logistic Regression:
         * Generatse a specific, actionable RISK PROFILE for every active customer

**Risk Profile Calculation**
  
  The model acts as an early-warning radar by isolating the last 6 months of activity for every active customer and scoring them based on 3 Core Criteria (The "Warning Signs"):

  1. Average 6-month Volume: How much product are they actually buying? (massive account of tiny one)
    
  2. Volume Volatility (Standard Deviation): How sporatic are their orders?
       * a customer who orders exactly 10,000 SCF every single month is very stable
       * a customer who orders 20,000 one month, 0 the next, and 5,000 the next is highly volatine and inherently riskier
    
  3. Zero-Volume Months: Out of the last 6 months, how many months did they order absolutely nothing?
       * **this is usally the biggest red flag for impending churn**

**The Probability Score**
  Model weighs those 3 factors together and assigns every active customer a Churn Probability Score from 0% to 100% 

  Ex. If a customer's volume has been dropping erratically and they haven't ordered anything in the last 2 months, the model might flag them with an 88% probability of churning.

**Under the Hood: The Logistic Regression Algorithm**

To understand exactly how a customer gets assigned a specific number like 88%, we have to look under the hood at how the Logistic Regression algorithm works. It is not just a simple "if/then" rule; it is a mathematical formula. Think of it like calculating a credit score, where different financial behaviors are weighted differently.

**Here is the exact three-step process the Python code uses to generate that percentage:**

Step 1: Learning the "Weights" (The Training Phase)
When you run the script, the first thing it does is look at all the customers in your dataset who have already churned (Status = 'LOST'). The algorithm analyzes those lost customers to figure out exactly how important each of our three criteria is. It assigns a mathematical weight (or multiplier) to each factor.

It might discover that Zero-Volume Months is the single biggest predictor of a customer leaving, so it assigns it a massive positive weight.

It might find that a high Avg_6M_Volume means a customer is deeply entrenched and less likely to leave, so it assigns that a negative weight (meaning it pushes the risk down).

Step 2: Scoring the Active Customer
Once the model knows the "weights," it looks at your current, active customers one by one. It multiplies the customer's actual data by the model's learned weights to calculate a Raw Score. Conceptually, the math looks like this:

$$(\text{Zero-Volume Months} \times \text{Weight}) + (\text{Volume Volatility} \times \text{Weight}) + (\text{Avg Volume} \times \text{Weight}) + \text{Baseline} = \text{Raw Score}$$

If a customer has 3 zero-volume months, and the weight for that is very high, their Raw Score is going to shoot up.

Step 3: The "S-Curve" (Squishing it into a Percentage)
This is where the magic happens. The "Raw Score" from Step 2 is just an unbounded number—it could be $-400$ or $+150$. To turn that into a usable probability between $0\%$ and $100\%$, the algorithm pushes that Raw Score through a mathematical funnel called a Sigmoid Function (often called an S-Curve).

If the Raw Score is a high positive number (lots of red flags), the S-curve pushes the output up toward 0.99 (99%).

If the Raw Score is a high negative number (very stable, huge volume), the S-curve pushes the output down toward 0.01 (1%).

If the customer has mixed signals (maybe one zero-volume month, but decent average volume), the score lands somewhere in the middle of the curve, outputting something like 0.55 (55%).

How it looks in the code: When the script runs churn_probs = log_model.predict_proba(X_active_scaled)[:, 1], it is instantly calculating that Raw Score and pushing it through the S-Curve for every single active delivery point in your Excel file. It takes the resulting decimal, multiplies it by 100, and hands you the clean 88% seen in the output CSV.

**3. The Risk Brackets (Action Zones)**

Once the probability percentage is calculated, the script uses a strict ruleset to drop them into designated Airgas action zones:

High Risk (Zone 1/2): Any customer with a $75\%$ or higher probability of leaving. These are the "Code Red" accounts that are showing severe signs of drop-off and need immediate intervention.

Medium Risk (Zone 3/4): Customers with a 40% to 74% probability. These accounts are starting to show wobbly behavior (like an unexpected missed month) but haven't completely flatlined yet.

Low Risk (Zone 5/6): Customers with under 40% probability. These are your healthy, stable, and consistent buyers.

By feeding these brackets directly into Power BI, the commercial team isn't just looking at a list of names; they are looking at a scientifically ranked hit-list of who to call today.

**4. Generated Outputs**

Running the pipeline will automatically generate and push the following files to this repository:

[Product]_Churn_Dataset_Enhanced.csv: Cleaned historical timeline of all DPs.

[Product]_Churn_Summary_Results.csv: Rolled-up monthly and yearly churn percentages.

[Product]_Customer_Risk_Profiles.csv: The predictive hit-list of active customers and their churn probability.

[Product]_Churn_Forecast_12M.csv: The future 12-month business-level forecast.

[Product]_Forecast_Visual.png: High-resolution, corporate-branded trendline graphs.

EXECUTION: Running script locally

1. Raw excel delivery data is placed in correct working directory
2. Ensure you have the required libraries installed (pandas, numpy, scikit-learn)
3. Run script via terminal
