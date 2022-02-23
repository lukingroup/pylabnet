import codecs
import os
import sys
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

# Needed for jupyter notebook in developer mode
if len(sys.argv) > 1 and sys.argv[1] == 'develop':
    install('jupyter')

    install('pre-commit')
    from pre_commit.main import main as pre_commit_main
    pre_commit_main(['install', '--install-hooks', '--overwrite'])

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
            'pylabnet_proxy=pylabnet.launchers.launch_control:main_proxy',
            'pylabnet_master=pylabnet.launchers.launch_control:main_master',
            'pylabnet_staticproxy =pylabnet.launchers.launch_control:main_staticproxy'
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
        'atlassian-python-api>=3.13.2',
        'debugpy>=1.3.0',
        'decorator>=4.4.0',
        'ipywidgets>=7.5.1',
        'matplotlib>=3.1.3',
        'netifaces>=0.10.9',
        'nidaqmx>=0.5.7',
        'numpy>=1.16.5',
        'paramiko>=2.7.2',
        'plotly>=4.7.1',
        'PyQt5>=5.13.0',
        'pyqtgraph>=0.10.0',
        'pyserial>=3.4',
        'python-decouple>=3.3',
        'python-kasa>=0.4.0.dev2',
        'pytz>=2019.3',
        'PyVISA>=1.10.1',
        'ptvsd>=5.0.0a12',
        'qdarkstyle>=2.8.1',
        'qm-qua>=0.3.6',
        'rpyc>=4.1.2',
        'scipy>=1.6.1',
        'si_prefix>=1.2.2',
        'simpleeval>=0.9.10',
        'slack-sdk>=3.5.0'
    ]
)
