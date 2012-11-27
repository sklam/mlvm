
class TypeUnimplementedError(Exception):
    pass

class TypeImplementation(object):
    def __init__(self, name):
        self.__name = name

    @property
    def name(self):
        return self.__name

    def value(self, backend):
        raise NotImplementedError

    def return_type(self, backend):
        raise NotImplementedError

    def argument(self, backend):
        raise NotImplementedError
    
    def ctype(self, backend):
        raise NotImplementedError

    def ctype_argument(self, backend, value):
        return value

    def ctype_return(self, backend, value):
        return value

    def ctype_prolog(self, backend, builder, value):
        return value

    def ctype_epilog(self, backend, builder, value):
        pass
    
    def constant(self, builder, value):
        raise NotImplementedError

    def allocate(self, backend, builder):
        raise NotImplementedError

    def deallocate(self, backend, builder, value):
        pass

    def use(self, backend, builder, value):
        raise NotImplementedError

    def assign(self, backend, builder, value, storage):
        raise NotImplementedError

    def precall(self, backend, builder, value):
        return value

    def postcall(self, backend, builder, value):
        pass

    def prolog(self, backend, builder, value, attrs):
        return value

    def epilog(self, backend, builder, arg, value, attrs):
        pass


class Value(object):
    '''
    Use to aid translation from MLVM IR to LLVM IR
    '''
    def __init__(self, backend, tyimpl, value):
        self.__backend = backend
        self.__value = value
        self.__tyimpl = tyimpl

    @property
    def type(self):
        return self.__tyimpl

    @property
    def backend(self):
        return self.__backend

    @property
    def value(self):
        return self.__value

    def use(self, builder):
        return self.value

class Variable(Value):
    def __init__(self, backend, tyimpl, builder):
        value = tyimpl.allocate(backend, builder)
        super(Variable, self).__init__(backend, tyimpl, value)

    def assign(self, builder, value):
        return self.type.assign(self.backend, builder, value, self.value)

    def use(self, builder):
        return self.type.use(self.backend, builder, self.value)

    def deallocate(self, builder):
        self.type.deallocate(self.backend, builder, self.value)

class Argument(Variable):
    def __init__(self, backend, tyimpl, builder, arg, attrs):
        super(Argument, self).__init__(backend, tyimpl, builder)
        self.__arg = arg
        self.__attrs = attrs
        value = self.type.prolog(self.backend, builder, arg, attrs)
        self.assign(builder, value)

    @property
    def arg(self):
        return self.__arg

    @property
    def attributes(self):
        return self.__attrs

    def epilog(self, builder):
        self.type.epilog(self.backend, builder, self.value,
                         self.arg, self.attributes)

class ConstValue(Value):
    def __init__(self, backend, tyimpl, const):
        super(ConstValue, self).__init__(backend, tyimpl,
                                   tyimpl.constant(backend, const))

class Backend(object):
    def __init__(self):
        self.__typeimpl = {}
        self.__opimpl = {}
        self.__intrimpl = {}
        self.__extralib = []

    #
    # Should override
    #

    def compile(self, funcdef):
        raise NotImplementedError

    def link(self, unit):
        raise NotImplementedError


    def _build_intrinsic_call(self, op):
        raise NotImplementedError


    def _build_function_call(self, op):
        raise NotImplementedError

    def _implement_intrinsic(self, name, retty, argtys, impl):
        '''
        Called in implement_intrinsic
        '''
        raise NotImplementedError

    #
    # Should NOT override
    #
    def list_extra_libraries(self):
        return list(self.__extralib)

    def add_extra_library(self, lib):
        self.__extralib.append(lib)

    def install(self, ext):
        ext.install_to_backend(self)

    def implement_intrinsic(self, name, retty, argtys, impl):
        key = (name, tuple(argtys))
        assert key not in self.__intrimpl
        self.__intrimpl[key] = impl
        self._implement_intrinsic(name, retty, argtys, impl)

    def list_intrinsic_implementations(self):
        return self.__intrimpl.items()

    def get_intrinsic_implementation(self, name, argtys):
        return self.__intrimpl[(name, tuple(argtys))]

    def implement_type(self, impl):
        self.__typeimpl[impl.name] = impl

    def list_implemented_types(self):
        return self.__typeimpl.items()

    def is_type_implemented(self, ty):
        return ty in self.__typeimpl

    def get_type_implementation(self, ty):
        try:
            return self.__typeimpl[ty]
        except KeyError:
            raise TypeUnimplementedError(ty)

    def implement_operation(self, operator, operand_types, impl):
        self.__opimpl[(operator, tuple(operand_types))] = impl

    def list_implemented_operation(self):
        return self.__opimpl.items()

    def get_operation_implementation(self, op):
        if op.name.startswith('call.intr'):
            return self._build_intrinsic_call(op)
        elif op.name.startswith('call'):
            return self._build_function_call(op)
        operator = op.name
        operand_types = tuple(i.type for i in op.operands)
        return self.__opimpl[(operator, operand_types)]
