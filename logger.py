import os
import csv
import datetime
from pathlib import Path




# --------------------------------------------------------------
#  Logger implementation
# --------------------------------------------------------------
ACTION = "Action"

ATTEMPTS_AT_TALKING_BEFORE_REGISTERING = "AttemptsAtTalkingBeforeRegistering"

# For basic movement logging
DISTANCE_MOVED = "DistanceMoved"
DISTANCE_THOUGHT_IT_MOVED = "DistanceThoughtItMoved"
ANGLE_ROTATED = "AngleRotated"
ANGLE_THOUGHT_IT_ROTATED = "AngleThoughtItRotated"


# For triangulation logging
TDOA_PHAT_WEIGHT_10_2K_SAMPLES_WITH_FILTER = "TDOAPhatWeighting1.0_2k_samples_With_Filter"
TDOA_PHAT_WEIGHT_09_2K_SAMPLES_WITH_FILTER = "TDOAPhatWeighting0.9_2k_samples_With_Filter"
TDOA_PHAT_WEIGHT_08_2K_SAMPLES_WITH_FILTER = "TDOAPhatWeighting0.8_2k_samples_With_Filter"
TDOA_PHAT_WEIGHT_07_2K_SAMPLES_WITH_FILTER = "TDOAPhatWeighting0.7_2k_samples_With_Filter"
TDOA_PHAT_WEIGHT_06_2K_SAMPLES_WITH_FILTER = "TDOAPhatWeighting0.6_2k_samples_With_Filter"
TDOA_PHAT_WEIGHT_05_2K_SAMPLES_WITH_FILTER = "TDOAPhatWeighting0.5_2k_samples_With_Filter"
TDOA_PHAT_WEIGHT_04_2K_SAMPLES_WITH_FILTER = "TDOAPhatWeighting0.4_2k_samples_With_Filter"
TDOA_PHAT_WEIGHT_03_2K_SAMPLES_WITH_FILTER = "TDOAPhatWeighting0.3_2k_samples_With_Filter"
TDOA_PHAT_WEIGHT_02_2K_SAMPLES_WITH_FILTER = "TDOAPhatWeighting0.2_2k_samples_With_Filter"
TDOA_PHAT_WEIGHT_01_2K_SAMPLES_WITH_FILTER = "TDOAPhatWeighting0.1_2k_samples_With_Filter"
TDOA_PHAT_WEIGHT_00_2K_SAMPLES_WITH_FILTER = "TDOAPhatWeighting0.0_2k_samples_With_Filter"
TDOA_PHAT_WEIGHT_10_2K_SAMPLES_WITHOUT_FILTER = "TDOAPhatWeighting1.0_2k_samples_Without_Filter"
TDOA_PHAT_WEIGHT_09_2K_SAMPLES_WITHOUT_FILTER = "TDOAPhatWeighting0.9_2k_samples_Without_Filter"
TDOA_PHAT_WEIGHT_08_2K_SAMPLES_WITHOUT_FILTER = "TDOAPhatWeighting0.8_2k_samples_Without_Filter"
TDOA_PHAT_WEIGHT_07_2K_SAMPLES_WITHOUT_FILTER = "TDOAPhatWeighting0.7_2k_samples_Without_Filter"
TDOA_PHAT_WEIGHT_06_2K_SAMPLES_WITHOUT_FILTER = "TDOAPhatWeighting0.6_2k_samples_Without_Filter"
TDOA_PHAT_WEIGHT_05_2K_SAMPLES_WITHOUT_FILTER = "TDOAPhatWeighting0.5_2k_samples_Without_Filter"
TDOA_PHAT_WEIGHT_04_2K_SAMPLES_WITHOUT_FILTER = "TDOAPhatWeighting0.4_2k_samples_Without_Filter"
TDOA_PHAT_WEIGHT_03_2K_SAMPLES_WITHOUT_FILTER = "TDOAPhatWeighting0.3_2k_samples_Without_Filter"
TDOA_PHAT_WEIGHT_02_2K_SAMPLES_WITHOUT_FILTER = "TDOAPhatWeighting0.2_2k_samples_Without_Filter"
TDOA_PHAT_WEIGHT_01_2K_SAMPLES_WITHOUT_FILTER = "TDOAPhatWeighting0.1_2k_samples_Without_Filter"
TDOA_PHAT_WEIGHT_00_2K_SAMPLES_WITHOUT_FILTER = "TDOAPhatWeighting0.0_2k_samples_Without_Filter"


