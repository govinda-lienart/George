# ========================================
# 📋 ROLE OF THIS SCRIPT - logger.py
# ========================================

"""
Logger module for the George AI Hotel Receptionist app.
- Provides centralized logging system for application monitoring and debugging
- Implements in-memory logging for Streamlit UI display integration
- Manages log streams for both console output and web interface viewing
- Formats log messages with timestamps and severity levels
- Enables real-time log viewing through developer tools panel
- Essential monitoring component for system health and troubleshooting
- Supports both development debugging and production monitoring
"""

# ========================================
# 📜 LOGGER MODULE (STREAMLIT + IN-MEMORY LOGGING)
# ========================================

# ────────────────────────────────────────────────
# 🔧 PYTHON STANDARD LIBRARY IMPORTS
# ────────────────────────────────────────────────
import logging
import io

# ========================================
# 🧠 IN-MEMORY LOGGING SETUP (For Streamlit UI)
# ========================================
# ┌─────────────────────────────────────────┐
# │  CREATE STRINGIO STREAM FOR UI DISPLAY  │
# └─────────────────────────────────────────┘
log_stream = io.StringIO()

# ┌─────────────────────────────────────────┐
# │  SETUP STREAM HANDLER WITH FORMATTER    │
# └─────────────────────────────────────────┘
stream_handler = logging.StreamHandler(log_stream)
formatter = logging.Formatter('%(asctime)s — %(levelname)s — %(message)s')
stream_handler.setFormatter(formatter)

# ========================================
# 🧾 LOGGER CONFIGURATION
# ========================================
# ┌─────────────────────────────────────────┐
# │  INITIALIZE LOGGER INSTANCE             │
# └─────────────────────────────────────────┘
logger = logging.getLogger("assistant_logger")
logger.setLevel(logging.INFO)
logger.addHandler(stream_handler)

# ┌─────────────────────────────────────────┐
# │  OPTIONAL: ADD CONSOLE HANDLER          │
# └─────────────────────────────────────────┘
logger.addHandler(logging.StreamHandler())