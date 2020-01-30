import functools

def get_signature(*args, **kwargs):
    """ Gets printable function signature"""
    args_repr = [repr(a) for a in args]
    kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
    signature = ", ".join(args_repr + kwargs_repr)
    return signature

def protected_widget_change(func):
    """ Error handling decorator useable for all functions changing widgets properties

    This will ensure that periodic KeyError will not stop execution.
    """

    def wrapper(*args, **kwargs):
        updated = False
        timeout = 100  # Number of times to try function execution before timeout.
        try_num = 0

        # Try until timeout is reached
        while not updated and try_num < timeout:
            try_num += 1
            try:
                updated = True
                return func(*args, **kwargs)
            except KeyError:
                print(f"KeyError in calling {func.__name__}({get_signature(*args, **kwargs)}), trying again {try_num}/{timeout}.")

        if not updated:
            # If timeout is reached, execute function and throw error
            func(*args, **kwargs)

    return wrapper

def gui_connect_check(func):
    """ Error handling decorator checking for EOFError

    Checks for EOF error and sets self._gui_connected accordingly

    Can only be added to member function of a gui_handler instance
    """

    def wrapper(self, *args, **kwargs):
        try:
            self._gui_connected = True
            return func(self, *args, **kwargs)
        except EOFError:
            self._gui_connected = False
            print(f"Gui disconnected for function {func.__name__}({get_signature(*args, **kwargs)})")

         # Handle case where we run out of GUI elements
        except IndexError:
            print(f"No more room at GUI for function {func.__name__}({get_signature(*args, **kwargs)})")

        # Handle case where we tried to assign some GUI widget that didn't exist
        except AttributeError:
            print(f"Incorrect GUI widget name for function {func.__name__}({get_signature(*args, **kwargs)})")

    return wrapper