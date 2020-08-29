"""
The MIT License (MIT)

Copyright (c) 2020 Alex Tremblay

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

from yasha.main import Yasha
from tests.conftest import wrap

from pathlib import Path

def test_datafile_loading(with_tmp_path):
    "Variables in data files should be merged together. conflicting variables in later data files should overwrite those variables from previous data files"
    Path('data.json').write_text('{"key1": "value1","key2": {"subkey1": "value"},"key3": "value"}')
    Path('data.ini').write_text(wrap("""
        [key2]
        subkey2 = value
        """))
    Path('data.toml').write_text(wrap("""
        key3 = "value2"
        key4 = ["value1"]
        """))
    Path('data.yaml').write_text(wrap("""
        key4:
          - value2
        """))
    y = Yasha(data_files=['data.json', 'data.ini', 'data.toml', 'data.yaml'])
    output = y.env.globals
    expected = {'key1': 'value1', 'key2': {'subkey2': 'value'}, 'key3': 'value2', 'key4': ['value2']}
    assert expected.items() <= output.items()  # assert that expected is a subset of output (ie. that all items in in expected are found in output)

def test_inline_variables(with_tmp_path):
    "Variables from the global_variables key should override variables in data files"
    Path('data.json').write_text('{"key1": "value1","key2": {"subkey1": "value"},"key3": "value"}')
    y = Yasha(data_files=['data.json'], global_variables={'key1': 'value2'})
    output = y.env.globals
    expected = {'key1': 'value2', 'key2': {'subkey1': 'value'}, 'key3': 'value'}
    assert expected.items() <= output.items()  # assert that expected is a subset of output (ie. that all items in in expected are found in output)


def test_extension_file(with_tmp_path):
    Path("extension.py").write_text(wrap("""
        def test_divisiblebythree(number):
            return number % 3 == 0
        
        def is_divisible_by_four(number):
            return number % 4 == 0
            
        TESTS = {
            'divisiblebyfour': is_divisible_by_four
        }

        def filter_my_replace(s, old, new):
            return s.replace(old, new)
        
        FILTERS = {
            'split': lambda s: s.split()
        }
        
        import jinja2.ext

        ExprStmtExtension = jinja2.ext.ExprStmtExtension

        CLASSES = [
            'jinja2.ext.InternationalizationExtension'
        ]
        
        def parse_xml(file):
            import xml.etree.ElementTree as et
            assert file.name.endswith('.xml')
            tree = et.parse(file.name)
            root = tree.getroot()
            
            persons = []
            for elem in root.iter('person'):
                persons.append({
                    'name': elem.find('name').text,
                    'address': elem.find('address').text,
                })
                
            return dict(persons=persons)
        
        PARSERS = {
            '.specialxml': parse_xml
        }
            
        BLOCK_START_STRING = '<%'
        BLOCK_END_STRING = '%>'
        VARIABLE_START_STRING = '<<'
        VARIABLE_END_STRING = '>>'
        COMMENT_START_STRING = '<#'
        COMMENT_END_STRING = '#>'
        """))

    y = Yasha(yasha_extensions_file='extension.py')

    assert 'divisiblebythree' in y.env.tests
    assert 'divisiblebyfour' in y.env.tests

    assert 'split' in y.env.filters
    assert 'my_replace' in y.env.filters

    assert 'jinja2.ext.ExprStmtExtension' in y.env.extensions
    assert 'jinja2.ext.InternationalizationExtension' in y.env.extensions

    assert '.specialxml' in y.parsers
    assert y.parsers['.specialxml'] == y.parsers['.xml']

    assert y.env.block_end_string == '%>'
    assert y.env.block_start_string == '<%'
    assert y.env.variable_start_string == '<<'
    assert y.env.variable_end_string == '>>'
    assert y.env.comment_start_string == '<#'
    assert y.env.comment_end_string == '#>'


def test_extension_file_isolation(with_tmp_path):
    Path("tests.py").write_text(wrap("""
        def test_divisiblebythree(number):
            return number % 3 == 0
        
        def is_divisible_by_four(number):
            return number % 4 == 0
            
        TESTS = {
            'divisiblebyfour': is_divisible_by_four
        }
        """))
    Path("filters.py").write_text(wrap("""
        def filter_my_replace(s, old, new):
            return s.replace(old, new)
        
        FILTERS = {
            'split': lambda s: s.split()
        }
        """))
    Path("jinja_ext.py").write_text(wrap("""
        import jinja2.ext

        ExprStmtExtension = jinja2.ext.ExprStmtExtension

        CLASSES = [
            'jinja2.ext.InternationalizationExtension'
        ]
        """))
    Path("parsers.py").write_text(wrap("""
        def parse_xml(file):
            import xml.etree.ElementTree as et
            assert file.name.endswith('.xml')
            tree = et.parse(file.name)
            root = tree.getroot()
            
            persons = []
            for elem in root.iter('person'):
                persons.append({
                    'name': elem.find('name').text,
                    'address': elem.find('address').text,
                })
                
            return dict(persons=persons)
        
        PARSERS = {
            '.specialxml': parse_xml
        }
        """))
    Path("jinja_conf.py").write_text(wrap("""
        BLOCK_START_STRING = '<%'
        BLOCK_END_STRING = '%>'
        VARIABLE_START_STRING = '<<'
        VARIABLE_END_STRING = '>>'
        COMMENT_START_STRING = '<#'
        COMMENT_END_STRING = '#>'
        """))

    y1 = Yasha(yasha_extensions_file='tests.py')
    y2 = Yasha(yasha_extensions_file='filters.py')
    y3 = Yasha(yasha_extensions_file='jinja_ext.py')
    y4 = Yasha(yasha_extensions_file='parsers.py')
    y5 = Yasha(yasha_extensions_file='jinja_conf.py')

    assert 'divisiblebythree' in y1.env.tests
    assert 'divisiblebyfour' in y1.env.tests
    assert 'divisiblebythree' not in y2.env.tests
    assert 'divisiblebyfour' not in y2.env.tests

    assert 'split' in y2.env.filters
    assert 'my_replace' in y2.env.filters
    assert 'split' not in y3.env.filters
    assert 'my_replace' not in y3.env.filters

    assert 'jinja2.ext.ExprStmtExtension' in y3.env.extensions
    assert 'jinja2.ext.InternationalizationExtension' in y3.env.extensions
    assert 'jinja2.ext.ExprStmtExtension' not in y4.env.extensions
    assert 'jinja2.ext.InternationalizationExtension' not in y4.env.extensions

    assert '.specialxml' in y4.parsers
    assert y4.parsers['.specialxml'] == y4.parsers['.xml']
    assert '.specialxml' not in y5.parsers

    assert y4.env.block_end_string != '%>'
    assert y4.env.block_start_string != '<%'
    assert y4.env.variable_start_string != '<<'
    assert y4.env.variable_end_string != '>>'
    assert y4.env.comment_start_string != '<#'
    assert y4.env.comment_end_string != '#>'
    assert y5.env.block_end_string == '%>'
    assert y5.env.block_start_string == '<%'
    assert y5.env.variable_start_string == '<<'
    assert y5.env.variable_end_string == '>>'
    assert y5.env.comment_start_string == '<#'
    assert y5.env.comment_end_string == '#>'