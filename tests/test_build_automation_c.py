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

from sys import stderr, stdout
from yasha.yasha import ENCODING
from yasha.cli import cli
import sys
from subprocess import run, PIPE
from os import path, chdir
from textwrap import dedent

import pytest

SCRIPT_PATH = path.dirname(path.realpath(__file__))

def wrap(text):
    return dedent(text).lstrip()


def yasha_cli(args):
    return cli(args, standalone_mode=False) # pylint: disable=no-value-for-parameter,unexpected-keyword-arg

build_dependencies = (
    'foo.c.jinja',
    'foo.h.jinja',
    'foo.c.py',
    'foo.toml',
    'header.j2inc'
)


@pytest.mark.slowtest
def test_scons():
    # This test is an end-to-end test of the entire SCons build system, including the yasha.scons component we need to test, 
    # and including the entire Clang build toolchain. It should be rewritten to be a unit test of yasha.scons by someone who 
    # knows how to write SCons CBuilder unit tests
    pytest.importorskip("scons", reason="SCons not installed")
    chdir(SCRIPT_PATH + '/fixtures/c_project')
    build_cmd = ('scons', '-Q')

    # First build
    out = run(build_cmd, stdout=PIPE, encoding=ENCODING).stdout
    assert not 'is up to date' in out
    assert path.isfile('build/a.out')

    # Immediate new build shouldn't do anything
    out = run(build_cmd, stdout=PIPE, encoding=ENCODING).stdout
    assert 'is up to date' in out

    # Check program output
    out = run(('./build/a.out'), stdout=PIPE, encoding=ENCODING).stdout
    assert 'bar has 3 chars ...\n' == out

    # FIXME: Sometimes the rebuild happens sometimes not.
    for dep in build_dependencies:
        run(('touch', path.join('src', dep)), stdout=PIPE, encoding=ENCODING)
        out = run(build_cmd, stdout=PIPE, encoding=ENCODING).stdout
        #assert not b'is up to date' in out
        print(out) # For debugging purposes, run 'pytest -s -k scons'
    run(('scons', '-c'))
    run(('scons', '-C', 'src', '-c'))


@pytest.mark.slowtest
def test_scons_without_build_dir():
    # This test is an end-to-end test of the entire SCons build system, including the yasha.scons component we need to test, 
    # and including the entire Clang build toolchain. It should be rewritten to be a unit test of yasha.scons by someone who 
    # knows how to write SCons CBuilder unit tests
    pytest.importorskip("scons", reason="SCons not installed")
    chdir(SCRIPT_PATH + '/fixtures/c_project')
    chdir('src')
    build_cmd = ('scons', '-Q')

    # First build
    out = run(build_cmd, stdout=PIPE, encoding=ENCODING).stdout
    assert not 'is up to date' in out
    assert path.isfile('a.out')

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
    run(('scons', '-c'))
    run(('scons', '-C', 'src', '-c'))  


def test_makefile_dependency_flag_m(tmpdir, capfd):
    template = wrap("""
        {% include "header.j2inc" %}

        void foo() {
            char foo[] = "{{ foo }}";
            printf("%s has %d chars ...\\n", foo, {{ foo|length }});
        }""")

    variables = 'foo = "bar"'
    j2inc = wrap("""
        #include <stdio.h>
        #include "foo.h" """)

    tmpdir.chdir()
    tmpdir.join("foo.toml").write(variables)
    tmpdir.join("foo.c.jinja").write(template)
    tmpdir.join("header.j2inc").write(j2inc)

    yasha_cli(['-M', 'foo.c.jinja'])
    captured_output, _ = capfd.readouterr()
    assert captured_output == 'foo.c: foo.c.jinja foo.toml header.j2inc\n'


def test_makefile_dependency_flag_md(tmpdir):
    template = wrap("""
        {% include "header.j2inc" %}

        void foo() {
            char foo[] = "{{ foo }}";
            printf("%s has %d chars ...\\n", foo, {{ foo|length }});
        }""")

    variables = 'foo = "bar"'
    j2inc = wrap("""
        #include <stdio.h>
        #include "foo.h" """)

    tmpdir.chdir()
    tmpdir.join("foo.toml").write(variables)
    tmpdir.join("foo.c.jinja").write(template)
    tmpdir.join("header.j2inc").write(j2inc)

    yasha_cli(['-MD', 'foo.c.jinja'])
    assert path.isfile("foo.c.d")
    assert tmpdir.join("foo.c.d").read() == 'foo.c: foo.c.jinja foo.toml header.j2inc\n'
    
    assert path.isfile("foo.c")
    assert tmpdir.join("foo.c").read() == wrap("""
        #include <stdio.h>
        #include "foo.h" 
        void foo() {
            char foo[] = "bar";
            printf("%s has %d chars ...\\n", foo, 3);
        }""")