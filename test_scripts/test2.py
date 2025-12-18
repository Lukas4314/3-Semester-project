import logger
arr = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
arr2 = [11, 12, 13, 14, 15]

arr3 = arr + arr2
print(arr3)
logger.Logger.initialize(logger.Logger.get_all_logger_keys())
logger.Logger.write_row()
logger.Logger.close()