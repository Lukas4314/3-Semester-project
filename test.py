import numpy as np

buffer = np.zeros(0, dtype=np.float32)
buffer = np.append(buffer, np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float32))

samples_per_chunk = 2
print(buffer[:samples_per_chunk])
print(buffer[samples_per_chunk:])