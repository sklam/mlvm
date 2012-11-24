import weakref

class JIT(object):

    OPT_NONE = 0
    OPT_LESS = 1
    OPT_NORMAL = 2
    OPT_AGGRESSIVE = 3
    OPT_MAXIMUM = OPT_AGGRESSIVE

    def __init__(self, manager, context, opt=OPT_NORMAL):
        self.__manager = manager
        self.__context = context # owns the context
        self.__opt = opt

    @property
    def manager(self):
        return self.__manager

    @property
    def backend(self):
        return self.manager.backend

    @property
    def context(self):
        return self.__context

    @property
    def opt(self):
        return self.__opt

    def compile(self, funcdef):
        unit = self.backend.compile(funcdef)
        callable = self.backend.build_callable(self, unit)
        self.__symlib.put(funcdef, unit)
        return JITFunction(self, callable, funcdef)

class JITFunction(object):
    def __init__(self, parent, callable, funcdef):
        self.__parent = weakref.proxy(parent) # does not own

    @property
    def parent(self):
        return self.__parent

class LLVMExecutionManager(object):
    def __init__(self, backend):
        self.__backend = backend
        self.__lib = {}

    @property
    def backend(self):
        return self.__backend

    def compile(self, funcdef):
        lfunc = self.__lib.get(funcdef)
        if not unit:
            lfunc = self.backend.compile(funcdef)
            self.__lib[funcdef] = lfunc
        return lfunc

    def build_callable(self, unit):
        raise
