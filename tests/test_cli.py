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

from tests.conftest import yasha_cli, wrap
from yasha.cli import cli

from subprocess import run, PIPE
from pathlib import Path
from typing import List

import pytest
from click.testing import CliRunner
from click.exceptions import ClickException


@pytest.fixture(params=('json', 'yaml', 'yml', 'toml', 'ini', 'csv', 'csv_with_header'))
def testdata(request):
    templates = dict(
        default=wrap("""
            {% for item in list_data %}
            "{{ item.key1 }}"=>{{ item.key2 }}
            {% endfor %}
            {{ a_variable }}
            {{ a.nested.variable }}"""),
        # Ini files don't support the kinds of arbitrarily nested data structures found in the default template,
        # so they can only be tested with a template which uses data structured in ini-format (ie a dict (the ini file)
        # of dicts(the sections of the ini file) of keys (whose values can be None or strings)
        ini=wrap("""
            Section One, variable one: {{ section_one.variable_one }}
            {{ section_two.key }}"""),
        # CSV files don't support the kinds of arbitrarily nested data structures found in the default template,
        # so they can only be tested with a template which uses data structured in csv-format
        # ie. a list of dicts if the csv file has a header row, a list of lists if it doesn't
        csv=wrap("""
            {% for row in data %}
            cell 1 is {{ row[0] }}, cell 2 is {{ row[1] }}
            {% endfor %}"""),
        csv_with_header=wrap("""
            {% for row in data %}
            cell 1 is {{ row.first_column }}, cell 2 is {{ row['second column'] }}
            {% endfor %}""")
    )
    output = dict(
        default=wrap("""
            "some value"=>key2 value
            "another value"=>another key2 value
            a variable value
            a nested value"""),
        ini=wrap("""
            Section One, variable one: S1 V1 value
            S2 key value"""),
        csv=wrap("""
            cell 1 is value1, cell 2 is 2
            cell 1 is value3, cell 2 is 4
            cell 1 is value5, cell 2 is 6
            cell 1 is value7, cell 2 is 8
            cell 1 is value9, cell 2 is 10
            """)
    )
    data = dict(
        # Each entry is a list of strings [template, expected_output, data, extension]
        json=[
            templates['default'],
            output['default'],
            wrap("""
                {
                    "list_data": [
                        {
                            "key1": "some value",
                            "key2": "key2 value"
                        },
                        {
                            "key1": "another value",
                            "key2": "another key2 value"
                        }
                    ],
                    "a_variable": "a variable value",
                    "a": {
                        "nested": {
                            "variable": "a nested value"
                        }
                    }
                }"""),
            'json'
        ],
        yaml=[
            templates['default'],
            output['default'],
            wrap("""
                list_data:
                  - key1: some value
                    key2: key2 value
                  - key1: another value
                    key2: another key2 value
                a_variable: a variable value
                a:
                  nested:
                    variable: a nested value
                """),
            'yaml'
        ],
        toml=[
            templates['default'],
            output['default'],
            wrap("""
                a_variable = "a variable value"
                [[list_data]]
                key1 = "some value"
                key2 = "key2 value"
                [[list_data]]
                key1 = "another value"
                key2 = "another key2 value"
                [a.nested]
                variable = "a nested value"
                """),
            'toml'
        ],
        ini=[
            templates['ini'],
            output['ini'],
            wrap("""
                [section_one]
                variable_one = S1 V1 value
                [section_two]
                key = S2 key value
                """),
            'ini'
        ],
        csv=[
            templates['csv'],
            output['csv'],
            wrap("""
                value1,2
                value3,4
                value5,6
                value7,8
                value9,10"""),
            'csv'
        ],
        csv_with_header=[
            templates['csv_with_header'],
            output['csv'],
            wrap("""
                first_column,second column
                value1,2
                value3,4
                value5,6
                value7,8
                value9,10"""),
            'csv'
        ]
    )
    data['yml'] = data['yaml']
    data['yml'][3] = 'yml'
    fmt = request.param
    return data[fmt]


