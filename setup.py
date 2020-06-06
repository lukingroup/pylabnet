import codecs
import os, sys
import subprocess
from setuptools import setup, find_packages

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def read(rel_path):
    here = os.path.abspath(os.path.dirname(__file__))
    with codecs.open(os.path.join(here, rel_path), 'r') as fp:
        return fp.read()

def get_version(rel_path):
    for line in read(rel_path).splitlines():
        if line.startswith('__version__'):
            delim = '"' if '"' in line else "'"
            return line.split(delim)[1]
    else:
        raise RuntimeError("Unable to find version string.")

with open('README.md', 'r') as fh:
    long_description = fh.read()

# Build the executables unless we are packaging for pip
if sys.argv[1] == 'develop':
    pn = open(os.path.join(os.getcwd(),'pylabnet','launchers','pylabnet.cmd'), 'w+')
    pnp = open(os.path.join(os.getcwd(),'pylabnet','launchers','pylabnet_proxy.cmd'), 'w+')
    pn.seek(0, 0), pnp.seek(0, 0)
    content_p = 'start /min "Launch control" python launch_control.py -p'
    content = 'start /min "Launch control" python launch_control.py'

    # If we have a virtual environment
    if len(sys.argv) > 2 and sys.argv[2] != 'bdist_wheel':
        pn.write(sys.argv[2]+' && '+content), pnp.write(sys.argv[2]+' && '+content_p)
        del sys.argv[2]
    else:
        pn.write(content), pnp.write(content)
    install('jupyter')  # Needed for jupyter notebook in developer mode

setup(
    name='pylabnet',
    version=get_version('pylabnet/__init__.py'),
    description='Client-server, python-based laboratory software',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/lukingroup/pylabnet',
    author='Lukin SiV Team',
    author_email='b16lukin@gmail.com',
    license='MIT',
    packages=find_packages(),
    include_package_data=True,
    python_requires='>=3.7',  # This may not be strictly necessary
    entry_points={
        'console_scripts': [
            'pylabnet=pylabnet.launchers.launch_control:main',
            'pylabnet_proxy=pylabnet.launchers.launch_control:main_proxy'
            ]
        },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows :: Windows 10",
        "Programming Language :: Python :: 3",
        "Topic :: Scientific/Engineering :: Physics"
    ],
    install_requires=[
        'decorator>=4.4.0',
        'ipywidgets>=7.5.1',
        'matplotlib>=3.1.3',
        'nidaqmx>=0.5.7',
        'numpy>=1.16.5',
        'plotly>=4.7.1'
        'ptvsd>=4.3.2',
        'PyQt5>=5.13.0',
        'pyqtgraph>=0.10.0',
        'pyserial>=3.4',
        'pytz>=2019.3',
        'PyVISA>=1.10.1',
        'rpyc>=4.1.2',
        'zhinst>=20.1.1211'
    ]
)
