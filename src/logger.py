import logging
import sys
from logging.handlers import RotatingFileHandler


def setup_logger(verbose=False):
    logger = logging.getLogger("RepoDownloader")
    
    if not logger.handlers:
        level = logging.DEBUG if verbose else logging.INFO
        logger.setLevel(level)
        
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler = RotatingFileHandler(
            "app.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        if verbose:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            console_handler.setLevel(logging.DEBUG)
            logger.addHandler(console_handler)
    
    return logger


logger = setup_logger()
