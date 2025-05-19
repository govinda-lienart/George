# logger.py
import logging
import io

# In-memory stream for UI display/download
log_stream = io.StringIO()

# Stream handler to write to memory
stream_handler = logging.StreamHandler(log_stream)
formatter = logging.Formatter('%(asctime)s — %(levelname)s — %(message)s')
stream_handler.setFormatter(formatter)

# Logger config
logger = logging.getLogger("assistant_logger")
logger.setLevel(logging.INFO)
logger.addHandler(stream_handler)

# Optional: also log to console (shows in Streamlit Cloud logs)
logger.addHandler(logging.StreamHandler())
