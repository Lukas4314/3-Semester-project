from pc_code.transcriber import transcriber
import queue

class test:
    def __init__(self, queue):
        print("Test initialized with queue:")
"""
class transcriber:
	def __init__(self, queue):
		print("idk")
  """
  
queue_test = queue.Queue()
transcriber = transcriber(queue_test)
