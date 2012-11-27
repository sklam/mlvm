import weakref
from .value import *

class InvalidTypeName(Exception):
    pass

class AleadyDefinedError(NameError):
    pass

class MissingImplementation(Exception):
    pass

class ReimplementationError(Exception):
    pass

class BlockTerminatorAlreadyExist(Exception):
    pass

_builtin_signed_int = ['int8',
                       'int16',
                       'int32',
                       'int64',]

_builtin_unsigned_int = ['uint8',
                         'uint16',
                         'uint32',
                         'uint64',]

_builtin_real = ['float', 'double']

_builtin_special = ['pred', 'address']

_builtin_void = ['void']

_builtin_int = _builtin_signed_int + _builtin_unsigned_int

def _build_implicit_cast_table():
    conv = {}
    # allow all integral types to promote without change sign
    for group in [_builtin_signed_int, _builtin_unsigned_int]:
        for i, s in enumerate(group):
            for d in group[i + 1:]:
                cset = conv[s] = conv.get(s, set())
                cset.add(d)

    # allow predicate to promote to any integer
    for i in _builtin_int:
        cset = conv['pred'] = conv.get('pred', set())
        cset.add(i)

    # allow real types to promote
    for i, s in enumerate(_builtin_real):
        for d in _builtin_real[i + 1:]:
            cset = conv[s] = conv.get(s, set())
            cset.add(d)

    # allow address to cast to and from any integer type

    for group in [_builtin_signed_int, _builtin_unsigned_int]:
        for intty in group:
            cset = conv['address'] = conv.get('address', set())
            cset.add(intty)
            cset = conv[intty] = conv.get(intty, set())
            cset.add('address')

    return conv

_builtin_implicit_cast = _build_implicit_cast_table()

class TypeSystem(object):
    '''
    Type can be any object that supports comparision.
    '''
    builtin_signed_int = _builtin_signed_int
    builtin_unsigned_int = _builtin_unsigned_int
    builtin_int = _builtin_signed_int + _builtin_unsigned_int
    builtin_special = _builtin_special

    builtins = _builtin_special + _builtin_int + _builtin_real + _builtin_void

    builtin_implicit_cast = _build_implicit_cast_table()

    def __init__(self, types=[], implicit_casts=None):
        '''
        implicit_casts --- overrides implicit cast table
        '''
        self.__types = set(self.builtins) | set(types)
        self.__iconvtable = implicit_casts or self.builtin_implicit_cast
        self.__reverse_iconvtable = {}
        self.__build_reverse_iconvtable()

    def __build_reverse_iconvtable(self):
        '''
        Build a reverse lookup table for implicit cast table
        '''
        table = self.__reverse_iconvtable
        for s, dg in self.__iconvtable.items():
            for d in dg:
                cset = table[d] = table.get(d, set())
                cset.add(s)
    
    def can_implicit_cast(self, fromty, totype):
        try:
            return totype in self.implicit_cast_table[fromty]
        except KeyError:
            if not self.is_type_valid(fromty):
                raise InvalidTypeName(fromty)
            return False

    def update_implicit_cast(self, castmap):
        '''Update implicit cast table.

        Automatically perform chaining of cast-able types.
        '''
        def _sentry(t):
            if not self.is_type_valid(t):
                raise InvalidTypeName(t)

        # do chaining
        empty = []
        chainmap = {}
        for s, dg in castmap.items():
            _sentry(s)
            for d in dg:
                _sentry(d)
                for i in self.__reverse_iconvtable.get(s, empty):
                    cset = chainmap[i] = chainmap.get(i, set())
                    cset.add(d)

        # merge tables
        def _merge(table):
            for k, v in table.items():
                cset = self.__iconvtable.get(k)
                if cset:
                    cset |= set(v)
        _merge(castmap)
        _merge(chainmap)

    @property
    def implicit_cast_table(self):
        return self.__iconvtable

    def is_type_valid(self, ty):
        if ty in self.__types:
            return True
        else:
            return self.is_type_valid(ty[:-1])

    def get_subtype_count(self, generic_type):
        return self.__generics[generic_type]

    @property
    def types(self):
        return list(self.__types)

    def add_type(self, type):
        return self.__types.add(type)

