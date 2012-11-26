__all__ = ['TypeSystem', 'Builder', 'Context', 'FunctionImplementation']

from .context import *
from .value import *
import weakref

class MissingDefinition(TypeError):
    def __init__(self, callable, args):
        super(MissingDefinition, self).__init__(
                                        "%s does not have definition %s(%s)" %
                                        (type(callable).__name__,
                                         callable.name,
                                         ', '.join(x.type for x in args)))

class MultiplePossibleDefinition(TypeError):
    def __init__(self, callable, args):
        super(MultiplePossibleDefinition, self).__init__(
                                "%s has multiple possibe definitions %s(%s)" %
                                (type(callable).__name__,
                                 callable.name,
                                 ', '.join(x.type for x in args)))

class InvalidCast(TypeError):
    def __init__(self, srcty, dstty):
        super(InvalidCast, self).__init__(
                "Conversion from %s to %s is not supported" % (srcty, dstty))

class CannotCoerce(TypeError):
    def __init__(self, srcty, dstty):
        super(CannotCoerce, self).__init__(
                    "Cannot coerce types: %s and %s without loss of precision"
                    % (srcty, dstty))



class Builder(object):
    def __init__(self, basicblock):
        self.__basicblock = basicblock

    @property
    def context(self):
        return self.basic_block.context

    @property
    def basic_block(self):
        return self.__basicblock

    def set_basic_block(self, bb):
        '''Set insert position to the end of the new basic-block.
        '''
        self.__basicblock = bb

    def append_basic_block(self):
        return self.basic_block.implementation.append_basic_block()

    def const(self, type, val, name=''):
        const = Constant(type, val, name)
        self.basic_block.implementation.constants.append(const)
        return const

    def var(self, type, name=''):
        var = Variable(type, name)
        self.basic_block.implementation.variables.append(var)
        return var

    def call(self, callee, *args):
        calltys = tuple(x.type for x in args)
        
        # find defintion
        possible = []
        ts = self.context.type_system
        for defn in callee.list_definitions():
            argtys = defn.args
            if len(calltys) != len(argtys):
                continue
            elif calltys == argtys:
                selected_defn = defn
                break
            else:
                # use the definition with the least conversion
                rank = 0
                for x, y in zip(calltys, argtys):
                    if x == y:
                        rank += 0
                    elif ts.can_implicit_cast(x, y):
                        rank += 1
                    else:
                        rank = 2**31
                        break # not convertible
                else:
                    # is convertible
                    possible.append((rank, argtys, defn))
        else:
            if len(possible) == 0:
                raise MissingDefinition(callee, args)
            ordered = sorted(possible)
            if len(ordered) > 1 and ordered[0][0] > ordered[1][0]:
                # first two entries have the same rank
                raise MultiplePossibleDefinition(callee, args)
            selected_defn = possible[0][2]

        args = [self.cast(arg, ty)
                for ty, arg in zip(selected_defn.args, args)]

        op = Call(selected_defn, args)
        self.basic_block.operations.append(op)
        return op

    def ret(self, val):
        ts = self.context.type_system
        retty = self.basic_block.implementation.return_type
        if val.type != retty:
            if ts.can_implicit_cast(val.type, retty):
                val = self.cast(val, retty)
            else:
                raise InvalidCast(val.type, retty)
        op = Return(val)
        self.basic_block.terminator = op
        return op

    def cast(self, val, ty):
        if val.type == ty:
            return val
        op = Cast(val, ty)
        self.basic_block.operations.append(op)
        return op

    def coerce(self, lhs, rhs):
        if lhs.type == rhs.type:
            return lhs, rhs
        else:
            ts = self.context.type_system
            if ts.can_implicit_cast(lhs.type, rhs.type):
                newtype = rhs.type
            elif ts.can_implicit_cast(rhs.type, lhs.type):
                newtype = lhs.type
            else:
                raise CannotCoerce(lhs.type, rhs.type)
            lhs = self.cast(lhs, newtype)
            rhs = self.cast(rhs, newtype)
            return lhs, rhs

    def add(self, lhs, rhs):
        lhs, rhs = self.coerce(lhs, rhs)
        op = Add(lhs, rhs)
        self.basic_block.operations.append(op)
        return op

    def sub(self, lhs, rhs):
        lhs, rhs = self.coerce(lhs, rhs)
        op = Sub(lhs, rhs)
        self.basic_block.operations.append(op)
        return op

    def mul(self, lhs, rhs):
        lhs, rhs = self.coerce(lhs, rhs)
        op = Mul(lhs, rhs)
        self.basic_block.operations.append(op)
        return op

    def div(self, lhs, rhs):
        lhs, rhs = self.coerce(lhs, rhs)
        op = Div(lhs, rhs)
        self.basic_block.operations.append(op)
        return op

    def rem(self, lhs, rhs):
        lhs, rhs = self.coerce(lhs, rhs)
        op = Rem(lhs, rhs)
        self.basic_block.operations.append(op)
        return op

    def branch(self, bb):
        br = Branch(bb)
        self.basic_block.terminator = br
        return br

    def condition_branch(self, condition, truebr, falsebr):
        br = ConditionBranch(condition, truebr, falsebr)
        self.basic_block.terminator = br
        return br

    def compare(self, op, lhs, rhs):
        cmp = Compare(op, lhs, rhs)
        self.basic_block.operations.append(cmp)
        return cmp

    def assign(self, value, var):
        op = Assign(value, var)
        self.basic_block.operations.append(op)
        return op
            
    def __getattr__(self, name):
        intr = self.context.get_intrinsic(name)
        def _call(*args):
            return self.call(intr, *args)
        return _call


