import logging

def get_console_logger(name="repliq"):
    logger = logging.getLogger(name)
    if not logger.hasHandlers():
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname) - %(name)s - %(path)ss - %(message)s'
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        logger.setLevel(logging.INFO)
    return logger


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