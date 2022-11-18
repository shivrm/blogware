from __future__ import annotations
from typing import Callable

import tomli, os

LAYOUT_DIR = 'layouts'
TEMPLATE_FN = str.format

FRONTMATTER_TOP = '---'
FRONTMATTER_BOTTOM = '---'
FRONTMATTER_PARSER = tomli.loads

CONFIG_PARSER = tomli.loads
CONFIG_NAME = 'config.toml'


class Path(str):
    """Wraps a `str` and provides some utility methods for path manipulation."""

    def __init__(self, *args) -> None:
        super().__init__()
    
    def swap_root(self, old_root: str, new_root: str):
        """
        Swaps the root of a path
        
        ```py
        >>> Path("C:/folder/file.txt").swap_root('C:/folder', 'C:/dir')
        'C:/dir/file.txt'
        ```
        """
        relpath = os.path.relpath(self, old_root)
        return Path(os.path.join(new_root, relpath))
    
    def swap_ext(self, new_ext: str):
        """
        Swaps the extension of a file path
        
        ```py
        >>> Path('index.md').swap_ext('.html')
        'index.html'
        ```
        """

        return Path(os.path.splitext(self)[0] + new_ext)


class File:
    """Represents a buildable file"""

    def __init__(self, path: str, *args, **kwargs) -> None:
        self.path = Path(path)

        self.dir, self.filename = os.path.split(self.path)
        self.basename, self.ext = os.path.splitext(self.filename)

        self.args = args
        self.kwargs = kwargs
        
        self._content = None

    def template(self, vars: dict) -> str:
        """Templates the content of the file"""
        return TEMPLATE_FN(self.content, **vars)

    @property
    def content(self) -> str:
        """The content of the file"""
        if self._content is None:
            self._content = open(self.path).read()

        return self._content


class FrontMatterFile(File):
    """Represents a file that might have frontmatter at the start"""

    def __init__(self, path: str, *args, **kwargs) -> None:
        super().__init__(path)

        self.args = args
        self.kwargs = kwargs

        self._body = None
        self._frontmatter = None

    def split_frontmatter(self):
        """Splits the frontmatter and the body and returns them"""

        if self.content.lstrip().startswith(FRONTMATTER_TOP):
            self._frontmatter, self._body = (
                self.content
                    .replace(FRONTMATTER_TOP, '', 1)
                    .split(FRONTMATTER_BOTTOM, 1)
            )

            return FRONTMATTER_PARSER(self._frontmatter), self._body

        return {}, self._content
    
    def template(self, vars: dict) -> str:
        """Templates the body using variables in the frontmatter"""
        return TEMPLATE_FN(self.body, **vars, **self.frontmatter)

    @property
    def frontmatter(self) -> dict:
        """The frontmatter of the file"""

        if self._frontmatter == None:
            self._frontmatter, self._body = self.split_frontmatter()

        return self._frontmatter # type: ignore

    @property
    def body(self) -> str:
        """The body of the file, which is the part after the frontmatter"""

        if self._body == None:
            self._frontmatter, self._body = self.split_frontmatter()

        return self._body


class DirIndex:
    """A lazy iterator over the contents of a directory"""

    def __init__(self, path: str, *args, **kwargs) -> None:
        self.path = Path(path)
        self.args = args
        self.kwargs = kwargs
    
    def items(self):
        """
        Get an iterator over the items in the directory.

        Each child file is represented by a `FrontMatterFile`, and each
        child directory is represented by a `DirIndex`.
        """

        for entry in os.scandir(self.path):
            if entry.is_file():
                yield FrontMatterFile(entry.path, *self.args, **self.kwargs)

            elif entry.is_dir():
                yield DirIndex(entry.path, *self.args, **self.kwargs)

    def __iter__(self):
        return self.items()


class Iter:
    """Provides utility functions for working with a `DirIndex`"""

    def __init__(self, index: DirIndex) -> None:
        self.index = index
        self.items = index.items()

    @staticmethod
    def from_dir(dir: str) -> Iter:
        """Constructs an `Iter` from a directory path"""
        return Iter(DirIndex(dir))

    def files(self) -> Iter:
        """Filters the items of the iterator, so that it contains only files"""
        self.items = filter(is_file, self.items)
        return self

    def dirs(self) -> Iter:
        """Filters the items of the iterator, so that it contains only directoriess"""
        self.items = filter(is_dir, self.items)
        return self

    def match_exec(self, predicate: Callable, fn: Callable, *args, **kwargs) -> Iter:
        """Iterates over all entries and calls a function if they match a predicate"""

        items = []
        
        for item in self.items:
            items.append(item)
            if predicate(item):
                fn(item, *args, **kwargs)

        self.items = items
        return self

    def set_var(self, name: str, value) -> Iter:
        # Useless as of now
        self.index.kwargs[name] = value
        return self


def get_config(dir, root) -> dict:
    """
    Returns the config of a directory, as a dict.

    Config is calculated in this manner:
    ```
    config_of_this_dir = config_of_parent_dir + config_from_config_file
    ```
    """
    config_path = os.path.join(dir, CONFIG_NAME)

    if os.path.exists(config_path):
        config = CONFIG_PARSER(open(config_path).read())
    else:
        config = {}

    if os.path.samefile(dir, root):
        return config
    else:
        parent_dir = os.path.split(dir)[0]
        return {**get_config(parent_dir, root), **config}


def load_layout(name) -> FrontMatterFile:
    """
    Loads a layout file.
    """

    path = os.path.join(LAYOUT_DIR, name)

    if os.path.isfile(path):
        return FrontMatterFile(path)

    raise Exception("Layout {} does not exist".format(name))


def ext(*args):
    """Returns a function that returns `True` if a file has a specific extension.
    
    ```py
    >>> f = File('C:/index.md')
    >>> ext('.md')(f)
    True
    >>> ext('.md', '.html')(f)
    True
    >>> ext('.html')(f)
    False
    ```
    """

    def inner(file) -> bool:
        return isinstance(file, File) and file.ext in args
    
    return inner


def is_file(obj):
    """Returns True if the object is a `File`"""
    return isinstance(obj, File)


def is_dir(obj):
    """Returns True if the object is a `DirIndex`"""
    return isinstance(obj, DirIndex)