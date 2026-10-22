from .DataSource import DataSource
from .CSVDataSource import CSVDataSource
from .SerialDataSource import SerialDataSource
from .RadioDataSource import RadioDataSource


class DataSourceFactory:
    """Create a source without connecting or probing hardware as a side effect."""

    _data_sources = {"csv": CSVDataSource, "serial": SerialDataSource, "radio": RadioDataSource}

    @classmethod
    def get_data_source_types(cls, verbose=False):
        names = list(cls._data_sources)
        if verbose:
            print("Available data sources:", ", ".join(names))
        return names

    get_available_types = get_data_source_types

    @classmethod
    def create_data_source(cls, source_type, verbose=False, **kwargs) -> DataSource:
        name = source_type.strip().lower()
        if name not in cls._data_sources:
            raise ValueError(f"Unknown source {source_type!r}. Choose: {', '.join(cls._data_sources)}")
        if verbose:
            print(f"Creating {name} source")
        return cls._data_sources[name](**kwargs)

    @classmethod
    def register_data_source(cls, name, data_source_class):
        if not isinstance(data_source_class, type) or not issubclass(data_source_class, DataSource):
            raise TypeError("Source class must inherit DataSource")
        name = name.strip().lower()
        if not name:
            raise ValueError("Source name cannot be blank")
        cls._data_sources[name] = data_source_class
