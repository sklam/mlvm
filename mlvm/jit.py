import weakref
from ctypes import CFUNCTYPE, PYFUNCTYPE
from llvm.ee import EngineBuilder
from llvm.core import Module

class JIT(object):

    OPT_NONE = 0
    OPT_LESS = 1
    OPT_NORMAL = 2
    OPT_AGGRESSIVE = 3
    OPT_MAXIMUM = OPT_AGGRESSIVE

    def __init__(self, manager, backends, opt=OPT_NORMAL):
        '''
        manager  --- an execution manager instance
                     Ownership is obtained.
        backends --- A dictionary of name -> backend.
                     Use '' (empty string) as default backend.
                     Ownership of all backends is obtained.
        opt      --- (optional) optimization-level.  Defaults to OPT_NORMAL.
        '''
        assert backends, "no backends specified"
        self.__manager = manager
        self.__backends = backends
        self.__opt = opt

    def list_backends(self):
        return self.__backends.items()

    @property
    def manager(self):
        return self.__manager

    @property
    def context(self):
        return self.__context

    @property
    def opt(self):
        return self.__opt

    def compile(self, funcdef, backend='', **attrs):
        '''Compile a function-definition using a specific backend.
        
        **attrs --- attributes for build_function
        '''
        if self.manager.has_function(funcdef):
            callable = self.manager.get_function(funcdef)
        else:
            codegen = self.__backends[backend]
            unit = codegen.compile(funcdef)
            callable = self.manager.build_function(codegen, funcdef, unit,
                                                   **attrs)
        return JITFunction(self, callable, funcdef)

class JITFunction(object):
    def __init__(self, parent, callable, funcdef):
        self.__parent = weakref.proxy(parent) # does not own
        self.__callable = callable

    @property
    def name(self):
        return funcdef.name

    @property
    def parent(self):
        return self.__parent

    def __call__(self, *args):
        return self.__callable(*args)

    def __eq__(self, rhs):
        '''Two instances are equal if their parent is the same and
        the callable is the same.
        '''
        return self.parent is rhs.parent and self.__callable is rhs.__callable

class ExecutionManagerInterface(object):
    '''
    An execution manager provides managment of compiled function for execution.
    It does not compile the function itself.  Instead, the compilation
    is performed by a backend.
        
    Once a function is built by an execution manager for execution,
    it should not be built again.  The execution manager does not protects
    against duplicated compilation.  Instead the user of the manager should
    guarantee this rule is not violated.
    '''
    def has_function(self, funcdef):
        raise NotImplementedError

    def get_function(self, funcdef):
        raise NotImplementedError

    def build_function(self, codegen, funcdef, unit, **attrs):
        raise NotImplementedError

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

    def build_function(self, backend, funcdef, lfunc, gil=True):
        '''Returns a ctype CFUNCTYPE.
            
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
        callable = self.build_wrapper(backend, funcdef, func, gil=gil)

        # remember JIT'ed functions
        self.__symlib[(funcdef.name, tuple(argtys))] = callable
        return callable

    def build_wrapper(self, backend, funcdef, callee, gil=True):
        print callee
        # get address of funciton; forces JIT
        address = self.__engine.get_pointer_to_function(callee)
        # get ctypes of retty and argtys
        get_ty_impl = backend.get_type_implementation
        cretty = get_ty_impl(funcdef.return_type).ctype(backend)
        cargtys = [get_ty_impl(x).ctype(backend)
                   for x in funcdef.args]

        if gil:
            ffi = PYFUNCTYPE
        else:
            ffi = CFUNCTYPE
        
        callable = ffi(cretty, *cargtys)(address)
        return callable

