import tempfile
from dataclasses import dataclass
from pathlib import Path

import pytest

from piquid.pickleable import PickleAble


# define the test class
class Basic(PickleAble):

    def __init__(self, a: int, b: list[str], c: dict[str, list[float]]):
        self.a = a
        self.b = b
        self.c = c
        self.e = None

    def test_method(self):
        return ' '.join(map(str, (self.a, self.c, self.b, self.e)))


# define fixtures
@pytest.fixture()
def test_instance() -> Basic:
    instance = Basic(a=1, b=['hello', 'there'], c={'I': [5.5, 6.6, 7.7], 'am': [1.1, 2.2, 3.3], 'a': [4.4, 5.5]})
    instance.e = ['a', 'b', 'c']
    return instance


def test_roundtrip_file(test_instance):

    # roundtrip the instance
    temp_file_path = Path(tempfile.mkdtemp()).joinpath('file.pkl')
    test_instance.to_pickle_file(file_path=temp_file_path)
    instance_roundtrip = Basic.from_pickle_file(file_path=temp_file_path)

    # check
    assert test_instance.__dict__ == instance_roundtrip.__dict__


def test_roundtrip(test_instance):

    # roundtrip the instance
    obj_bytes = test_instance.to_pickle()
    instance_roundtrip = Basic.from_pickle(pickle_bytes=obj_bytes)

    # check
    assert test_instance.__dict__ == instance_roundtrip.__dict__


@dataclass(frozen=True)
class BasicDataclass(PickleAble):
    a: int
    b: list[str]
    c: dict[str, list[float]]

    def test_method(self):
        return ' '.join(map(str, (self.a, self.c, self.b, self.e)))


@pytest.fixture()
def test_dataclass_instance() -> BasicDataclass:
    return BasicDataclass(a=9, b=['Hey', 'here', 'we', 'are'], c={'a': [1.1, 2.2]})


def test_roundtrip_dataclass(test_dataclass_instance):

    # roundtrip the instance
    obj_bytes = test_dataclass_instance.to_pickle()
    instance_roundtrip = BasicDataclass.from_pickle(pickle_bytes=obj_bytes)

    # check
    assert instance_roundtrip == test_dataclass_instance
