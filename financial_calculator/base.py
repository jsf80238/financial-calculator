import sys
import logging
from pathlib import Path
# Imports above are standard Python
# Imports below are 3rd-party

min_major, min_minor = 3, 11
major, minor = sys.version_info[:2]
if major < min_major or minor < min_minor:
    raise Exception(f"Your Python version needs to be at least {min_major}.{min_minor}.")


RETURNS_PATH = Path(__file__).parent.parent / "historical_data"


class Logger:
    __instance = None
    # Formatting
    date_format = '%Y-%m-%dT%H:%M:%S%z'
    formatter = logging.Formatter('%(asctime)s | %(levelname)8s | %(message)s', datefmt=date_format)

    def __new__(cls,
                level: [str | int] = None,
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
            # Logging to STDERR
            console_handler = logging.StreamHandler()
            console_handler.setLevel(cls.level)
            console_handler.setFormatter(cls.formatter)
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

    @classmethod
    def set_file(cls, file_path: Path | str, is_append: bool = False) -> None:
        if isinstance(file_path, str):
            file_path = Path(file_path)
        if not file_path.parent.exists():
            cls.logger.error(f"File path {file_path} does not exist")
        else:
            file_handler = logging.FileHandler(file_path, mode='a' if is_append else 'w')
            file_handler.setLevel(cls.logger.level)
            file_handler.setFormatter(cls.formatter)
            cls.logger.addHandler(file_handler)


if __name__ == "__main__":
    logger = Logger().get_logger()
    Logger().set_file("/tmp/test.log", is_append=True)
    logger.info("a logging message")
