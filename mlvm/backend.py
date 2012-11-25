
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
        return value

    def prolog(self, backend, builder, value, attrs):
        return value

    def epilog(self, backend, builder, arg, value, attrs):
        pass


class Value(object):
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
