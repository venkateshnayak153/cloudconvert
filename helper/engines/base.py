"""
Base engine class and conversion exceptions.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable, Optional

ProgressCallback = Callable[[int, str], None]


class EngineError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class BaseEngine(ABC):
    name: str = "base"

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the engine is installed and callable on this system."""
        pass

    @abstractmethod
    def convert(
        self,
        input_path: Path,
        output_path: Path,
        target_ext: str,
        progress_cb: Optional[ProgressCallback] = None,
        **kwargs,
    ) -> Path:
        """
        Executes conversion.
        Raises EngineError on failure.
        Returns final Path to converted file.
        """
        pass
