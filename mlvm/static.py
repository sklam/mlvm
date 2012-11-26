try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

class AlreadyDefinedError(Exception):
    pass

class Compiler(object):
    def __init__(self, impl, backends):
        '''
        impl --- implementationo of the compiler. Ownership is obtained
        '''
        assert backends, "No backends are defined"
        self.__impl = impl # owned
        self.__backends = backends
        self.__symlib = {}

    @property
    def backend(self):
        return self.__backend

    def add_function(self, funcdef, backend=''):
        if self.has_function(funcdef):
            raise AlreadyDefinedError(funcdef.name, funcdef.args)

        # use backend to generate a function unit
        codegen = self.__backends[backend]
        unit = codegen.compile(funcdef)
        unit = codegen.link(unit)

        realname = self.__impl.add_function(unit)

        self.__symlib[(funcdef.name, tuple(funcdef.args))] = realname

    def has_function(self, funcdef):
        return (funcdef.name, tuple(funcdef.args)) in self.__symlib

    def list_functions(self):
        return self.__symlib.keys()

    def write_assembly(self, file=None):
        '''Write the assembly to the specified file.
        If file is None, returns the byte string contining the assembly.

        file --- an optional file-object
        '''
        return self.__write_dispatch(self.__impl.write_assembly, file)
    
    def write_object(self, file=None):
        '''Write the assembly to the specified file.
        If file is None, returns the byte string contining the object code.

        file --- an optional file-object
            '''
        return self.__write_dispatch(self.__impl.write_object, file)

    def __write_dispatch(self, impl, file):
        return_string = False
        if not file:
            return_string = True
            file = StringIO()

        impl(file)

        if return_string:
            return file.getvalue()


class CompilerInterface(object):
    def add_function(self, unit):
        '''Performs real compiling work on unit.

        Returns the actual symbol name.
        '''
        raise NotImplementedError
    
    def write_assembly(self, file):
        '''Write the assembly to the specified file.
        
        file --- a file-object
        '''
        raise NotImplementedError

    def write_object(self, file):
        '''Write the object code to the specified file
        
        file --- a file-object
        '''
        raise NotImplementedError

