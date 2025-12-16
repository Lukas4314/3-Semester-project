import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import csv

def analyze_triangulation_data(csv_path, output_dir="analysis_output"):
    """
    Analyze triangulation differences and create visualizations
    """
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Load data
    print(f"Loading data from: {csv_path}")
    df = pd.read_csv(csv_path)
    
    # Get ground truth values
    # Assuming last row has actual values or they're in specific columns
    actual_angle = None
    actual_distance = None
    
    # Try to find actual values (they might be in specific columns or in the data)
    if 'ActualTriangulationAngle' in df.columns:
        actual_angle = df['ActualTriangulationAngle'].iloc[0]
    if 'ActualTriangulationDistance' in df.columns:
        actual_distance = df['ActualTriangulationDistance'].iloc[0]
    
    # If actual values are in the data row, extract them
    if pd.isna(actual_angle) or actual_angle == "None":
        # Try to find from the first data row
        for col in df.columns:
            if 'Actual' in col:
                val = df[col].iloc[0]
                if not pd.isna(val) and val != "None":
                    if 'Angle' in col:
                        actual_angle = float(val)
                    elif 'Distance' in col:
                        actual_distance = float(val)
    
    print(f"Actual Angle: {actual_angle}, Actual Distance: {actual_distance}")
    
    # Get TDOA columns
    tdoa_columns = [col for col in df.columns if col.startswith('TDOAPhatWeighting')]
    print(f"Found {len(tdoa_columns)} TDOA columns")
    
    # Parse angle and distance from each TDOA column
    results = []
    
    for col in tdoa_columns:
        # Parse column name to extract parameters
        # Format: TDOAPhatWeighting0.8_8k_samples_With_Filter
        parts = col.split('_')
        
        if len(parts) >= 4:
            weight_str = parts[0].replace('TDOAPhatWeighting', '')
            sample_size = parts[1]  # 2k, 4k, 8k
            filter_state = '_'.join(parts[2:])  # With_Filter or Without_Filter
            weight = float(weight_str)
            
            # Get angle and distance from the first row
            if not df[col].empty:
                value = df[col].iloc[0]
                if isinstance(value, str) and ';' in value:
                    try:
                        angle_str, dist_str = value.split(';')
                        angle = float(angle_str)
                        distance = float(dist_str)
                        
                        results.append({
                            'column': col,
                            'weight': weight,
                            'sample_size': sample_size,
                            'filter_state': filter_state,
                            'estimated_angle': angle,
                            'estimated_distance': distance,
                            'angle_error': None if actual_angle is None else abs(angle - actual_angle),
                            'distance_error': None if actual_distance is None else abs(distance - actual_distance),
                            'angle_error_percent': None if actual_angle is None else abs(angle - actual_angle) / abs(actual_angle) * 100 if actual_angle != 0 else None,
                            'distance_error_percent': None if actual_distance is None else abs(distance - actual_distance) / actual_distance * 100
                        })
                    except (ValueError, IndexError) as e:
                        print(f"Error parsing column {col}: {e}")
                        continue
    
    # Create results DataFrame
    results_df = pd.DataFrame(results)
    
    if results_df.empty:
        print("No valid triangulation data found!")
        return
    
    # Save detailed results to CSV
    results_csv = output_path / "triangulation_analysis.csv"
    results_df.to_csv(results_csv, index=False)
    print(f"Detailed analysis saved to: {results_csv}")
    
    # Create summary statistics
    summary_stats = {
        'parameter': ['Angle', 'Distance'],
        'min_error': [
            results_df['angle_error'].min() if 'angle_error' in results_df.columns else None,
            results_df['distance_error'].min() if 'distance_error' in results_df.columns else None
        ],
        'max_error': [
            results_df['angle_error'].max() if 'angle_error' in results_df.columns else None,
            results_df['distance_error'].max() if 'distance_error' in results_df.columns else None
        ],
        'mean_error': [
            results_df['angle_error'].mean() if 'angle_error' in results_df.columns else None,
            results_df['distance_error'].mean() if 'distance_error' in results_df.columns else None
        ],
        'std_error': [
            results_df['angle_error'].std() if 'angle_error' in results_df.columns else None,
            results_df['distance_error'].std() if 'distance_error' in results_df.columns else None
        ],
        'best_weight': [
            results_df.loc[results_df['angle_error'].idxmin()]['weight'] if 'angle_error' in results_df.columns else None,
            results_df.loc[results_df['distance_error'].idxmin()]['weight'] if 'distance_error' in results_df.columns else None
        ],
        'best_sample_size': [
            results_df.loc[results_df['angle_error'].idxmin()]['sample_size'] if 'angle_error' in results_df.columns else None,
            results_df.loc[results_df['distance_error'].idxmin()]['sample_size'] if 'distance_error' in results_df.columns else None
        ],
        'best_filter_state': [
            results_df.loc[results_df['angle_error'].idxmin()]['filter_state'] if 'angle_error' in results_df.columns else None,
            results_df.loc[results_df['distance_error'].idxmin()]['filter_state'] if 'distance_error' in results_df.columns else None
        ]
    }
    
    summary_df = pd.DataFrame(summary_stats)
    summary_csv = output_path / "summary_statistics.csv"
    summary_df.to_csv(summary_csv, index=False)
    print(f"Summary statistics saved to: {summary_csv}")
    
    # Create visualizations
    create_visualizations(results_df, actual_angle, actual_distance, output_path)
    
    return results_df, summary_df