class Context(object):
    def __init__(self, typesystem):
        self.__typesystem = typesystem
        self.__intrinsics = {}
        self.__functions = {}

    @property
    def type_system(self):
        return self.__typesystem

    def add_intrinsic(self, name):
        if name in self.__intrinsics:
            raise AleadyDefinedError(name)
        intr = Intrinsic(self, name)
        self.__intrinsics[name] = intr
        return intr

    def add_function(self, name):
        fn = Function(self, name)
        if name in self.__functions:
            print self.__functions
            raise AleadyDefinedError(name)
        self.__functions[name] = fn
        return fn

    def get_or_insert_intrinsic(self, name):
        try:
            return self.get_intrinsic(name)
        except:
            return self.add_intrinsic(name)

    def get_or_insert_function(self, name):
        try:
            return self.get_function(name)
        except KeyError:
            return self.add_function(name)

    def get_intrinsic(self, name):
        return self.__intrinsics[name]

    def get_function(self, name):
        return self.__functions[name]

    def list_intrinsics(self):
        return self.__intrinsics.values()

    def list_functions(self):
        return self.__functions.values()

    def install(self, ext):
        ext.install_to_context(self)

class Callable(object):

    _definition_type_ = None
    _kind_ = None

    def __init__(self, context, name):
        '''
        Do not invoke this directly.  Always use Context.add_intrinsic()
        '''
        self.__context = weakref.proxy(context)
        self.__name = name
        self.__defs = {}

    def add_definition(self, retty, argtys):
        assert all(map(self.context.type_system.is_type_valid, argtys))
        key = tuple(argtys)
        if key in self.__defs:
            raise AleadyDefinedError(key)
        defn = self.__defs[key] = self._definition_type_(self, retty, argtys)
        return defn

    def get_or_insert_definition(self, retty, argtys):
        if self.has_definition(argtys):
            return self.get_definition(argtys)
        else:
            return self.add_definition(argtys)

    def get_definition(self, argtys):
        return self.__defs[argtys]

    def has_definition(self, argtys):
        return tuple(argtys) in self.__defs

    def iter_definitions(self):
        return self.__defs.itervalues()

    def list_definitions(self):
        return list(self.iter_definitions())

    @property
    def name(self):
        return self.__name

    @property
    def context(self):
        return self.__context

    def __str__(self):
        defns = self.list_definitions()
        if not defns:
            # empty definitions
            return "%s %s {}" % (self.kind, self.name)
        else:
            buf = []
            for defn in defns:
                buf.append(str(defn))
            return '\n'.join(buf)

class Definition(object):

    def __init__(self, parent, retty, argtys):
        self.__parent = weakref.proxy(parent)
        self.__retty = retty
        self.__argtys = tuple(argtys) # immutable

    @property
    def name(self):
        return self.parent.name

    @property
    def parent(self):
        return self.__parent

    @property
    def return_type(self):
        return self.__retty

    @property
    def args(self):
        return self.__argtys

    @property
    def kind(self):
        return self._kind_


