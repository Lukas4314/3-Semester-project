import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

def analyze_all_triangulation_data(input_folder="triangulation_outputs", output_dir="analysis_output"):
    """
    Analyze triangulation differences from ALL CSV files in a folder
    """
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Find all CSV files
    input_path = Path(input_folder)
    if not input_path.exists():
        print(f"ERROR: Input folder '{input_folder}' not found!")
        return None, None
    
    csv_files = list(input_path.glob("*.csv"))
    if not csv_files:
        print(f"No CSV files found in {input_folder}")
        return None, None
    
    print(f"Found {len(csv_files)} CSV files in {input_folder}")
    
    all_results = []
    all_actuals = []
    
    # Process each file
    for i, csv_file in enumerate(csv_files, 1):
        print(f"\nProcessing file {i}/{len(csv_files)}: {csv_file.name}")
        
        try:
            df = pd.read_csv(csv_file)
            
            # Get actual values from this file
            actual_angle = None
            actual_distance = None
            
            # Try to find actual values in columns
            if 'ActualTriangulationAngle' in df.columns:
                # Get non-None values
                actual_angles = df['ActualTriangulationAngle'].dropna()
                actual_angles = actual_angles[actual_angles != "None"]
                if not actual_angles.empty:
                    actual_angle = float(actual_angles.iloc[0])
            
            if 'ActualTriangulationDistance' in df.columns:
                actual_distances = df['ActualTriangulationDistance'].dropna()
                actual_distances = actual_distances[actual_distances != "None"]
                if not actual_distances.empty:
                    actual_distance = float(actual_distances.iloc[0])
            
            # If actual values not in columns, check the data
            if actual_angle is None:
                for col in df.columns:
                    if 'Actual' in col and 'Angle' in col:
                        vals = df[col].dropna()
                        vals = vals[vals != "None"]
                        if not vals.empty:
                            try:
                                actual_angle = float(vals.iloc[0])
                                break
                            except (ValueError, TypeError):
                                continue
            
            if actual_distance is None:
                for col in df.columns:
                    if 'Actual' in col and 'Distance' in col:
                        vals = df[col].dropna()
                        vals = vals[vals != "None"]
                        if not vals.empty:
                            try:
                                actual_distance = float(vals.iloc[0])
                                break
                            except (ValueError, TypeError):
                                continue
            
            if actual_angle is not None or actual_distance is not None:
                all_actuals.append({
                    'file': csv_file.name,
                    'actual_angle': actual_angle,
                    'actual_distance': actual_distance
                })
            
            # Get TDOA columns
            tdoa_columns = [col for col in df.columns if col.startswith('TDOAPhatWeighting')]
            print(f"  Found {len(tdoa_columns)} TDOA columns, {len(df)} rows")
            
            # Process each row in the file
            for row_idx, row in df.iterrows():
                # Process ALL TDOA columns in this row
                for col_name in tdoa_columns:
                    value = row[col_name]
                    
                    # Skip if NaN, None, or empty
                    if pd.isna(value) or value == "None" or (isinstance(value, str) and not value.strip()):
                        continue
                    
                    if isinstance(value, str) and ';' in value:
                        parts = value.split(';')
                        if len(parts) == 2:  # Already triangulated (angle;distance)
                            try:
                                angle_str, dist_str = parts
                                angle = float(angle_str)
                                distance = float(dist_str)
                                
                                # Parse column name to extract parameters
                                col_parts = col_name.split('_')
                                
                                if len(col_parts) >= 4:
                                    weight_str = col_parts[0].replace('TDOAPhatWeighting', '')
                                    sample_size = col_parts[1]  # 2k, 4k, 8k
                                    filter_state = '_'.join(col_parts[2:])  # With_Filter or Without_Filter
                                    
                                    try:
                                        weight = float(weight_str)
                                    except ValueError:
                                        weight = 0.0
                                    
                                    # Create result entry
                                    result = {
                                        'source_file': csv_file.name,
                                        'row_index': row_idx,
                                        'weight': weight,
                                        'sample_size': sample_size,
                                        'filter_state': filter_state,
                                        'tdoa_column': col_name,
                                        'estimated_angle': angle,
                                        'estimated_distance': distance,
                                        'file_actual_angle': actual_angle,
                                        'file_actual_distance': actual_distance
                                    }
                                    
                                    # Calculate errors if actual values exist
                                    if actual_angle is not None:
                                        result['abs_angle_error'] = abs(angle - actual_angle)
                                        result['signed_angle_error'] = angle - actual_angle
                                        if actual_angle != 0:
                                            result['angle_error_percent'] = abs(angle - actual_angle) / abs(actual_angle) * 100
                                    
                                    if actual_distance is not None:
                                        result['abs_distance_error'] = abs(distance - actual_distance)
                                        result['signed_distance_error'] = distance - actual_distance
                                        if actual_distance != 0:
                                            result['distance_error_percent'] = abs(distance - actual_distance) / actual_distance * 100
                                    
                                    all_results.append(result)
                                    
                            except (ValueError, IndexError) as e:
                                print(f"  Row {row_idx}, Col {col_name}: Error parsing '{value}': {e}")
                                continue
        
        except Exception as e:
            print(f"  ERROR processing {csv_file.name}: {e}")
            import traceback
            traceback.print_exc()
    
    # Create consolidated DataFrame
    if not all_results:
        print("\nNo valid triangulation data found in any file!")
        return None, None
    
    results_df = pd.DataFrame(all_results)
    print(f"\nConsolidated {len(results_df)} triangulation results from all files")
    
    # Save consolidated results
    consolidated_csv = output_path / "consolidated_triangulation_results.csv"
    results_df.to_csv(consolidated_csv, index=False)
    print(f"Consolidated results saved to: {consolidated_csv}")
    
    # Create summary statistics
    summary_df = create_summary_statistics(results_df, output_path)
    
    # Create visualizations
    create_comprehensive_visualizations(results_df, output_path)
    
    return results_df, summary_df

