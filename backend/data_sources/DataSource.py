from abc import ABC, abstractmethod


class DataSource(ABC):
    """Polling interface. None means no NEW data; check finished for CSV EOF.

    Telemetry values are strings, matching the existing dashboard convention.
    Use one owner/thread per source; these objects are not thread safe.
    Connection failures return False and expose last_error. Configuration
    mistakes raise ValueError/TypeError instead of being silently swallowed.
    """

    last_error: str | None = None

    @abstractmethod
    def connect(self, **kwargs) -> bool: ...

    @abstractmethod
    def disconnect(self) -> None: ...

    @abstractmethod
    def get_data(self) -> dict[str, str] | None: ...

    @abstractmethod
    def is_connected(self) -> bool: ...

    def send_command(self, command: str, add_newline: bool = True) -> bool:
        raise NotImplementedError("This source does not support commands")

    def get_type(self) -> str:
        return type(self).__name__.removesuffix("DataSource").lower()
