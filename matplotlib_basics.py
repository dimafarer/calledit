#!/usr/bin/env python3
"""
Matplotlib Basics Demo
This script demonstrates fundamental matplotlib operations for data visualization.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

# Create a directory for saving plots if it doesn't exist
import os
if not os.path.exists('plots'):
    os.makedirs('plots')

# Set the style for plots
plt.style.use('seaborn-v0_8-whitegrid')

print("=" * 50)
print("MATPLOTLIB BASIC PLOTS DEMONSTRATION")
print("=" * 50)

# Create sample data
np.random.seed(42)  # For reproducibility
x = np.linspace(0, 10, 50)
y1 = 3 * x + 5 + np.random.normal(0, 2, 50)
y2 = 2 * x**2 + np.random.normal(0, 10, 50)

# Create a DataFrame for later use
df = pd.DataFrame({
    'x': x,
    'y1': y1,
    'y2': y2,
    'category': np.random.choice(['A', 'B', 'C', 'D'], 50)
})

# 1. Line Plot
print("\n1. Creating a basic line plot")
plt.figure(figsize=(10, 6))
plt.plot(x, y1, label='Linear Trend', color='blue', linestyle='-', linewidth=2, marker='o', markersize=5)
plt.plot(x, y2, label='Quadratic Trend', color='red', linestyle='--', linewidth=2, marker='s', markersize=5)

# Adding plot elements
plt.title('Basic Line Plot Example', fontsize=16)
plt.xlabel('X-axis Label', fontsize=12)
plt.ylabel('Y-axis Label', fontsize=12)
plt.grid(True, linestyle='--', alpha=0.7)
plt.legend(fontsize=12)

# Save the plot
plt.tight_layout()
plt.savefig('plots/line_plot.png', dpi=300)
print("Line plot saved as 'plots/line_plot.png'")
plt.close()

# 2. Scatter Plot
print("\n2. Creating a scatter plot")
plt.figure(figsize=(10, 6))
plt.scatter(x, y1, label='Group 1', color='blue', marker='o', s=50, alpha=0.7)
plt.scatter(x, y2, label='Group 2', color='red', marker='x', s=50, alpha=0.7)

# Adding plot elements
plt.title('Scatter Plot Example', fontsize=16)
plt.xlabel('X-axis Label', fontsize=12)
plt.ylabel('Y-axis Label', fontsize=12)
plt.grid(True, linestyle='--', alpha=0.7)
plt.legend(fontsize=12)

# Save the plot
plt.tight_layout()
plt.savefig('plots/scatter_plot.png', dpi=300)
print("Scatter plot saved as 'plots/scatter_plot.png'")
plt.close()

# 3. Bar Plot
print("\n3. Creating a bar plot")
categories = ['Category A', 'Category B', 'Category C', 'Category D', 'Category E']
values1 = np.random.randint(10, 100, 5)
values2 = np.random.randint(10, 100, 5)

plt.figure(figsize=(10, 6))
bar_width = 0.35
x_pos = np.arange(len(categories))

plt.bar(x_pos - bar_width/2, values1, bar_width, label='Group 1', color='skyblue', edgecolor='black')
plt.bar(x_pos + bar_width/2, values2, bar_width, label='Group 2', color='lightcoral', edgecolor='black')

# Adding plot elements
plt.title('Bar Plot Example', fontsize=16)
plt.xlabel('Categories', fontsize=12)
plt.ylabel('Values', fontsize=12)
plt.xticks(x_pos, categories, fontsize=10)
plt.grid(True, linestyle='--', alpha=0.7, axis='y')
plt.legend(fontsize=12)

# Save the plot
plt.tight_layout()
plt.savefig('plots/bar_plot.png', dpi=300)
print("Bar plot saved as 'plots/bar_plot.png'")
plt.close()

# 4. Histogram
print("\n4. Creating a histogram")
plt.figure(figsize=(10, 6))
plt.hist(y1, bins=15, alpha=0.7, color='skyblue', edgecolor='black', label='Distribution 1')
plt.hist(y2, bins=15, alpha=0.5, color='lightcoral', edgecolor='black', label='Distribution 2')

# Adding plot elements
plt.title('Histogram Example', fontsize=16)
plt.xlabel('Values', fontsize=12)
plt.ylabel('Frequency', fontsize=12)
plt.grid(True, linestyle='--', alpha=0.7)
plt.legend(fontsize=12)

# Save the plot
plt.tight_layout()
plt.savefig('plots/histogram.png', dpi=300)
print("Histogram saved as 'plots/histogram.png'")
plt.close()

# 5. Subplots
print("\n5. Creating subplots")
fig, axes = plt.subplots(2, 2, figsize=(12, 10))

# Line plot in the first subplot
axes[0, 0].plot(x, y1, color='blue', marker='o')
axes[0, 0].set_title('Line Plot')
axes[0, 0].set_xlabel('X-axis')
axes[0, 0].set_ylabel('Y-axis')
axes[0, 0].grid(True)

# Scatter plot in the second subplot
axes[0, 1].scatter(x, y2, color='red', marker='x')
axes[0, 1].set_title('Scatter Plot')
axes[0, 1].set_xlabel('X-axis')
axes[0, 1].set_ylabel('Y-axis')
axes[0, 1].grid(True)

# Bar plot in the third subplot
axes[1, 0].bar(categories[:3], values1[:3], color='green')
axes[1, 0].set_title('Bar Plot')
axes[1, 0].set_xlabel('Categories')
axes[1, 0].set_ylabel('Values')
axes[1, 0].grid(True)

# Histogram in the fourth subplot
axes[1, 1].hist(y1, bins=10, color='purple', alpha=0.7)
axes[1, 1].set_title('Histogram')
axes[1, 1].set_xlabel('Values')
axes[1, 1].set_ylabel('Frequency')
axes[1, 1].grid(True)

# Adjust layout and save
plt.tight_layout()
plt.savefig('plots/subplots.png', dpi=300)
print("Subplots saved as 'plots/subplots.png'")
plt.close()

# 6. Pair Plot (using pandas)
print("\n6. Creating a pair plot")
# Create a more interesting dataset for the pair plot
np.random.seed(42)
pair_data = pd.DataFrame({
    'feature1': np.random.normal(0, 1, 100),
    'feature2': np.random.normal(5, 2, 100),
    'feature3': np.random.normal(-3, 1.5, 100),
    'feature4': np.random.normal(10, 3, 100)
})

# Calculate correlations between features
correlations = pair_data.corr()

# Create a figure with a grid of subplots
fig = plt.figure(figsize=(12, 10))
n_vars = len(pair_data.columns)
grid = GridSpec(n_vars, n_vars)

# Loop through all pairs of variables
for i, var1 in enumerate(pair_data.columns):
    for j, var2 in enumerate(pair_data.columns):
        ax = plt.subplot(grid[i, j])
        
        # Diagonal: Show histograms
        if i == j:
            ax.hist(pair_data[var1], bins=20, color='skyblue', edgecolor='black')
            ax.set_title(f'{var1}', fontsize=10)
        # Off-diagonal: Show scatter plots
        else:
            ax.scatter(pair_data[var2], pair_data[var1], alpha=0.6, s=20)
            ax.set_title(f'r = {correlations.iloc[i, j]:.2f}', fontsize=8)
        
        # Only show x-axis labels for the bottom row
        if i == n_vars - 1:
            ax.set_xlabel(var2, fontsize=8)
        else:
            ax.set_xticklabels([])
        
        # Only show y-axis labels for the first column
        if j == 0:
            ax.set_ylabel(var1, fontsize=8)
        else:
            ax.set_yticklabels([])

plt.tight_layout()
plt.savefig('plots/pair_plot.png', dpi=300)
print("Pair plot saved as 'plots/pair_plot.png'")
plt.close()

print("\n" + "=" * 50)
print("END OF MATPLOTLIB BASICS DEMO")
print("=" * 50)