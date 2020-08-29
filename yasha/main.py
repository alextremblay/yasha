"""
The MIT License (MIT)

Copyright (c) 2015-2020 Kim Blomqvist
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

from yasha.parsers import PARSERS
from yasha.classes import CLASSES
from yasha.filters import FILTERS
from yasha.tests import TESTS

from pathlib import Path
from typing import List, Union

from typing_extensions import Literal
import jinja2 as j2


class Yasha:
    def __init__(self, 
            root_dir: Path = Path('.'),
            data_files: List[Union[Path,str]] = list(), 
            global_variables = dict(),
            yasha_extensions_file: Union[Path,str] = None, 
            template_lookup_paths: List[Union[Path,str]] = list(), 
            mode: Union[Literal['pedantic'], Literal['debug'], None] = None,
            encoding: str = 'utf-8', 
            **jinja_kwargs):
        """The core component of this software is the Yasha class. 
        When used as a command-line tool, a new instance will be create with each invocation. 
        When used as a library, multiple different instances can be created with different configurations

        Args:
            root_dir (Path, optional): The root directory for all automatic file lookups. Any automatic variable, extension, or template file lookup will iteratively search upwards from the folder containing the template up to this root directory. Defaults to the current working directory.
            data_files (List[Path], optional): [description]. Defaults to list().
            yasha_extension_file (Path, optional): [description]. Defaults to None.
            template_lookup_paths (List[Path], optional): [description]. Defaults to list().
            mode ('pedantic' or 'debug' or None, optional): [description]. Defaults to None.
            encoding (str, optional): [description]. Defaults to 'utf-8'.
        """
        self.root = root_dir
        self.data_files = [Path(f) for f in data_files]
        self.global_variables = global_variables
        self.mode = mode
        self.parsers = PARSERS.copy()
        self.filters = FILTERS.copy()
        self.tests = TESTS.copy()
        self.jinja_extensions = CLASSES.copy()
        self.jinja_kwargs = jinja_kwargs if jinja_kwargs else dict()
        if yasha_extensions_file:
            self._load_extensions_file(Path(yasha_extensions_file))
        self.template_lookup_paths = [Path(p) for p in template_lookup_paths]
        self.encoding = encoding

        self.env = self._setup_jinja_env()


    def _load_data_files(self, files: List[Path]) -> dict:
        "load a list of data files using file parsers from self.parsers, and merge the resulting dicts together"
        data = {}
        for file in files:
            ext = file.suffix
            parser = self.parsers.get(ext)
            if not parser:
                raise Exception(f"No parser found for data file {file}")
            data.update(parser(file))
        return data


    def _load_extensions_file(self, extensions_file: Path):
        "Loads jinja and yasha extensions from a given extension file, and update the jinja environment with those extensions"
        from importlib.util import spec_from_file_location, module_from_spec
        from jinja2.ext import Extension
        # load the module
        filename = extensions_file.stem
        module_name = 'yasha_ext.' + filename
        spec = spec_from_file_location(module_name, extensions_file)
        module = module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore

        for name, value in module.__dict__.items():
            # Skip dunder attributes (ie __file__ or __name__)
            if name.startswith('__'):
                continue

            # Tests
            if name.startswith('test_'):
                name = name[5:]
                self.tests[name] = value
                continue
            if name == 'TESTS':
                self.tests.update(value)
                continue
            
            # Filters
            if name.startswith('filter_'):
                name = name[7:]
                self.filters[name] = value
                continue
            if name == 'FILTERS':
                self.filters.update(value)
                continue
            
            # Parsers
            if name.startswith('parse_'):
                name = name[6:]
                self.parsers['.' + name] = value
                continue
            if name == 'PARSERS':
                self.parsers.update(value)
                continue
            
            # Jinja Extensions
            if isinstance(value, type) and issubclass(value, Extension):
                self.jinja_extensions.append(value)
                continue
            if name == 'CLASSES':
                assert isinstance(value, list), f"The CLASSES variable in {extensions_file} must be a list of jinja extension classes, or strings referencing jinja extension classes"
                self.jinja_extensions.extend(value)
                continue
                
            # Jinja Configuration
            configuration_directives = [
                'BLOCK_START_STRING', 'BLOCK_END_STRING', 'VARIABLE_START_STRING', 
                'VARIABLE_END_STRING', 'COMMENT_START_STRING', 'COMMENT_END_STRING', 
                'LINE_STATEMENT_PREFIX', 'LINE_COMMENT_PREFIX'
            ]
            if name in configuration_directives:
                name = name.lower()
                self.jinja_kwargs[name] = value


    def _setup_jinja_env(self) -> j2.Environment:
        env = j2.Environment(**self.jinja_kwargs)
        env.filters.update(FILTERS)
        if self.mode == 'pedantic': env.undefined = j2.StrictUndefined
        if self.mode == 'debug': env.undefined = j2.DebugUndefined
        env.globals.update(self._load_data_files(self.data_files))  # data from the data files becomes the baseline for jinja global vars
        env.globals.update(self.global_variables) # data from inline variables / directly-specified global variables overrides data from the data files
        env.filters.update(self.filters)
        env.tests.update(self.tests)
        for ext in self.jinja_extensions:
            env.add_extension(ext)
        return env


    def render_template(self, template: Path, find_data_files=True, find_extension_files=True, jinja_env_overrides=dict()):
        """Render a single template

        Args:
            template (Path): The path to the template to render
            find_data_files (bool, optional): 
                Wether or not to automatically load implicit variable file data. 
                See the `Automatic file variables look up` section of the README for details. 
                Defaults to True.
            find_extension_files (bool, optional): 
                Wether or not to automatically load implicit extension files. 
                See the `Template extensions` section of the README for details. 
                Defaults to True.
            jinja_env_overrides (dict, optional): Any Jinja environment configurations to override for this specific template.
        """
        pass

    def generate_makefile_dependencies(self):
        pass
