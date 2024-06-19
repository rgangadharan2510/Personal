import logging
import os

# Logging setup
logger = logging.getLogger('logger')
logger.propagate = False
Log_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
logger.setLevel(Log_LEVEL)
ch = logging.StreamHandler()
ch.setLevel(Log_LEVEL)
formatter = logging.Formatter(fmt='%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
ch.setFormatter(formatter)
logger.addHandler(ch)


def get_logger():
    return logger
