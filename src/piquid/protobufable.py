"""Protobuf serialization"""
import inspect
import subprocess
from abc import ABCMeta
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import GenericAlias
from typing import Optional


class ProtobufAble(metaclass=ABCMeta):
    """Base class that provides protobuf serialization.

    This class provides its subclasses with protobuf serialization functionality. This includes writing a proto files,
    compiling protofiles, importing message classes, and serializing instances to binary protobuf.

    The class translates some standard python types to protobuf types though there isn't much flexibility to how this is
    done. Generally this class is quite limited in terms of its flexibility. In simple use cases it can enable protobuf
    serializtion, however for more complex cases extending the class or writing more bespoke infrstructure is warranted.

    The class works by inspecting the signature of the init method to capture members that are to be serialized. It will
    assign basic types to Python primitives, and it can assign container types such as dicts and lists to protobuf
    repeated types. Container types can be handled if they are expected to contain uniform collections of the same type.
    Nested containers and containers with multiple or types are not supported.

    The class works by lazily completing a series of step. When one of the serialization methods is called the class
    will make sure the message class is imported. If this hasn't happend the class will ensure the message module
    exists before importing it. While ensuring the method module exists the class will write and compile a protofile if
    necessary.

    Note:
        * subclasses will write protofiles and modules to directories named "__protobuf__" where subclasses are defined
        * only members referenced in the __init__ signature will be serialized
        * each parameter in the __init__ signature must have type hints
    """

    _PROTOBUF_DIRNAME = '__protobuf__'
    _PROTOFILE_SUFFIX = '.proto'
    _OPTIONAL_TYPE_BY_TYPE = {str: 'string', bool: 'bool', int: 'int32', float: 'double'}
    _REPEATED_TYPE_SET = frozenset((list, set))
    _CONSTRUCTOR_PARAMETER_BY_NAME: Optional[dict] = None
    _OPTIONAL_TYPE_BY_MEMBER: Optional[dict] = None
    _REPEATED_CONTAINER_TYPE_BY_MEMBER: Optional[dict] = None
    _REPEATED_ELEMENT_TYPE_BY_MEMBER: Optional[dict] = None
    _MESSAGE_CLASS: Optional = None

    @classmethod
    def _get_protobuf_dir_path(cls) -> Path:
        """Get the directory where protobuf files will be stored."""
        return Path(inspect.getmodule(cls).__file__).parent.joinpath(cls._PROTOBUF_DIRNAME)

    @classmethod
    def _get_protofile_path(cls) -> Path:
        """Get the protofile path for this class."""
        return cls._get_protobuf_dir_path().joinpath(cls.__name__).with_suffix('.proto')

    @classmethod
    def _get_message_class_file_path(cls) -> Path:
        """Get the protofile path for this class."""
        return cls._get_protobuf_dir_path().joinpath(f'{cls.__name__}_pb2.py')

    @classmethod
    def _ensure_type_by_member_dicts(cls) -> None:
        """Ensure that the type by member dicts are set for this ProtobufAble class."""

        if (
                cls._OPTIONAL_TYPE_BY_MEMBER is None
                or cls._REPEATED_CONTAINER_TYPE_BY_MEMBER is None
                or cls._REPEATED_ELEMENT_TYPE_BY_MEMBER is None
        ):

            cls._CONSTRUCTOR_PARAMETER_BY_NAME = {
                name: parameter
                for name, parameter in inspect.signature(cls.__init__).parameters.items()
                if name != 'self'
            }

            type_by_member = {
                name: parameter.annotation
                for name, parameter in cls._CONSTRUCTOR_PARAMETER_BY_NAME.items()
            }

            cls._OPTIONAL_TYPE_BY_MEMBER = {
                name: member_type for name, member_type in type_by_member.items()
                if member_type in cls._OPTIONAL_TYPE_BY_TYPE
            }

            repeated_type_by_member = {
                name: member_type for name, member_type in type_by_member.items()
                if name not in cls._OPTIONAL_TYPE_BY_MEMBER
            }

            cls._REPEATED_CONTAINER_TYPE_BY_MEMBER = {}
            cls._REPEATED_ELEMENT_TYPE_BY_MEMBER = {}
            for member, repeated_type in repeated_type_by_member.items():
                assert isinstance(repeated_type, GenericAlias), f'unexpected repeated type, {member} {repeated_type}'

                container_type = getattr(repeated_type, '__origin__')
                element_type = next(iter(getattr(repeated_type, '__args__')))

                assert container_type in cls._REPEATED_TYPE_SET, f'unaccepted container type, {member} {container_type}'
                assert element_type in cls._OPTIONAL_TYPE_BY_TYPE, f'unaccepted type, {member} {element_type}'

                cls._REPEATED_CONTAINER_TYPE_BY_MEMBER[member] = container_type
                cls._REPEATED_ELEMENT_TYPE_BY_MEMBER[member] = element_type

    @classmethod
    def _write_protofile(cls) -> None:
        """Write a protofile for this ProtobufAble."""

        # make the protobuf dir if necessary
        cls._get_protobuf_dir_path().mkdir(exist_ok=True)

        with cls._get_protofile_path().open(mode='w') as outf:

            # write the header
            print('syntax = "proto3";', file=outf)
            print('', file=outf)
            print(f'package {cls.__name__};', file=outf)
            print('', file=outf)

            # write the message
            print(f'message {cls.__name__} {{', file=outf)

            # set the type by member dicts if they are None
            cls._ensure_type_by_member_dicts()

            # write declarations for each repeated type
            element_count = 0
            for member, element_type in cls._REPEATED_ELEMENT_TYPE_BY_MEMBER.items():
                element_count += 1
                print(
                    f'\trepeated {cls._OPTIONAL_TYPE_BY_TYPE[element_type]} {member} = {element_count};',
                    file=outf
                )
                print(f'', file=outf)

            # write declarations for each optional type
            for member, optional_type in cls._OPTIONAL_TYPE_BY_MEMBER.items():
                element_count += 1
                print(
                    f'\toptional {cls._OPTIONAL_TYPE_BY_TYPE[optional_type]} {member} = {element_count};',
                    file=outf
                )
                print(f'', file=outf)

            print('}', file=outf)

    @classmethod
    def _compile(cls) -> None:
        """Compile the protofile for this ProtobufAble."""

        # get the protofile
        protofile_path = cls._get_protofile_path()

        # write the protofile if it doesn't exist
        if not protofile_path.is_file():
            cls._write_protofile()

        # run the compile command
        protobuf_dir_path = cls._get_protobuf_dir_path()
        cmd_tuple = ('protoc', f'-I={protobuf_dir_path}', f'--python_out={protobuf_dir_path}', f'{protofile_path}')
        subprocess.run(cmd_tuple)

        # make sure the message class file can be found
        assert cls._get_message_class_file_path().exists(), (
            f'could not find message class path, {list(cls._get_protobuf_dir_path().glob("*"))}'
        )

    @classmethod
    def _import_message_class(cls) -> None:
        """Import the message class for this ProtobufAble."""

        if cls._MESSAGE_CLASS is None:

            # get the message class file path and make sure it exists
            message_class_file_path = cls._get_message_class_file_path()
            if not message_class_file_path.exists():
                cls._compile()

            # load the mesage module
            loader = SourceFileLoader(fullname=message_class_file_path.stem, path=str(message_class_file_path))
            message_module = loader.load_module()

            # get the source class
            cls._MESSAGE_CLASS = getattr(message_module, cls.__name__)

    @classmethod
    def from_protobuf_file(cls, file_path: Path):
        """Create an instance from  a file path.

        Parameters
        ----------
        file_path : Path | str
            the file path to read the instance from

        Returns
        -------
        __class__
            an instance of the class
        """
        with file_path.open(mode='rb') as inf:
            return cls.from_protobuf(protobuf=inf.read())

    @classmethod
    def from_protobuf(cls, protobuf: bytes):
        """Create an instance from protobuf bytes.

        Parameters
        ----------
        protobuf : bytes
            protobuf serialized bytes of the class.

        Returns
        -------
        __class__
            an instance of the class
        """

        # import the message class if necessary
        if cls._MESSAGE_CLASS is None:
            cls._import_message_class()

        # create the message instance
        instance = cls._MESSAGE_CLASS()
        instance.ParseFromString(protobuf)

        # create the constructor arguments
        kwarg_dict = {member: getattr(instance, member) for member in cls._OPTIONAL_TYPE_BY_MEMBER}
        kwarg_dict.update(
            (member, container_type(getattr(instance, member)))
            for member, container_type in cls._REPEATED_CONTAINER_TYPE_BY_MEMBER.items()
        )

        return cls(**kwarg_dict)

    def to_protobuf_file(self, file_path: Path) -> None:
        """Serialize the instance and write to a file path.

        Parameters
        ----------
        file_path : Union[Path, str]
            the file path to write to

        Returns
        -------
        None
            nothing
        """
        with file_path.open(mode='wb') as outf:
            outf.write(self.to_protobuf())

    def to_protobuf(self) -> bytes:
        """Serialize the instance to protobuf bytes.

        Returns
        -------
        bytes
            protobuf serialized bytes of the instance.
        """

        # import the message class if necessary
        if self._MESSAGE_CLASS is None:
            self._import_message_class()

        # set the type by member dicts if they are None
        self._ensure_type_by_member_dicts()

        # create an instance of the message class
        instance = self._MESSAGE_CLASS()

        # add each optional member
        for member in self._OPTIONAL_TYPE_BY_MEMBER:
            setattr(instance, member, getattr(self, member))

        # add each repeated member
        for member in self._REPEATED_ELEMENT_TYPE_BY_MEMBER:
            getattr(instance, member).extend(getattr(self, member))

        # serialize and return
        return instance.SerializeToString()
