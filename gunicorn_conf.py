import multiprocessing
import os

# The socket to bind
bind = "0.0.0.0:8000"

# Number of worker processes (often calculated based on CPU cores)
workers = multiprocessing.cpu_count() * 2 + 1

# Logging configuration
loglevel = os.getenv("LOG_LEVEL", "info")
accesslog = "-" # Log to stdout
errorlog = "-"  # Log to stderr

# Timeouts
timeout = 120 # Workers silent for more than this many seconds are killed and restarted
graceful_timeout = 120
keepalive = 5 # Seconds to wait for requests on a Keep-Alive connection

# WSGI application path
wsgi_app = "main:app"
