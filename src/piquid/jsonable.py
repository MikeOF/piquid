"""JSON serialization"""

import inspect
import json
from abc import ABCMeta
from pathlib import Path
from typing import Optional, Union


class JSONAble(metaclass=ABCMeta):
    """A base class providing JSON serialization functionality.

    This class includes an interface for JSON serialization that relies on the signature of the inheriting classes
    __init__ method. During serialization the parameters of the __init__ method are collected from the class to be
    serialized, and during deserialization the parameters of the __init__ method are used to create keyword arguments
    to the __init__ method. The means that any class members which need to be included in serialzied instances of the
    class must be included as paramters to the __init__ signature.

    Notes & Caveats:

    * Currently only standard JSON types are supported.
    * Any instance state that is not part of the __init__ signature will not be serialized.
    """

    _CONSTRUCTOR_PARAMETER_SET: Optional[set[str]] = None

    @classmethod
    def _ensure_constructor_parameter_set(cls) -> None:
        """Ensure that the constructor parameter set is set for this JSONAble class."""

        if cls._CONSTRUCTOR_PARAMETER_SET is None:

            cls._CONSTRUCTOR_PARAMETER_SET = {
                name for name in inspect.signature(cls.__init__).parameters if name != 'self'
            }

    @classmethod
    def from_json_file(cls, file_path: Union[Path, str]):
        """Deserialize an instance from a file path.

        Parameters
        ----------
        file_path : Path | str
            the file path to deserialize the instance from

        Returns
        -------
        __class__
            the instance of the class
        """
        with Path(file_path).open(mode='r') as inf:
            return cls.from_json(json_str=inf.read())

    @classmethod
    def from_json(cls, json_str: str):
        """Deserialize an instance from a JSON string.

        Parameters
        ----------
        json_str : str
            the JSON string to deserialize the instance from

        Returns
        -------
        __class__
            the instance of the class
        """

        return cls.from_json_obj(json_obj=json.loads(json_str))

    @classmethod
    def from_json_obj(cls, json_obj: dict):
        """Create an instance from a JSON object.

        Parameters
        ----------
        json_obj : dict
            the object to generate the instance from

        Returns
        -------
        __class__
            an instance of the class
        """

        cls._ensure_constructor_parameter_set()
        construction_kwarg_by_name = {k: v for k, v in json_obj.items() if k in cls._CONSTRUCTOR_PARAMETER_SET}

        return cls(**construction_kwarg_by_name)

    def to_json_file(self, file_path: Union[Path, str], indent: Optional[int] = None) -> None:
        """Serialize the instance and write to a file path.

        Parameters
        ----------
        file_path : Union[Path, str]
            the file path to write to
        indent : Optional[int]
            the number of spaces to used when indenting the JSON string

        Returns
        -------
        None
            nothing
        """

        with Path(file_path).open(mode='w') as outf:
            outf.write(self.to_json(indent=indent))

    def to_json(self, indent: int = None) -> str:
        """Serialize the instance to a JSON string.

        Parameters
        ----------
        indent : Optional[int]
            the number of spaces to used when indenting the JSON string

        Returns
        -------
        str
            JSON serialized string of the instance
        """

        return json.dumps(self.to_json_obj(), indent=indent)

    def to_json_obj(self) -> dict:
        """Serialize the instance to a JSON object.

        Returns
        -------
        dict
            JSON serialized object of the instance
        """

        self._ensure_constructor_parameter_set()
        return {k: getattr(self, k) for k in self._CONSTRUCTOR_PARAMETER_SET}
