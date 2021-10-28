from flake8.main import cli as flake8_cli
from interrogate import cli as interrogate_cli

def check(files):
    if len(files) == 0:
        files = None

    flake8_cli.main(['--ignore=E26,E265,E266,E501', '--jobs=auto'])
    interrogate_cli.main(None, files, fail_under=0)

if __name__ == '__main__':
    check(sys.argv[1:])
