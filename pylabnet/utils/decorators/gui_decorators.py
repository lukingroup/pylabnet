from .decorator_utils import get_signature


def handle_gui_errors(func):
    """ Error handling decorator checking all GUI configuration errors

    Checks for EOF error and sets self.gui_connected accordingly

    Can only be added to member function of a gui_handler instance
    """

    def wrapper(self, *args, **kwargs):

        # Check 1: KeyError
        updated = False
        timeout = 10  # Number of times to try function execution before timeout.
        try_num = 0

        # Try until timeout is reached
        while not updated and try_num < timeout:
            try_num += 1
            try:
                updated = True
                self.gui_connected = True
                return func(self, *args, **kwargs)
            except KeyError:
                updated = False

                # Note that we should use a warning here, since KeyErrors can happen during normal operation
                self.logger_client.warn(f"KeyError in calling {func.__name__}({get_signature(*args, **kwargs)}), trying again {try_num}/{timeout}.")

            except EOFError:
                updated = False
                self.gui_connected = False
                self.logger_client.error(f"Gui disconnected for function {func.__name__}({get_signature(*args, **kwargs)}), trying again {try_num}/{timeout}.")

            # Handle case where we run out of GUI elements
            except IndexError:
                updated = False
                self.gui_connected = False
                self.logger_client.error(f"No more room at GUI for function {func.__name__}({get_signature(*args, **kwargs)}), trying again {try_num}/{timeout}.")

            # Handle case where we tried to assign some GUI widget that didn't exist
            except AttributeError:
                updated = False
                self.gui_connected = False
                self.logger_client.error(f"Incorrect GUI widget name for function {func.__name__}({get_signature(*args, **kwargs)}), trying again {try_num}/{timeout}.")

            except ConnectionRefusedError:
                updated = False
                self.gui_connected = False
                self.logger_client.error(f"GUI connection failed for function {func.__name__}({get_signature(*args, **kwargs)}), trying again {try_num}/{timeout}.")

    return wrapper