def test_cli_direct(with_tmp_path):
    "minimally test the yasha cli when imported and called as a function"
    Path('data.json').write_text('{"foo": "bar"}')
    Path('template.j2').write_text('The value of foo is {{ foo }}.')

    yasha_cli('-v data.json template.j2')
    
    output = Path('template')
    assert output.is_file()
    assert output.read_text() == 'The value of foo is bar.'


def test_cli_runner(with_tmp_path):
    "minimally test the yasha cli when imported and called with click.testing.CliRunner"
    Path('data.json').write_text('{"foo": "bar"}')
    Path('template.j2').write_text('The value of foo is {{ foo }}.')

    result = CliRunner().invoke(cli, '-v data.json template.j2')
    assert result.exit_code == 0
    
    output = Path('template')
    assert output.is_file()
    assert output.read_text() == 'The value of foo is bar.'


def test_cli_entrypoint(with_tmp_path):
    "minimally test the yasha cli when called as a command-line binary"
    Path('data.json').write_text('{"foo": "bar"}')
    Path('template.j2').write_text('The value of foo is {{ foo }}.')

    run('yasha -v data.json template.j2', shell=True, stdout=PIPE, stderr=PIPE)
    
    output = Path('template')
    assert output.is_file()
    assert output.read_text() == 'The value of foo is bar.'


def test_explicit_variable_file(testdata: List[str], with_tmp_path):
    template, expected_output, data, extension = testdata
    Path(f'data.{extension}').write_text(data)
    Path('template.j2').write_text(template)

    yasha_cli(f'-v data.{extension} template.j2')
    
    output = Path('template')
    assert output.is_file()
    assert output.read_text() == expected_output


def test_two_explicitly_given_variables_files(with_tmp_path):
    # Template to calculate a + b + c:
    Path('template.j2').write_text('{{ a + b + c }}')

    # First variable file defines a & b:
    Path('a.yaml').write_text('a: 1\nb: 100')

    # Second variable file redefines b & defines c:
    Path('b.toml').write_text('b = 2\nc = 3')

    yasha_cli('-v a.yaml -v b.toml template.j2')

    output = Path('template')
    assert output.is_file()
    assert output.read_text() == '6'  # a + b + c = 1 + 2 + 3 = 6


def test_variable_file_lookup(with_tmp_path):
    # /cwd
    #   /sub
    #     foo.c.j2
    Path('sub').mkdir()
    Path('sub/foo.c.j2').write_text('int x = {{ int }};')

    # /cwd
    #   /sub
    #     foo.c.j2
    #     foo.c.json    int = 2
    #     foo.json      int = 1
    #   foo.json        int = 0
    for i, varfile in enumerate(('foo', 'sub/foo', 'sub/foo.c')):
        Path(f'{varfile}.json').write_text(f'{{"int": {i}}}')

        yasha_cli('sub/foo.c.j2')

        output = Path('sub/foo.c')
        assert output.is_file()
        assert output.read_text() == f'int x = {i};'


def test_custom_xmlparser(with_tmp_path):
    Path('foo.toml.jinja').write_text(wrap("""
        {% for p in persons %}
        [[persons]]
        name = "{{ p.name }}"
        address = "{{ p.address }}"
        {% endfor %}"""))
    Path('foo.xml').write_text(wrap("""
        <persons>
            <person>
                <name>Foo</name>"
                <address>Foo Valley</address>
            </person>
            <person>
                <name>Bar</name>
                <address>Bar Valley</address>
            </person>
        </persons>
        """))
    Path('foo.j2ext').write_text(wrap("""
        def parse_xml(file):
            import xml.etree.ElementTree as et
            tree = et.parse(file.name)
            root = tree.getroot()
            variables = {"persons": []}
            for elem in root.iter("person"):
                variables["persons"].append({
                    "name": elem.find("name").text,
                    "address": elem.find("address").text,
                })
            return variables
            """))

    yasha_cli('foo.toml.jinja')

    output = Path('foo.toml')
    assert output.is_file()
    assert output.read_text() == wrap("""
        [[persons]]
        name = "Foo"
        address = "Foo Valley"
        [[persons]]
        name = "Bar"
        address = "Bar Valley"\n""")


