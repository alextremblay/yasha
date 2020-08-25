"""
The MIT License (MIT)

Copyright (c) 2015-2020 Kim Blomqvist

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

from yasha.cli import cli

from os import chdir, getcwd
from pathlib import Path
from textwrap import dedent

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(f'{__file__}/../fixtures').resolve()

@pytest.fixture
def with_tmp_path(tmp_path: Path):
    """This fixture temporarily sets the current working directory to a new tmp directory for the duration of the test using the fixture.
    After the test is complete, the previous working directory is restored"""
    current_dir = getcwd()
    try:
        chdir(tmp_path)
        yield tmp_path  # with statement block runs here
    finally:
        chdir(current_dir)


def wrap(text):
    return dedent(text).lstrip()


def yasha_cli(args):
    if isinstance(args, str):
        args = args.split()
    return cli(args, standalone_mode=False) # pylint: disable=no-value-for-parameter,unexpected-keyword-arg