def create_visualizations(results_df, actual_angle, actual_distance, output_path):
    """
    Create various visualization plots
    """
    plt.style.use('seaborn-v0_8-darkgrid')
    
    # 1. Angle Error vs Weight (grouped by sample size and filter)
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Triangulation Error Analysis', fontsize=16, fontweight='bold')
    
    # Plot angle errors
    ax1 = axes[0, 0]
    for (sample_size, filter_state), group in results_df.groupby(['sample_size', 'filter_state']):
        label = f"{sample_size}, {filter_state}"
        group_sorted = group.sort_values('weight')
        ax1.plot(group_sorted['weight'], group_sorted['angle_error'], 
                marker='o', label=label, linewidth=2)
    
    ax1.axhline(y=0, color='r', linestyle='--', alpha=0.3)
    ax1.set_xlabel('PHAT Weight', fontsize=12)
    ax1.set_ylabel('Angle Error (degrees)', fontsize=12)
    ax1.set_title('Angle Error vs Weight', fontsize=14, fontweight='bold')
    ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    ax1.grid(True, alpha=0.3)
    
    # Plot distance errors
    ax2 = axes[0, 1]
    for (sample_size, filter_state), group in results_df.groupby(['sample_size', 'filter_state']):
        label = f"{sample_size}, {filter_state}"
        group_sorted = group.sort_values('weight')
        ax2.plot(group_sorted['weight'], group_sorted['distance_error'], 
                marker='s', label=label, linewidth=2)
    
    ax2.axhline(y=0, color='r', linestyle='--', alpha=0.3)
    ax2.set_xlabel('PHAT Weight', fontsize=12)
    ax2.set_ylabel('Distance Error (meters)', fontsize=12)
    ax2.set_title('Distance Error vs Weight', fontsize=14, fontweight='bold')
    ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    ax2.grid(True, alpha=0.3)
    
    # 2. Heatmap of angle errors
    ax3 = axes[1, 0]
    if 'angle_error' in results_df.columns:
        pivot_table = results_df.pivot_table(
            values='angle_error', 
            index='weight', 
            columns=['sample_size', 'filter_state'],
            aggfunc='mean'
        )
        
        # Flatten column names for display
        pivot_table.columns = [f"{size}_{filter}" for size, filter in pivot_table.columns]
        
        im = ax3.imshow(pivot_table.T, cmap='YlOrRd', aspect='auto')
        ax3.set_xticks(range(len(pivot_table.index)))
        ax3.set_xticklabels([f"{w:.1f}" for w in pivot_table.index])
        ax3.set_yticks(range(len(pivot_table.columns)))
        ax3.set_yticklabels(pivot_table.columns, fontsize=8)
        ax3.set_xlabel('PHAT Weight', fontsize=12)
        ax3.set_title('Angle Error Heatmap (degrees)', fontsize=14, fontweight='bold')
        plt.colorbar(im, ax=ax3)
    
    # 3. Bar chart of best performing configurations
    ax4 = axes[1, 1]
    if 'angle_error' in results_df.columns:
        # Find top 5 best configurations for angle
        top_angle = results_df.nsmallest(5, 'angle_error')[['weight', 'sample_size', 'filter_state', 'angle_error']]
        bars = ax4.barh(range(len(top_angle)), top_angle['angle_error'])
        ax4.set_yticks(range(len(top_angle)))
        ax4.set_yticklabels([f"W={row['weight']:.1f}, {row['sample_size']}, {row['filter_state']}" 
                           for _, row in top_angle.iterrows()])
        ax4.set_xlabel('Angle Error (degrees)', fontsize=12)
        ax4.set_title('Top 5 Configurations (Lowest Angle Error)', fontsize=14, fontweight='bold')
        
        # Add error values on bars
        for i, (bar, error) in enumerate(zip(bars, top_angle['angle_error'])):
            ax4.text(error + 0.01, bar.get_y() + bar.get_height()/2, 
                    f'{error:.2f}°', va='center')
    
    plt.tight_layout()
    plt.savefig(output_path / 'error_analysis.png', dpi=300, bbox_inches='tight')
    
    # 4. Scatter plot of all estimates
    fig2, axes2 = plt.subplots(1, 3, figsize=(18, 6))
    
    # Angle estimates
    ax5 = axes2[0]
    colors = plt.cm.tab20(np.linspace(0, 1, len(results_df)))
    for i, (_, row) in enumerate(results_df.iterrows()):
        ax5.scatter(row['weight'], row['estimated_angle'], 
                   color=colors[i], s=100, alpha=0.6, 
                   label=f"{row['sample_size']}, {row['filter_state']}")
    
    if actual_angle is not None:
        ax5.axhline(y=actual_angle, color='r', linestyle='--', linewidth=2, 
                   label=f'Actual: {actual_angle:.1f}°')
    
    ax5.set_xlabel('PHAT Weight', fontsize=12)
    ax5.set_ylabel('Estimated Angle (degrees)', fontsize=12)
    ax5.set_title('All Angle Estimates', fontsize=14, fontweight='bold')
    ax5.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
    ax5.grid(True, alpha=0.3)
    
    # Distance estimates
    ax6 = axes2[1]
    for i, (_, row) in enumerate(results_df.iterrows()):
        ax6.scatter(row['weight'], row['estimated_distance'], 
                   color=colors[i], s=100, alpha=0.6, 
                   label=f"{row['sample_size']}, {row['filter_state']}")
    
    if actual_distance is not None:
        ax6.axhline(y=actual_distance, color='r', linestyle='--', linewidth=2, 
                   label=f'Actual: {actual_distance:.1f}m')
    
    ax6.set_xlabel('PHAT Weight', fontsize=12)
    ax6.set_ylabel('Estimated Distance (meters)', fontsize=12)
    ax6.set_title('All Distance Estimates', fontsize=14, fontweight='bold')
    ax6.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
    ax6.grid(True, alpha=0.3)
    
    # Error correlation
    ax7 = axes2[2]
    scatter = ax7.scatter(results_df['angle_error'], results_df['distance_error'], 
                         c=results_df['weight'], cmap='viridis', s=100, alpha=0.7)
    ax7.set_xlabel('Angle Error (degrees)', fontsize=12)
    ax7.set_ylabel('Distance Error (meters)', fontsize=12)
    ax7.set_title('Error Correlation', fontsize=14, fontweight='bold')
    plt.colorbar(scatter, ax=ax7, label='PHAT Weight')
    ax7.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path / 'estimates_scatter.png', dpi=300, bbox_inches='tight')
    
    # 5. Summary box plots
    fig3, axes3 = plt.subplots(1, 2, figsize=(14, 6))
    
    # Box plot by sample size
    ax8 = axes3[0]
    if 'angle_error' in results_df.columns:
        sns.boxplot(data=results_df, x='sample_size', y='angle_error', ax=ax8)
        ax8.set_xlabel('Sample Size', fontsize=12)
        ax8.set_ylabel('Angle Error (degrees)', fontsize=12)
        ax8.set_title('Angle Error Distribution by Sample Size', fontsize=14, fontweight='bold')
    
    # Box plot by filter state
    ax9 = axes3[1]
    if 'angle_error' in results_df.columns:
        sns.boxplot(data=results_df, x='filter_state', y='angle_error', ax=ax9)
        ax9.set_xlabel('Filter State', fontsize=12)
        ax9.set_ylabel('Angle Error (degrees)', fontsize=12)
        ax9.set_title('Angle Error Distribution by Filter State', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(output_path / 'error_distributions.png', dpi=300, bbox_inches='tight')
    
    # Show all plots
    plt.show()
    
    print(f"Visualizations saved to: {output_path}")

def main():
    # Get CSV file path
    csv_path = input("Enter the path to your triangulation CSV file: ").strip().strip('"')
    
    if not Path(csv_path).exists():
        # Try in current directory
        csv_path = Path("triangulation_outputs") / csv_path
        if not csv_path.exists():
            # List available files
            files = list(Path("triangulation_outputs").glob("*.csv"))
            if files:
                print("Available files:")
                for i, f in enumerate(files):
                    print(f"{i+1}. {f.name}")
                choice = int(input("Select file number: ")) - 1
                csv_path = files[choice]
            else:
                print("No CSV files found in triangulation_outputs/")
                return
    
    # Analyze the data
    results_df, summary_df = analyze_triangulation_data(csv_path)
    
    # Print key findings
    if results_df is not None:
        print("\n" + "="*60)
        print("KEY FINDINGS:")
        print("="*60)
        
        if 'angle_error' in results_df.columns:
            best_angle = results_df.loc[results_df['angle_error'].idxmin()]
            print(f"Best angle estimation:")
            print(f"  Configuration: Weight={best_angle['weight']:.1f}, "
                  f"Sample={best_angle['sample_size']}, Filter={best_angle['filter_state']}")
            print(f"  Estimated: {best_angle['estimated_angle']:.2f}°, "
                  f"Error: {best_angle['angle_error']:.2f}°")
        
        if 'distance_error' in results_df.columns:
            best_distance = results_df.loc[results_df['distance_error'].idxmin()]
            print(f"\nBest distance estimation:")
            print(f"  Configuration: Weight={best_distance['weight']:.1f}, "
                  f"Sample={best_distance['sample_size']}, Filter={best_distance['filter_state']}")
            print(f"  Estimated: {best_distance['estimated_distance']:.2f}m, "
                  f"Error: {best_distance['distance_error']:.2f}m")
        
        print("\n" + "="*60)

if __name__ == "__main__":
    main()