#!/usr/bin/env python3
"""
Integrated Data Analysis Demo
This script demonstrates a complete workflow using pandas, matplotlib, and seaborn.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Create directories for saving plots and data if they don't exist
if not os.path.exists('plots'):
    os.makedirs('plots')
if not os.path.exists('data'):
    os.makedirs('data')

# Set the seaborn style for all plots
sns.set_theme(style="whitegrid")

print("=" * 50)
print("INTEGRATED DATA ANALYSIS DEMONSTRATION")
print("=" * 50)

# Step 1: Generate a synthetic dataset (simulating real-world data)
print("\nStep 1: Generating synthetic dataset (simulating real-world data)")

# Set random seed for reproducibility
np.random.seed(42)

# Number of samples
n_samples = 200

# Create a DataFrame with synthetic data
data = {
    # Customer demographics
    'customer_id': range(1, n_samples + 1),
    'age': np.random.randint(18, 80, n_samples),
    'gender': np.random.choice(['Male', 'Female', 'Other'], n_samples),
    'income': np.random.normal(50000, 15000, n_samples),
    
    # Purchase behavior
    'purchase_frequency': np.random.randint(1, 30, n_samples),
    'avg_purchase_value': np.random.normal(100, 50, n_samples),
    
    # Product preferences (categories A through E)
    'product_category': np.random.choice(['A', 'B', 'C', 'D', 'E'], n_samples),
    
    # Customer satisfaction
    'satisfaction_score': np.random.randint(1, 11, n_samples),
    
    # Customer tenure (in months)
    'tenure_months': np.random.randint(1, 60, n_samples)
}

# Create the DataFrame
df = pd.DataFrame(data)

# Add some realistic correlations
# Higher income tends to correlate with higher purchase value
df['avg_purchase_value'] = df['avg_purchase_value'] + df['income'] * 0.0003 + np.random.normal(0, 20, n_samples)

# Longer tenure tends to correlate with higher satisfaction
df['satisfaction_score'] = df['satisfaction_score'] + df['tenure_months'] * 0.03 + np.random.normal(0, 1, n_samples)
df['satisfaction_score'] = df['satisfaction_score'].clip(1, 10).round().astype(int)

# Add a calculated field: total spend
df['total_spend'] = df['purchase_frequency'] * df['avg_purchase_value']

# Add some missing values to simulate real-world data
indices = np.random.choice(n_samples, 20, replace=False)
df.loc[indices, 'income'] = np.nan

indices = np.random.choice(n_samples, 15, replace=False)
df.loc[indices, 'satisfaction_score'] = np.nan

# Save the raw data
df.to_csv('data/customer_data_raw.csv', index=False)
print(f"Raw data saved to 'data/customer_data_raw.csv' ({df.shape[0]} rows, {df.shape[1]} columns)")

# Step 2: Data Exploration and Cleaning
print("\nStep 2: Data Exploration and Cleaning")

# Display basic information about the dataset
print("\nDataset Overview:")
print(f"Shape: {df.shape}")
print("\nData Types:")
print(df.dtypes)

print("\nSummary Statistics:")
print(df.describe())

print("\nMissing Values:")
missing_values = df.isnull().sum()
print(missing_values[missing_values > 0])

# Clean the data
print("\nCleaning the data...")

# Fill missing income values with median
median_income = df['income'].median()
df['income'].fillna(median_income, inplace=True)

# Fill missing satisfaction scores with median
median_satisfaction = df['satisfaction_score'].median()
df['satisfaction_score'].fillna(median_satisfaction, inplace=True)

# Check if all missing values are handled
print("\nRemaining Missing Values:")
missing_values = df.isnull().sum()
print(missing_values[missing_values > 0] if any(missing_values > 0) else "No missing values remaining")

# Save the cleaned data
df.to_csv('data/customer_data_cleaned.csv', index=False)
print("Cleaned data saved to 'data/customer_data_cleaned.csv'")

# Step 3: Exploratory Data Analysis with Visualizations
print("\nStep 3: Exploratory Data Analysis with Visualizations")

# 1. Distribution of Age
print("\n1. Analyzing age distribution")
plt.figure(figsize=(10, 6))
sns.histplot(df['age'], kde=True, bins=20)
plt.title('Distribution of Customer Age', fontsize=16)
plt.xlabel('Age', fontsize=12)
plt.ylabel('Count', fontsize=12)
plt.savefig('plots/age_distribution.png', dpi=300)
plt.close()

# 2. Gender Distribution
print("\n2. Analyzing gender distribution")
plt.figure(figsize=(8, 6))
gender_counts = df['gender'].value_counts()
plt.pie(gender_counts, labels=gender_counts.index, autopct='%1.1f%%', startangle=90, colors=sns.color_palette('pastel'))
plt.title('Gender Distribution', fontsize=16)
plt.axis('equal')
plt.savefig('plots/gender_distribution.png', dpi=300)
plt.close()

# 3. Income vs. Average Purchase Value
print("\n3. Analyzing relationship between income and purchase value")
plt.figure(figsize=(10, 6))
sns.scatterplot(x='income', y='avg_purchase_value', hue='gender', data=df, alpha=0.7)
plt.title('Income vs. Average Purchase Value', fontsize=16)
plt.xlabel('Income ($)', fontsize=12)
plt.ylabel('Average Purchase Value ($)', fontsize=12)
plt.savefig('plots/income_vs_purchase.png', dpi=300)
plt.close()

# 4. Satisfaction Score Distribution
print("\n4. Analyzing satisfaction score distribution")
plt.figure(figsize=(10, 6))
sns.countplot(x='satisfaction_score', data=df, palette='viridis')
plt.title('Distribution of Satisfaction Scores', fontsize=16)
plt.xlabel('Satisfaction Score (1-10)', fontsize=12)
plt.ylabel('Count', fontsize=12)
plt.savefig('plots/satisfaction_distribution.png', dpi=300)
plt.close()

# 5. Product Category Analysis
print("\n5. Analyzing product category preferences")
plt.figure(figsize=(12, 10))

# Create a 2x2 grid of subplots
plt.subplot(2, 2, 1)
sns.countplot(x='product_category', data=df, palette='Set2')
plt.title('Product Category Distribution', fontsize=14)
plt.xlabel('Product Category', fontsize=12)
plt.ylabel('Count', fontsize=12)

plt.subplot(2, 2, 2)
sns.boxplot(x='product_category', y='avg_purchase_value', data=df, palette='Set2')
plt.title('Purchase Value by Category', fontsize=14)
plt.xlabel('Product Category', fontsize=12)
plt.ylabel('Average Purchase Value ($)', fontsize=12)

plt.subplot(2, 2, 3)
sns.boxplot(x='product_category', y='satisfaction_score', data=df, palette='Set2')
plt.title('Satisfaction by Category', fontsize=14)
plt.xlabel('Product Category', fontsize=12)
plt.ylabel('Satisfaction Score', fontsize=12)

plt.subplot(2, 2, 4)
category_gender = pd.crosstab(df['product_category'], df['gender'])
category_gender.plot(kind='bar', stacked=True, ax=plt.gca())
plt.title('Category Preference by Gender', fontsize=14)
plt.xlabel('Product Category', fontsize=12)
plt.ylabel('Count', fontsize=12)
plt.legend(title='Gender')

plt.tight_layout()
plt.savefig('plots/product_category_analysis.png', dpi=300)
plt.close()

# 6. Correlation Analysis
print("\n6. Performing correlation analysis")
# Select only numeric columns for correlation
numeric_df = df.select_dtypes(include=[np.number])
correlation = numeric_df.corr()

plt.figure(figsize=(10, 8))
sns.heatmap(correlation, annot=True, cmap='coolwarm', fmt='.2f', linewidths=0.5)
plt.title('Correlation Matrix of Numeric Variables', fontsize=16)
plt.tight_layout()
plt.savefig('plots/correlation_matrix.png', dpi=300)
plt.close()

# 7. Customer Segmentation
print("\n7. Performing customer segmentation analysis")
# Create customer segments based on spending and frequency
df['spend_category'] = pd.qcut(df['total_spend'], 3, labels=['Low', 'Medium', 'High'])
df['frequency_category'] = pd.qcut(df['purchase_frequency'], 3, labels=['Low', 'Medium', 'High'])

# Create a segment matrix
segment_matrix = pd.crosstab(df['spend_category'], df['frequency_category'])
print("\nCustomer Segment Matrix:")
print(segment_matrix)

# Visualize the segments
plt.figure(figsize=(10, 6))
sns.scatterplot(x='purchase_frequency', y='total_spend', hue='product_category', 
                size='satisfaction_score', sizes=(20, 200), alpha=0.7, data=df)
plt.title('Customer Segmentation by Purchase Behavior', fontsize=16)
plt.xlabel('Purchase Frequency', fontsize=12)
plt.ylabel('Total Spend ($)', fontsize=12)
plt.savefig('plots/customer_segmentation.png', dpi=300)
plt.close()

# 8. Age Group Analysis
print("\n8. Analyzing customer behavior by age group")
# Create age groups
df['age_group'] = pd.cut(df['age'], bins=[17, 30, 45, 60, 80], labels=['18-30', '31-45', '46-60', '61+'])

plt.figure(figsize=(12, 10))

# Create a 2x2 grid of subplots
plt.subplot(2, 2, 1)
sns.countplot(x='age_group', data=df, palette='Blues')
plt.title('Distribution by Age Group', fontsize=14)
plt.xlabel('Age Group', fontsize=12)
plt.ylabel('Count', fontsize=12)

plt.subplot(2, 2, 2)
sns.boxplot(x='age_group', y='total_spend', data=df, palette='Blues')
plt.title('Total Spend by Age Group', fontsize=14)
plt.xlabel('Age Group', fontsize=12)
plt.ylabel('Total Spend ($)', fontsize=12)

plt.subplot(2, 2, 3)
sns.boxplot(x='age_group', y='satisfaction_score', data=df, palette='Blues')
plt.title('Satisfaction by Age Group', fontsize=14)
plt.xlabel('Age Group', fontsize=12)
plt.ylabel('Satisfaction Score', fontsize=12)

plt.subplot(2, 2, 4)
age_product = pd.crosstab(df['age_group'], df['product_category'])
age_product.plot(kind='bar', stacked=True, ax=plt.gca())
plt.title('Product Preference by Age Group', fontsize=14)
plt.xlabel('Age Group', fontsize=12)
plt.ylabel('Count', fontsize=12)
plt.legend(title='Product')

plt.tight_layout()
plt.savefig('plots/age_group_analysis.png', dpi=300)
plt.close()

# Step 4: Advanced Analysis - Customer Lifetime Value (CLV) Estimation
print("\nStep 4: Advanced Analysis - Customer Lifetime Value (CLV) Estimation")

# Calculate a simple CLV based on total spend and tenure
df['monthly_value'] = df['total_spend'] / df['tenure_months']
df['estimated_clv'] = df['monthly_value'] * 36  # Assuming 3-year customer lifetime

# Visualize CLV distribution
plt.figure(figsize=(10, 6))
sns.histplot(df['estimated_clv'], kde=True, bins=30)
plt.title('Distribution of Estimated Customer Lifetime Value', fontsize=16)
plt.xlabel('Estimated CLV ($)', fontsize=12)
plt.ylabel('Count', fontsize=12)
plt.savefig('plots/clv_distribution.png', dpi=300)
plt.close()

# CLV by product category
plt.figure(figsize=(10, 6))
sns.boxplot(x='product_category', y='estimated_clv', data=df, palette='Set3')
plt.title('Customer Lifetime Value by Product Category', fontsize=16)
plt.xlabel('Product Category', fontsize=12)
plt.ylabel('Estimated CLV ($)', fontsize=12)
plt.savefig('plots/clv_by_category.png', dpi=300)
plt.close()

# Step 5: Summary and Insights
print("\nStep 5: Summary and Insights")

# Calculate key metrics
avg_clv = df['estimated_clv'].mean()
top_category = df['product_category'].value_counts().index[0]
avg_satisfaction = df['satisfaction_score'].mean()
high_value_customers = df[df['estimated_clv'] > df['estimated_clv'].quantile(0.75)].shape[0]
high_value_percentage = (high_value_customers / df.shape[0]) * 100

print(f"\nAverage Customer Lifetime Value: ${avg_clv:.2f}")
print(f"Most Popular Product Category: {top_category}")
print(f"Average Satisfaction Score: {avg_satisfaction:.2f}/10")
print(f"High-Value Customers: {high_value_customers} ({high_value_percentage:.1f}% of total)")

# Save the final enriched dataset
df.to_csv('data/customer_data_enriched.csv', index=False)
print("\nEnriched data saved to 'data/customer_data_enriched.csv'")

print("\n" + "=" * 50)
print("END OF INTEGRATED DATA ANALYSIS DEMO")
print("=" * 50)
print("\nAll visualizations have been saved to the 'plots' directory.")
print("All data files have been saved to the 'data' directory.")