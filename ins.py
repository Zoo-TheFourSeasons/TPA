# from multiprocessing.dummy import Queue
from multiprocessing import Queue

ins_xls_cache = {}

# que for multiprocess
ins_que = Queue()

# bps for start app
ins_bps = None

ins_tokens = {}

# websocket background tasks
ins_tasks = {}