TDOA_PHAT_WEIGHT_10_4K_SAMPLES_WITH_FILTER = "TDOAPhatWeighting1.0_4k_samples_With_Filter"
TDOA_PHAT_WEIGHT_09_4K_SAMPLES_WITH_FILTER = "TDOAPhatWeighting0.9_4k_samples_With_Filter"
TDOA_PHAT_WEIGHT_08_4K_SAMPLES_WITH_FILTER = "TDOAPhatWeighting0.8_4k_samples_With_Filter"
TDOA_PHAT_WEIGHT_07_4K_SAMPLES_WITH_FILTER = "TDOAPhatWeighting0.7_4k_samples_With_Filter"
TDOA_PHAT_WEIGHT_06_4K_SAMPLES_WITH_FILTER = "TDOAPhatWeighting0.6_4k_samples_With_Filter"
TDOA_PHAT_WEIGHT_05_4K_SAMPLES_WITH_FILTER = "TDOAPhatWeighting0.5_4k_samples_With_Filter"
TDOA_PHAT_WEIGHT_04_4K_SAMPLES_WITH_FILTER = "TDOAPhatWeighting0.4_4k_samples_With_Filter"
TDOA_PHAT_WEIGHT_03_4K_SAMPLES_WITH_FILTER = "TDOAPhatWeighting0.3_4k_samples_With_Filter"
TDOA_PHAT_WEIGHT_02_4K_SAMPLES_WITH_FILTER = "TDOAPhatWeighting0.2_4k_samples_With_Filter"
TDOA_PHAT_WEIGHT_01_4K_SAMPLES_WITH_FILTER = "TDOAPhatWeighting0.1_4k_samples_With_Filter"
TDOA_PHAT_WEIGHT_00_4K_SAMPLES_WITH_FILTER = "TDOAPhatWeighting0.0_4k_samples_With_Filter"
TDOA_PHAT_WEIGHT_10_4K_SAMPLES_WITHOUT_FILTER = "TDOAPhatWeighting1.0_4k_samples_Without_Filter"
TDOA_PHAT_WEIGHT_09_4K_SAMPLES_WITHOUT_FILTER = "TDOAPhatWeighting0.9_4k_samples_Without_Filter"
TDOA_PHAT_WEIGHT_08_4K_SAMPLES_WITHOUT_FILTER = "TDOAPhatWeighting0.8_4k_samples_Without_Filter"
TDOA_PHAT_WEIGHT_07_4K_SAMPLES_WITHOUT_FILTER = "TDOAPhatWeighting0.7_4k_samples_Without_Filter"
TDOA_PHAT_WEIGHT_06_4K_SAMPLES_WITHOUT_FILTER = "TDOAPhatWeighting0.6_4k_samples_Without_Filter"
TDOA_PHAT_WEIGHT_05_4K_SAMPLES_WITHOUT_FILTER = "TDOAPhatWeighting0.5_4k_samples_Without_Filter"
TDOA_PHAT_WEIGHT_04_4K_SAMPLES_WITHOUT_FILTER = "TDOAPhatWeighting0.4_4k_samples_Without_Filter"
TDOA_PHAT_WEIGHT_03_4K_SAMPLES_WITHOUT_FILTER = "TDOAPhatWeighting0.3_4k_samples_Without_Filter"
TDOA_PHAT_WEIGHT_02_4K_SAMPLES_WITHOUT_FILTER = "TDOAPhatWeighting0.2_4k_samples_Without_Filter"
TDOA_PHAT_WEIGHT_01_4K_SAMPLES_WITHOUT_FILTER = "TDOAPhatWeighting0.1_4k_samples_Without_Filter"
TDOA_PHAT_WEIGHT_00_4K_SAMPLES_WITHOUT_FILTER = "TDOAPhatWeighting0.0_4k_samples_Without_Filter"

