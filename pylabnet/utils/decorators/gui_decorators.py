def protected_widget_change(func):
    """ Error handling wrapdecorator useable for all functions changing widgets properties

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
                pass

        # If timeout is reached, execute function and throw error
        func(*args, **kwargs)

    return wrapper


