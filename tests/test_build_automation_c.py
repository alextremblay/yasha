"""
The MIT License (MIT)

Copyright (c) 2015-2020 Kim Blomqvist
Portions Copyright (c) 2020 Alex Tremblay

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

from yasha.constants import ENCODING
from tests.conftest import yasha_cli, wrap

from subprocess import run, PIPE
from os import chdir
from pathlib import Path
from shutil import copytree

import pytest


build_dependencies = (
    'foo.c.jinja',
    'foo.h.jinja',
    'foo.c.py',
    'foo.toml',
    'header.j2inc'
)


@pytest.mark.slowtest
def test_scons(with_tmp_path, fixtures_dir):
    # This test is an end-to-end test of the entire SCons build system, including the yasha.scons component we need to test, 
    # and including the entire Clang build toolchain. It should be rewritten to be a unit test of yasha.scons by someone who 
    # knows how to write SCons CBuilder unit tests
    pytest.importorskip("scons", reason="SCons not installed")
    c_project = fixtures_dir / 'c_project'
    copytree(c_project, with_tmp_path)
    build_cmd = ('scons', '-Q')

    # First build
    out = run(build_cmd, stdout=PIPE, encoding=ENCODING).stdout
    assert not 'is up to date' in out
    assert Path('build/a.out').is_file()

    # Immediate new build shouldn't do anything
    out = run(build_cmd, stdout=PIPE, encoding=ENCODING).stdout
    assert 'is up to date' in out

    # Check program output
    out = run(('./build/a.out'), stdout=PIPE, encoding=ENCODING).stdout
    assert 'bar has 3 chars ...\n' == out

    # FIXME: Sometimes the rebuild happens sometimes not.
    for dep in build_dependencies:
        run(('touch', Path('src').joinpath(dep)), stdout=PIPE, encoding=ENCODING)
        out = run(build_cmd, stdout=PIPE, encoding=ENCODING).stdout
        #assert not b'is up to date' in out
        print(out) # For debugging purposes, run 'pytest -s -k scons'


@pytest.mark.slowtest
def test_scons_without_build_dir(with_tmp_path, fixtures_dir):
    # This test is an end-to-end test of the entire SCons build system, including the yasha.scons component we need to test, 
    # and including the entire Clang build toolchain. It should be rewritten to be a unit test of yasha.scons by someone who 
    # knows how to write SCons CBuilder unit tests
    pytest.importorskip("scons", reason="SCons not installed")
    c_project = fixtures_dir / 'c_project'
    copytree(c_project, with_tmp_path)
    chdir('src')
    build_cmd = ('scons', '-Q')

    # First build
    out = run(build_cmd, stdout=PIPE, encoding=ENCODING).stdout
    assert not 'is up to date' in out
    assert Path('a.out').is_file()

    # Immediate new build shouldn't do anything
    out = run(build_cmd, stdout=PIPE, encoding=ENCODING).stdout
    assert 'is up to date' in out

    # Check program output
    out = run(('./a.out'), stdout=PIPE, encoding=ENCODING).stdout
    assert 'bar has 3 chars ...\n' == out

    # FIXME: Sometimes the rebuild happens sometimes not.
    for dep in build_dependencies:
        run(('touch', dep))
        out = run(build_cmd, stdout=PIPE, encoding=ENCODING).stdout
        #assert not b'is up to date' in out
        print(out) # for debugging, run 'pytest -s -k scons'


def test_makefile_dependency_flag_m(with_tmp_path, capfd):
    Path('foo.json').write_text('{"foo": "bar"}')
    Path("foo.c.jinja").write_text(wrap("""
        {% include "header.j2inc" %}

        void foo() {
            char foo[] = "{{ foo }}";
            printf("%s has %d chars ...\\n", foo, {{ foo|length }});
        }"""))
    Path("header.j2inc").write_text(wrap("""
        #include <stdio.h>
        #include "foo.h" """))

    yasha_cli(['-M', 'foo.c.jinja'])
    captured_output, _ = capfd.readouterr()
    assert captured_output == 'foo.c: foo.c.jinja foo.json header.j2inc\n'


def test_makefile_dependency_flag_md(with_tmp_path):
    Path('foo.json').write_text('{"foo": "bar"}')
    Path("foo.c.jinja").write_text(wrap("""
        {% include "header.j2inc" %}

        void foo() {
            char foo[] = "{{ foo }}";
            printf("%s has %d chars ...\\n", foo, {{ foo|length }});
        }"""))
    Path("header.j2inc").write_text(wrap("""
        #include <stdio.h>
        #include "foo.h" """))

    yasha_cli(['-MD', 'foo.c.jinja'])
    assert Path("foo.c.d").is_file()
    assert Path("foo.c.d").read_text() == 'foo.c: foo.c.jinja foo.json header.j2inc\n'
    
    assert Path("foo.c")
    assert Path("foo.c").read_text() == wrap("""
        #include <stdio.h>
        #include "foo.h" 
        void foo() {
            char foo[] = "bar";
            printf("%s has %d chars ...\\n", foo, 3);
        }""")