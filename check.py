'''Check documentation coverage and PEP8 compliance.

Arguments passed on command line are treated as arguments passed to `git diff` to narrow the scope of checking. Otherwise, the entire pylabnet directory is checked.'''

import subprocess
import sys
from flake8.main import application as flake8_application
from flake8 import utils as flake8_utils
from interrogate import coverage as interrogate_coverage


def git(*args):
    '''Run git in a subprocess with the given arguments and return its standard output as a string.'''
    print(args)
    output = subprocess.run(['git', *args], stdout=subprocess.PIPE, check=True).stdout.decode('utf-8')
    print(output)
    return output


def check(*diff_args):
    '''Check documentation coverage and PEP8 compliance, optionally narrowing only to the changes selected by diff_args, which are arguments that would be passed to `git diff`. Returns True if all checks passed, False otherwise.'''
    flake8_instance = flake8_application.Application()
    flake8_instance.initialize(['--ignore=E26,E265,E266,E501', '--jobs=auto'])
    if len(diff_args) > 0:
        flake8_instance.running_against_diff = True
        parsed_diff = {key: value for key, value in flake8_utils.parse_unified_diff(git('diff', '-U0', *diff_args)).items() if key.endswith('.py')}
        if not parsed_diff:
            return True
        flake8_instance.parsed_diff = parsed_diff
    flake8_instance.run_checks()
    flake8_instance.report()

    interrogate_instance = interrogate_coverage.InterrogateCoverage(paths=['pylabnet'])
    if len(diff_args) > 0:
        interrogate_results = interrogate_instance._get_coverage([filename for filename in git('diff', '--name-only', *diff_args).splitlines() if filename.endswith('.py')])
    else:
        interrogate_results = interrogate_instance.get_coverage()
    interrogate_passed = True
    for result in interrogate_results.file_results:
        for node in result.nodes:
            if node.node_type == 'Module' and result.ignore_module:
                continue
            if not node.covered:
                interrogate_passed = False
                print(f'{result.filename}:{0 if node.lineno is None else node.lineno}: {node.path} is not documented', file=sys.stderr)

    return flake8_instance.result_count == 0 and interrogate_passed


if __name__ == '__main__':
    sys.exit(int(not check(*sys.argv[1:])))
