
from .decorator_utils import get_signature
import functools



def dummy_wrap(func):
    """ Decorator which re-routed functions of Driver() objects
    to only produce logged outputs, if the dummy flas ist set.

    This will enable to use of dummy-versions of drivers.
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):

        # If in dummy mode, log which function is executed.
        if self.dummy:
            function_name = func.__name__
            self.log.info(f'Dummy execution of {function_name}')
        # If not in dummy mode, execute function.
        else:
            # Execute function.
            return func(self, *args, **kwargs)

    return wrapper