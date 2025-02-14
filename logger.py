import logging
import sys

# Create a custom logger
logger = logging.getLogger("my_app_logger")
logger.setLevel(logging.DEBUG)

# Create handlers
console_handler = logging.StreamHandler(sys.stdout)
file_handler = logging.FileHandler("log.txt", mode="a", encoding="utf-8")

console_handler.setLevel(logging.DEBUG)
file_handler.setLevel(logging.DEBUG)

# Create a formatter
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

# Assign the formatter
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)
