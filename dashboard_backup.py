"""
Interactive RUSLE Analysis Dashboard
View soil erosion statistics and maps for 2014-2024

Author: Bhavya Singh
Date: 17 November 2025
"""

import sys
import tkinter as tk
from tkinter import ttk
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import rasterio
import numpy as np
from pathlib import Path
from PIL import Image, ImageTk

# Paths
BASE_DIR = Path(__file__).parent
STATS_DIR = BASE_DIR / "outputs" / "statistics"
MAPS_DIR = BASE_DIR / "outputs" / "maps"

class RUSLEDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("RUSLE Soil Erosion Dashboard - Mula-Mutha Catchment (2014-2024)")
        self.root.geometry("1920x1080")  # Landscape full HD
        self.root.state('zoomed')  # Start maximized
        self.root.configure(bg='#f5f5f5')
        
        # Load data
        self.load_data()
        
        # Create UI
        self.create_header()
        self.create_year_selector()
        self.create_data_table()
        self.create_main_dashboard()
        
        # Load initial year
        self.update_display(2024)
    
    def load_data(self):
        """Load all statistics data"""
        try:
            self.rusle_stats = pd.read_csv(STATS_DIR / "rusle_annual_statistics.csv")
            self.temporal_stats = pd.read_csv(STATS_DIR / "temporal_statistics.csv")
            self.r_stats = pd.read_csv(STATS_DIR / "r_factor_annual_statistics.csv")
            self.c_stats = pd.read_csv(STATS_DIR / "c_factor_annual_statistics.csv")
            self.p_stats = pd.read_csv(STATS_DIR / "p_factor_annual_statistics.csv")
        except Exception as e:
            print(f"Error loading data: {e}")
            sys.exit(1)
    
    def create_header(self):
        """Create header section"""
        header = tk.Frame(self.root, bg='#2c3e50', height=80)
        header.pack(fill=tk.X, padx=0, pady=0)
        
        title = tk.Label(
            header,
            text="🌍 RUSLE Soil Erosion Analysis Dashboard",
            font=('Arial', 24, 'bold'),
            bg='#2c3e50',
            fg='white'
        )
        title.pack(pady=15)
        
        subtitle = tk.Label(
            header,
            text="Mula-Mutha River Catchment, Pune | 2014-2024 | MSc Geoinformatics Project",
            font=('Arial', 12),
            bg='#2c3e50',
            fg='#ecf0f1'
        )
        subtitle.pack()
    
    def create_year_selector(self):
        """Create year selection panel"""
        selector_frame = tk.Frame(self.root, bg='#ecf0f1', height=100)
        selector_frame.pack(fill=tk.X, padx=20, pady=15)
        
        tk.Label(
            selector_frame,
            text="Select Year:",
            font=('Arial', 14, 'bold'),
            bg='#ecf0f1'
        ).pack(side=tk.LEFT, padx=10)
        
        # Year buttons
        years = sorted(self.rusle_stats['year'].unique())
        for year in years:
            btn = tk.Button(
                selector_frame,
                text=str(year),
                font=('Arial', 12, 'bold'),
                bg='#3498db',
                fg='white',
                width=6,
                height=2,
                relief=tk.RAISED,
                command=lambda y=year: self.update_display(y)
            )
            btn.pack(side=tk.LEFT, padx=5)
        
        # All years button
        all_btn = tk.Button(
            selector_frame,
            text="ALL\nYEARS",
            font=('Arial', 12, 'bold'),
            bg='#e74c3c',
            fg='white',
            width=6,
            height=2,
            relief=tk.RAISED,
            command=self.show_all_years
        )
        all_btn.pack(side=tk.LEFT, padx=5)
    
    def create_data_table(self):
        """Create data table showing all years statistics"""
        table_frame = tk.LabelFrame(
            self.root,
            text="📊 Annual Statistics Summary",
            font=('Arial', 12, 'bold'),
            bg='white',
            fg='#2c3e50',
            relief=tk.RIDGE,
            bd=3
        )
        table_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Create Treeview for table
        columns = ('Year', 'Mean Erosion', 'Median Erosion', 'Maximum', 'Severe Erosion %')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=6)
        
        # Define column headings and widths
        self.tree.heading('Year', text='Year')
        self.tree.heading('Mean Erosion', text='Mean Erosion (t/ha/yr)')
        self.tree.heading('Median Erosion', text='Median Erosion (t/ha/yr)')
        self.tree.heading('Maximum', text='Maximum (t/ha/yr)')
        self.tree.heading('Severe Erosion %', text='Severe Erosion (%)')
        
        self.tree.column('Year', width=100, anchor='center')
        self.tree.column('Mean Erosion', width=200, anchor='center')
        self.tree.column('Median Erosion', width=200, anchor='center')
        self.tree.column('Maximum', width=200, anchor='center')
        self.tree.column('Severe Erosion %', width=200, anchor='center')
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        # Pack table and scrollbar
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
        
        # Populate table with data
        for _, row in self.rusle_stats.iterrows():
            values = (
                int(row['year']),
                f"{row['mean']:.2f}",
                f"{row['median']:.2f}",
                f"{row['max']:.2f}",
                f"{row['Severe']:.2f}"
            )
            self.tree.insert('', tk.END, values=values, tags=('data',))
        
        # Style alternating rows
        self.tree.tag_configure('data', background='#f9f9f9')
    
    def create_main_dashboard(self):
        """Create main dashboard with large map and charts"""
        # Main container
        main_container = tk.Frame(self.root, bg='#f5f5f5')
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Top section: Large Map (center)
        map_frame = tk.LabelFrame(
            main_container,
            text="🗺️ SOIL EROSION RISK MAP - MULA-MUTHA CATCHMENT",
            font=('Arial', 16, 'bold'),
            bg='white',
            fg='#2c3e50',
            relief=tk.RIDGE,
            bd=5
        )
        map_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Map display
        self.map_label = tk.Label(map_frame, bg='white', relief=tk.SUNKEN, bd=3)
        self.map_label.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Bottom section: Charts side by side
        charts_container = tk.Frame(main_container, bg='#f5f5f5')
        charts_container.pack(fill=tk.BOTH, expand=False)
        
        # Left: Pie chart for erosion classes
        pie_frame = tk.LabelFrame(
            charts_container,
            text="📈 Erosion Class Distribution",
            font=('Arial', 12, 'bold'),
            bg='white',
            fg='#2c3e50',
            relief=tk.RIDGE,
            bd=3
        )
        pie_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        self.pie_fig = Figure(figsize=(6, 4), facecolor='white')
        self.pie_canvas = FigureCanvasTkAgg(self.pie_fig, master=pie_frame)
        self.pie_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Middle: Temporal trend (Mean)
        trend_mean_frame = tk.LabelFrame(
            charts_container,
            text="📊 Temporal Trend - Mean Erosion",
            font=('Arial', 12, 'bold'),
            bg='white',
            fg='#2c3e50',
            relief=tk.RIDGE,
            bd=3
        )
        trend_mean_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.trend_mean_fig = Figure(figsize=(6, 4), facecolor='white')
        self.trend_mean_canvas = FigureCanvasTkAgg(self.trend_mean_fig, master=trend_mean_frame)
        self.trend_mean_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Right: Temporal trend (Median)
        trend_median_frame = tk.LabelFrame(
            charts_container,
            text="📊 Temporal Trend - Median Erosion",
            font=('Arial', 12, 'bold'),
            bg='white',
            fg='#2c3e50',
            relief=tk.RIDGE,
            bd=3
        )
        trend_median_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        self.trend_median_fig = Figure(figsize=(6, 4), facecolor='white')
        self.trend_median_canvas = FigureCanvasTkAgg(self.trend_median_fig, master=trend_median_frame)
        self.trend_median_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def load_map_image(self, year):
        """Load and display map for the selected year"""
        map_path = MAPS_DIR / f"soil_loss_map_{year}.png"
        
        if map_path.exists():
            try:
                # Load image
                img = Image.open(map_path)
                
                # Resize to large size for prominence
                max_width = 1200
                max_height = 600
                img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                
                # Convert to PhotoImage
                photo = ImageTk.PhotoImage(img)
                
                # Update label
                self.map_label.config(image=photo)
                self.map_label.image = photo  # Keep a reference
            except Exception as e:
                self.map_label.config(text=f"Error loading map: {e}", font=('Arial', 10))
        else:
            self.map_label.config(text=f"Map not found for {year}", font=('Arial', 10))
    
    def update_display(self, year):
        """Update dashboard for selected year"""
        # Highlight selected row in table
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            if int(values[0]) == year:
                self.tree.selection_set(item)
                self.tree.see(item)
                break
        
        # Update charts
        self.plot_pie_chart(year)
        self.plot_temporal_trends(year)
        
        # Load map for the year
        self.load_map_image(year)
    
    def plot_pie_chart(self, year):
        """Plot pie chart for erosion class distribution"""
        self.pie_fig.clear()
        ax = self.pie_fig.add_subplot(111)
        
        year_data = self.rusle_stats[self.rusle_stats['year'] == year].iloc[0]
        
        # Data for pie chart
        labels = ['Very Low\n(<5)', 'Low\n(5-10)', 'Moderate\n(10-20)', 'High\n(20-40)', 'Very High\n(>40)']
        sizes = [
            year_data['Slight'],
            year_data['Moderate'],
            year_data['High'],
            year_data['Very High'],
            year_data['Severe']
        ]
        colors = ['#006837', '#7CB342', '#FFEB3B', '#FF9800', '#D32F2F']
        
        # Create pie chart
        wedges, texts, autotexts = ax.pie(
            sizes, 
            labels=labels, 
            colors=colors,
            autopct='%1.1f%%',
            startangle=90,
            textprops={'fontsize': 9, 'weight': 'bold'}
        )
        
        # Make percentage text white for visibility
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(10)
        
        ax.set_title(f'Year {int(year)} - Erosion Classes', fontsize=12, fontweight='bold', pad=10)
        
        self.pie_fig.tight_layout()
        self.pie_canvas.draw()
    
    def plot_temporal_trends(self, current_year):
        """Plot temporal trends for mean and median erosion"""
        years = sorted(self.rusle_stats['year'].unique())
        means = [self.rusle_stats[self.rusle_stats['year'] == y]['mean'].values[0] for y in years]
        medians = [self.rusle_stats[self.rusle_stats['year'] == y]['median'].values[0] for y in years]
        
        # Mean trend
        self.trend_mean_fig.clear()
        ax1 = self.trend_mean_fig.add_subplot(111)
        
        bars = ax1.bar(years, means, color='#3498db', edgecolor='black', linewidth=1.5, alpha=0.8)
        
        # Highlight current year
        idx = years.index(current_year)
        bars[idx].set_color('#e74c3c')
        bars[idx].set_alpha(1.0)
        
        ax1.set_xlabel('Year', fontsize=10, fontweight='bold')
        ax1.set_ylabel('Mean Erosion (t/ha/yr)', fontsize=10, fontweight='bold')
        ax1.set_title('Mean Erosion Over Time', fontsize=11, fontweight='bold')
        ax1.grid(axis='y', alpha=0.3, linestyle='--')
        
        # Add value labels on bars
        for i, (year, mean) in enumerate(zip(years, means)):
            ax1.text(year, mean, f'{mean:.1f}', ha='center', va='bottom', fontsize=8, fontweight='bold')
        
        self.trend_mean_fig.tight_layout()
        self.trend_mean_canvas.draw()
        
        # Median trend
        self.trend_median_fig.clear()
        ax2 = self.trend_median_fig.add_subplot(111)
        
        ax2.plot(years, medians, 'o-', linewidth=3, markersize=8, color='#2ecc71', 
                label='Median Erosion', markeredgecolor='black', markeredgewidth=1.5)
        
        # Highlight current year
        ax2.plot(current_year, medians[idx], 'o', markersize=15, color='#e74c3c', 
                zorder=5, markeredgecolor='black', markeredgewidth=2)
        
        ax2.set_xlabel('Year', fontsize=10, fontweight='bold')
        ax2.set_ylabel('Median Erosion (t/ha/yr)', fontsize=10, fontweight='bold')
        ax2.set_title('Median Erosion Over Time', fontsize=11, fontweight='bold')
        ax2.grid(True, alpha=0.3, linestyle='--')
        ax2.fill_between(years, medians, alpha=0.2, color='#2ecc71')
        
        self.trend_median_fig.tight_layout()
        self.trend_median_canvas.draw()
    
    def show_all_years(self):
        """Load and display map for the selected year"""
        stats = [
            ('year', 'Year', '#3498db'),
            ('mean', 'Mean Erosion\n(t/ha/yr)', '#e74c3c'),
            ('median', 'Median Erosion\n(t/ha/yr)', '#2ecc71'),
            ('max', 'Maximum\n(t/ha/yr)', '#f39c12'),
            ('Severe_pct', 'Severe Erosion\n(% area)', '#e67e22')
        ]
        
        for i, (key, label, color) in enumerate(stats):
            card = tk.Frame(self.stats_frame, bg=color, relief=tk.RAISED, bd=3)
            card.grid(row=0, column=i, padx=10, pady=10, sticky='nsew')
            
            tk.Label(
                card,
                text=label,
                font=('Arial', 11, 'bold'),
                bg=color,
                fg='white'
            ).pack(pady=(10, 5))
            
            value_label = tk.Label(
                card,
                text="---",
                font=('Arial', 20, 'bold'),
                bg=color,
                fg='white'
            )
            value_label.pack(pady=(0, 10))
            
            self.stat_cards[key] = value_label
            self.stats_frame.columnconfigure(i, weight=1)
    
    def create_visualization_panel(self, parent):
        """Create visualization panel with charts"""
        viz_frame = tk.LabelFrame(
            parent,
            text="📊 Statistical Analysis",
            font=('Arial', 14, 'bold'),
            bg='white',
            fg='#2c3e50',
            relief=tk.RIDGE,
            bd=4
        )
        viz_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create matplotlib figure (optimized for side panel)
        self.fig = Figure(figsize=(8, 8), facecolor='white')
        self.canvas = FigureCanvasTkAgg(self.fig, master=viz_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def create_comparison_panel(self):
        """Create factor comparison panel"""
        self.comparison_frame = tk.LabelFrame(
            self.root,
            text="RUSLE Factors Comparison",
            font=('Arial', 12, 'bold'),
            bg='#ecf0f1',
            fg='#2c3e50'
        )
        self.comparison_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Factor labels (will be updated)
        self.factor_labels = {}
        factors = [
            ('R', 'Rainfall Erosivity', '#3498db'),
            ('K', 'Soil Erodibility', '#2ecc71'),
            ('LS', 'Topographic', '#e74c3c'),
            ('C', 'Vegetation Cover', '#f39c12'),
            ('P', 'Conservation', '#9b59b6')
        ]
        
        for i, (key, name, color) in enumerate(factors):
            frame = tk.Frame(self.comparison_frame, bg='white', relief=tk.RIDGE, bd=2)
            frame.grid(row=0, column=i, padx=8, pady=8, sticky='nsew')
            
            tk.Label(
                frame,
                text=f"{key}-Factor",
                font=('Arial', 10, 'bold'),
                bg=color,
                fg='white'
            ).pack(fill=tk.X)
            
            tk.Label(
                frame,
                text=name,
                font=('Arial', 9),
                bg='white'
            ).pack(pady=2)
            
            value_label = tk.Label(
                frame,
                text="---",
                font=('Arial', 12, 'bold'),
                bg='white',
                fg=color
            )
            value_label.pack(pady=5)
            
            self.factor_labels[key] = value_label
            self.comparison_frame.columnconfigure(i, weight=1)
    
    def update_display(self, year):
        """Update dashboard for selected year"""
        # Highlight selected row in table
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            if int(values[0]) == year:
                self.tree.selection_set(item)
                self.tree.see(item)
                break
        
        # Update charts
        self.plot_pie_chart(year)
        self.plot_temporal_trends(year)
        
        # Load map for the year
        self.load_map_image(year)
    
    def plot_year_data(self, year):
        """Plot data for selected year"""
        self.fig.clear()
        
        year_data = self.rusle_stats[self.rusle_stats['year'] == year].iloc[0]
        
        # Create 2 subplots (adjusted for vertical layout)
        ax1 = self.fig.add_subplot(211)
        ax2 = self.fig.add_subplot(212)
        
        # 1. Erosion class distribution
        classes = ['Very Low\n(<5)', 'Low\n(5-10)', 'Moderate\n(10-20)', 
                   'High\n(20-40)', 'Very High\n(>40)']
        values = [
            year_data['Slight'],
            year_data['Moderate'],
            year_data['High'],
            year_data['Very High'],
            year_data['Severe']
        ]
        colors = ['#006837', '#7CB342', '#FFEB3B', '#FF9800', '#D32F2F']  # New soil degradation colors
        
        bars = ax1.bar(classes, values, color=colors, edgecolor='black', linewidth=1.5)
        ax1.set_ylabel('Area (%)', fontsize=11, fontweight='bold')
        ax1.set_title(f'Erosion Class Distribution - {int(year)}', 
                      fontsize=12, fontweight='bold', pad=10)
        ax1.set_ylim(0, max(values) * 1.2)
        ax1.grid(axis='y', alpha=0.3, linestyle='--')
        
        # Add value labels on bars
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{value:.1f}', ha='center', va='bottom', 
                    fontweight='bold', fontsize=9)
        
        # 2. Temporal trend (all years with current year highlighted)
        years = sorted(self.rusle_stats['year'].unique())
        means = [self.rusle_stats[self.rusle_stats['year'] == y]['mean'].values[0] 
                 for y in years]
        
        ax2.plot(years, means, 'o-', linewidth=2, markersize=8, 
                color='#3498db', label='Mean Erosion')
        
        # Highlight current year
        idx = years.index(year)
        ax2.plot(year, means[idx], 'o', markersize=15, 
                color='#e74c3c', zorder=5, label=f'Year {int(year)}')
        
        ax2.set_xlabel('Year', fontsize=11, fontweight='bold')
        ax2.set_ylabel('Mean Soil Loss (t/ha/yr)', fontsize=11, fontweight='bold')
        ax2.set_title('Temporal Trend (2014-2024)', 
                     fontsize=12, fontweight='bold', pad=10)
        ax2.grid(True, alpha=0.3, linestyle='--')
        ax2.legend(loc='upper right', fontsize=9)
        
        self.fig.tight_layout()
        self.canvas.draw()
    
    def show_all_years(self):
        """Show comparison of all years"""
        # Clear table selection
        self.tree.selection_remove(self.tree.selection())
        
        # Update pie chart with average values
        self.plot_average_pie_chart()
        
        # Update trends showing all years (default to 2024 highlight)
        self.plot_temporal_trends(2024)
        
        # Show 2024 map for ALL YEARS view
        self.load_map_image(2024)
    
    def plot_average_pie_chart(self):
        """Plot average pie chart across all years"""
        self.pie_fig.clear()
        ax = self.pie_fig.add_subplot(111)
        
        # Calculate averages
        avg_slight = self.rusle_stats['Slight'].mean()
        avg_moderate = self.rusle_stats['Moderate'].mean()
        avg_high = self.rusle_stats['High'].mean()
        avg_very_high = self.rusle_stats['Very High'].mean()
        avg_severe = self.rusle_stats['Severe'].mean()
        
        labels = ['Very Low\n(<5)', 'Low\n(5-10)', 'Moderate\n(10-20)', 'High\n(20-40)', 'Very High\n(>40)']
        sizes = [avg_slight, avg_moderate, avg_high, avg_very_high, avg_severe]
        colors = ['#006837', '#7CB342', '#FFEB3B', '#FF9800', '#D32F2F']
        
        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=labels,
            colors=colors,
            autopct='%1.1f%%',
            startangle=90,
            textprops={'fontsize': 9, 'weight': 'bold'}
        )
        
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(10)
        
        ax.set_title('Average Erosion Classes (2014-2024)', fontsize=12, fontweight='bold', pad=10)
        
        self.pie_fig.tight_layout()
        self.pie_canvas.draw()
        
        # Create 2 subplots
        ax1 = self.fig.add_subplot(121)
        ax2 = self.fig.add_subplot(122)
        
        # 1. All years erosion comparison
        years = sorted(self.rusle_stats['year'].unique())
        means = [self.rusle_stats[self.rusle_stats['year'] == y]['mean'].values[0] 
                 for y in years]
        medians = [self.rusle_stats[self.rusle_stats['year'] == y]['median'].values[0] 
                   for y in years]
        
        x = np.arange(len(years))
        width = 0.35
        
        bars1 = ax1.bar(x - width/2, means, width, label='Mean', 
                       color='#e74c3c', edgecolor='black', linewidth=1)
        bars2 = ax1.bar(x + width/2, medians, width, label='Median', 
                       color='#2ecc71', edgecolor='black', linewidth=1)
        
        ax1.set_xlabel('Year', fontsize=11, fontweight='bold')
        ax1.set_ylabel('Soil Loss (t/ha/yr)', fontsize=11, fontweight='bold')
        ax1.set_title('Mean vs Median Erosion (2014-2024)', 
                     fontsize=12, fontweight='bold', pad=10)
        ax1.set_xticks(x)
        ax1.set_xticklabels([str(int(y)) for y in years], rotation=45)
        ax1.legend(fontsize=10)
        ax1.grid(axis='y', alpha=0.3, linestyle='--')
        
        # 2. Severe erosion trend
        severe_pcts = [self.rusle_stats[self.rusle_stats['year'] == y]['Severe'].values[0] 
                       for y in years]
        
        ax2.plot(years, severe_pcts, 'o-', linewidth=3, markersize=10,
                color='#c0392b', markerfacecolor='#e74c3c',
                markeredgecolor='black', markeredgewidth=1.5)
        
        ax2.fill_between(years, severe_pcts, alpha=0.3, color='#e74c3c')
        ax2.set_xlabel('Year', fontsize=11, fontweight='bold')
        ax2.set_ylabel('Severe Erosion (%)', fontsize=11, fontweight='bold')
        ax2.set_title('Severe Erosion Trend (>40 t/ha/yr)', 
                     fontsize=12, fontweight='bold', pad=10)
        ax2.grid(True, alpha=0.3, linestyle='--')
        
        # Add trend line
        z = np.polyfit(years, severe_pcts, 1)
        p = np.poly1d(z)
        ax2.plot(years, p(years), "--", linewidth=2, color='black', 
                alpha=0.7, label=f'Trend: {z[0]:.2f}%/year')
        ax2.legend(fontsize=9)
        
        self.fig.tight_layout()
        self.canvas.draw()


def main():
    """Launch dashboard"""
    root = tk.Tk()
    app = RUSLEDashboard(root)
    root.mainloop()


if __name__ == "__main__":
    main()
