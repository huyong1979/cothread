# Wrappers for coroutine functions.

import ctypes
import os

try:
    _coroutine = ctypes.cdll.LoadLibrary(
        os.path.join(os.path.dirname(__file__), '_coroutine.so'))

except:
    # Can't load _coroutine library, try using greenlet in one form or another
    # instead.  Odd.  Two different versions of the greenlet library with
    # slightly different interfaces.
    try:
        import greenlet
        create_greenlet = greenlet.greenlet
    except ImportError:
        from py.magic import greenlet
        create_greenlet = greenlet

    get_current = greenlet.getcurrent

    def create(parent, action, stack_size):
        return create_greenlet(action, parent)

    def switch(coroutine, arg):
        return coroutine.switch(arg)

    def delete(coroutine):
        pass

else:
    # _coroutine successfully loaded, proceed with wrapping it.
    get_current = _coroutine.get_current_coroutine
    delete = _coroutine.delete_coroutine

    _coroutine_action = ctypes.CFUNCTYPE(
        ctypes.py_object, ctypes.py_object, ctypes.py_object)

    _create_coroutine = _coroutine.create_coroutine
    _create_coroutine.argtypes = [
        ctypes.c_void_p, _coroutine_action, ctypes.c_int, ctypes.py_object]
    _create_coroutine.restype = ctypes.c_void_p

    _switch_coroutine = _coroutine.switch_coroutine
    _switch_coroutine.argtypes = [ctypes.c_void_p, ctypes.py_object]
    _switch_coroutine.restype = ctypes.py_object

    ctypes.pythonapi.Py_IncRef.argtypes = [ctypes.py_object]
    ctypes.pythonapi.Py_DecRef.argtypes = [ctypes.py_object]

    def switch(coroutine, arg):
        # The story here with reference counting is a little delicate.  The
        # argument is effectively transposed into a result _switch_coroutine,
        # which means that we need to add an extra reference count.
        ctypes.pythonapi.Py_IncRef(arg)
        return _switch_coroutine(coroutine, arg)

    @_coroutine_action
    def _action_wrapper(action, arg):
        # Pick up arg and switch back.  Something like this anyway.  Important
        # thing is to only create one instance of action_wrapper to avoid memory
        # leaks from within ctypes.
        result = action(arg)
        ctypes.pythonapi.Py_DecRef(action)
        return result

    def create(parent, action, stack_size):
        ctypes.pythonapi.Py_IncRef(action)
        return _coroutine.create_coroutine(
            parent, _action_wrapper, stack_size, action)


# Ignored for greenlet, but needs to be defined anyway.
DEFAULT_STACK_SIZE = (1 << 16)
