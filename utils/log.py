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

    def __init__(self, fmt=None, datefmt=None, style='%', validate=True, use_colors=True):
        super().__init__(fmt=fmt, datefmt=datefmt, style=style, validate=validate)
        self.use_colors = use_colors

    def format(self, record):
        asctime = self.formatTime(record, self.datefmt)
        levelname = self.LEVEL_MAP.get(record.levelname, record.levelname[:4])
        
        if self.use_colors:
            color = self.COLORS.get(record.levelno, self.RESET)
            colored_levelname = f"{color}{levelname}{self.RESET}"
            dim_asctime = f"{self.DIM}{asctime}{self.RESET}"
        else:
            colored_levelname = levelname
            dim_asctime = asctime
            
        logger_name = f" [{record.name}]" if record.name != "root" else ""
        message = f"{dim_asctime} [{colored_levelname}]{logger_name} {record.getMessage()}"
        
        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            message = f"{message.rstrip()}\n{record.exc_text}"
            
        if record.stack_info:
            message = f"{message.rstrip()}\n{self.formatStack(record.stack_info)}"
            
        return message

def setup_logging():
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    use_colors = sys.stdout.isatty()
    handler = logging.StreamHandler(sys.stdout)
    formatter = ColoredFormatter(datefmt="%Y-%m-%d %H:%M:%S", use_colors=use_colors)
    handler.setFormatter(formatter)
    
    root_logger.addHandler(handler)
