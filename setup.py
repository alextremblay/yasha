import re
import ast
from setuptools import setup, find_packages

_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('yasha/yasha.py', 'rb') as f:
    __version__ = str(ast.literal_eval(_version_re.search(
        f.read().decode('utf-8')).group(1)))

setup(
    name="yasha",
    author="Kim Blomqvist",
    author_email="kblomqvist@iki.fi",
    version=__version__,
    description="A command-line tool to render Jinja templates",
    keywords=["jinja", "code generator", "template"],
    license="MIT",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "Click",
        "Jinja2",
        "pytoml",
        "pyyaml",
        "xmltodict",
        "typing_extensions;python_version<3.8"
    ],
    python_requires='>=3.6',
    entry_points='''
        [console_scripts]
        yasha=yasha.cli:cli
    ''',
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Software Development :: Code Generators",
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: MIT License",
    ],
    url="https://github.com/kblomqvist/yasha",
    download_url="https://github.com/kblomqvist/yasha/tarball/" + __version__,
)
