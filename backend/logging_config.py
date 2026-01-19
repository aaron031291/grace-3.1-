import logging
import logging.handlers
from pathlib import Path

def setup_logging():
    """
    Configure logging to send verbose logs to file and only important logs to console.
    """
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture everything
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # File handler - captures EVERYTHING (DEBUG and above)
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "grace.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    
    # Console handler - only WARNING and above (errors, important stuff)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    
    # Add handlers to root logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Suppress noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("watchfiles").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    
    # Suppress verbose internal loggers
    logging.getLogger("ingestion").setLevel(logging.WARNING)
    logging.getLogger("auto_ingest").setLevel(logging.WARNING)
    logging.getLogger("continuous_learning").setLevel(logging.WARNING)
    logging.getLogger("genesis").setLevel(logging.WARNING)
    logging.getLogger("embedding").setLevel(logging.WARNING)  # Suppress embedding verbosity
    
    # Keep important loggers at INFO level
    logging.getLogger("app").setLevel(logging.INFO)
    logging.getLogger("scraping").setLevel(logging.INFO)
    logging.getLogger("auto_search").setLevel(logging.INFO)
    
    print(f"✅ Logging configured: Console (WARNING+), File (DEBUG+) -> {log_dir / 'grace.log'}")
