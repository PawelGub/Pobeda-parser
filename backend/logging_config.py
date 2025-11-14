# logging_config.py
import logging
import logging.config
import json
from pythonjsonlogger import jsonlogger

# Настройка JSON логгера для ELK
class ELKJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record['timestamp'] = record.created
        log_record['level'] = record.levelname
        log_record['service'] = 'pobeda-backend'
        log_record['module'] = record.module
        log_record['function'] = record.funcName

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': ELKJsonFormatter,
        },
        'simple': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        }
    },
    'handlers': {
        'elk': {
            'class': 'logging.handlers.HTTPHandler',
            'host': 'localhost:5000',  # Logstash
            'url': '/logs',
            'method': 'POST',
            'formatter': 'json'
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'app.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'json'
        }
    },
    'loggers': {
        '': {  # root logger
            'handlers': ['console', 'elk', 'file'],
            'level': 'INFO',
        },
        'anywhere_service': {
            'handlers': ['console', 'elk', 'file'],
            'level': 'DEBUG',
            'propagate': False
        },
        'flight_service': {
            'handlers': ['console', 'elk', 'file'],
            'level': 'DEBUG',
            'propagate': False
        }
    }
}

# Инициализация логгера
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)