class FunctionImplementation(object):
    def __init__(self, funcdef):
        self.__funcdef = weakref.proxy(funcdef)
        self.__args = tuple(map(Argument, self.definition.args))
        self.__attrs = set()
        self.__bb = []
        self.__consts = []
        self.__vars = []

    def append_basic_block(self):
        bb = BasicBlock(self)
        self.basic_blocks.append(bb)
        return bb

    @property
    def context(self):
        return self.definition.parent.context

    @property
    def definition(self):
        return self.__funcdef

    @property
    def basic_blocks(self):
        return self.__bb

    @property
    def name(self):
        return self.definition.name

    @property
    def return_type(self):
        return self.definition.return_type

    @property
    def args(self):
        return self.__args

    @property
    def attributes(self):
        return self.__attrs

    @property
    def variables(self):
        return self.__vars

    @property
    def constants(self):
        return self.__consts

    def __str__(self):
        '''Pretty print the whole implementation
            using a custom IR similar to LLVM IR.
            '''
        buf = []

        namemap = {}
        template = "{:>20s} {:>10s} {:s},"

        buf.append('define %s %s (' % (self.return_type or 'void', self.name))
        for i, arg in enumerate(self.args):
            name = namemap[id(arg)] = arg.name or ("%%arg_%d" % i)
            attrs = ' '.join(list(arg.attributes))
            buf.append(template.format(arg.type, attrs, name))

        buf.append('    )')
        buf.append('{')

        template = "{:>10s} = {:<20s} {:<30s} ; {:s}"
        pad = ''
        for i, k in enumerate(self.constants):
            name=  namemap[id(k)] = k.name or ("%%const_%d" % i)
            buf.append(template.format(name, str(k.constant), pad, k.type))

        for i, v in enumerate(self.variables):
            name = namemap[id(v)] = v.name or ("%%var_%d" % i)
            if v.initializer:
                init = namemap[id(v.initializer)]
            else:
                init = 'uninitialized'
            buf.append(template.format(name, str(init), pad, v.type))


        template = "{:>12s} {:<20s} {:<30s} {:s}"
        for i, bb in enumerate(self.basic_blocks):
            buf.append("block_%d:" % i)
            for op in bb.operations:
                if op.type is not None:
                    name = namemap[id(op)] = "%%%d" % len(namemap)
                    uid = "%s =" % name
                    value_type = '; %s' % op.type
                else:
                    uid = ''
                    value_type = ''
                operands = [namemap[id(x)] for x in op.operands]

                buf.append(template.format(uid, op.name, ',  '.join(operands),
                                           value_type))
            term = bb.terminator
            idx_of_bb = lambda x: ("block_%d" % self.basic_blocks.index(x))
            if isinstance(term, ConditionBranch):
                term_template = "{:>12s} {:5s} [{:s}, {:s}]"
                buf.append(term_template.format('br',
                                                namemap[id(term.condition)],
                                                idx_of_bb(term.true_branch),
                                                idx_of_bb(term.false_branch)))
            elif isinstance(term, Branch):
                term_template = "{:>12s} {:s}"
                buf.append(term_template.format('br',
                                                idx_of_bb(term.destination)))
            elif isinstance(term, Return):
                term_template = "{:>12s} {:s}"
                if term.value:
                    retval = namemap[id(term.value)]
                else:
                    retval = ''
                buf.append(term_template.format('return', retval))
        
        
        
        buf.append('}')
        return '\n'.join(buf)


class FunctionDefinition(Definition):
    _kind_ = 'func'
    default_implementator = FunctionImplementation

    def __init__(self, parent, retty, argtys):
        super(FunctionDefinition, self).__init__(parent, retty, argtys)
        self.__impl = None

    def __str__(self):
        if not self.is_declaration:
            return str(self.implementation)
        else:
            return "%s %s(%s)" % (self.return_type or 'void',
                                  self.name,
                                  ', '.join(self.args))

    def implement(self, impl=None):
        '''
        impl --- [optional] Implementator class.  
                 If None, the `default_implementator` is used.
        '''
        if impl is None:
            impl = self.default_implementator
        assert impl is not None, "default_implementator is None?"
        if not self.is_declaration:
            raise ReimplementationError(self)
        self.__impl = impl(self)
        return self.__impl

    @property
    def is_declaration(self):
        return self.__impl is None

    @property
    def implementation(self):
        if self.is_declaration:
            raise MissingImplementation(self)
        return self.__impl

class IntrinsicDefinition(Definition):
    _kind_ = 'intr'

    def __str__(self):
        if self.return_type:
            retty = '-> %s' % self.return_type
        else:
            retty = ''
        return "intrinsic %s(%s) %s" % (self.name,
                                       ', '.join(self.args),
                                       retty)

class Intrinsic(Callable):
    _definition_type_ = IntrinsicDefinition

class Function(Callable):
    _definition_type_ = FunctionDefinition

class BasicBlock(object):
    '''
        Does not own the parent function (weakref).
        '''
    def __init__(self, impl):
        '''
            function --- Parent function.
            '''
        self.__impl = weakref.proxy(impl) # prevent circular ref
        self.__ops = []
        self.__term = None

    def __get_terminator(self):
        return self.__term

    def __set_terminator(self, term):
        if self.__term is not None:
            raise BlockTerminatorAlreadyExist(self)
        self.__term = term

    terminator = property(__get_terminator, __set_terminator)

    @property
    def context(self):
        return self.implementation.context

    @property
    def implementation(self):
        return self.__impl

    @property
    def operations(self):
        return self.__ops

class Branch(object):
    def __init__(self, dest):
        self.__dest = dest

    @property
    def destination(self):
        return self.__dest

class Return(Operation):
    def __init__(self, value):
        self.__value = value

    @property
    def value(self):
        return self.__value

class ConditionBranch(Branch):
    def __init__(self, condition, truebr, falsebr):
        self.__condition = condition
        self.__truebr = truebr
        self.__falsebr = falsebr

    @property
    def condition(self):
        return self.__condition

    @property
    def true_branch(self):
        return self.__truebr

    @property
    def false_branch(self):
        return self.__falsebr

