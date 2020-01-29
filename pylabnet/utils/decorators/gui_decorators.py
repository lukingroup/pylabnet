import functools

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
                func(*args, **kwargs)
                updated = True
            except KeyError:
                args_repr = [repr(a) for a in args]                      # 1
                kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]  # 2
                signature = ", ".join(args_repr + kwargs_repr)           # 3
                print(f"KeyError in calling {func.__name__}({signature}), trying again {try_num}/{try_num}.")
                pass

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
            print(f"Gui connected")
            return func(self, *args, **kwargs)
        except EOFError:
            self._gui_connected = False
            args_repr = [repr(a) for a in args]                      # 1
            kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]  # 2
            signature = ", ".join(args_repr + kwargs_repr)           # 3
            print(f"Gui disconnected for function {func.__name__}({signature}), trying again {try_num}/{try_num}.")
    return wrapper