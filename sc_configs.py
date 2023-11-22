# database
DB_HOST = 'localhost'
DB_NAME = 'appdb'
DB_USER = 'appuser'
DB_PORT = '3306'

# timeout
REQUEST_TIMEOUT = 16

# logging
LOGGING = True
LOGGING_QUEUE_MAX_SIZE = 4096

# health
HEALTH = True
HEALTH_ENDPOINT = True

# inspector
INSPECTOR = True
INSPECTOR_PORT = 9755
INSPECTOR_HOST = 'localhost'

# websocket
WEBSOCKET_MAX_SIZE = 2 ** 20
WEBSOCKET_PING_INTERVAL = 30
WEBSOCKET_PING_TIMEOUT = 30
