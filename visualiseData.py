import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

def analyze_consolidated_csv(csv_path, output_dir="analysis_output"):
    """
    Analyze the consolidated CSV file with pre-calculated triangulation results
    """
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Load the consolidated CSV
    print(f"Loading consolidated data from: {csv_path}")
    results_df = pd.read_csv(csv_path)
    
    # Clean up column names (strip whitespace)
    results_df.columns = results_df.columns.str.strip()
    
    print(f"Loaded {len(results_df)} rows")
    print(f"Columns: {list(results_df.columns)}")
    
    # Check what columns we have
    print("\nColumn Analysis:")
    print(f"- Has angle_error: {'angle_error' in results_df.columns}")
    print(f"- Has distance_error: {'distance_error' in results_df.columns}")
    print(f"- Has actual_angle: {'actual_angle' in results_df.columns}")
    print(f"- Has actual_distance: {'actual_distance' in results_df.columns}")
    
    # Clean the data
    results_df = clean_dataframe(results_df)
    
    # Create summary statistics
    summary_df = create_summary_statistics(results_df, output_path)
    
    # Create visualizations
    create_comprehensive_visualizations(results_df, output_path)
    
    # Print key findings
    print_key_findings(results_df)
    
    return results_df, summary_df

def clean_dataframe(df):
    """Clean and prepare the dataframe"""
    # Convert numeric columns
    numeric_columns = [
        'estimated_angle', 'estimated_distance',
        'angle_error', 'signed_angle_error',
        'distance_error', 'signed_distance_error',
        'actual_angle', 'actual_distance'
    ]
    
    for col in numeric_columns:
        if col in df.columns:
            # Convert to numeric, coerce errors to NaN
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Clean string columns
    string_columns = ['sample_size', 'filter_state', 'action', 'source_file']
    for col in string_columns:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    
    # Create absolute errors if not present
    if 'angle_error' in df.columns and 'abs_angle_error' not in df.columns:
        df['abs_angle_error'] = df['angle_error'].abs()
    
    if 'distance_error' in df.columns and 'abs_distance_error' not in df.columns:
        df['abs_distance_error'] = df['distance_error'].abs()
    
    # Create percentage errors
    if 'angle_error' in df.columns and 'actual_angle' in df.columns:
        df['angle_error_percent'] = (df['abs_angle_error'] / df['actual_angle'].abs()) * 100
    
    if 'distance_error' in df.columns and 'actual_distance' in df.columns:
        df['distance_error_percent'] = (df['abs_distance_error'] / df['actual_distance']) * 100
    
    return df

def create_summary_statistics(results_df, output_path):
    """Create summary statistics from the data"""
    
    # Overall statistics
    overall_stats = {
        'total_samples': len(results_df),
        'unique_files': results_df['source_file'].nunique() if 'source_file' in results_df.columns else 1,
        'unique_configs': results_df[['weight', 'sample_size', 'filter_state']].drop_duplicates().shape[0]
    }
    
    # Angle statistics
    if 'angle_error' in results_df.columns:
        overall_stats.update({
            'angle_error_mean': results_df['angle_error'].abs().mean(),
            'angle_error_std': results_df['angle_error'].abs().std(),
            'angle_error_min': results_df['angle_error'].abs().min(),
            'angle_error_max': results_df['angle_error'].abs().max(),
        })
        
        # Best configuration for angle
        if 'abs_angle_error' in results_df.columns:
            best_angle_idx = results_df['abs_angle_error'].idxmin()
            best_angle = results_df.loc[best_angle_idx]
            overall_stats.update({
                'best_angle_config': f"Weight={best_angle['weight']:.1f}, {best_angle['sample_size']}, {best_angle['filter_state']}",
                'best_angle_error': best_angle['abs_angle_error'],
                'best_angle_source': best_angle['source_file'] if 'source_file' in results_df.columns else 'N/A'
            })
    
    # Distance statistics
    if 'distance_error' in results_df.columns:
        overall_stats.update({
            'distance_error_mean': results_df['distance_error'].abs().mean(),
            'distance_error_std': results_df['distance_error'].abs().std(),
            'distance_error_min': results_df['distance_error'].abs().min(),
            'distance_error_max': results_df['distance_error'].abs().max(),
        })
        
        # Best configuration for distance
        if 'abs_distance_error' in results_df.columns:
            best_dist_idx = results_df['abs_distance_error'].idxmin()
            best_dist = results_df.loc[best_dist_idx]
            overall_stats.update({
                'best_distance_config': f"Weight={best_dist['weight']:.1f}, {best_dist['sample_size']}, {best_dist['filter_state']}",
                'best_distance_error': best_dist['abs_distance_error'],
                'best_distance_source': best_dist['source_file'] if 'source_file' in results_df.columns else 'N/A'
            })
    
    # Save overall statistics
    overall_df = pd.DataFrame([overall_stats])
    overall_df.to_csv(output_path / "overall_statistics.csv", index=False)
    print(f"Overall statistics saved to: {output_path / 'overall_statistics.csv'}")
    
    # Create configuration summary
    if 'abs_angle_error' in results_df.columns:
        config_summary = results_df.groupby(['weight', 'sample_size', 'filter_state']).agg({
            'estimated_angle': ['count', 'mean', 'std', 'min', 'max'],
            'estimated_distance': ['mean', 'std', 'min', 'max'],
            'abs_angle_error': ['mean', 'std', 'min', 'max'],
            'abs_distance_error': ['mean', 'std', 'min', 'max'] if 'abs_distance_error' in results_df.columns else 'count'
        }).round(3)
        
        # Flatten multi-level columns
        config_summary.columns = ['_'.join(col).strip() for col in config_summary.columns.values]
        config_summary = config_summary.reset_index()
        config_summary.to_csv(output_path / "configuration_summary.csv", index=False)
        print(f"Configuration summary saved to: {output_path / 'configuration_summary.csv'}")
    
    return overall_df

