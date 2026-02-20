"""
FocusGuard - Centralized Logging Configuration
Provides structured logging with file rotation for all components
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime


# ==================== LOG DIRECTORY ====================
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)


# ==================== LOG FORMAT ====================
LOG_FORMAT = "%(asctime)s [%(levelname)-8s] %(name)-20s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Concise format for console
CONSOLE_FORMAT = "%(asctime)s [%(levelname)-8s] %(message)s"


# ==================== SETUP FUNCTIONS ====================

def setup_logger(
    name: str,
    log_file: str = None,
    level: int = logging.INFO,
    max_bytes: int = 5 * 1024 * 1024,  # 5MB per file
    backup_count: int = 5,  # Keep 5 backup files
    console: bool = True
) -> logging.Logger:
    """
    Create a configured logger with file rotation and console output.
    
    Args:
        name: Logger name (e.g., 'focusguard.server', 'focusguard.client')
        log_file: Log file name (stored in logs/ directory). None = no file logging.
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        max_bytes: Max size per log file before rotation
        backup_count: Number of rotated files to keep
        console: Whether to also log to console
        
    Returns:
        Configured Logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid adding duplicate handlers
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # File handler with rotation
    if log_file:
        file_path = os.path.join(LOG_DIR, log_file)
        file_handler = logging.handlers.RotatingFileHandler(
            file_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8"
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
        logger.addHandler(file_handler)
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(logging.Formatter(CONSOLE_FORMAT, LOG_DATE_FORMAT))
        logger.addHandler(console_handler)
    
    return logger


# ==================== PRE-CONFIGURED LOGGERS ====================

def get_server_logger() -> logging.Logger:
    """Logger for server operations (API, WebSocket, startup)"""
    return setup_logger("focusguard.server", "server.log")


def get_auth_logger() -> logging.Logger:
    """Logger for authentication events (login, logout, password changes)"""
    return setup_logger("focusguard.auth", "auth.log")


def get_violation_logger() -> logging.Logger:
    """Logger for violation events (detected violations, screenshots)"""
    return setup_logger("focusguard.violations", "violations.log")


def get_exam_logger() -> logging.Logger:
    """Logger for exam management (create, start, end, join)"""
    return setup_logger("focusguard.exams", "exams.log")


def get_client_logger() -> logging.Logger:
    """Logger for client operations (camera, AI engine, connection)"""
    return setup_logger("focusguard.client", "client.log")


def get_ai_logger() -> logging.Logger:
    """Logger for AI engine operations (detection, classification)"""
    return setup_logger("focusguard.ai", "ai.log")
