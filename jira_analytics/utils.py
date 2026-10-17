"""
Модуль вспомогательных функций и настройки логирования.
Разработчик: Суханов С.С.
"""

import os
import sys
import logging
import configparser
from datetime import datetime
from typing import Dict, Any, Optional
from dateutil import parser as date_parser


def ensure_dir(path: str) -> str:
    """
    Создает директорию, если она не существует.
    
    :param path: Путь к директории.
    :return: Исходный путь.
    """
    if path and not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    return path


def setup_logging(log_file: Optional[str] = "logs/jira_analytics.log",
                  log_level: str = "INFO") -> logging.Logger:
    """
    Инициализирует и настраивает систему логирования для приложения.
    
    :param log_file: Путь к файлу логов.
    :param log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR).
    :return: Настроенный логгер.
    """
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger = logging.getLogger("jira_analytics")
    logger.setLevel(level)
    logger.propagate = False

    # Предотвращение дублирования обработчиков при повторном вызове
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Консольный обработчик
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Файловый обработчик
    if log_file:
        ensure_dir(os.path.dirname(log_file))
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger.info("Система логирования успешно инициализирована (уровень: %s)", log_level)
    return logger


def get_logger(name: str = "jira_analytics") -> logging.Logger:
    """
    Возвращает экземпляр именованного логгера.
    
    :param name: Имя логгера.
    :return: Объект Logger.
    """
    return logging.getLogger(name)


def load_config(config_path: str = "config.ini") -> Dict[str, Any]:
    """
    Загружает конфигурационные параметры из INI-файла с безопасными значениями по умолчанию.
    
    :param config_path: Путь к конфигурационному файлу.
    :return: Словарь со структурированной конфигурацией.
    """
    config = configparser.ConfigParser()
    defaults = {
        "jira": {
            "base_url": "https://issues.apache.org/jira",
            "default_project": "KAFKA",
            "timeout": "30",
            "max_results": "500",
        },
        "storage": {
            "cache_dir": "cache",
            "results_dir": "results",
            "log_dir": "logs",
        },
        "logging": {
            "log_file": "logs/jira_analytics.log",
            "log_level": "INFO",
        },
        "visualization": {
            "dpi": "300",
            "figure_width": "10",
            "figure_height": "6",
        }
    }
    config.read_dict(defaults)

    if os.path.exists(config_path):
        config.read(config_path, encoding="utf-8")

    return {
        "base_url": config.get("jira", "base_url"),
        "default_project": config.get("jira", "default_project"),
        "timeout": config.getint("jira", "timeout"),
        "max_results": config.getint("jira", "max_results"),
        "cache_dir": config.get("storage", "cache_dir"),
        "results_dir": config.get("storage", "results_dir"),
        "log_dir": config.get("storage", "log_dir"),
        "log_file": config.get("logging", "log_file"),
        "log_level": config.get("logging", "log_level"),
        "dpi": config.getint("visualization", "dpi"),
        "figure_width": config.getfloat("visualization", "figure_width"),
        "figure_height": config.getfloat("visualization", "figure_height"),
    }


def parse_jira_date(date_str: Optional[str]) -> Optional[datetime]:
    """
    Парсит дату из формата JIRA REST API в объект datetime.
    
    :param date_str: Строка с датой (например, '2026-10-15T20:21:42.000+0000').
    :return: Объект datetime или None в случае ошибки/пустой строки.
    """
    if not date_str:
        return None
    try:
        return date_parser.parse(date_str)
    except Exception:
        return None
