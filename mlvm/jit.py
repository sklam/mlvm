import weakref

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

    def compile(self, funcdef, backend='', attrs={}, gil=True):
        '''Compile a function-definition using a specific backend.
        
        attrs --- attributes for build_function
        '''
        if self.manager.has_function(funcdef):
            wrapper, ctype = self.manager.get_function(funcdef)
        else:
            codegen = self.__backends[backend]
            unit = codegen.compile(funcdef)
            unit = codegen.link(unit)
            wrapper, ctype = self.manager.build_function(codegen, funcdef,
                                                         unit, attrs, gil)
        return JITFunction(self, wrapper, ctype, funcdef)

class JITFunction(object):
    def __init__(self, parent, wrapper, ctype, funcdef):
        self.__parent = weakref.proxy(parent) # does not own
        self.__wrapper = wrapper
        self.__ctype = ctype
        self.__funcdef = weakref.proxy(funcdef) # does not own

    @property
    def definition(self):
        return self.__funcdef

    @property
    def ctype(self):
        return self.__ctype

    @property
    def parent(self):
        return self.__parent

    def __call__(self, *args):
        return self.__wrapper(*args)

    def __eq__(self, rhs):
        '''Two instances are equal if their parent is the same and
        the callable is the same.
        '''
        return self.parent is rhs.parent and self.__wrapper is rhs.__wrapper

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

    def build_function(self, codegen, funcdef, unit, attrs, gil):
        '''Returns a wrapper and a ctype function.
        The wrapper handles conversion of python objects to ctypes.
        The handler is implemented in TypeImplementation.
        '''
        raise NotImplementedError
