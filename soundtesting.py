import csv
import numpy as np
import math
from pathlib import Path
from pc_code.sound_localization.Triangulate import microphone_placement, find_sound_origin

def triangulate_on_all_rows():
    log_folder = Path("Logs")
    output_folder = Path("triangulation_outputs")
    output_folder.mkdir(exist_ok=True)
    
    if not log_folder.exists():
        print(f"ERROR: Log folder '{log_folder}' not found!")
        return
    
    for log_file in log_folder.glob("*.csv"):
        print(f"Processing: {log_file.name}")
        output_file = output_folder / f"triangulated_{log_file.stem}.csv"
        
        try:
            with open(log_file, 'r') as infile, open(output_file, 'w', newline='') as outfile:
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
                
                # Create output with same headers
                writer = csv.DictWriter(outfile, fieldnames=reader.fieldnames)
                writer.writeheader()
                
                rows_processed = 0
                
                for row in reader:
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
                                    # Already in angle;distance format, skip
                                    continue
                            
                            try:
                                # Parse TDOA values (format: "15;-34;-73")
                                tdoa_values = list(map(float, tdoa_str.split(';')))
                                
                                if len(tdoa_values) == 3:
                                    # Triangulate to get (x, y) point
                                    best_point, best_score = find_sound_origin(microphone_placement(), tdoa_values)
                                    
                                    # Convert (x, y) to angle and distance
                                    angle_rad = float(np.arctan2(best_point[1], best_point[0]))
                                    angle_deg = angle_rad * 180.0 / math.pi
                                    distance_m = float(np.sqrt(best_point[0] ** 2 + best_point[1] ** 2))
                                    
                                    # Format: "angle_deg;distance_m"
                                    triangulated_value = f"{angle_deg:.2f};{distance_m:.2f}"
                                    
                                    # Update the SAME cell with angle/distance
                                    row[col_name] = triangulated_value
                                    
                                else:
                                    print(f"  Row {rows_processed+1}: Invalid TDOA data in {col_name}: {tdoa_str}")
                                    
                            except (ValueError, IndexError) as e:
                                print(f"  Row {rows_processed+1}: Error parsing {col_name} '{tdoa_str}': {e}")
                                continue
                    
                    # Write the updated row
                    writer.writerow(row)
                    rows_processed += 1
                    
                    # Progress indicator
                    if rows_processed % 10 == 0:
                        print(f"  Processed {rows_processed} rows...")
                
                print(f"  Done: {rows_processed} rows written to {output_file.name}")
                
        except Exception as e:
            print(f"  ERROR processing {log_file.name}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    triangulate_on_all_rows()