def test_extensions(with_tmp_path):
    Path("foo.j2").write_text("The value of foo is {{ foo | filterfoo }}")
    Path('foo.json').write_text('{"foo": "bar"}')
    Path("foo.j2ext").write_text(wrap("""
        FILTERS = {
            'filterfoo': lambda s: s.upper()
        }"""))

    yasha_cli('foo.j2')
    output = Path('foo')
    assert output.is_file()
    assert output.read_text() == "The value of foo is BAR"


def test_broken_extensions_syntaxerror(with_tmp_path):
    Path("foo.j2").write_text("")
    Path("foo.j2ext").write_text(wrap("""
        def foo()
        return 'foo'"""))

    with pytest.raises(ClickException) as exc_info:
        yasha_cli('foo.j2')

    assert exc_info.value.exit_code == 1
    assert "Unable to load extensions\nInvalid syntax (foo.j2ext, line 1)" in exc_info.value.message


def test_broken_extensions_nameerror(with_tmp_path):
    Path("foo.j2").write_text("")
    Path("foo.j2ext").write_text(wrap("""
        print(asd)"""))

    with pytest.raises(ClickException) as exc_info:
        yasha_cli('foo.j2')

    assert exc_info.value.exit_code == 1
    assert "Unable to load extensions, name 'asd' is not defined" in exc_info.value.message


def test_render_template_from_stdin_to_stdout():
    out = run('yasha --foo=bar -', shell=True, input=b'{{ foo }}', stdout=PIPE).stdout
    assert out == b'bar'


def test_json_template(with_tmp_path, capfd):
    """gh-34, and gh-35"""

    Path('template.json').write_text('{"foo": {{\'"%s"\'|format(bar)}}}')

    yasha_cli('--bar=baz -o- template.json')
    out, _ = capfd.readouterr()
    assert out == '{"foo": "baz"}'


def test_undefined_var_when_mode_is_none(with_tmp_path):
    """gh-42, and gh-44"""
    Path('template.j2').write_text('The value of foo is {{ foo }}.')

    yasha_cli(['template.j2'])
    
    output = Path('template')
    assert output.is_file()
    assert output.read_text() == 'The value of foo is .'


def test_undefined_var_when_mode_is_pedantic(with_tmp_path):
    """gh-42, and gh-48"""
    Path('template.j2').write_text('The value of foo is {{ foo }}.')

    with pytest.raises(ClickException) as exc_info:
        yasha_cli('--mode=pedantic template.j2')
    
    assert exc_info.value.message == "Variable 'foo' is undefined"


def test_undefined_var_when_mode_is_debug(with_tmp_path):
    """gh-44"""
    Path('template.j2').write_text('The value of foo is {{ foo }}.')

    yasha_cli('--mode=debug template.j2')
    
    output = Path('template')
    assert output.is_file()
    assert output.read_text() == 'The value of foo is {{ foo }}.'


def test_template_syntax_for_latex(with_tmp_path):
    """gh-43"""
    Path('template.tex').write_text(wrap(r"""
        \begin{itemize}
        <% for x in range(0, 3) %>
            \item Counting: << x >>
        <% endfor %>
        \end{itemize}
        """))

    Path('extensions.py').write_text(wrap("""
        BLOCK_START_STRING = '<%'
        BLOCK_END_STRING = '%>'
        VARIABLE_START_STRING = '<<'
        VARIABLE_END_STRING = '>>'
        COMMENT_START_STRING = '<#'
        COMMENT_END_STRING = '#>'
        """))

    expected_output = wrap(r"""
        \begin{itemize}
            \item Counting: 0
            \item Counting: 1
            \item Counting: 2
        \end{itemize}
        """)

    # This test needs to run in a subprocess until the following issue is fixed:
    # https://github.com/kblomqvist/yasha/issues/67
    out = run('yasha --keep-trailing-newline -e extensions.py -o- template.tex', shell=True, stdout=PIPE).stdout
    assert out.decode() == expected_output


def test_extensions_file_with_do(with_tmp_path):
    """gh-52"""
    Path('extensions.py').write_text('from jinja2.ext import do')
    Path('template.j2').write_text(r'{% set list = [1, 2, 3] %}{% do list.append(4) %}{{ list }}')

    run('yasha -e extensions.py template.j2', shell=True)

    output = Path('template')
    assert output.is_file()
    assert output.read_text() == '[1, 2, 3, 4]'
