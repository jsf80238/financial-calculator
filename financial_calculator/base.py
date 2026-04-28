import sys
import logging
# Imports above are standard Python
# Imports below are 3rd-party

min_major, min_minor = 3, 11
major, minor = sys.version_info[:2]
if major < min_major or minor < min_minor:
    raise Exception(f"Your Python version needs to be at least {min_major}.{min_minor}.")


class Logger:
    __instance = None

    def __new__(cls,
                level: [str | int] = None,
                is_generate_session_id: bool = False,
                session_id: str = None,
                **kwargs
                ):
        """
        Return the same logger for every invocation.
        """
        if not cls.__instance:
            if level:
                cls.level = level.upper()
            else:
                cls.level = "INFO"

            cls.logger = logging.getLogger()
            # Set overall logging level, will be overridden by the handlers
            cls.logger.setLevel(logging.DEBUG)
            # Formatting
            date_format = '%Y-%m-%dT%H:%M:%S%z'
            if is_generate_session_id:
                formatter = logging.Formatter('%(asctime)s | %(levelname)8s | session_id=%(session_id)s | %(message)s', datefmt=date_format)
            else:
                formatter = logging.Formatter('%(asctime)s | %(levelname)8s | %(message)s', datefmt=date_format)
            # Logging to STDERR
            console_handler = logging.StreamHandler()
            console_handler.setLevel(cls.level)
            console_handler.setFormatter(formatter)
            # Add console handler to logger
            cls.logger.addHandler(console_handler)
            cls.__instance = object.__new__(cls)
        return cls.__instance

    @classmethod
    def get_logger(cls) -> logging.Logger:
        return cls.logger

    @classmethod
    def set_level(cls, level: str) -> None:
        for handler in cls.logger.handlers:
            handler.setLevel(level)


if __name__ == "__main__":
    logger = Logger().get_logger()
    logger.info("a logging message")
