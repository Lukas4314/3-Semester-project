import csv
import numpy as np
import math
from pathlib import Path
from pc_code.sound_localization.Triangulate import microphone_placement, find_sound_origin

def triangulate_on_all_rows():
    log_folder = Path("Logs")
    output_folder = Path("triangulation_outputs")
    output_folder.mkdir(exist_ok=True)
    known_angles = []
    if not log_folder.exists():
        print(f"ERROR: Log folder '{log_folder}' not found!")
        return
    
    # Create a single master CSV file for all results
    master_output_file = output_folder / "all_triangulated_angles.csv"
    
    # Prepare master CSV
    master_fieldnames_written = False
    master_rows = []
    
    for log_file in log_folder.glob("*.csv"):
        print(f"Processing: {log_file.name}")
        
        try:
            with open(log_file, 'r') as infile:
                reader = csv.DictReader(infile)
                
                if reader.fieldnames is None:
                    print(f"  Warning: {log_file.name} is empty")
                    continue
                
                # Get all TDOA columns from the actual CSV headers
                tdoa_columns = [col for col in reader.fieldnames if col.startswith("TDOAPhatWeighting")]
                print(f"  Found {len(tdoa_columns)} TDOA columns in CSV")
                
                if not tdoa_columns:
                    print(f"  No TDOA columns found in {log_file.name}")
                    continue
                
                rows_processed = 0
                
                for row in reader:
                    # Extract metadata (action, etc.)
                    metadata = {
                        'source_file': log_file.name,
                        'row_index': rows_processed + 1,
                        'action': row.get('Action', ''),
                        'attempts': row.get('AttemptsAtTalkingBeforeRegistering', ''),
                        'distance_moved': row.get('DistanceMoved', ''),
                        'distance_thought': row.get('DistanceThoughtItMoved', ''),
                        'angle_rotated': row.get('AngleRotated', ''),
                        'angle_thought': row.get('AngleThoughtItRotated', ''),
                        'actual_angle': row.get('ActualTriangulationAngle', ''),
                        'actual_distance': row.get('ActualTriangulationDistance', '')
                    }
                    if metadata['action'].lower() != 'come':
                        # Skip rows where action is not "Come"
                        rows_processed += 1
                        continue
                    
                    # Process ALL TDOA columns in this row
                    for col_name in tdoa_columns:
                        if col_name in row and row[col_name]:
                            tdoa_str = row[col_name]
                            
                            # Skip if "None" or empty
                            if tdoa_str.lower() == "none" or not tdoa_str.strip():
                                continue
                            
                            # Check if already triangulated (contains ';' but not TDOA format)
                            # If it's already in angle;distance format, skip
                            if ";" in tdoa_str:
                                parts = tdoa_str.split(';')
                                if len(parts) == 2:
                                    # Already in angle;distance format, use it
                                    try:
                                        angle_deg, distance_m = map(float, parts)
                                        triangulated_value = f"{angle_deg:.2f};{distance_m:.2f}"
                                    except ValueError:
                                        continue
                                else:
                                    # Need to triangulate
                                    try:
                                        # Parse TDOA values (format: "15;-34;-73")
                                        tdoa_values = list(map(float, tdoa_str.split(';')))
                                        
                                        if len(tdoa_values) == 3:
                                            # Triangulate to get (x, y) point
                                            if (tdoa_values, known_angles):
                                                for known_point, known_tdoa in known_angles:
                                                    if np.allclose(tdoa_values, known_tdoa, atol=1e-2):
                                                        best_point = known_point
                                                        break
                                                else:
                                                    best_point, _ = find_sound_origin(microphone_placement(), tdoa_values)
                                            else:
                                                best_point, _ = find_sound_origin(microphone_placement(), tdoa_values)
                                            
                                            known_angles.append((best_point, tdoa_values))
                                            # Convert (x, y) to angle and distance
                                            angle_rad = float(np.arctan2(best_point[1], best_point[0]))
                                            angle_deg = angle_rad * 180.0 / math.pi
                                            distance_m = float(np.sqrt(best_point[0] ** 2 + best_point[1] ** 2))
                                            
                                            # Format: "angle_deg;distance_m"
                                            triangulated_value = f"{angle_deg:.2f};{distance_m:.2f}"
                                        else:
                                            print(f"  Row {rows_processed+1}: Invalid TDOA data in {col_name}: {tdoa_str}")
                                            continue
                                            
                                    except (ValueError, IndexError) as e:
                                        print(f"  Row {rows_processed+1}: Error parsing {col_name} '{tdoa_str}': {e}")
                                        continue
                            
                            # Parse column name to extract parameters
                            # Format: TDOAPhatWeighting0.8_8k_samples_With_Filter
                            parts = col_name.split('_')
                            
                            if len(parts) >= 4:
                                weight_str = parts[0].replace('TDOAPhatWeighting', '')
                                sample_size = parts[1]  # 2k, 4k, 8k
                                filter_state = '_'.join(parts[2:])  # With_Filter or Without_Filter
                                
                                try:
                                    weight = float(weight_str)
                                except ValueError:
                                    weight = 0.0
                                
                                # Parse angle and distance from triangulated_value
                                angle_str, dist_str = triangulated_value.split(';')
                                angle = float(angle_str)
                                distance = float(dist_str)
                                
                                # Create result entry for master CSV
                                result_entry = {
                                    **metadata,
                                    'weight': weight,
                                    'sample_size': sample_size,
                                    'filter_state': filter_state,
                                    'tdoa_column': col_name,
                                    'estimated_angle': angle,
                                    'estimated_distance': distance,
                                    'tdoa_values': tdoa_str if len(tdoa_str.split(';')) == 3 else 'N/A'
                                }
                                
                                # Add actual comparison if available
                                if metadata['actual_angle'] and metadata['actual_angle'].lower() != 'none':
                                    try:
                                        actual_angle = float(metadata['actual_angle'])
                                        
                                        angle_err = abs(angle - actual_angle)
                                        if angle_err > 180:
                                            angle_err = 360 - angle_err
                                        result_entry['angle_error'] = angle_err


                                        result_entry['signed_angle_error'] = angle - actual_angle
                                    except (ValueError, TypeError):
                                        pass
                                
                                if metadata['actual_distance'] and metadata['actual_distance'].lower() != 'none':
                                    try:
                                        actual_distance = float(metadata['actual_distance'])
                                        result_entry['distance_error'] = abs(distance - actual_distance)
                                        result_entry['signed_distance_error'] = distance - actual_distance
                                    except (ValueError, TypeError):
                                        pass
                                
                                master_rows.append(result_entry)
                    
                    rows_processed += 1
                    
                    # Progress indicator
                    if rows_processed % 10 == 0:
                        print(f"  Processed {rows_processed} rows...")
                
                print(f"  Done: {rows_processed} rows processed from {log_file.name}")
                
        except Exception as e:
            print(f"  ERROR processing {log_file.name}: {e}")
            import traceback
            traceback.print_exc()
    
    # Write all results to the single master CSV file
    if master_rows:
        # Define fieldnames for the master CSV
        master_fieldnames = [
            'source_file', 'row_index', 'action', 'attempts',
            'distance_moved', 'distance_thought', 'angle_rotated', 'angle_thought',
            'actual_angle', 'actual_distance',
            'weight', 'sample_size', 'filter_state', 'tdoa_column',
            'estimated_angle', 'estimated_distance',
            'angle_error', 'signed_angle_error',
            'distance_error', 'signed_distance_error',
            'tdoa_values'
        ]
        
        with open(master_output_file, 'w', newline='') as master_file:
            writer = csv.DictWriter(master_file, fieldnames=master_fieldnames)
            writer.writeheader()
            writer.writerows(master_rows)
        
        print(f"\nSUCCESS: Saved {len(master_rows)} triangulation results to {master_output_file}")
        
        # Print summary
        print("\nSummary:")
        print(f"- Total entries: {len(master_rows)}")
        
        # Group by configuration
        if master_rows:
            configs = set()
            for row in master_rows:
                configs.add(f"W={row['weight']}, {row['sample_size']}, {row['filter_state']}")
            
            print(f"- Unique configurations: {len(configs)}")
            print(f"- Sample configurations: {list(configs)[:5]}..." if len(configs) > 5 else f"- Configurations: {list(configs)}")
    else:
        print("No triangulation results were generated!")

if __name__ == "__main__":
    triangulate_on_all_rows()