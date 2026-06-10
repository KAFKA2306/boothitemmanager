from typing import Any, Dict, Type

class SchemaRegistry:
    _schemas: Dict[str, Type] = {}
    _locked: bool = False

    @classmethod
    def register(cls, name: str, schema: Type) -> None:
        if cls._locked:
            raise RuntimeError('SchemaRegistry is locked')
        cls._schemas[name] = schema

    @classmethod
    def validate(cls, name: str, data: Any) -> None:
        if name not in cls._schemas:
            raise KeyError(f"Schema '{name}' not found")
        if not isinstance(data, cls._schemas[name]):
            raise TypeError(f"Data does not match schema '{name}'")

    @classmethod
    def lock(cls) -> None:
        cls._locked = True

    @classmethod
    def is_locked(cls) -> bool:
        return cls._locked