TDOA_PHAT_WEIGHT_10_8K_SAMPLES_WITH_FILTER = "TDOAPhatWeighting1.0_8k_samples_With_Filter"
TDOA_PHAT_WEIGHT_09_8K_SAMPLES_WITH_FILTER = "TDOAPhatWeighting0.9_8k_samples_With_Filter"
TDOA_PHAT_WEIGHT_08_8K_SAMPLES_WITH_FILTER = "TDOAPhatWeighting0.8_8k_samples_With_Filter"
TDOA_PHAT_WEIGHT_07_8K_SAMPLES_WITH_FILTER = "TDOAPhatWeighting0.7_8k_samples_With_Filter"
TDOA_PHAT_WEIGHT_06_8K_SAMPLES_WITH_FILTER = "TDOAPhatWeighting0.6_8k_samples_With_Filter"
TDOA_PHAT_WEIGHT_05_8K_SAMPLES_WITH_FILTER = "TDOAPhatWeighting0.5_8k_samples_With_Filter"
TDOA_PHAT_WEIGHT_04_8K_SAMPLES_WITH_FILTER = "TDOAPhatWeighting0.4_8k_samples_With_Filter"
TDOA_PHAT_WEIGHT_03_8K_SAMPLES_WITH_FILTER = "TDOAPhatWeighting0.3_8k_samples_With_Filter"
TDOA_PHAT_WEIGHT_02_8K_SAMPLES_WITH_FILTER = "TDOAPhatWeighting0.2_8k_samples_With_Filter"
TDOA_PHAT_WEIGHT_01_8K_SAMPLES_WITH_FILTER = "TDOAPhatWeighting0.1_8k_samples_With_Filter"
TDOA_PHAT_WEIGHT_00_8K_SAMPLES_WITH_FILTER = "TDOAPhatWeighting0.0_8k_samples_With_Filter"
TDOA_PHAT_WEIGHT_10_8K_SAMPLES_WITHOUT_FILTER = "TDOAPhatWeighting1.0_8k_samples_Without_Filter"
TDOA_PHAT_WEIGHT_09_8K_SAMPLES_WITHOUT_FILTER = "TDOAPhatWeighting0.9_8k_samples_Without_Filter"
TDOA_PHAT_WEIGHT_08_8K_SAMPLES_WITHOUT_FILTER = "TDOAPhatWeighting0.8_8k_samples_Without_Filter"
TDOA_PHAT_WEIGHT_07_8K_SAMPLES_WITHOUT_FILTER = "TDOAPhatWeighting0.7_8k_samples_Without_Filter"
TDOA_PHAT_WEIGHT_06_8K_SAMPLES_WITHOUT_FILTER = "TDOAPhatWeighting0.6_8k_samples_Without_Filter"
TDOA_PHAT_WEIGHT_05_8K_SAMPLES_WITHOUT_FILTER = "TDOAPhatWeighting0.5_8k_samples_Without_Filter"
TDOA_PHAT_WEIGHT_04_8K_SAMPLES_WITHOUT_FILTER = "TDOAPhatWeighting0.4_8k_samples_Without_Filter"
TDOA_PHAT_WEIGHT_03_8K_SAMPLES_WITHOUT_FILTER = "TDOAPhatWeighting0.3_8k_samples_Without_Filter"
TDOA_PHAT_WEIGHT_02_8K_SAMPLES_WITHOUT_FILTER = "TDOAPhatWeighting0.2_8k_samples_Without_Filter"
TDOA_PHAT_WEIGHT_01_8K_SAMPLES_WITHOUT_FILTER = "TDOAPhatWeighting0.1_8k_samples_Without_Filter"
TDOA_PHAT_WEIGHT_00_8K_SAMPLES_WITHOUT_FILTER = "TDOAPhatWeighting0.0_8k_samples_Without_Filter"




ACTUAL_TRIANGULATION_ANGLE = "ActualTriangulationAngle"
ACTUAL_TRIANGULATION_DISTANCE = "ActualTriangulationDistance"





