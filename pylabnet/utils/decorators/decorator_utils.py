'''
This module contains utility functions used for pylabnet decorators.
'''


def get_signature(*args, **kwargs):
    """ Gets printable function signature"""
    args_repr = [repr(a) for a in args]
    kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
    signature = ", ".join(args_repr + kwargs_repr)
    return signature

