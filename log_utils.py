import logging
import sys

class ColoredFormatter(logging.Formatter):
    RESET = "\033[0m"
    DIM = "\033[2m"
    
    COLORS = {
        logging.DEBUG: "\033[36m",     # Cyan
        logging.INFO: "\033[32m",      # Green
        logging.WARNING: "\033[33m",   # Yellow
        logging.ERROR: "\033[31m",     # Red
        logging.CRITICAL: "\033[1;31m" # Bold Red
    }

    LEVEL_MAP = {
        "DEBUG": "DBUG",
        "INFO": "INFO",
        "WARNING": "WARN",
        "ERROR": "ERRO",
        "CRITICAL": "CRIT"
    }

    def format(self, record):
        asctime = self.formatTime(record, self.datefmt)
        levelname = self.LEVEL_MAP.get(record.levelname, record.levelname[:4])
        color = self.COLORS.get(record.levelno, self.RESET)
        colored_levelname = f"{color}{levelname}{self.RESET}"
        logger_name = f" [{record.name}]" if record.name != "root" else ""
        return f"{self.DIM}{asctime}{self.RESET} [{colored_levelname}]{logger_name} {record.getMessage()}"

def setup_logging():
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    handler = logging.StreamHandler(sys.stdout)
    formatter = ColoredFormatter(datefmt="%Y-%m-%d %H:%M:%S")
    handler.setFormatter(formatter)
    
    root_logger.addHandler(handler)
