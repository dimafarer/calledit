#!/usr/bin/env python3
"""
Seaborn Basics Demo
This script demonstrates how seaborn enhances matplotlib visualizations.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Create a directory for saving plots if it doesn't exist
import os
if not os.path.exists('plots'):
    os.makedirs('plots')

print("=" * 50)
print("SEABORN VISUALIZATION DEMONSTRATION")
print("=" * 50)

# Set the seaborn style
sns.set_theme(style="whitegrid")
print("\nSeaborn theme set to 'whitegrid'")

# Create sample data
np.random.seed(42)  # For reproducibility
x = np.linspace(0, 10, 50)
y1 = 3 * x + 5 + np.random.normal(0, 2, 50)
y2 = 2 * x**2 + np.random.normal(0, 10, 50)

# Create a DataFrame for the demonstrations
df = pd.DataFrame({
    'x': x,
    'y1': y1,
    'y2': y2,
    'category': np.random.choice(['A', 'B', 'C', 'D'], 50)
})

# 1. Enhanced Line Plot
print("\n1. Creating an enhanced line plot with seaborn")
plt.figure(figsize=(10, 6))
sns.lineplot(x='x', y='y1', data=df, label='Linear Trend', marker='o')
sns.lineplot(x='x', y='y2', data=df, label='Quadratic Trend', marker='s')

# Adding plot elements
plt.title('Seaborn Line Plot Example', fontsize=16)
plt.xlabel('X-axis Label', fontsize=12)
plt.ylabel('Y-axis Label', fontsize=12)
plt.legend(fontsize=12)

# Save the plot
plt.tight_layout()
plt.savefig('plots/seaborn_line_plot.png', dpi=300)
print("Enhanced line plot saved as 'plots/seaborn_line_plot.png'")
plt.close()

# 2. Enhanced Scatter Plot with Regression Line
print("\n2. Creating a scatter plot with regression line")
plt.figure(figsize=(10, 6))
sns.regplot(x='x', y='y1', data=df, scatter_kws={'alpha':0.6}, line_kws={'color':'red'})

# Adding plot elements
plt.title('Scatter Plot with Regression Line', fontsize=16)
plt.xlabel('X-axis Label', fontsize=12)
plt.ylabel('Y-axis Label', fontsize=12)

# Save the plot
plt.tight_layout()
plt.savefig('plots/seaborn_regplot.png', dpi=300)
print("Scatter plot with regression line saved as 'plots/seaborn_regplot.png'")
plt.close()

# 3. Enhanced Bar Plot (Categorical)
print("\n3. Creating an enhanced categorical bar plot")
# Create categorical data
cat_data = pd.DataFrame({
    'category': ['A', 'B', 'C', 'D', 'E'] * 5,
    'group': ['Group 1', 'Group 2', 'Group 3', 'Group 4', 'Group 5'] * 5,
    'value': np.random.randint(10, 100, 25)
})

plt.figure(figsize=(12, 6))
sns.barplot(x='category', y='value', hue='group', data=cat_data, palette='viridis')

# Adding plot elements
plt.title('Seaborn Categorical Bar Plot', fontsize=16)
plt.xlabel('Categories', fontsize=12)
plt.ylabel('Values', fontsize=12)
plt.legend(title='Group', fontsize=10, title_fontsize=12)

# Save the plot
plt.tight_layout()
plt.savefig('plots/seaborn_barplot.png', dpi=300)
print("Enhanced bar plot saved as 'plots/seaborn_barplot.png'")
plt.close()

# 4. Distribution Plots
print("\n4. Creating distribution plots")
plt.figure(figsize=(12, 10))

# Create a 2x2 grid of subplots
plt.subplot(2, 2, 1)
sns.histplot(df['y1'], kde=True, color='skyblue')
plt.title('Histogram with KDE', fontsize=14)

plt.subplot(2, 2, 2)
sns.kdeplot(df['y1'], fill=True, color='lightcoral')
plt.title('KDE Plot', fontsize=14)

plt.subplot(2, 2, 3)
sns.boxplot(y=df['y1'], color='lightgreen')
plt.title('Box Plot', fontsize=14)

plt.subplot(2, 2, 4)
sns.violinplot(y=df['y1'], color='mediumpurple')
plt.title('Violin Plot', fontsize=14)

# Save the plot
plt.tight_layout()
plt.savefig('plots/seaborn_distributions.png', dpi=300)
print("Distribution plots saved as 'plots/seaborn_distributions.png'")
plt.close()

# 5. Heatmap for Correlation
print("\n5. Creating a correlation heatmap")
# Create a more complex dataset for correlation
np.random.seed(42)
corr_data = pd.DataFrame({
    'feature1': np.random.normal(0, 1, 100),
    'feature2': np.random.normal(5, 2, 100),
    'feature3': np.random.normal(-3, 1.5, 100),
    'feature4': np.random.normal(10, 3, 100),
    'feature5': np.random.normal(2, 2, 100)
})

# Add some correlations
corr_data['feature6'] = corr_data['feature1'] * 0.8 + np.random.normal(0, 0.5, 100)
corr_data['feature7'] = corr_data['feature3'] * -0.6 + corr_data['feature5'] * 0.4 + np.random.normal(0, 0.5, 100)

# Calculate correlation matrix
corr_matrix = corr_data.corr()

plt.figure(figsize=(10, 8))
sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', vmin=-1, vmax=1, fmt='.2f', linewidths=0.5)
plt.title('Correlation Heatmap', fontsize=16)

# Save the plot
plt.tight_layout()
plt.savefig('plots/seaborn_heatmap.png', dpi=300)
print("Correlation heatmap saved as 'plots/seaborn_heatmap.png'")
plt.close()

# 6. Pair Plot with Seaborn
print("\n6. Creating a pair plot with seaborn")
# Use the same data as the heatmap
plt.figure(figsize=(12, 10))
sns.pairplot(corr_data, diag_kind='kde', plot_kws={'alpha': 0.6}, height=2.5)
plt.suptitle('Seaborn Pair Plot', y=1.02, fontsize=16)

# Save the plot
plt.savefig('plots/seaborn_pairplot.png', dpi=300)
print("Seaborn pair plot saved as 'plots/seaborn_pairplot.png'")
plt.close()

# 7. Categorical Plot Grid
print("\n7. Creating a categorical plot grid")
# Create a dataset with categorical and numerical variables
cat_grid_data = pd.DataFrame({
    'category': np.repeat(['A', 'B', 'C', 'D'], 25),
    'value': np.concatenate([
        np.random.normal(0, 1, 25),
        np.random.normal(2, 1.5, 25),
        np.random.normal(-1, 2, 25),
        np.random.normal(3, 0.8, 25)
    ]),
    'group': np.random.choice(['Group 1', 'Group 2'], 100)
})

plt.figure(figsize=(15, 10))
g = sns.catplot(
    data=cat_grid_data, kind="violin",
    x="category", y="value", hue="group",
    palette="Set2", height=6, aspect=1.5
)
g.set_axis_labels("Category", "Value")
g.legend.set_title("Group")
g.fig.suptitle('Categorical Plot Grid (Violin Plots)', y=1.02, fontsize=16)

# Save the plot
plt.savefig('plots/seaborn_catplot.png', dpi=300)
print("Categorical plot grid saved as 'plots/seaborn_catplot.png'")
plt.close()

print("\n" + "=" * 50)
print("END OF SEABORN BASICS DEMO")
print("=" * 50)