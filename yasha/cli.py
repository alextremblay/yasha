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

import os
import encodings
import ast
import csv
from pathlib import Path

import click
from click import ClickException
from jinja2.exceptions import UndefinedError as JinjaUndefinedError

from yasha import __version__, util, constants
from yasha.tests import TESTS
from yasha.filters import FILTERS
from yasha.classes import CLASSES
from yasha.parsers import PARSERS

def print_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    click.echo(__version__)
    ctx.exit()


def parse_cli_variables(args):
    variables = dict()
    for i, arg in enumerate(args):
        if arg[:2] != '--':
            continue
        if '=' in arg:
            opt, val = arg[2:].split('=', 1)
        else:
            try:
                if args[i+1] != '--':
                    opt = arg[2:]
                    val = args[i+1]
            except IndexError:
                break
        try:
            val = ast.literal_eval(val)
        except ValueError:
            pass
        except SyntaxError:
            pass
        if isinstance(val, str):
            # Convert foo,bar,baz to list ['foo', 'bar', 'baz'] and
            # '"foo,bar,baz"' to string 'foo,bar,baz'
            reader = csv.reader([val], delimiter=',', quotechar='"')
            val = list(reader)[0]
            if len(val) == 1:
                val = val[0]
        variables[opt] = val
    return variables


@click.command(context_settings=dict(
    help_option_names=["-h", "--help"],
    ignore_unknown_options=True,
))
@click.argument("template_variables", nargs=-1, type=click.UNPROCESSED)
@click.argument("template", type=click.File("rb"))
@click.option("--output", "-o", type=click.File("wb"), help="Place the rendered template into FILENAME.")
@click.option("--variables", "-v", type=click.Path(exists=True, dir_okay=False, path_type=str), multiple=True, help="Read template variables from FILENAME. Built-in parsers are JSON, YAML, TOML and XML.")
@click.option("--extensions", "-e", envvar='YASHA_EXTENSIONS', type=click.File("rb"), help="Read template extensions from FILENAME. A Python file is expected.")
@click.option("--encoding", "-c", default=constants.ENCODING, help="Default is UTF-8.")
@click.option("--include_path", "-I", type=click.Path(exists=True, file_okay=False), multiple=True, help="Add DIRECTORY to the list of directories to be searched for the referenced templates.")
@click.option("--no-variable-file", is_flag=True, help="Omit template variable file.")
@click.option("--no-extension-file", is_flag=True, help="Omit template extension file.")
@click.option("--no-trim-blocks", is_flag=True, help="Load Jinja with trim_blocks=False.")
@click.option("--no-lstrip-blocks", is_flag=True, help="Load Jinja with lstrip_blocks=False.")
@click.option("--keep-trailing-newline", is_flag=True, help="Load Jinja with keep_trailing_newline=True.")
@click.option("--mode", type=click.Choice(['pedantic', 'debug']), help="In pedantic mode Yasha becomes extremely picky on templates, e.g. undefined variables will raise an error. In debug mode undefined variables will print as is.")
@click.option("-M", is_flag=True, help="Outputs Makefile compatible list of dependencies. Doesn't render the template.")
@click.option("-MD", is_flag=True, help="Creates Makefile compatible .d file alongside the rendered template.")
@click.option('--version', is_flag=True, callback=print_version, expose_value=False, is_eager=True, help="Print version and exit.")
def cli(
        template_variables, template, output, variables, extensions,
        encoding, include_path, no_variable_file, no_extension_file,
        no_trim_blocks, no_lstrip_blocks, keep_trailing_newline,
        mode, m, md):
    """Reads the given Jinja TEMPLATE and renders its content
    into a new file. For example, a template called 'foo.c.j2'
    will be written into 'foo.c' in case the output file is not
    explicitly given.

    Template variables can be defined in a separate file or
    given as part of the command-line call, e.g.

        yasha --hello=world -o output.txt template.j2

    defines a variable 'hello' for a template like:

        Hello {{ hello }} !
    """

    # Set the encoding of the template file
    if encodings.search_function(encoding) is None:
        msg = "Unrecognized encoding name '{}'"
        raise ClickException(msg.format(encoding))
    constants.ENCODING = encoding

    # Append include path of referenced templates
    include_path = [os.path.dirname(template.name)] + list(include_path)

    if not extensions or not variables:
        template_companion = util.find_template_companion(template.name)
        template_companion = list(template_companion)

    if not extensions and not no_extension_file:
        for file in template_companion:
            if file.endswith(constants.EXTENSION_FILE_FORMATS):
                extensions = click.open_file(file, "rb")
                break

    if extensions:
        util.load_extensions(extensions)

    if not variables and not no_variable_file:
        for file in template_companion:
            if file.endswith(tuple(PARSERS.keys())):
                variables = (file,)
                break

    if not output:
        if template.name == "<stdin>":
            output = click.open_file("-", "wb")
        else:
            output = os.path.splitext(template.name)[0]
            output = click.open_file(output, "wb", lazy=True)

    if m or md:
        deps = [os.path.relpath(template.name)]
        for file in variables:
            deps.append(os.path.relpath(file))
        if extensions:
            deps.append(os.path.relpath(extensions.name))
        for d in util.find_referenced_templates(template, include_path):
            deps.append(os.path.relpath(d))

        deps = os.path.relpath(output.name) + ": " + " ".join(deps)
        if m:
            click.echo(deps)
            return  # Template won't be rendered
        if md:
            deps += os.linesep
            output_d = click.open_file(output.name + ".d", "wb")
            output_d.write(deps.encode(constants.ENCODING))

    # Load Jinja
    jinja = util.load_jinja(
        path=include_path,
        tests=TESTS,
        filters=FILTERS,
        classes=CLASSES,
        mode=mode,
        trim_blocks=not no_trim_blocks,
        lstrip_blocks=not no_lstrip_blocks,
        keep_trailing_newline=keep_trailing_newline
   )

    # Get template
    if template.name == "<stdin>":
        stdin = template.read()
        t = jinja.from_string(stdin.decode(constants.ENCODING))
    else:
        t = jinja.get_template(os.path.basename(template.name))

    # Parse variables
    context = dict()
    for file in variables:
        context.update(util.parse_variable_file(Path(file)))
    context.update(parse_cli_variables(template_variables))

    # Finally render template and save it
    try:
        t_stream = t.stream(context)
        t_stream.enable_buffering(size=5)
        t_stream.dump(output, encoding=constants.ENCODING)
    except JinjaUndefinedError as e:
        raise ClickException("Variable {}".format(e))
