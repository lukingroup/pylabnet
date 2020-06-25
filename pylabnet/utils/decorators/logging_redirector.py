import io
import functools
from contextlib import redirect_stdout


def log_standard_output(func):
    """ Decorator reading standard output produced by function and logging it in LogHandler

    This functions can be used to capture diagnostic print output produced by
    third party APIs and route this to a LogHandler instance. Must be called by
    instance of a hardware class which has a attached self.log LogHandler instance.

    Note that the standard output will only be logged after the function has been called.
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):

        with io.StringIO() as buf, redirect_stdout(buf):
            # Execute function.
            func_return = func(self, *args, **kwargs)

            # Read standard output from buffer.
            std_output = buf.getvalue()

        # Log every line
        for line in std_output.splitlines():
            self.log.info(line)

        return func_return

    return wrapper

