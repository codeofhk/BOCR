import multiprocessing
import os

# Railway dynamically assigns a port, so we must use the PORT env var
bind = "0.0.0.0:" + os.getenv("PORT", "5001")

workers = multiprocessing.cpu_count() * 2 + 1

loglevel = os.getenv("LOG_LEVEL", "info")
accesslog = "-" 
errorlog = "-" 

timeout = 120 
graceful_timeout = 120
keepalive = 5 

# Set this to "app:app" if your file is app.py
wsgi_app = "app:app"