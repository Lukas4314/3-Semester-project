import logger
import os
import csv
import datetime
from pathlib import Path
from pc_code.sound_localization.Triangulate import triangulate_from_sound


def triangulate_on_all_rows():
    log_folder = Path("logs")
    output_folder = Path("triangulation_outputs")
    output_folder.mkdir(exist_ok=True)

    keys = logger.Logger.get_all_logger_keys()

    weights = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    filter_states = ["WITHOUT_FILTER", "WITH_FILTER"]
    sample_sizes = [8, 4, 2]

    for log_file in log_folder.glob("*.csv"):
        output_file = output_folder / f"triangulated_{log_file.stem}.csv"
        with open(log_file, 'r') as infile, open(output_file, 'w', newline='') as outfile:
            reader = csv.DictReader(infile)
            fieldnames = reader.fieldnames + ['x', 'y', 'z']
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()

            for row in reader:
                for weight in weights:
                    for filter_state in filter_states:
                        for sample_size in sample_sizes:
                            const_name = f"TDOA_PHAT_WEIGHT_{int(weight*10):02d}_{sample_size}_SAMPLES_{filter_state}"
                            if const_name in keys:
                                tdoa_data = row[const_name]
                                if tdoa_data:
                                    tdoa_values = list(map(float, tdoa_data.split(';')))
                                    if len(tdoa_values) == 3:
                                        mic1_data = [tdoa_values[0]]
                                        mic2_data = [tdoa_values[1]]
                                        mic3_data = [tdoa_values[2]]
                                        best_point, best_score = triangulate_from_sound(mic1_data, mic2_data, mic3_data)
                                        row.update({'x': best_point[0], 'y': best_point[1], 'z': best_point[2]})
                                        writer.writerow(row)
                                    else:
                                        print(f"Invalid TDOA data length in row: {row}")
                            else:
                                print(f"Constant {const_name} not found in logger keys.")
        writer.close()

if __name__ == "__main__":
    triangulate_on_all_rows()

                    