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

from tests.conftest import yasha_cli, wrap

import os
from pathlib import Path

import pytest
from click import ClickException


def test_env(with_tmp_path):
    Path('template.j2').write_text("{{ 'POSTGRES_URL' | env('postgresql://localhost') }}")

    yasha_cli('template.j2')
    
    assert Path('template').read_text() == 'postgresql://localhost'

    os.environ['POSTGRES_URL'] = 'postgresql://127.0.0.1'
    yasha_cli('template.j2')
    assert Path('template').read_text() == 'postgresql://127.0.0.1'



def test_shell(with_tmp_path):
    Path('template.j2').write_text('{{ "uname" | shell }}')
    
    yasha_cli('template.j2')

    assert Path('template').read_text() == os.uname().sysname


def test_subprocess(with_tmp_path):
    Path('template.j2').write_text(wrap("""
        {% set r = "uname" | subprocess %}
        {{ r.stdout.decode() }}"""))

    yasha_cli('template.j2')

    assert Path('template').read_text().strip() == os.uname().sysname


def test_subprocess_with_unknown_cmd(with_tmp_path):
    Path('template.j2').write_text('{{ "unknown_cmd" | subprocess }}')

    with pytest.raises(ClickException) as e:
        yasha_cli('template.j2')

    assert 'command not found' in e.value.message


def test_subprocess_with_unknown_cmd_while_check_is_false(with_tmp_path):
    Path('template.j2').write_text(wrap("""
        {% set r = "unknown_cmd" | subprocess(check=False) %}
        {{ r.returncode > 0 }}"""))

    yasha_cli('template.j2')

    assert Path('template').read_text().strip() == 'True'
