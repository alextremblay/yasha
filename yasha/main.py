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
from yasha.constants import EXTENSION_FILE_FORMATS, ENCODING

from pathlib import Path
from typing import BinaryIO, Callable, Dict, List, Union, Iterable, Set
from copy import deepcopy

from typing_extensions import Literal
from jinja2.environment import Environment, TemplateStream
from jinja2.loaders import FileSystemLoader
from jinja2.meta import find_referenced_templates
from jinja2 import StrictUndefined, DebugUndefined


def find_template_companion_files(template: Path, extensions: Iterable[str], recurse_up_to: Path = None) -> Set[Path]:
    """for a given template and list of extensions, find every file related to that template which has one of the extensions.

    Args:
        template (Path): the path to the template file
        extensions (List[str]): list of extensions to look for
        recurse_up_to (Path, optional): 
            Optional parent directory. If provided, will recursively search for companion files 
            in all parent directories up to this one. Defaults to None.
    
    Examples:
        `_find_template_companion_files(template=Path('/etc/test/nested/path/template.sh.j2'), extensions=['.json','.yaml','.xml'])` 
        will look for the following files and return a list of the ones it finds:
            Path('/etc/test/nested/path/template.sh.json')
            Path('/etc/test/nested/path/template.sh.yaml')
            Path('/etc/test/nested/path/template.sh.xml')
            Path('/etc/test/nested/path/template.json')
            Path('/etc/test/nested/path/template.yaml')
            Path('/etc/test/nested/path/template.xml')
        `_find_template_companion_files(template=Path('/etc/test/nested/path/template.j2'), extensions=['.json','.yaml'], recurse_up_to=Path('/etc/test/'))` 
        will look for the following files and return a list of the ones it finds:
            Path('/etc/test/nested/path/template.json')
            Path('/etc/test/nested/path/template.yaml')
            Path('/etc/test/nested/template.json')
            Path('/etc/test/nested/template.yaml')
            Path('/etc/test/template.json')
            Path('/etc/test/template.yaml')
    """
    files_to_check = []

    # Get a list of all file names to look for in each folder
    data_file_names = []
    basename = template.name.split('.')[0]
    for i in range(len(template.suffixes)):
        ext = ''.join(template.suffixes[:i+1])
        for data_file_ext in extensions:
            data_file_names.append(Path(basename + ext).with_suffix(data_file_ext))

    # Look for those files in the template's current folder (a.k.a. parent directory)
    files_to_check.extend([template.parent / file_name for file_name in data_file_names])

    if recurse_up_to and recurse_up_to in template.parents:
        # Look for those files in every parent directory up to `recurse_up_to`, 
        # excluding the template's parent directory which has already been checked
        relative_path = template.parent.relative_to(recurse_up_to)
        for folder in relative_path.parents:
            for file in data_file_names:
                files_to_check.append(recurse_up_to / folder / file)
    return set([file for file in files_to_check if file.is_file()])


