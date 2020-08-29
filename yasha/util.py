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

import os
from pathlib import Path

import jinja2 as jinja
from .tests import TESTS
from .filters import FILTERS
from .classes import CLASSES
from .parsers import PARSERS
from click import ClickException

def find_template_companion(template, extension='', check=True):
    """
    Returns the first found template companion file
    """

    if check and not os.path.isfile(template):
        yield ''
        return # May be '<stdin>' (click)

    template = os.path.abspath(template)
    template_dirname = os.path.dirname(template)
    template_basename = os.path.basename(template).split('.')

    current_path = template_dirname
    stop_path = os.path.commonprefix((os.getcwd(), current_path))
    stop_path = os.path.dirname(stop_path)

    token = template_basename[0] + '.'

    while True:

        for file in sorted(os.listdir(current_path)):
            if not file.startswith(token):
                continue
            if not file.endswith(extension):
                continue

            file_parts = file.split('.')
            for i in range(1, len(template_basename)):
                if template_basename[:-i] != file_parts[:-1]:
                    continue
                if current_path == template_dirname:
                    if file_parts == template_basename:
                        continue # Do not accept template itself

                yield os.path.join(current_path, file)

        if current_path == stop_path:
            break

        # cd ..
        current_path = os.path.split(current_path)[0]


def find_referenced_templates(template, search_path):
    """
    Returns a list of files which can be either {% imported %},
    {% extended %} or {% included %} within a template.
    """
    from jinja2 import Environment, meta
    env = Environment()
    ast = env.parse(template.read())
    referenced_templates = list(meta.find_referenced_templates(ast))

    def realpath(tpl):
        for path in search_path:
            t = os.path.realpath(os.path.join(path, tpl))
            if os.path.isfile(t):
                return t
        return None

    return [realpath(t) for t in referenced_templates if t is not None]


def load_jinja(
        path, tests, filters, classes, mode,
        trim_blocks, lstrip_blocks, keep_trailing_newline):
    from jinja2.defaults import BLOCK_START_STRING, BLOCK_END_STRING, \
        VARIABLE_START_STRING, VARIABLE_END_STRING, \
        COMMENT_START_STRING, COMMENT_END_STRING, \
        LINE_STATEMENT_PREFIX, LINE_COMMENT_PREFIX, \
        NEWLINE_SEQUENCE

    undefined = {
        'pedantic': jinja.StrictUndefined,
        'debug': jinja.DebugUndefined,
        None: jinja.Undefined,
    }

    env = jinja.Environment(
        block_start_string=BLOCK_START_STRING,
        block_end_string=BLOCK_END_STRING,
        variable_start_string=VARIABLE_START_STRING,
        variable_end_string=VARIABLE_END_STRING,
        comment_start_string=COMMENT_START_STRING,
        comment_end_string=COMMENT_END_STRING,
        line_statement_prefix=LINE_STATEMENT_PREFIX,
        line_comment_prefix=LINE_COMMENT_PREFIX,
        trim_blocks=trim_blocks,
        lstrip_blocks=lstrip_blocks,
        newline_sequence=NEWLINE_SEQUENCE,
        keep_trailing_newline=keep_trailing_newline,
        extensions=classes,
        undefined=undefined[mode],
        loader=jinja.FileSystemLoader(path)
    )
    env.tests.update(tests)
    env.filters.update(filters)
    return env


def parse_variable_file(file: Path):
    try:
        file_extension = file.suffix
        return PARSERS[file_extension](file)
    except AttributeError:
        return dict()
    except KeyError:
        error = "Unkown variable file extension '{}'"
        raise ClickException(error.format(file_extension))

def load_python_module(file):
    try:
        from importlib.machinery import SourceFileLoader
        loader = SourceFileLoader('yasha_extensions', file.name)
        module = loader.load_module()
    except ImportError:  # Fallback to Python2
        import imp
        with open(file.name) as f:
            desc = (".py", "rb", imp.PY_SOURCE)
            module = imp.load_module('yasha_extensions', f, file.name, desc)
        pass
    return module

def load_extensions(file):
    from jinja2.ext import Extension
    import inspect

    tests   = dict()
    filters = dict()
    parsers = dict()
    classes = []

    try:
        module = load_python_module(file)
    except NameError as e:
        msg = 'Unable to load extensions, {}'
        raise ClickException(msg.format(e))
    except SyntaxError as e:
        msg = "Unable to load extensions\n{} ({}, line {})"
        error = e.msg[0].upper() + e.msg[1:]
        filename = os.path.relpath(e.filename)
        raise ClickException(msg.format(error, filename, e.lineno))

    for attr in [getattr(module, x) for x in dir(module)]:
        if inspect.isfunction(attr):
            if attr.__name__.startswith('test_'):
                name = attr.__name__[5:]
                tests[name] = attr
            if attr.__name__.startswith('filter_'):
                name = attr.__name__[7:]
                filters[name] = attr
            if attr.__name__.startswith('parse_'):
                name = attr.__name__[6:]
                parsers['.' + name] = attr
        if inspect.isclass(attr):
            if issubclass(attr, Extension):
                classes.append(attr)

    import jinja2.defaults
    for name, obj in inspect.getmembers(module):
        if name in tuple(x for x in dir(jinja2.defaults) if x.isupper()):
            setattr(jinja2.defaults, name, obj)

    try:
        TESTS.update(module.TESTS)
    except AttributeError:
        TESTS.update(tests)

    try:
        FILTERS.update(module.FILTERS)
    except AttributeError:
        FILTERS.update(filters)

    try:
        PARSERS.update(module.PARSERS)
    except AttributeError:
        PARSERS.update(parsers)

    try:
        CLASSES.extend(module.CLASSES)
    except AttributeError:
        CLASSES.extend(classes)