def create_comprehensive_visualizations(results_df, output_path):
    """Create comprehensive visualizations for all data"""
    
    plt.style.use('seaborn-v0_8-darkgrid')
    
    # Check if we have error data
    has_angle_error = 'abs_angle_error' in results_df.columns
    has_distance_error = 'abs_distance_error' in results_df.columns
    
    # 1. Configuration Performance Heatmap
    if has_angle_error:
        fig, axes = plt.subplots(2, 2, figsize=(16, 14))
        fig.suptitle('Triangulation Performance Analysis', fontsize=16, fontweight='bold')
        
        # Angle error heatmap
        ax1 = axes[0, 0]
        try:
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
                ax1.set_title('Mean Angle Error by Configuration', fontsize=14, fontweight='bold')
                plt.colorbar(im1, ax=ax1, label='Angle Error (degrees)')
        except Exception as e:
            ax1.text(0.5, 0.5, f"Heatmap Error:\n{str(e)}", 
                    ha='center', va='center', transform=ax1.transAxes)
        
        # Distance error heatmap
        ax2 = axes[0, 1]
        if has_distance_error:
            try:
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
                    ax2.set_title('Mean Distance Error by Configuration', fontsize=14, fontweight='bold')
                    plt.colorbar(im2, ax=ax2, label='Distance Error (meters)')
            except Exception as e:
                ax2.text(0.5, 0.5, f"Heatmap Error:\n{str(e)}", 
                        ha='center', va='center', transform=ax2.transAxes)
        
        # 2. Error distributions by configuration
        ax3 = axes[1, 0]
        if has_angle_error:
            try:
                # Create a combined label for grouping
                results_df['config_label'] = results_df.apply(
                    lambda x: f"W={x['weight']:.1f}\n{x['sample_size']}\n{x['filter_state']}", axis=1
                )
                
                # Get top 10 configurations by frequency
                top_configs = results_df['config_label'].value_counts().head(10).index
                top_data = results_df[results_df['config_label'].isin(top_configs)]
                
                if not top_data.empty:
                    sns.boxplot(data=top_data, x='abs_angle_error', y='config_label', ax=ax3, orient='h')
                    ax3.set_xlabel('Angle Error (degrees)', fontsize=12)
                    ax3.set_ylabel('Configuration', fontsize=12)
                    ax3.set_title('Angle Error Distribution (Top 10 Configs)', fontsize=14, fontweight='bold')
            except Exception as e:
                ax3.text(0.5, 0.5, f"Boxplot Error:\n{str(e)}", 
                        ha='center', va='center', transform=ax3.transAxes)
        
        # 3. Performance by sample size
        ax4 = axes[1, 1]
        if has_angle_error:
            try:
                sample_performance = results_df.groupby('sample_size')['abs_angle_error'].agg(['mean', 'std', 'count']).reset_index()
                
                if not sample_performance.empty:
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
                                f'n={int(count)}', ha='center', va='bottom', fontsize=9)
            except Exception as e:
                ax4.text(0.5, 0.5, f"Bar Chart Error:\n{str(e)}", 
                        ha='center', va='center', transform=ax4.transAxes)
        
        plt.tight_layout()
        plt.savefig(output_path / 'performance_analysis.png', dpi=300, bbox_inches='tight')
    
    # 4. Scatter plot: All estimates
    fig2, axes2 = plt.subplots(1, 3, figsize=(18, 6))
    
    # All angle estimates
    ax5 = axes2[0]
    try:
        if 'estimated_angle' in results_df.columns:
            scatter1 = ax5.scatter(results_df['weight'], results_df['estimated_angle'],
                                  c=results_df.index, cmap='viridis', 
                                  s=30, alpha=0.6)
            ax5.set_xlabel('PHAT Weight', fontsize=12)
            ax5.set_ylabel('Estimated Angle (degrees)', fontsize=12)
            ax5.set_title('All Angle Estimates', fontsize=14, fontweight='bold')
            ax5.grid(True, alpha=0.3)
    except Exception as e:
        ax5.text(0.5, 0.5, f"Scatter Error:\n{str(e)}", 
                ha='center', va='center', transform=ax5.transAxes)
    
    # All distance estimates
    ax6 = axes2[1]
    try:
        if 'estimated_distance' in results_df.columns:
            scatter2 = ax6.scatter(results_df['weight'], results_df['estimated_distance'],
                                  c=results_df.index, cmap='plasma',
                                  s=30, alpha=0.6)
            ax6.set_xlabel('PHAT Weight', fontsize=12)
            ax6.set_ylabel('Estimated Distance (meters)', fontsize=12)
            ax6.set_title('All Distance Estimates', fontsize=14, fontweight='bold')
            ax6.grid(True, alpha=0.3)
    except Exception as e:
        ax6.text(0.5, 0.5, f"Scatter Error:\n{str(e)}", 
                ha='center', va='center', transform=ax6.transAxes)
    
    # Error correlation (if available)
    ax7 = axes2[2]
    if has_angle_error and has_distance_error:
        try:
            scatter3 = ax7.scatter(results_df['abs_angle_error'], results_df['abs_distance_error'],
                                  c=results_df['weight'], cmap='coolwarm',
                                  s=50, alpha=0.7)
            ax7.set_xlabel('Angle Error (degrees)', fontsize=12)
            ax7.set_ylabel('Distance Error (meters)', fontsize=12)
            ax7.set_title('Error Correlation', fontsize=14, fontweight='bold')
            plt.colorbar(scatter3, ax=ax7, label='PHAT Weight')
        except Exception as e:
            ax7.text(0.5, 0.5, f"Correlation Error:\n{str(e)}", 
                    ha='center', va='center', transform=ax7.transAxes)
    else:
        # Show configuration distribution instead
        try:
            if 'sample_size' in results_df.columns:
                config_counts = results_df['sample_size'].value_counts()
                ax7.pie(config_counts.values, labels=config_counts.index, autopct='%1.1f%%')
                ax7.set_title('Sample Size Distribution', fontsize=14, fontweight='bold')
        except Exception as e:
            ax7.text(0.5, 0.5, f"Pie Chart Error:\n{str(e)}", 
                    ha='center', va='center', transform=ax7.transAxes)
    
    ax7.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path / 'all_estimates.png', dpi=300, bbox_inches='tight')
    
    # 5. Performance trends over weight
    fig3, axes3 = plt.subplots(2, 2, figsize=(16, 12))
    
    # Angle error trend by sample size
    ax8 = axes3[0, 0]
    if has_angle_error and 'sample_size' in results_df.columns:
        try:
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
        except Exception as e:
            ax8.text(0.5, 0.5, f"Trend Error:\n{str(e)}", 
                    ha='center', va='center', transform=ax8.transAxes)
    
    # Distance error trend by filter
    ax9 = axes3[0, 1]
    if has_distance_error and 'filter_state' in results_df.columns:
        try:
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
        except Exception as e:
            ax9.text(0.5, 0.5, f"Trend Error:\n{str(e)}", 
                    ha='center', va='center', transform=ax9.transAxes)
    
    # Configuration frequency
    ax10 = axes3[1, 0]
    if 'sample_size' in results_df.columns and 'filter_state' in results_df.columns:
        try:
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
        except Exception as e:
            ax10.text(0.5, 0.5, f"Bar Chart Error:\n{str(e)}", 
                    ha='center', va='center', transform=ax10.transAxes)
    
    # Best performing configurations
    ax11 = axes3[1, 1]
    if has_angle_error:
        try:
            # Group by configuration and get mean error
            config_performance = results_df.groupby(['weight', 'sample_size', 'filter_state']).agg({
                'abs_angle_error': 'mean',
                'estimated_angle': 'count'
            }).reset_index()
            
            # Sort and get top 10
            top_configs = config_performance.nsmallest(10, 'abs_angle_error')
            
            if not top_configs.empty:
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
        except Exception as e:
            ax11.text(0.5, 0.5, f"Bar Chart Error:\n{str(e)}", 
                    ha='center', va='center', transform=ax11.transAxes)
    
    plt.tight_layout()
    plt.savefig(output_path / 'performance_trends.png', dpi=300, bbox_inches='tight')
    
    # Additional visualization: Error distribution by actual angle/distance
    if 'actual_angle' in results_df.columns and has_angle_error:
        fig4, axes4 = plt.subplots(1, 2, figsize=(14, 6))
        
        # Angle error vs actual angle
        ax12 = axes4[0]
        scatter4 = ax12.scatter(results_df['actual_angle'], results_df['abs_angle_error'],
                              c=results_df['weight'], cmap='cool', s=50, alpha=0.7)
        ax12.set_xlabel('Actual Angle (degrees)', fontsize=12)
        ax12.set_ylabel('Angle Error (degrees)', fontsize=12)
        ax12.set_title('Angle Error vs Actual Angle', fontsize=14, fontweight='bold')
        plt.colorbar(scatter4, ax=ax12, label='PHAT Weight')
        ax12.grid(True, alpha=0.3)
        
        # Distance error vs actual distance
        ax13 = axes4[1]
        if 'actual_distance' in results_df.columns and has_distance_error:
            scatter5 = ax13.scatter(results_df['actual_distance'], results_df['abs_distance_error'],
                                  c=results_df['weight'], cmap='winter', s=50, alpha=0.7)
            ax13.set_xlabel('Actual Distance (meters)', fontsize=12)
            ax13.set_ylabel('Distance Error (meters)', fontsize=12)
            ax13.set_title('Distance Error vs Actual Distance', fontsize=14, fontweight='bold')
            plt.colorbar(scatter5, ax=ax13, label='PHAT Weight')
        else:
            # Signed angle error distribution
            if 'signed_angle_error' in results_df.columns:
                ax13.hist(results_df['signed_angle_error'].dropna(), bins=30, alpha=0.7, edgecolor='black')
                ax13.axvline(x=0, color='r', linestyle='--', linewidth=2)
                ax13.set_xlabel('Signed Angle Error (degrees)', fontsize=12)
                ax13.set_ylabel('Frequency', fontsize=12)
                ax13.set_title('Signed Angle Error Distribution', fontsize=14, fontweight='bold')
        
        ax13.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_path / 'error_distributions.png', dpi=300, bbox_inches='tight')
    
    print(f"\nVisualizations saved to: {output_path}")
    plt.show()

