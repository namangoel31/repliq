# import logging

# def get_logger():
    # logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    # logger = logging.getLogger('uvicorn')
    # console_handler = logging.StreamHandler()
    # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(path)s - %(message)s')
    # console_handler.setFormatter(formatter)
    # logger.addHandler(console_handler)
    # logger.setLevel(logging.INFO)
    # return logger
import logging

def get_console_logger(name="repliq"):
    logger = logging.getLogger(name)
    if not logger.hasHandlers():  # avoid adding multiple handlers
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname) - %(name)s - %(path)ss - %(message)s'
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        logger.setLevel(logging.INFO)
    return logger

# logger = get_logger("repliq")

def get_file_logger(name="repliq", log_file="app.log"):
    logger = logging.getLogger(name)
    
    if not logger.hasHandlers():
        logger.propagate = False
        file_handler = logging.FileHandler(log_file)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(name)s - %(path)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        logger.setLevel(logging.INFO)
    
    return logger

# import logging
# # Create a custom logger
# logger = logging.getLogger(__name__)
# # Create handlers
# console_handler = logging.StreamHandler()
# # Create formatters and add them to handlers
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# console_handler.setFormatter(formatter)
# # Add handlers to the logger
# logger.addHandler(console_handler)
# # Set the logging level
# logger.setLevel(logging.INFO)
# # Log messages
# logger.info("This is an info message")
# logger.warning("This is a warning message")