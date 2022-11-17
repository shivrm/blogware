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
    def __init__(self, *args) -> None:
        super().__init__()
    
    def swap_root(self, old_root: str, new_root: str):
        relpath = os.path.relpath(self, old_root)
        return Path(os.path.join(new_root, relpath))
    
    def swap_ext(self, new_ext: str):
        return Path(os.path.split(self)[0] + new_ext)


class File:
    def __init__(self, path: str, *args, **kwargs) -> None:
        self.path = Path(path)

        self.dir, self.filename = os.path.split(self.path)
        self.basename, self.ext = os.path.splitext(self.filename)

        self.args = args
        self.kwargs = kwargs
        
        self._content = None

    def template(self, vars: dict) -> str:
        return TEMPLATE_FN(self.content, **vars)

    @property
    def content(self) -> str:
        if self._content is None:
            self._content = open(self.path).read()

        return self._content


class FrontMatterFile(File):
    def __init__(self, path: str, *args, **kwargs) -> None:
        super().__init__(path)

        self.args = args
        self.kwargs = kwargs

        self._body = None
        self._frontmatter = None

    def split_frontmatter(self):
        if self.content.lstrip().startswith(FRONTMATTER_TOP):
            self._frontmatter, self._body = (
                self.content
                    .replace(FRONTMATTER_TOP, '', 1)
                    .split(FRONTMATTER_BOTTOM, 1)
            )

            return FRONTMATTER_PARSER(self._frontmatter), self._body

        return {}, self._content
    
    def template(self, vars: dict) -> str:
        return TEMPLATE_FN(self.body, **vars, **self.frontmatter)

    @property
    def frontmatter(self) -> dict:
        if self._frontmatter == None:
            self._frontmatter, self._body = self.split_frontmatter()

        return self._frontmatter # type: ignore

    @property
    def body(self) -> str:
        if self._body == None:
            self._frontmatter, self._body = self.split_frontmatter()

        return self._body


class DirIndex:
    def __init__(self, path: str, *args, **kwargs) -> None:
        self.path = Path(path)
        self.args = args
        self.kwargs = kwargs
    
    def items(self):
        for entry in os.scandir(self.path):
            if entry.is_file():
                yield FrontMatterFile(entry.path, *self.args, **self.kwargs)

            elif entry.is_dir():
                yield DirIndex(entry.path, *self.args, **self.kwargs)

    def __iter__(self):
        return self.items()


class Iter:
    def __init__(self, index: DirIndex) -> None:
        self.index = index
        self.items = index.items()

    @staticmethod
    def from_dir(dir: str) -> Iter:
        return Iter(DirIndex(dir))

    def files(self) -> Iter:
        self.items = (item for item in self.items if isinstance(item, File))
        return self

    def match_exec(self, predicate: Callable, fn: Callable, *args, **kwargs) -> Iter:
        items = []
        
        for item in self.items:
            items.append(item)
            if predicate(item):
                fn(item, *args, **kwargs)

        self.items = items
        return self

    def set_var(self, name: str, value) -> Iter:
        self.index.kwargs[name] = value
        return self


def get_config(dir, root) -> dict:
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
    path = os.path.join(LAYOUT_DIR, name)

    if os.path.isfile(path):
        return FrontMatterFile(path)

    raise Exception("Layout {} does not exist".format(name))


def ext(*args):
    def inner(file) -> bool:
        return isinstance(file, File) and file.ext in args
    
    return inner


def is_dir(obj):
    return isinstance(obj, DirIndex)