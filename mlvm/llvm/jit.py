__all__ = ['LLVMExecutionManager']

from mlvm.jit import *

from ctypes import CFUNCTYPE, PYFUNCTYPE
from llvm.ee import EngineBuilder
from llvm.core import Module


class LLVMExecutionManager(ExecutionManagerInterface):
    OPT_NONE = 0
    OPT_LESS = 1
    OPT_NORMAL = 2
    OPT_AGRESSIVE = 3
    OPT_MAXIMUM = OPT_AGRESSIVE

    def __init__(self, opt=OPT_NORMAL):
        self.__opt = opt
        self.__fatmod = Module.new('mlvm.jit.%X' % id(self))
        self.__engine = EngineBuilder.new(self.__fatmod).opt(opt).create()
        self.__symlib = {} # stores (name, argtys) -> callable

    @property
    def opt(self):
        return self.opt

    def has_function(self, funcdef):
        k = (funcdef.name, tuple(funcdef.args))
        return k in self.__symlib

    def get_function(self, funcdef):
        k = (funcdef.name, tuple(funcdef.args))
        return self.__symlib[k]

    def build_function(self, backend, funcdef, lfunc, attrs):
        '''Returns a wrapper and a ctype CFUNCTYPE.

            lfunc --- Ownership of lfunc is obtained.
            Callee should no longer use this object.
            '''
        retty = funcdef.return_type
        argtys = funcdef.args
        # link function's module to fat module
        self.__fatmod.link_in(lfunc.module)
        # lfunc's module is invalidated

        # get function by name
        func = self.__fatmod.get_function_named(lfunc.name)
        # build wrapper
        wrapper, callable = self.build_wrapper(backend, funcdef, func, attrs)

        # remember JIT'ed functions
        self.__symlib[(funcdef.name, tuple(argtys))] = wrapper, callable
        return wrapper, callable

    def build_wrapper(self, backend, funcdef, callee, gil=True):
        # get address of funciton; forces JIT
        address = self.__engine.get_pointer_to_function(callee)
        # get ctypes of retty and argtys
        get_ty_impl = backend.get_type_implementation

        rettyimpl = get_ty_impl(funcdef.return_type)
        argtyimpls = [get_ty_impl(x) for x in funcdef.args]
        
        cretty = rettyimpl.ctype(backend)
        cargtys = [x.ctype(backend) for x in argtyimpls]

        if gil:
            ffi = PYFUNCTYPE
        else:
            ffi = CFUNCTYPE

        callable = ffi(cretty, *cargtys)(address)

        def _wrapper(*args):
            args = [ty.ctype_argument(backend, arg)
                    for ty, arg in zip(argtyimpls, args)]
            retval = callable(*args)
            return rettyimpl.ctype_return(backend, retval)

        return _wrapper, callable