def create_summary_statistics(results_df, output_path):
    """Create summary statistics from consolidated data"""
    
    # Group by configuration
    config_summary = results_df.groupby(['weight', 'sample_size', 'filter_state']).agg({
        'estimated_angle': ['count', 'mean', 'std', 'min', 'max'],
        'estimated_distance': ['mean', 'std', 'min', 'max'],
        'abs_angle_error': ['mean', 'std', 'min', 'max'] if 'abs_angle_error' in results_df.columns else 'count',
        'abs_distance_error': ['mean', 'std', 'min', 'max'] if 'abs_distance_error' in results_df.columns else 'count'
    }).round(3)
    
    # Flatten multi-level columns
    config_summary.columns = ['_'.join(col).strip() for col in config_summary.columns.values]
    config_summary = config_summary.reset_index()
    
    # Overall statistics
    overall_stats = {}
    
    if 'abs_angle_error' in results_df.columns:
        overall_stats['angle_error_mean'] = results_df['abs_angle_error'].mean()
        overall_stats['angle_error_std'] = results_df['abs_angle_error'].std()
        overall_stats['angle_error_min'] = results_df['abs_angle_error'].min()
        overall_stats['angle_error_max'] = results_df['abs_angle_error'].max()
        
        # Best configuration for angle
        best_angle_idx = results_df['abs_angle_error'].idxmin()
        best_angle_config = results_df.loc[best_angle_idx]
        overall_stats['best_angle_config'] = f"Weight={best_angle_config['weight']:.1f}, {best_angle_config['sample_size']}, {best_angle_config['filter_state']}"
        overall_stats['best_angle_error'] = best_angle_config['abs_angle_error']
        overall_stats['best_angle_file'] = best_angle_config['source_file']
    
    if 'abs_distance_error' in results_df.columns:
        overall_stats['distance_error_mean'] = results_df['abs_distance_error'].mean()
        overall_stats['distance_error_std'] = results_df['abs_distance_error'].std()
        overall_stats['distance_error_min'] = results_df['abs_distance_error'].min()
        overall_stats['distance_error_max'] = results_df['abs_distance_error'].max()
        
        # Best configuration for distance
        best_dist_idx = results_df['abs_distance_error'].idxmin()
        best_dist_config = results_df.loc[best_dist_idx]
        overall_stats['best_distance_config'] = f"Weight={best_dist_config['weight']:.1f}, {best_dist_config['sample_size']}, {best_dist_config['filter_state']}"
        overall_stats['best_distance_error'] = best_dist_config['abs_distance_error']
        overall_stats['best_distance_file'] = best_dist_config['source_file']
    
    overall_stats['total_samples'] = len(results_df)
    overall_stats['unique_configs'] = len(results_df[['weight', 'sample_size', 'filter_state']].drop_duplicates())
    overall_stats['unique_files'] = results_df['source_file'].nunique()
    
    # Save summaries
    config_summary.to_csv(output_path / "configuration_summary.csv", index=False)
    
    overall_df = pd.DataFrame([overall_stats])
    overall_df.to_csv(output_path / "overall_statistics.csv", index=False)
    
    print(f"Configuration summary saved to: {output_path / 'configuration_summary.csv'}")
    print(f"Overall statistics saved to: {output_path / 'overall_statistics.csv'}")
    
    return pd.concat([config_summary, overall_df], ignore_index=True)