class Logger:
    log_file = None
    file_name = None
    buffer = []
    headers = []
    header_index_map = {}
    
    
    current_samples_size = -1
    mic_pair = 1


    log_dir = Path("Logs")

    @staticmethod
    def current_date_time_for_file():
        return datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    @staticmethod
    def generate_unique_file_name():
        base_name = f"log_{Logger.current_date_time_for_file()}"
        Logger.log_dir.mkdir(exist_ok=True)

        counter = 0
        while True:
            if counter == 0:
                fname = Logger.log_dir / f"{base_name}.csv"
            else:
                fname = Logger.log_dir / f"{base_name}_{counter}.csv"

            if not fname.exists():
                return fname

            counter += 1

    @staticmethod
    def escape_csv(value: str) -> str:
        return value.replace('"', '""')

    @staticmethod
    def initialize(header_names):
        Logger.file_name = Logger.generate_unique_file_name()

        Logger.log_file = open(Logger.file_name, "w", newline="", encoding="utf-8")
        Logger.headers = list(header_names)
        Logger.header_index_map = {name: i for i, name in enumerate(Logger.headers)}
        Logger.buffer = [""] * len(Logger.headers)

        Logger.write_headers()
        Logger.set_standard_values()

        print(f"Logger initialized: {Logger.file_name}")

    @staticmethod
    def write_headers():
        writer = csv.writer(Logger.log_file)
        writer.writerow(Logger.headers)

    @staticmethod
    def set_value(header_name, value):
        if header_name not in Logger.header_index_map:
            print(f"Unknown header: {header_name}")
            return
        Logger.buffer[Logger.header_index_map[header_name]] = value

    @staticmethod
    def write_row():
        writer = csv.writer(Logger.log_file, quoting=csv.QUOTE_ALL)
        writer.writerow(Logger.buffer)

        # Reset buffer
        Logger.buffer = [""] * len(Logger.headers)

        # Reapply default values
        Logger.set_standard_values()

    @staticmethod
    def set_standard_values():
        defaults = {
            
            ACTION : "None",
            ATTEMPTS_AT_TALKING_BEFORE_REGISTERING : "None",
            # For basic movement logging
            DISTANCE_MOVED : "None",
            DISTANCE_THOUGHT_IT_MOVED : "None",
            ANGLE_ROTATED : "None",
            ANGLE_THOUGHT_IT_ROTATED : "None",

            # For triangulation logging
            TDOA_PHAT_WEIGHT_10_2K_SAMPLES_WITH_FILTER : "None",
            TDOA_PHAT_WEIGHT_09_2K_SAMPLES_WITH_FILTER : "None",
            TDOA_PHAT_WEIGHT_08_2K_SAMPLES_WITH_FILTER : "None",
            TDOA_PHAT_WEIGHT_07_2K_SAMPLES_WITH_FILTER : "None",
            TDOA_PHAT_WEIGHT_06_2K_SAMPLES_WITH_FILTER : "None",
            TDOA_PHAT_WEIGHT_05_2K_SAMPLES_WITH_FILTER : "None",
            TDOA_PHAT_WEIGHT_04_2K_SAMPLES_WITH_FILTER : "None",
            TDOA_PHAT_WEIGHT_03_2K_SAMPLES_WITH_FILTER : "None",
            TDOA_PHAT_WEIGHT_02_2K_SAMPLES_WITH_FILTER : "None",
            TDOA_PHAT_WEIGHT_01_2K_SAMPLES_WITH_FILTER : "None",
            TDOA_PHAT_WEIGHT_00_2K_SAMPLES_WITH_FILTER : "None",
            TDOA_PHAT_WEIGHT_10_2K_SAMPLES_WITHOUT_FILTER : "None",
            TDOA_PHAT_WEIGHT_09_2K_SAMPLES_WITHOUT_FILTER : "None",
            TDOA_PHAT_WEIGHT_08_2K_SAMPLES_WITHOUT_FILTER : "None",
            TDOA_PHAT_WEIGHT_07_2K_SAMPLES_WITHOUT_FILTER : "None",
            TDOA_PHAT_WEIGHT_06_2K_SAMPLES_WITHOUT_FILTER : "None",
            TDOA_PHAT_WEIGHT_05_2K_SAMPLES_WITHOUT_FILTER : "None",
            TDOA_PHAT_WEIGHT_04_2K_SAMPLES_WITHOUT_FILTER : "None",
            TDOA_PHAT_WEIGHT_03_2K_SAMPLES_WITHOUT_FILTER : "None",
            TDOA_PHAT_WEIGHT_02_2K_SAMPLES_WITHOUT_FILTER : "None",
            TDOA_PHAT_WEIGHT_01_2K_SAMPLES_WITHOUT_FILTER : "None",
            TDOA_PHAT_WEIGHT_00_2K_SAMPLES_WITHOUT_FILTER : "None",


            TDOA_PHAT_WEIGHT_10_4K_SAMPLES_WITH_FILTER : "None",
            TDOA_PHAT_WEIGHT_09_4K_SAMPLES_WITH_FILTER : "None",
            TDOA_PHAT_WEIGHT_08_4K_SAMPLES_WITH_FILTER : "None",
            TDOA_PHAT_WEIGHT_07_4K_SAMPLES_WITH_FILTER : "None",
            TDOA_PHAT_WEIGHT_06_4K_SAMPLES_WITH_FILTER : "None",
            TDOA_PHAT_WEIGHT_05_4K_SAMPLES_WITH_FILTER : "None",
            TDOA_PHAT_WEIGHT_04_4K_SAMPLES_WITH_FILTER : "None",
            TDOA_PHAT_WEIGHT_03_4K_SAMPLES_WITH_FILTER : "None",
            TDOA_PHAT_WEIGHT_02_4K_SAMPLES_WITH_FILTER : "None",
            TDOA_PHAT_WEIGHT_01_4K_SAMPLES_WITH_FILTER : "None",
            TDOA_PHAT_WEIGHT_00_4K_SAMPLES_WITH_FILTER : "None",
            TDOA_PHAT_WEIGHT_10_4K_SAMPLES_WITHOUT_FILTER : "None",
            TDOA_PHAT_WEIGHT_09_4K_SAMPLES_WITHOUT_FILTER : "None",
            TDOA_PHAT_WEIGHT_08_4K_SAMPLES_WITHOUT_FILTER : "None",
            TDOA_PHAT_WEIGHT_07_4K_SAMPLES_WITHOUT_FILTER : "None",
            TDOA_PHAT_WEIGHT_06_4K_SAMPLES_WITHOUT_FILTER : "None",
            TDOA_PHAT_WEIGHT_05_4K_SAMPLES_WITHOUT_FILTER : "None",
            TDOA_PHAT_WEIGHT_04_4K_SAMPLES_WITHOUT_FILTER : "None",
            TDOA_PHAT_WEIGHT_03_4K_SAMPLES_WITHOUT_FILTER : "None",
            TDOA_PHAT_WEIGHT_02_4K_SAMPLES_WITHOUT_FILTER : "None",
            TDOA_PHAT_WEIGHT_01_4K_SAMPLES_WITHOUT_FILTER : "None",
            TDOA_PHAT_WEIGHT_00_4K_SAMPLES_WITHOUT_FILTER : "None",



            TDOA_PHAT_WEIGHT_10_8K_SAMPLES_WITH_FILTER : "None",
            TDOA_PHAT_WEIGHT_09_8K_SAMPLES_WITH_FILTER : "None",
            TDOA_PHAT_WEIGHT_08_8K_SAMPLES_WITH_FILTER : "None",
            TDOA_PHAT_WEIGHT_07_8K_SAMPLES_WITH_FILTER : "None",
            TDOA_PHAT_WEIGHT_06_8K_SAMPLES_WITH_FILTER : "None",
            TDOA_PHAT_WEIGHT_05_8K_SAMPLES_WITH_FILTER : "None",
            TDOA_PHAT_WEIGHT_04_8K_SAMPLES_WITH_FILTER : "None",
            TDOA_PHAT_WEIGHT_03_8K_SAMPLES_WITH_FILTER : "None",
            TDOA_PHAT_WEIGHT_02_8K_SAMPLES_WITH_FILTER : "None",
            TDOA_PHAT_WEIGHT_01_8K_SAMPLES_WITH_FILTER : "None",
            TDOA_PHAT_WEIGHT_00_8K_SAMPLES_WITH_FILTER : "None",
            TDOA_PHAT_WEIGHT_10_8K_SAMPLES_WITHOUT_FILTER : "None",
            TDOA_PHAT_WEIGHT_09_8K_SAMPLES_WITHOUT_FILTER : "None",
            TDOA_PHAT_WEIGHT_08_8K_SAMPLES_WITHOUT_FILTER : "None",
            TDOA_PHAT_WEIGHT_07_8K_SAMPLES_WITHOUT_FILTER : "None",
            TDOA_PHAT_WEIGHT_06_8K_SAMPLES_WITHOUT_FILTER : "None",
            TDOA_PHAT_WEIGHT_05_8K_SAMPLES_WITHOUT_FILTER : "None",
            TDOA_PHAT_WEIGHT_04_8K_SAMPLES_WITHOUT_FILTER : "None",
            TDOA_PHAT_WEIGHT_03_8K_SAMPLES_WITHOUT_FILTER : "None",
            TDOA_PHAT_WEIGHT_02_8K_SAMPLES_WITHOUT_FILTER : "None",
            TDOA_PHAT_WEIGHT_01_8K_SAMPLES_WITHOUT_FILTER : "None",
            TDOA_PHAT_WEIGHT_00_8K_SAMPLES_WITHOUT_FILTER : "None",


            ACTUAL_TRIANGULATION_ANGLE : "None",
            ACTUAL_TRIANGULATION_DISTANCE : "None"
            }

        for key, value in defaults.items():
            if key in Logger.header_index_map:
                Logger.set_value(key, value)

    @staticmethod
    def get_all_logger_keys():
        """Exactly matches C++ getAllLoggerKeys()"""
        return [
            ACTION,

            ATTEMPTS_AT_TALKING_BEFORE_REGISTERING,

            # For basic movement logging
            DISTANCE_MOVED,
            DISTANCE_THOUGHT_IT_MOVED,
            ANGLE_ROTATED,
            ANGLE_THOUGHT_IT_ROTATED,


            # For triangulation logging
            TDOA_PHAT_WEIGHT_10_2K_SAMPLES_WITH_FILTER,
            TDOA_PHAT_WEIGHT_09_2K_SAMPLES_WITH_FILTER,
            TDOA_PHAT_WEIGHT_08_2K_SAMPLES_WITH_FILTER,
            TDOA_PHAT_WEIGHT_07_2K_SAMPLES_WITH_FILTER,
            TDOA_PHAT_WEIGHT_06_2K_SAMPLES_WITH_FILTER,
            TDOA_PHAT_WEIGHT_05_2K_SAMPLES_WITH_FILTER,
            TDOA_PHAT_WEIGHT_04_2K_SAMPLES_WITH_FILTER,
            TDOA_PHAT_WEIGHT_03_2K_SAMPLES_WITH_FILTER,
            TDOA_PHAT_WEIGHT_02_2K_SAMPLES_WITH_FILTER,
            TDOA_PHAT_WEIGHT_01_2K_SAMPLES_WITH_FILTER,
            TDOA_PHAT_WEIGHT_00_2K_SAMPLES_WITH_FILTER,
            TDOA_PHAT_WEIGHT_10_2K_SAMPLES_WITHOUT_FILTER,
            TDOA_PHAT_WEIGHT_09_2K_SAMPLES_WITHOUT_FILTER,
            TDOA_PHAT_WEIGHT_08_2K_SAMPLES_WITHOUT_FILTER,
            TDOA_PHAT_WEIGHT_07_2K_SAMPLES_WITHOUT_FILTER,
            TDOA_PHAT_WEIGHT_06_2K_SAMPLES_WITHOUT_FILTER,
            TDOA_PHAT_WEIGHT_05_2K_SAMPLES_WITHOUT_FILTER,
            TDOA_PHAT_WEIGHT_04_2K_SAMPLES_WITHOUT_FILTER,
            TDOA_PHAT_WEIGHT_03_2K_SAMPLES_WITHOUT_FILTER,
            TDOA_PHAT_WEIGHT_02_2K_SAMPLES_WITHOUT_FILTER,
            TDOA_PHAT_WEIGHT_01_2K_SAMPLES_WITHOUT_FILTER,
            TDOA_PHAT_WEIGHT_00_2K_SAMPLES_WITHOUT_FILTER,
            
            
            TDOA_PHAT_WEIGHT_10_4K_SAMPLES_WITH_FILTER,
            TDOA_PHAT_WEIGHT_09_4K_SAMPLES_WITH_FILTER,
            TDOA_PHAT_WEIGHT_08_4K_SAMPLES_WITH_FILTER,
            TDOA_PHAT_WEIGHT_07_4K_SAMPLES_WITH_FILTER,
            TDOA_PHAT_WEIGHT_06_4K_SAMPLES_WITH_FILTER,
            TDOA_PHAT_WEIGHT_05_4K_SAMPLES_WITH_FILTER,
            TDOA_PHAT_WEIGHT_04_4K_SAMPLES_WITH_FILTER,
            TDOA_PHAT_WEIGHT_03_4K_SAMPLES_WITH_FILTER,
            TDOA_PHAT_WEIGHT_02_4K_SAMPLES_WITH_FILTER,
            TDOA_PHAT_WEIGHT_01_4K_SAMPLES_WITH_FILTER,
            TDOA_PHAT_WEIGHT_00_4K_SAMPLES_WITH_FILTER,
            TDOA_PHAT_WEIGHT_10_4K_SAMPLES_WITHOUT_FILTER,
            TDOA_PHAT_WEIGHT_09_4K_SAMPLES_WITHOUT_FILTER,
            TDOA_PHAT_WEIGHT_08_4K_SAMPLES_WITHOUT_FILTER,
            TDOA_PHAT_WEIGHT_07_4K_SAMPLES_WITHOUT_FILTER,
            TDOA_PHAT_WEIGHT_06_4K_SAMPLES_WITHOUT_FILTER,
            TDOA_PHAT_WEIGHT_05_4K_SAMPLES_WITHOUT_FILTER,
            TDOA_PHAT_WEIGHT_04_4K_SAMPLES_WITHOUT_FILTER,
            TDOA_PHAT_WEIGHT_03_4K_SAMPLES_WITHOUT_FILTER,
            TDOA_PHAT_WEIGHT_02_4K_SAMPLES_WITHOUT_FILTER,
            TDOA_PHAT_WEIGHT_01_4K_SAMPLES_WITHOUT_FILTER,
            TDOA_PHAT_WEIGHT_00_4K_SAMPLES_WITHOUT_FILTER,
            
            
            TDOA_PHAT_WEIGHT_10_8K_SAMPLES_WITH_FILTER,
            TDOA_PHAT_WEIGHT_09_8K_SAMPLES_WITH_FILTER,
            TDOA_PHAT_WEIGHT_08_8K_SAMPLES_WITH_FILTER,
            TDOA_PHAT_WEIGHT_07_8K_SAMPLES_WITH_FILTER,
            TDOA_PHAT_WEIGHT_06_8K_SAMPLES_WITH_FILTER,
            TDOA_PHAT_WEIGHT_05_8K_SAMPLES_WITH_FILTER,
            TDOA_PHAT_WEIGHT_04_8K_SAMPLES_WITH_FILTER,
            TDOA_PHAT_WEIGHT_03_8K_SAMPLES_WITH_FILTER,
            TDOA_PHAT_WEIGHT_02_8K_SAMPLES_WITH_FILTER,
            TDOA_PHAT_WEIGHT_01_8K_SAMPLES_WITH_FILTER,
            TDOA_PHAT_WEIGHT_00_8K_SAMPLES_WITH_FILTER,
            TDOA_PHAT_WEIGHT_10_8K_SAMPLES_WITHOUT_FILTER,
            TDOA_PHAT_WEIGHT_09_8K_SAMPLES_WITHOUT_FILTER,
            TDOA_PHAT_WEIGHT_08_8K_SAMPLES_WITHOUT_FILTER,
            TDOA_PHAT_WEIGHT_07_8K_SAMPLES_WITHOUT_FILTER,
            TDOA_PHAT_WEIGHT_06_8K_SAMPLES_WITHOUT_FILTER,
            TDOA_PHAT_WEIGHT_05_8K_SAMPLES_WITHOUT_FILTER,
            TDOA_PHAT_WEIGHT_04_8K_SAMPLES_WITHOUT_FILTER,
            TDOA_PHAT_WEIGHT_03_8K_SAMPLES_WITHOUT_FILTER,
            TDOA_PHAT_WEIGHT_02_8K_SAMPLES_WITHOUT_FILTER,
            TDOA_PHAT_WEIGHT_01_8K_SAMPLES_WITHOUT_FILTER,
            TDOA_PHAT_WEIGHT_00_8K_SAMPLES_WITHOUT_FILTER,
            


            ACTUAL_TRIANGULATION_ANGLE,
            ACTUAL_TRIANGULATION_DISTANCE
        ]

    @staticmethod
    def close():
        if Logger.log_file:
            Logger.log_file.close()
            Logger.log_file = None