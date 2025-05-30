#!/usr/bin/env python3
"""
Pandas Basics Demo
This script demonstrates fundamental pandas operations for data manipulation and analysis.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Set the style for plots
plt.style.use('seaborn-v0_8-whitegrid')

print("=" * 50)
print("PANDAS SERIES DEMONSTRATION")
print("=" * 50)

# Creating a Series
print("\n1. Creating Series objects:")
s1 = pd.Series([10, 20, 30, 40, 50], name='Values')
print(f"Series with default index:\n{s1}")

s2 = pd.Series([10, 20, 30, 40, 50], index=['a', 'b', 'c', 'd', 'e'], name='Custom Index')
print(f"\nSeries with custom index:\n{s2}")

# Series operations
print("\n2. Series operations:")
print(f"Series addition: s1 + 5 =\n{s1 + 5}")
print(f"Series multiplication: s1 * 2 =\n{s1 * 2}")
print(f"Series filtering: s1[s1 > 30] =\n{s1[s1 > 30]}")

# Series attributes and methods
print("\n3. Series attributes and methods:")
print(f"Series index: {s2.index}")
print(f"Series values: {s2.values}")
print(f"Series data type: {s2.dtype}")
print(f"Series mean: {s2.mean()}")
print(f"Series description:\n{s2.describe()}")

print("\n" + "=" * 50)
print("PANDAS DATAFRAME DEMONSTRATION")
print("=" * 50)

# Creating a DataFrame
print("\n1. Creating DataFrames:")

# From a dictionary of lists
data_dict = {
    'Name': ['Alice', 'Bob', 'Charlie', 'David', 'Eva'],
    'Age': [25, 30, 35, 40, 45],
    'City': ['New York', 'Boston', 'Chicago', 'Denver', 'Miami'],
    'Salary': [50000, 60000, 70000, 80000, 90000]
}
df1 = pd.DataFrame(data_dict)
print("DataFrame from dictionary:\n", df1)

# From a list of dictionaries
data_list = [
    {'Name': 'Frank', 'Age': 50, 'City': 'Seattle', 'Salary': 95000},
    {'Name': 'Grace', 'Age': 55, 'City': 'Portland', 'Salary': 100000}
]
df2 = pd.DataFrame(data_list)
print("\nDataFrame from list of dictionaries:\n", df2)

# From a NumPy array
array_data = np.random.randint(1, 100, size=(3, 4))
df3 = pd.DataFrame(array_data, columns=['W', 'X', 'Y', 'Z'])
print("\nDataFrame from NumPy array:\n", df3)

# DataFrame basic operations
print("\n2. DataFrame basic operations:")
print("First 2 rows:\n", df1.head(2))
print("\nLast 2 rows:\n", df1.tail(2))
print("\nDataFrame shape:", df1.shape)
print("\nDataFrame columns:", df1.columns.tolist())
print("\nDataFrame info:")
df1.info()
print("\nDataFrame statistics:\n", df1.describe())

# Accessing data
print("\n3. Accessing data in DataFrames:")
print("Accessing a column (Series):\n", df1['Name'])
print("\nAccessing multiple columns:\n", df1[['Name', 'Age']])
print("\nAccessing a row by index:\n", df1.iloc[0])
print("\nAccessing a row by label (if index is set):\n", df1.loc[0])
print("\nAccessing a specific value (row 0, column 'Name'):", df1.at[0, 'Name'])

# Data manipulation
print("\n" + "=" * 50)
print("DATA MANIPULATION")
print("=" * 50)

# Insert a new column
print("\n1. Inserting a new column:")
df1['Experience'] = [3, 5, 8, 12, 15]
print(df1)

# Drop a column
print("\n2. Dropping a column:")
df1_dropped = df1.drop('Experience', axis=1)
print(df1_dropped)

# Rename columns
print("\n3. Renaming columns:")
df1_renamed = df1.rename(columns={'Name': 'Employee', 'City': 'Location'})
print(df1_renamed)

# Data combination
print("\n" + "=" * 50)
print("DATA COMBINATION")
print("=" * 50)

# Concatenation
print("\n1. Concatenating DataFrames:")
df_concat = pd.concat([df1, df2], ignore_index=True)
print(df_concat)

# Merging
print("\n2. Merging DataFrames:")
df_left = pd.DataFrame({
    'id': [1, 2, 3, 4],
    'name': ['Alice', 'Bob', 'Charlie', 'David'],
    'dept': ['HR', 'IT', 'Finance', 'Marketing']
})

df_right = pd.DataFrame({
    'id': [1, 2, 3, 5],
    'name': ['Alice', 'Bob', 'Charlie', 'Eva'],
    'salary': [50000, 60000, 70000, 90000]
})

print("Left DataFrame:\n", df_left)
print("\nRight DataFrame:\n", df_right)

# Inner merge
df_inner = pd.merge(df_left, df_right, on='id', how='inner')
print("\nInner merge (only matching ids):\n", df_inner)

# Outer merge
df_outer = pd.merge(df_left, df_right, on='id', how='outer')
print("\nOuter merge (all ids):\n", df_outer)

# Left merge
df_left_merge = pd.merge(df_left, df_right, on='id', how='left')
print("\nLeft merge (all ids from left):\n", df_left_merge)

# Statistical analysis
print("\n" + "=" * 50)
print("STATISTICAL ANALYSIS")
print("=" * 50)

# Create sample data for crosstab and correlation
data = {
    'Department': ['HR', 'HR', 'IT', 'IT', 'Finance', 'Finance', 'Marketing', 'Marketing'],
    'Gender': ['M', 'F', 'M', 'F', 'M', 'F', 'M', 'F'],
    'Salary': [45000, 55000, 60000, 65000, 70000, 75000, 80000, 85000],
    'Experience': [2, 3, 5, 4, 8, 7, 10, 9]
}
df_stats = pd.DataFrame(data)
print("Sample data for statistical analysis:\n", df_stats)

# Crosstab
print("\n1. Crosstab (contingency table):")
ct = pd.crosstab(df_stats['Department'], df_stats['Gender'])
print(ct)

# Correlation
print("\n2. Correlation between numerical columns:")
corr = df_stats[['Salary', 'Experience']].corr()
print(corr)

# Save the correlation as a CSV for later use
corr.to_csv('correlation.csv')
print("\nCorrelation saved to 'correlation.csv'")

# Groupby operations
print("\n3. GroupBy operations:")
grouped = df_stats.groupby('Department')
print("Mean values by department:\n", grouped.mean())
print("\nCount by department:\n", grouped.count())

print("\n" + "=" * 50)
print("END OF PANDAS BASICS DEMO")
print("=" * 50)