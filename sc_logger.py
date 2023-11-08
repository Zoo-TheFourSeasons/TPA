from typing import Any, Dict
import sys

logs: Dict[str, Any] = dict(
    version=1,
    disable_existing_loggers=True,
    loggers={
        "sanic.root": {
            "level": "INFO",
            "handlers": ["console"]
        },
        "sanic.error": {
            "level": "INFO",
            "handlers": ["error"],
            "propagate": True,
            "qualname": "sanic.error",
        },
        "sanic.access": {
            "level": "INFO",
            "handlers": ["access"],
            "propagate": True,
            "qualname": "sanic.access",
        },
        "sanic.server": {
            "level": "INFO",
            "handlers": ["server"],
            "propagate": True,
            "qualname": "sanic.server",
        },
        "profile": {
            "level": "INFO",
            "handlers": ["profile"],
            "propagate": True,
            "qualname": "profile",
        },
    },
    # handlers={
    #     "console": {
    #         "class": "logging.StreamHandler",
    #         "formatter": "generic",
    #         "stream": sys.stdout,
    #     },
    #     "error_console": {
    #         "class": "logging.StreamHandler",
    #         "formatter": "generic",
    #         "stream": sys.stderr,
    #     },
    #     "access_console": {
    #         "class": "logging.StreamHandler",
    #         "formatter": "access",
    #         "stream": sys.stdout,
    #     },
    # },
    handlers={
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "generic",
            "stream": sys.stdout,
        },
        "error": {
            "class": "logging.FileHandler",
            "formatter": "generic",
            "filename": "logs/error.log",
        },
        "access": {
            "class": "logging.FileHandler",
            "formatter": "access",
            "filename": "logs/access.log",
        },
        "server": {
            "class": "logging.FileHandler",
            "formatter": "generic",
            "filename": "logs/server.log",
        },
        "profile": {
            "class": "logging.FileHandler",
            "formatter": "profile",
            "filename": "logs/profile.log",
        },
    },
    formatters={
        "profile": {
            'format': '%(asctime)s %(levelname)s %(message)s',
            "datefmt": "%Y-%m-%d %H:%M:%S %z",
            "class": "logging.Formatter",
        },
        "generic": {
            "format": "%(asctime)s %(process)s %(levelname)s [%(pathname)s:%(lineno)s] %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S %z",
            "class": "logging.Formatter",
        },
        "access": {
            "format": "%(asctime)s %(levelname)s %(host)s %(request)s %(message)s %(status)s %(byte)s",
            "datefmt": "%Y-%m-%d %H:%M:%S %z",
            "class": "logging.Formatter",
        },
    },
)
