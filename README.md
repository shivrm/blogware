# Blogware

Blogware is a Python library that provides hackable primitives for building static sites.

To use it, just copy `blogware.py` to your project folder.

Feel free to suggest a feature.

License: MIT

## Example:

Recursively copies all files with `.md` extension from `/content` to `/public`.

```py
import shutil, blogware as bw

INPUT_DIR = '/content'
OUTPUT_DIR = '/public'

def copy_file(file: bw.File):
    copy_path = file.path.swap_root(INPUT_DIR, OUTPUT_DIR)
    shutil.copyfile(file.path, copy_path)

def build_dir(dir: bw.DirIndex):
    (bw.Iter(dir)
        .match_exec(bw.ext('.md'), copy_file)
        # Repeat for child directories
        .match_exec(bw.is_dir, build_dir)
    )

build_dir(bw.DirIndex(INPUT_DIR))
```