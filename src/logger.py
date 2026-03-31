import logging

def setup_logger():
    logger = logging.getLogger("RepoDownloader")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        file_handler = logging.FileHandler("app.log", encoding="utf-8")
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    return logger

logger = setup_logger()
