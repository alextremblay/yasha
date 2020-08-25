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

from _pytest.outcomes import importorskip
from tests.conftest import with_tmp_path, yasha_cli, wrap

from pathlib import Path

import pytest



def test_string(with_tmp_path):
    Path('template.j2').write_text("{{ var is string }}, {{ var }}")

    yasha_cli('--var=foo template.j2')
    
    assert Path('template').read_text() == 'True, foo'

    yasha_cli("--var='foo' template.j2")
    
    assert Path('template').read_text() == 'True, foo'


def test_boolean(with_tmp_path):
    Path('template.j2').write_text("{{ var is sameas false }}, {{ var }}")

    yasha_cli('--var=False template.j2')
    
    assert Path('template').read_text() == 'True, False'


def test_number(with_tmp_path):
    Path('template.j2').write_text("{{ var is number }}, {{ var + 1 }}")

    yasha_cli('--var=1 template.j2')
    
    assert Path('template').read_text() == 'True, 2'


def test_list(with_tmp_path):
    Path('template.j2').write_text("{{ var is sequence }}, {{ var | join }}")

    yasha_cli("--var=['foo','bar','baz'] template.j2")
    
    assert Path('template').read_text() == 'True, foobarbaz'


def test_tuple(with_tmp_path):
    Path('template.j2').write_text("{{ var is sequence }}, {{ var | join }}")

    yasha_cli("--var=('foo','bar','baz') template.j2")
    
    assert Path('template').read_text() == 'True, foobarbaz'


def test_comma_separated_list(with_tmp_path):
    Path('template.j2').write_text("{{ var is sequence }}, {{ var | join }}")

    yasha_cli("--var=foo,bar,baz template.j2")
    
    assert Path('template').read_text() == 'True, foobarbaz'


def test_dictionary(with_tmp_path):
    Path('template.j2').write_text("{{ var is mapping }}, {% for k in 'abc' %}{{ var[k] }}{% endfor %}")

    yasha_cli("--var={'a':1,'b':2,'c':3} template.j2")
    
    assert Path('template').read_text() == 'True, 123'


def test_commas_in_quoted_string(with_tmp_path):
    """ gh-57 """
    Path('template.j2').write_text("{{ var is string }}, {{ var }}")

    yasha_cli("""--var='"foo,bar,baz"' template.j2""")
    
    assert Path('template').read_text() == 'True, foo,bar,baz'


def test_quoted_comma_in_comma_separated_list(with_tmp_path):
    """ gh-57 """
    Path('template.j2').write_text('{{ lst is sequence }}, {{ lst | join(".") }}')

    yasha_cli("""--lst='"foo,bar",baz' template.j2""")
    
    assert Path('template').read_text() == 'True, foo,bar.baz'