class Yasha:
    def __init__(self, 
            root_dir: Path = Path('.'),
            variable_files: List[Union[Path,str]] = list(), 
            inline_variables = dict(),
            yasha_extensions_files: List[Union[Path,str]] = list(), 
            template_lookup_paths: List[Union[Path,str]] = list(), 
            mode: Union[Literal['pedantic'], Literal['debug'], None] = None,
            encoding: str = ENCODING, 
            **jinja_configs):
        """The core component of this software is the Yasha class. 
        When used as a command-line tool, a new instance will be create with each invocation. 
        When used as a library, multiple different instances can be created with different configurations

        Args:
            root_dir (Path, optional): 
                The root directory for all automatic file lookups. Any automatic variable, extension, or 
                template file lookup will iteratively search upwards from the folder containing the 
                template up to this root directory. Defaults to the current working directory.
            variable_files (List[Union[Path,str]], optional): 
                List of data files to parse and load into the global context for templates
            inline_variables (dict, optional): 
                Dictionary of variables to merge into the global context for templates.
                Variables declared here override conflicting variables found in the data files.
            yasha_extensions_files (List[Union[Path,str]], optional): 
                List of files to load yasha extensions from.
            template_lookup_paths (List[Union[Path,str]], optional): 
                List of paths to add to jinja's template loader, for `include` and `extends` directives and such.
            mode (Union[Literal[, optional): Whether to run jinja in pedantic or debug mode. Defaults to None.
            encoding (str, optional): file encoding to use for all file operations. Defaults to 'utf-8'.
            **jinja_configs: any additional keyword arguments with be passed to the constructor of the jinja environment at the core of this class
        """
        self.root = root_dir
        self.parsers = PARSERS.copy()
        self.template_lookup_paths = [Path(p) for p in template_lookup_paths]
        self.yasha_extensions_files = [Path(p) for p in yasha_extensions_files]
        self.variable_files = [Path(f) for f in variable_files]
        self.encoding = encoding
        self.env = Environment()
        if mode == 'pedantic': self.env.undefined = StrictUndefined
        if mode == 'debug': self.env.undefined = DebugUndefined
        self.env.filters.update(FILTERS)
        self.env.tests.update(TESTS)
        for jinja_extension in CLASSES:
            self.env.add_extension(jinja_extension)
        if jinja_configs:
            for config, value in jinja_configs.items():
                setattr(self.env, config, value)
        for ext in self.yasha_extensions_files:
            self.env, self.parsers = self._load_extensions_file(ext)
        self.env.loader = FileSystemLoader(self.template_lookup_paths)
        self.env.globals.update(self._load_data_files(self.variable_files))  # data from the data files becomes the baseline for jinja global vars
        self.env.globals.update(inline_variables) # data from inline variables / directly-specified global variables overrides data from the data files

    def _load_data_files(self, files: Iterable[Path], parsers: dict = None) -> dict:
        "load a list of data files using file parsers from self.parsers, and merge the resulting dicts together"
        data = {}
        if not parsers:
            parsers = self.parsers
        for file in files:
            ext = file.suffix
            parser = self.parsers.get(ext)
            if not parser:
                raise Exception(f"No parser found for data file {file}")
            # Yasha 5.0 introduced a new function signature for parsers. 
            # Parsers written for yasha 4.4 and below expect one argument called file, and expect it to be an open binary file.
            # New parsers accept two arguments: one called filepath which is an instance of pathlib.Path, and another called encoding, 
            # which is a str representation of an encoding format like 'utf-8`
            if parser.__code__.co_varnames[0] == 'file':
                # This is an old-style parser
                data.update(parser(file.open('rb')))
            else:
                data.update(parser(file, self.encoding))
        return data

    def _load_extensions_file(self, extensions_file: Path, env: Environment = None, parsers: dict = None):
        "Loads jinja and yasha extensions from a given extension file, and update the jinja environment with those extensions"
        from importlib.util import spec_from_file_location, module_from_spec
        from jinja2.ext import Extension
        if not env: env = self.env # Use default env unless otherwise specified
        if not parsers: parsers = self.parsers # Use default parsers unless otherwise specified
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
                env.tests[name] = value
                continue
            if name == 'TESTS':
                env.tests.update(value)
                continue
            
            # Filters
            if name.startswith('filter_'):
                name = name[7:]
                env.filters[name] = value
                continue
            if name == 'FILTERS':
                env.filters.update(value)
                continue
            
            # Parsers
            if name.startswith('parse_'):
                name = name[6:]
                parsers['.' + name] = value
                continue
            if name == 'PARSERS':
                parsers.update(value)
                continue
            
            # Jinja Extensions
            if isinstance(value, type) and issubclass(value, Extension):
                env.add_extension(value)
                continue
            if name == 'CLASSES':
                assert isinstance(value, list), f"The CLASSES variable in {extensions_file} must be a list of jinja extension classes, or strings referencing jinja extension classes"
                for ext in value:
                    env.add_extension(ext)
                continue
                
            # Jinja Configuration
            configuration_directives = [
                'BLOCK_START_STRING', 'BLOCK_END_STRING', 'VARIABLE_START_STRING', 
                'VARIABLE_END_STRING', 'COMMENT_START_STRING', 'COMMENT_END_STRING', 
                'LINE_STATEMENT_PREFIX', 'LINE_COMMENT_PREFIX', 'NEWLINE_SEQUENCE'
            ]
            if name in configuration_directives:
                name = name.lower()
                setattr(env, name, value)
        return env, parsers

    def _get_env_for_template(self, template: Union[Path, str]) -> Environment:
        """When rendering or working with template files, we load extension files related to those templates, 
        which alters the environment, and we add that template's parent directory to the template loader search path,
        which also alters the environment. That means processing one template with a Yasha instance alters the 
        behaviour of the Yasha instance for all future templates processed. To avoid this, we derive a new jinja 
        environment for each template from the Yasha instance's base environment.
        """
        if isinstance(template, str):
            # string tempaltes have no associated files, and therefore don't alter the environment. They can use the base environment directly
            return self.env
        
        # Deplicate the base env, but replace references to dictionaries in the base env with copies of those dictionaries
        env: Environment = self.env.overlay()
        # globals can be a nested data structure, so it must be deep copied
        env.globals = deepcopy(env.globals)
        # filters and tests can be shallow-copied
        env.filters = env.filters.copy()
        env.tests = env.tests.copy()
        # create a new filesystem loader
        searchpath = env.loader.searchpath.copy()  # type: ignore
        env.loader = FileSystemLoader(searchpath=searchpath)
        return env
    
    def render_template(self, 
            template: Union[Path, str], 
            find_data_files = True, 
            find_extension_files = True, 
            jinja_env_overrides = dict(), 
            output: BinaryIO = None):
        """Render a single template

        Args:
            template (Union[Path, str]): 
                Can be either the path to the template file to render, or a template string to render
            find_data_files (bool, optional): 
                Wether or not to automatically load implicit variable file data. 
                See the `Automatic file variables look up` section of the README for details. 
                Defaults to True.
            find_extension_files (bool, optional): 
                Wether or not to automatically load implicit extension files. 
                See the `Template extensions` section of the README for details. 
                Defaults to True.
            jinja_env_overrides (dict, optional): Any Jinja environment configurations to override for this specific template.
            output (BinaryIO, optional): an open binary file to render the template into.
        """
        env = self._get_env_for_template(template)

        if isinstance(template, Path):
            # Automatic file lookup only works if template is a file. 
            # If template is a str (like, for example, something piped in to Yasha's STDIN), then don't bother trying to find related files
            parsers = self.parsers.copy()

            if find_extension_files:
                # load extension files related to this template, updating the local env and the local parsers dict
                extension_files = find_template_companion_files(template, EXTENSION_FILE_FORMATS, self.root)
                for ext in extension_files:
                    env, parsers = self._load_extensions_file(ext, env, parsers)

            if find_data_files:
                # load variable files related to this template, merging their variables into the local env's globals object
                data_files = find_template_companion_files(template, self.parsers.keys(), self.root)
                env.globals.update(self._load_data_files(data_files, parsers))
            
            # Add the template's directory to the template loader's search path
            env.loader.searchpath.append(template.parent) # type: ignore
            # Read the template string from the template path
            template_text = template.read_text()
        else:
            template_text = template
            
        for k, v in jinja_env_overrides:
            setattr(env, k, v)
        
        if output:
            # Don't return the rendered template, stream it to a file
            compiled_template: TemplateStream = env.from_string(template_text).stream()
            compiled_template.enable_buffering(5)
            compiled_template.dump(output, encoding=self.encoding)
        else:
            return env.from_string(template_text).render()

    def get_makefile_dependencies(self, template: Union[Path, str]) -> List[Path]:
        """Produces a list of all files that the rendering of this template depends on, 
        including files referenced within {% include %}, {% import %}, and {% extends %}
        blocks within the template
        """
        env = self._get_env_for_template(template)
        if isinstance(template, Path):
            template = template.read_text()
        dependencies = self.variable_files + self.yasha_extensions_files
        referenced_template_partials = find_referenced_templates(env.parse(template)) # returns a generator
        # convert the generator to a list, filtering out the None values
        referenced_template_partials: List[str] = list(filter(bool, referenced_template_partials))

        for relative_path in referenced_template_partials:
            for basepath in env.loader.searchpath: # type: ignore
                if not isinstance(basepath, Path): basepath = Path(basepath)
                template_path = basepath / relative_path
                if template_path.is_file:
                    # we've found the template partial inside this basepath
                    dependencies.append(template_path)
        return dependencies