def print_key_findings(results_df):
    """Print key findings from the analysis"""
    
    print("\n" + "="*80)
    print("KEY FINDINGS:")
    print("="*80)
    
    print(f"\nDataset Overview:")
    print(f"- Total measurements: {len(results_df):,}")
    
    if 'source_file' in results_df.columns:
        print(f"- Unique files: {results_df['source_file'].nunique()}")
    
    print(f"- Unique configurations: {results_df[['weight', 'sample_size', 'filter_state']].drop_duplicates().shape[0]}")
    
    if 'abs_angle_error' in results_df.columns:
        print(f"\nAngle Estimation Performance:")
        print(f"- Mean error: {results_df['abs_angle_error'].mean():.2f}°")
        print(f"- Std deviation: {results_df['abs_angle_error'].std():.2f}°")
        print(f"- Range: {results_df['abs_angle_error'].min():.2f}° to {results_df['abs_angle_error'].max():.2f}°")
        
        # Best configuration for angle
        best_angle_idx = results_df['abs_angle_error'].idxmin()
        best_angle = results_df.loc[best_angle_idx]
        print(f"- Best configuration: Weight={best_angle['weight']:.1f}, {best_angle['sample_size']}, {best_angle['filter_state']}")
        print(f"  Error: {best_angle['abs_angle_error']:.2f}°")
        
        if 'source_file' in best_angle:
            print(f"  Source: {best_angle['source_file']}")
        
        if 'actual_angle' in best_angle and pd.notna(best_angle['actual_angle']):
            print(f"  Actual: {best_angle['actual_angle']:.1f}°, Estimated: {best_angle['estimated_angle']:.1f}°")
    
    if 'abs_distance_error' in results_df.columns:
        print(f"\nDistance Estimation Performance:")
        print(f"- Mean error: {results_df['abs_distance_error'].mean():.2f}m")
        print(f"- Std deviation: {results_df['abs_distance_error'].std():.2f}m")
        print(f"- Range: {results_df['abs_distance_error'].min():.2f}m to {results_df['abs_distance_error'].max():.2f}m")
        
        # Best configuration for distance
        best_dist_idx = results_df['abs_distance_error'].idxmin()
        best_dist = results_df.loc[best_dist_idx]
        print(f"- Best configuration: Weight={best_dist['weight']:.1f}, {best_dist['sample_size']}, {best_dist['filter_state']}")
        print(f"  Error: {best_dist['abs_distance_error']:.2f}m")
        
        if 'source_file' in best_dist:
            print(f"  Source: {best_dist['source_file']}")
        
        if 'actual_distance' in best_dist and pd.notna(best_dist['actual_distance']):
            print(f"  Actual: {best_dist['actual_distance']:.1f}m, Estimated: {best_dist['estimated_distance']:.1f}m")
    
    # Configuration recommendations
    if 'abs_angle_error' in results_df.columns:
        print(f"\nConfiguration Analysis (Angle Error):")
        
        # By sample size
        if 'sample_size' in results_df.columns:
            sample_perf = results_df.groupby('sample_size')['abs_angle_error'].mean().sort_values()
            if not sample_perf.empty:
                print(f"- Best sample size: {sample_perf.index[0]} (avg error: {sample_perf.iloc[0]:.2f}°)")
        
        # By filter state
        if 'filter_state' in results_df.columns:
            filter_perf = results_df.groupby('filter_state')['abs_angle_error'].mean().sort_values()
            if not filter_perf.empty:
                print(f"- Best filter: {filter_perf.index[0]} (avg error: {filter_perf.iloc[0]:.2f}°)")
        
        # By weight
        weight_perf = results_df.groupby('weight')['abs_angle_error'].mean().sort_values()
        if not weight_perf.empty:
            print(f"- Best weight: {weight_perf.index[0]:.1f} (avg error: {weight_perf.iloc[0]:.2f}°)")
    
    print("\n" + "="*80)