def create_comprehensive_visualizations(results_df, output_path):
    """Create comprehensive visualizations for all data"""
    
    plt.style.use('seaborn-v0_8-darkgrid')
    
    # Check if we have error data
    has_angle_error = 'abs_angle_error' in results_df.columns
    has_distance_error = 'abs_distance_error' in results_df.columns
    
    # 1. Configuration Performance Heatmap
    if has_angle_error:
        fig, axes = plt.subplots(2, 2, figsize=(16, 14))
        fig.suptitle('Triangulation Performance Across All Files', fontsize=16, fontweight='bold')
        
        # Angle error heatmap
        ax1 = axes[0, 0]
        pivot_angle = results_df.pivot_table(
            values='abs_angle_error',
            index='weight',
            columns=['sample_size', 'filter_state'],
            aggfunc='mean'
        ).fillna(0)
        
        if not pivot_angle.empty:
            # Flatten column names
            pivot_angle.columns = [f"{size}\n{filter}" for size, filter in pivot_angle.columns]
            
            im1 = ax1.imshow(pivot_angle.T, cmap='YlOrRd', aspect='auto')
            ax1.set_xticks(range(len(pivot_angle.index)))
            ax1.set_xticklabels([f"{w:.1f}" for w in pivot_angle.index])
            ax1.set_yticks(range(len(pivot_angle.columns)))
            ax1.set_yticklabels(pivot_angle.columns, fontsize=9)
            ax1.set_xlabel('PHAT Weight', fontsize=12)
            ax1.set_ylabel('Configuration', fontsize=12)
            ax1.set_title('Mean Angle Error by Configuration', fontsize=14, fontweight='bold')
            plt.colorbar(im1, ax=ax1, label='Angle Error (degrees)')
        
        # Distance error heatmap
        ax2 = axes[0, 1]
        if has_distance_error:
            pivot_distance = results_df.pivot_table(
                values='abs_distance_error',
                index='weight',
                columns=['sample_size', 'filter_state'],
                aggfunc='mean'
            ).fillna(0)
            
            if not pivot_distance.empty:
                pivot_distance.columns = [f"{size}\n{filter}" for size, filter in pivot_distance.columns]
                
                im2 = ax2.imshow(pivot_distance.T, cmap='YlOrBr', aspect='auto')
                ax2.set_xticks(range(len(pivot_distance.index)))
                ax2.set_xticklabels([f"{w:.1f}" for w in pivot_distance.index])
                ax2.set_yticks(range(len(pivot_distance.columns)))
                ax2.set_yticklabels(pivot_distance.columns, fontsize=9)
                ax2.set_xlabel('PHAT Weight', fontsize=12)
                ax2.set_ylabel('Configuration', fontsize=12)
                ax2.set_title('Mean Distance Error by Configuration', fontsize=14, fontweight='bold')
                plt.colorbar(im2, ax=ax2, label='Distance Error (meters)')
        
        # 2. Error distributions by configuration
        ax3 = axes[1, 0]
        if has_angle_error:
            # Create a combined label for grouping
            results_df['config_label'] = results_df.apply(
                lambda x: f"W={x['weight']:.1f}, {x['sample_size']}, {x['filter_state']}", axis=1
            )
            
            # Get top 10 configurations by frequency
            top_configs = results_df['config_label'].value_counts().head(10).index
            top_data = results_df[results_df['config_label'].isin(top_configs)]
            
            if not top_data.empty:
                sns.boxplot(data=top_data, x='abs_angle_error', y='config_label', ax=ax3, orient='h')
                ax3.set_xlabel('Angle Error (degrees)', fontsize=12)
                ax3.set_ylabel('Configuration', fontsize=12)
                ax3.set_title('Angle Error Distribution (Top 10 Configs)', fontsize=14, fontweight='bold')
        
        # 3. Performance by sample size
        ax4 = axes[1, 1]
        if has_angle_error:
            sample_performance = results_df.groupby('sample_size')['abs_angle_error'].agg(['mean', 'std', 'count']).reset_index()
            
            x_pos = range(len(sample_performance))
            bars = ax4.bar(x_pos, sample_performance['mean'], 
                          yerr=sample_performance['std'], 
                          capsize=5, alpha=0.7)
            
            ax4.set_xticks(x_pos)
            ax4.set_xticklabels(sample_performance['sample_size'])
            ax4.set_xlabel('Sample Size', fontsize=12)
            ax4.set_ylabel('Mean Angle Error (degrees)', fontsize=12)
            ax4.set_title('Performance by Sample Size', fontsize=14, fontweight='bold')
            
            # Add count labels
            for i, (bar, count) in enumerate(zip(bars, sample_performance['count'])):
                ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                        f'n={count}', ha='center', va='bottom', fontsize=9)
        
        plt.tight_layout()
        plt.savefig(output_path / 'performance_analysis.png', dpi=300, bbox_inches='tight')
    
    # 4. Scatter plot: All estimates
    fig2, axes2 = plt.subplots(1, 3, figsize=(18, 6))
    
    # All angle estimates
    ax5 = axes2[0]
    scatter1 = ax5.scatter(results_df['weight'], results_df['estimated_angle'],
                          c=results_df.index, cmap='viridis', 
                          s=30, alpha=0.6)
    ax5.set_xlabel('PHAT Weight', fontsize=12)
    ax5.set_ylabel('Estimated Angle (degrees)', fontsize=12)
    ax5.set_title('All Angle Estimates', fontsize=14, fontweight='bold')
    ax5.grid(True, alpha=0.3)
    
    # All distance estimates
    ax6 = axes2[1]
    scatter2 = ax6.scatter(results_df['weight'], results_df['estimated_distance'],
                          c=results_df.index, cmap='plasma',
                          s=30, alpha=0.6)
    ax6.set_xlabel('PHAT Weight', fontsize=12)
    ax6.set_ylabel('Estimated Distance (meters)', fontsize=12)
    ax6.set_title('All Distance Estimates', fontsize=14, fontweight='bold')
    ax6.grid(True, alpha=0.3)
    
    # Error correlation (if available)
    ax7 = axes2[2]
    if has_angle_error and has_distance_error:
        scatter3 = ax7.scatter(results_df['abs_angle_error'], results_df['abs_distance_error'],
                              c=results_df['weight'], cmap='coolwarm',
                              s=50, alpha=0.7)
        ax7.set_xlabel('Angle Error (degrees)', fontsize=12)
        ax7.set_ylabel('Distance Error (meters)', fontsize=12)
        ax7.set_title('Error Correlation', fontsize=14, fontweight='bold')
        plt.colorbar(scatter3, ax=ax7, label='PHAT Weight')
    else:
        # Show configuration distribution instead
        config_counts = results_df['sample_size'].value_counts()
        ax7.pie(config_counts.values, labels=config_counts.index, autopct='%1.1f%%')
        ax7.set_title('Sample Size Distribution', fontsize=14, fontweight='bold')
    
    ax7.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path / 'all_estimates.png', dpi=300, bbox_inches='tight')
    
    # 5. Performance trends over weight
    fig3, axes3 = plt.subplots(2, 2, figsize=(16, 12))
    
    # Angle error trend by sample size
    ax8 = axes3[0, 0]
    if has_angle_error:
        for sample_size in results_df['sample_size'].unique():
            sample_data = results_df[results_df['sample_size'] == sample_size]
            trend = sample_data.groupby('weight')['abs_angle_error'].mean().reset_index()
            ax8.plot(trend['weight'], trend['abs_angle_error'], 
                    marker='o', linewidth=2, label=sample_size)
        
        ax8.set_xlabel('PHAT Weight', fontsize=12)
        ax8.set_ylabel('Mean Angle Error (degrees)', fontsize=12)
        ax8.set_title('Angle Error Trend by Sample Size', fontsize=14, fontweight='bold')
        ax8.legend()
        ax8.grid(True, alpha=0.3)
    
    # Distance error trend by filter
    ax9 = axes3[0, 1]
    if has_distance_error:
        for filter_state in results_df['filter_state'].unique():
            filter_data = results_df[results_df['filter_state'] == filter_state]
            trend = filter_data.groupby('weight')['abs_distance_error'].mean().reset_index()
            ax9.plot(trend['weight'], trend['abs_distance_error'],
                    marker='s', linewidth=2, label=filter_state)
        
        ax9.set_xlabel('PHAT Weight', fontsize=12)
        ax9.set_ylabel('Mean Distance Error (meters)', fontsize=12)
        ax9.set_title('Distance Error Trend by Filter State', fontsize=14, fontweight='bold')
        ax9.legend()
        ax9.grid(True, alpha=0.3)
    
    # Configuration frequency
    ax10 = axes3[1, 0]
    config_freq = results_df.groupby(['sample_size', 'filter_state']).size().reset_index(name='count')
    
    # Create stacked bar
    sample_sizes = results_df['sample_size'].unique()
    filter_states = results_df['filter_state'].unique()
    
    bottom = np.zeros(len(sample_sizes))
    colors = plt.cm.Set3(np.linspace(0, 1, len(filter_states)))
    
    for i, filter_state in enumerate(filter_states):
        counts = []
        for sample_size in sample_sizes:
            count = len(results_df[(results_df['sample_size'] == sample_size) & 
                                  (results_df['filter_state'] == filter_state)])
            counts.append(count)
        
        ax10.bar(sample_sizes, counts, bottom=bottom, label=filter_state, color=colors[i])
        bottom += np.array(counts)
    
    ax10.set_xlabel('Sample Size', fontsize=12)
    ax10.set_ylabel('Number of Measurements', fontsize=12)
    ax10.set_title('Configuration Frequency', fontsize=14, fontweight='bold')
    ax10.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    
    # Best performing configurations
    ax11 = axes3[1, 1]
    if has_angle_error:
        # Group by configuration and get mean error
        config_performance = results_df.groupby(['weight', 'sample_size', 'filter_state']).agg({
            'abs_angle_error': 'mean',
            'estimated_angle': 'count'
        }).reset_index()
        
        # Sort and get top 10
        top_configs = config_performance.nsmallest(10, 'abs_angle_error')
        
        # Create labels
        labels = [f"W={row['weight']:.1f}\n{row['sample_size']}\n{row['filter_state']}" 
                 for _, row in top_configs.iterrows()]
        
        bars = ax11.barh(range(len(top_configs)), top_configs['abs_angle_error'])
        ax11.set_yticks(range(len(top_configs)))
        ax11.set_yticklabels(labels, fontsize=9)
        ax11.set_xlabel('Mean Angle Error (degrees)', fontsize=12)
        ax11.set_title('Top 10 Configurations (Lowest Error)', fontsize=14, fontweight='bold')
        
        # Add error values
        for i, (bar, error) in enumerate(zip(bars, top_configs['abs_angle_error'])):
            ax11.text(error + 0.01, bar.get_y() + bar.get_height()/2, 
                     f'{error:.2f}°', va='center', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(output_path / 'performance_trends.png', dpi=300, bbox_inches='tight')
    
    print(f"\nVisualizations saved to: {output_path}")
    plt.show()

def print_key_findings(results_df):
    """Print key findings from the analysis"""
    
    print("\n" + "="*70)
    print("KEY FINDINGS FROM ALL FILES:")
    print("="*70)
    
    print(f"\nDataset Overview:")
    print(f"- Total measurements: {len(results_df):,}")
    print(f"- Unique files: {results_df['source_file'].nunique()}")
    print(f"- Unique configurations: {results_df[['weight', 'sample_size', 'filter_state']].drop_duplicates().shape[0]}")
    
    if 'abs_angle_error' in results_df.columns:
        print(f"\nAngle Estimation Performance:")
        print(f"- Mean error: {results_df['abs_angle_error'].mean():.2f}°")
        print(f"- Std deviation: {results_df['abs_angle_error'].std():.2f}°")
        print(f"- Range: {results_df['abs_angle_error'].min():.2f}° to {results_df['abs_angle_error'].max():.2f}°")
        
        # Best configuration
        best_angle_idx = results_df['abs_angle_error'].idxmin()
        best_angle = results_df.loc[best_angle_idx]
        print(f"- Best configuration: Weight={best_angle['weight']:.1f}, {best_angle['sample_size']}, {best_angle['filter_state']}")
        print(f"  Error: {best_angle['abs_angle_error']:.2f}°, File: {best_angle['source_file']}")
    
    if 'abs_distance_error' in results_df.columns:
        print(f"\nDistance Estimation Performance:")
        print(f"- Mean error: {results_df['abs_distance_error'].mean():.2f}m")
        print(f"- Std deviation: {results_df['abs_distance_error'].std():.2f}m")
        print(f"- Range: {results_df['abs_distance_error'].min():.2f}m to {results_df['abs_distance_error'].max():.2f}m")
        
        # Best configuration
        best_dist_idx = results_df['abs_distance_error'].idxmin()
        best_dist = results_df.loc[best_dist_idx]
        print(f"- Best configuration: Weight={best_dist['weight']:.1f}, {best_dist['sample_size']}, {best_dist['filter_state']}")
        print(f"  Error: {best_dist['abs_distance_error']:.2f}m, File: {best_dist['source_file']}")
    
    # Configuration recommendations
    print(f"\nConfiguration Analysis:")
    
    # By sample size
    if 'abs_angle_error' in results_df.columns:
        sample_perf = results_df.groupby('sample_size')['abs_angle_error'].mean().sort_values()
        print(f"- Best sample size: {sample_perf.index[0]} (avg error: {sample_perf.iloc[0]:.2f}°)")
    
    # By filter state
    if 'abs_angle_error' in results_df.columns:
        filter_perf = results_df.groupby('filter_state')['abs_angle_error'].mean().sort_values()
        print(f"- Best filter: {filter_perf.index[0]} (avg error: {filter_perf.iloc[0]:.2f}°)")
    
    # By weight
    if 'abs_angle_error' in results_df.columns:
        weight_perf = results_df.groupby('weight')['abs_angle_error'].mean().sort_values()
        print(f"- Best weight: {weight_perf.index[0]:.1f} (avg error: {weight_perf.iloc[0]:.2f}°)")
    
    print("\n" + "="*70)

def main():
    # Analyze all files in the triangulation_outputs folder
    input_folder = "triangulation_outputs"
    
    print(f"Analyzing ALL CSV files in: {input_folder}")
    print("-" * 50)
    
    results_df, summary_df = analyze_all_triangulation_data(input_folder)
    
    if results_df is not None:
        print_key_findings(results_df)
        
        # Optional: Save a quick report
        report_file = Path("analysis_output") / "analysis_report.txt"
        with open(report_file, 'w') as f:
            f.write(f"Triangulation Analysis Report\n")
            f.write(f"Generated: {pd.Timestamp.now()}\n")
            f.write(f"Total measurements: {len(results_df)}\n")
            f.write(f"Unique files: {results_df['source_file'].nunique()}\n")
            
            if 'abs_angle_error' in results_df.columns:
                f.write(f"\nAngle Error Statistics:\n")
                f.write(f"  Mean: {results_df['abs_angle_error'].mean():.2f}°\n")
                f.write(f"  Std: {results_df['abs_angle_error'].std():.2f}°\n")
                f.write(f"  Min: {results_df['abs_angle_error'].min():.2f}°\n")
                f.write(f"  Max: {results_df['abs_angle_error'].max():.2f}°\n")
        
        print(f"\nAnalysis report saved to: {report_file}")

if __name__ == "__main__":
    main()