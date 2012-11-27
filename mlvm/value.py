
class Value(object):
    def __init__(self, type):
        self.__type = type

    @property
    def type(self):
        return self.__type

class Operation(Value):
    def __init__(self, name, type, operands):
        super(Operation, self).__init__(type)
        self.__name = name
        self.__operands = tuple(operands)
        self.__attrs = set()

    @property
    def attributes(self):
        return self.__attrs

    @property
    def name(self):
        return self.__name

    @property
    def operands(self):
        return self.__operands

    def __str__(self):
        return "<%s %x>" % (self.name, id(self))

class Cast(Operation):
    def __init__(self, value, totype):
        super(Cast, self).__init__('cast.%s.%s' % (value.type, totype),
                                   totype, (value,))

class Reference(Operation):
    def __init__(self, value):
        super(Reference, self).__init__('ref', value.type + '*', (value,))

class BinaryOperation(Operation):
    pass

class BinaryArithmetic(BinaryOperation):
    _opname_ = None

    def __init__(self, lhs, rhs):
        assert self._opname_
        assert lhs.type == rhs.type, (lhs.type, rhs.type)
        super(BinaryOperation, self).__init__(self._opname_, lhs.type,
                                              (lhs, rhs))

class Add(BinaryArithmetic):
    _opname_ = 'add'

class Sub(BinaryArithmetic):
    _opname_ = 'sub'

class Mul(BinaryArithmetic):
    _opname_ = 'mul'

class Div(BinaryArithmetic):
    _opname_ = 'div'

class Rem(BinaryArithmetic):
    _opname_ = 'rem'

class Variable(Value):
    def __init__(self, type, name=''):
        super(Variable, self).__init__(type)
        self.__name = name
        self.__initializer = None

    @property
    def name(self):
        return self.__name

    def __str__(self):
        return '<Variable %s %s>' % (self.type, self.name)

    def _set_initializer(self, value):
        '''
            To remove initializer, use `value = None`.
            '''
        if self.__initializer is not None:
            raise ValueError("Cannot duplicate initializer")
        assert isinstance(value, Constant)
        self.__initializer = value

    def _get_initializer(self):
        return self.__initializer

    initializer = property(_get_initializer, _set_initializer)

class Argument(Value):
    def __init__(self, type, name=''):
        super(Argument, self).__init__(type)
        self.__name = name
        self.__attrs = set()

    @property
    def attributes(self):
        return self.__attrs

    def __str__(self):
        return '<Argument %s %s>' % (self.type, self.name)

    def __get_name(self):
        return self.__name

    def __set_name(self, name):
        self.__name = name

    name = property(__get_name, __set_name)

class Constant(Value):
    def __init__(self, type, constant, name=''):
        super(Constant, self).__init__(type)
        self.__constant = constant
        self.__name = name

    @property
    def constant(self):
        return self.__constant

    @property
    def name(self):
        return self.__name

    def __str__(self):
        return '<Constant %s %s>' % (self.type, self.constant)


class Call(Operation):
    def __init__(self, callee, args):
        name = 'call.%s %s' % (callee.kind, callee.name)
        super(Call, self).__init__(name, callee.return_type, args)
        self.__callee = callee

    @property
    def callee(self):
        return self.__callee

    @property
    def args(self):
        return self.operands

class Compare(BinaryOperation):
    supported_operators = {'>'  : 'cmp.gt',
                           '<'  : 'cmp.lt',
                           '==' : 'cmp.eq',
                           '!=' : 'cmp.ne',
                           '>=' : 'cmp.ge',
                           '<=' : 'cmp.le'}
    def __init__(self, op, lhs, rhs):
        super(Compare, self).__init__(self.supported_operators[op], 'pred',
                                      (lhs, rhs))

class Assign(Operation):
    def __init__(self, val, var):
        super(Assign, self).__init__('assign', None, (val, var))

class Store(Operation):
    def __init__(self, val, ptr):
        super(Store, self).__init__('store', None, (val, ptr))

class Load(Operation):
    def __init__(self, ptr):
        super(Load, self).__init__('load', ptr.type[:-1], (ptr,))