def main():
    # Ask for CSV file path
    csv_path = input("Enter the path to your consolidated CSV file: ").strip().strip('"')
    
    if not Path(csv_path).exists():
        print(f"File not found: {csv_path}")
        
        # Look for CSV files in current directory
        csv_files = list(Path(".").glob("*.csv"))
        if csv_files:
            print("\nAvailable CSV files in current directory:")
            for i, f in enumerate(csv_files):
                print(f"{i+1}. {f.name}")
            
            choice = input("\nSelect file number (or press Enter to exit): ")
            if choice.isdigit():
                csv_path = csv_files[int(choice) - 1]
            else:
                return
        else:
            print("No CSV files found!")
            return
    
    # Analyze the data
    results_df, summary_df = analyze_consolidated_csv(csv_path)
    
    if results_df is not None:
        # Optional: Save a quick report
        report_file = Path("analysis_output") / "analysis_report.txt"
        with open(report_file, 'w') as f:
            f.write(f"Triangulation Analysis Report\n")
            f.write(f"Generated: {pd.Timestamp.now()}\n")
            f.write(f"Data source: {csv_path}\n")
            f.write(f"Total measurements: {len(results_df)}\n")
            
            if 'source_file' in results_df.columns:
                f.write(f"Unique files: {results_df['source_file'].nunique()}\n")
            
            if 'abs_angle_error' in results_df.columns:
                f.write(f"\nAngle Error Statistics:\n")
                f.write(f"  Mean: {results_df['abs_angle_error'].mean():.2f}°\n")
                f.write(f"  Std: {results_df['abs_angle_error'].std():.2f}°\n")
                f.write(f"  Min: {results_df['abs_angle_error'].min():.2f}°\n")
                f.write(f"  Max: {results_df['abs_angle_error'].max():.2f}°\n")
            
            if 'abs_distance_error' in results_df.columns:
                f.write(f"\nDistance Error Statistics:\n")
                f.write(f"  Mean: {results_df['abs_distance_error'].mean():.2f}m\n")
                f.write(f"  Std: {results_df['abs_distance_error'].std():.2f}m\n")
                f.write(f"  Min: {results_df['abs_distance_error'].min():.2f}m\n")
                f.write(f"  Max: {results_df['abs_distance_error'].max():.2f}m\n")
        
        print(f"\nAnalysis report saved to: {report_file}")
        
        # Show some sample data
        print(f"\nSample of the data (first 5 rows):")
        print(results_df[['weight', 'sample_size', 'filter_state', 'estimated_angle', 'angle_error']].head())

if __name__ == "__main__":
    main()