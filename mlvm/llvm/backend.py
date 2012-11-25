__all__ = ['LLVMBackend']

import ctypes
from ctypes import c_float, c_double, c_size_t

import llvm.core as lc
import llvm.passes as lp

from mlvm.backend import *
from mlvm.context import (_builtin_signed_int, _builtin_unsigned_int,
                          _builtin_real, _builtin_special,
                          ConditionBranch, Branch, Return)
from mlvm.utils import ADDRESS_WIDTH

INLINER_THRESHOLD = 1000

class SimpleTypeImplementation(TypeImplementation):
    def __init__(self, name, ty, cty):
        super(SimpleTypeImplementation, self).__init__(name)
        self.__type = ty
        self.__ctype = cty

    @property
    def _type(self):
        return self.__type

    def ctype(self, backend):
        return self.__ctype

    def value(self, backend):
        return self._type

    def return_type(self, backend):
        return self._type

    def argument(self, backend):
        return self._type

    def use(self, backend, builder, value):
        module = _builder_module(builder)
        instr = builder.load(value)
        return instr

    def allocate(self, backend, builder):
        return builder.alloca(self._type)

    def deallocate(self, backend, builder, value):
        pass

    def assign(self, backend, builder, value, storage):
        assert storage.type.pointee == value.type, (storage.type, value.type)
        builder.store(value, storage)

class IntegerImplementation(SimpleTypeImplementation):
    def constant(self, builder, value):
        return lc.Constant.int(self._type, value)

class RealImplementation(SimpleTypeImplementation):
    def constant(self, builder, value):
        return lc.Constant.real(self._type, value)


class LLVMTranslator(object):
    def __init__(self, backend, funcdef):
        self.__backend = backend
        self.__funcdef = funcdef
        self.__valuemap = {}
        self.__bbmap = {}

    @property
    def backend(self):
        return self.__backend

    @property
    def funcdef(self):
        return self.__funcdef

    @property
    def valuemap(self):
        return self.__valuemap

    @property
    def bbmap(self):
        return self.__bbmap

    def _mangle_symbol(self, name):
        def _repl(c):
            return '_%X_' % ord(c)

        def _proc(name):
            for c in name:
                if not c.isalpha() and not c.isdigit():
                    yield _repl(c)
                else:
                    yield c
        return ''.join(_proc(name))

    def translate(self):
        module = self._build_module()
        func = self._build_function(module)
        self._implement(func)
        return func

    def _to_llvm_type(self, ty, context):
        return getattr(self._get_ty_impl(ty), context)(self.backend)

    def _get_ty_impl(self, ty):
        return self.backend.get_type_implementation(ty)

    def _build_module(self):
        name = "%s.%s" % (self.funcdef.name,
                          '.'.join(map(str, self.funcdef.args)))
        return lc.Module.new("mod_%s" % name)

    def _build_function(self, module):
        rawname = '%s.%s' % (self.funcdef.name, '.'.join(self.funcdef.args))
        name = self._mangle_symbol(rawname)
        lretty = self._to_llvm_type(self.funcdef.return_type, 'return_type')
        largtys = [self._to_llvm_type(x, 'argument')
                   for x in self.funcdef.args]
        fty = lc.Type.function(lretty, largtys)
        func = module.add_function(fty, name)
        return func

    def _implement(self, func):
        impl = self.funcdef.implementation
        bb_entry = func.append_basic_block('entry')
        builder = lc.Builder.new(bb_entry)

        # prepare constant
        for const in impl.constants:
            tyimpl = self._get_ty_impl(const.type)
            self.valuemap[const] = ConstValue(self.backend, tyimpl,
                                              const.constant)

        # alloc all varables
        for var in impl.variables:
            tyimpl = self._get_ty_impl(var.type)
            valobj = self.valuemap[var] = Variable(self, tyimpl, builder)
            if var.initializer:
                valobj.assign(builder,
                              self.valuemap[var.initializer].use(builder))
        # build prolog for arguments]
        for larg, arg in zip(func.args, impl.args):
            tyimpl = self._get_ty_impl(arg.type)
            self.valuemap[arg] = Argument(self.backend, tyimpl, builder, larg,
                                          arg.attributes)


        for i, irbb in enumerate(impl.basic_blocks):
            # allocate basicblocks
            bb = func.append_basic_block("block_%d" % i)
            self.bbmap[irbb] = bb

        # branch to first block
        builder.branch(self.bbmap[impl.basic_blocks[0]])

        self._build_body(impl, builder)


    def _build_body(self, impl, builder):
        for i, irbb in enumerate(impl.basic_blocks):
            # populate basicblocks
            bb = self.bbmap[irbb]
            builder.position_at_end(bb)

            for op in irbb.operations:
                # build operations
                if op.name == 'assign':
                    storage = self.valuemap[op.operands[1]]
                    storage.assign(builder,
                                   self.valuemap[op.operands[0]].use(builder))
                elif op.name == 'return':
                    retval = self.valuemap[op.operands[0]].use(builder)
                    builder.ret(retval)
                else:
                    opimpl = self.backend.get_operation_implementation(op)
                    operands = [self.valuemap[x].use(builder)
                                for x in op.operands]
                    tmp = opimpl(builder, *operands)
                    if op.type:
                        tyimpl = self._get_ty_impl(op.type)
                        assert tyimpl.value(self) == tmp.type
                        self.valuemap[op] = Value(self.backend, tyimpl, tmp)

            if irbb.terminator: # close basicblock
                term = irbb.terminator
                if isinstance(term, ConditionBranch):
                    cond = self.valuemap[term.condition].use(builder)
                    truebr = self.bbmap[term.true_branch]
                    falsebr = self.bbmap[term.false_branch]
                    builder.cbranch(cond, truebr, falsebr)
                elif isinstance(term, Branch):
                    builder.branch(self.bbmap[term.destination])
                else:
                    assert isinstance(term, Return)
                    if term.value is None:
                        assert impl.return_type == None
                    else:
                        retval = self.valuemap[term.value].use(builder)
                        self._teardown(builder)
                        builder.ret(retval)

            else: # default pass through
                if impl.return_type:
                    assert i + 1 < len(impl.basic_blocks), \
                        "Missing return statement in the last block of %s" \
                            % funcdef
                    builder.branch(bbmap[impl.basic_blocks[i + 1]])
                else:
                    self._teardown(builder)
                    builder.ret_void()

    def _teardown(self, builder):
        epilog = [i for i in self.valuemap.values()
                  if isinstance(i, Argument)]

        for val in epilog:
            val.epilog(builder)

        raii = [i for i in self.valuemap.values()
                if isinstance(i, Variable)]
        for val in raii:
            val.deallocate(builder)

class LLVMBackend(object):
    OPT_NONE = 0
    OPT_LESS = 1
    OPT_NORMAL = 2
    OPT_AGGRESSIVE = 3
    OPT_MAXIMUM = OPT_AGGRESSIVE

    def __init__(self, address_width=None, opt=OPT_NORMAL):
        if not address_width: # auto-detect
            address_width = ADDRESS_WIDTH
        assert address_width in [4, 8]
        self.__address_width = address_width
        self.__opt = opt
        self.__typeimpl = {}
        self.__opimpl = {}
        self.__intrimpl = {}

        # pass manager builder
        self.__pmb = lp.PassManagerBuilder.new()
        self.__pmb.opt_level = self.__opt
        self.__pmb.use_inliner_with_threshold(INLINER_THRESHOLD)

        # module-level pass manager
        self.__pm = lp.PassManager.new()
        self.__pmb.populate(self.__pm)

        # intrinsic library module
        self.__intrlib = lc.Module.new("mlvm.intrinsic.%d" % id(self))
        self.__intrlibfpm = lp.FunctionPassManager.new(self.__intrlib)
        self.__pmb.populate(self.__intrlibfpm)

        # initialize default implementations
        self._default_type_implementation()
        self._default_operation_implementation()

    @property
    def address_width(self):
        return self.__address_width

    def _default_operation_implementation(self):
        self._default_comparision_implementation()
        self._default_cast_implementation()
        self._default_arithmetic_implementation()

    def _default_arithmetic_implementation(self):
        def impl(name):
            def _impl(builder, lhs, rhs):
                assert lhs.type == rhs.type
                op = getattr(builder, name)
                return op(lhs, rhs)
            return _impl

        inttypes = (_builtin_signed_int + _builtin_unsigned_int +
                    _builtin_special)
        intop = {
            'add': 'add',
            'sub': 'sub',
            'mul': 'mul',
            'div': 'div',
            'rem': 'rem',
        }
        for ty in inttypes:
            for raw, real in intop.items():
                self.implement_operation(raw, (ty, ty), impl(real))

        realtypes = _builtin_real
        realop = {
            'add': 'fadd',
            'sub': 'fsub',
            'mul': 'fmul',
            'div': 'fdiv',
            'rem': 'frem',
        }
        for ty in realtypes:
            for raw, real in realop.items():
                self.implement_operation(raw, (ty, ty), impl(real))

    def _default_cast_implementation(self):
        def icast(fromty, toty):
            signed = toty in _builtin_signed_int
            tyimpl = self.get_type_implementation(toty)
            toty = tyimpl.value(self)
            assert isinstance(toty, lc.IntegerType)

            def _icast(builder, value):
                fromty = value.type
                if fromty == toty:
                    return value
                elif isinstance(fromty, lc.IntegerType):
                    if fromty.width > toty.width:
                        return builder.trunc(value, toty)
                    elif signed:
                        return builder.sext(value, toty)
                    else:
                        return builder.zext(value, toty)
                elif fromty == Type.float() or fromty == Type.double():
                    if signed:
                        return builder.fptosi(value, toty)
                    else:
                        return builder.fptoui(value, toty)
                else:
                    raise Exception("Cannot handle cast from %s to %s" \
                                    % (fromty, toty))
            return _icast

        def fcast(fromty, toty):
            tyimpl = self.get_type_implementation(toty)
            toty = tyimpl.value(self)
            assert toty == lc.Type.float() or toty == lc.Type.double()
            signed = fromty in _builtin_signed_int
            def _fcast(builder, value):
                fromty = value.type
                if fromty == toty:
                    return value
                elif isinstance(fromty, lc.IntegerType):
                    if signed:
                        return builder.fptosi(value, toty)
                    else:
                        return builder.fptoui(value, toty)
                elif fromty == lc.Type.float():
                    assert toty == lc.Type.double()
                    return builder.fpext(value, toty)
                elif fromty == lc.Type.double():
                    assert toty == lc.Type.float()
                    return builder.fptrunc(value, toty)
                else:
                    raise Exception("Cannot handle cast from %s to %s" \
                                    % (fromty, toty))
            return _fcast

        types = (_builtin_signed_int + _builtin_unsigned_int +
                 _builtin_real + _builtin_special)

        for fromty in types:
            for toty in types:
                if toty != fromty:
                    if toty not in ['float', 'double']:
                        castimpl = icast(fromty, toty)
                    else:
                        castimpl = fcast(fromty, toty)
                    op = 'cast.%s.%s' % (fromty, toty)
                    self.implement_operation(op, (fromty,), castimpl)

    def _default_comparision_implementation(self):
        def cmp_uint(flag):
            def _cmp_uint(builder, lhs, rhs):
                assert lhs.type == rhs.type
                return builder.icmp(flag, lhs, rhs)
            return _cmp_uint

        def cmp_int(flag):
            def _cmp_int(builder, lhs, rhs):
                assert lhs.type == rhs.type
                return builder.icmp(flag, lhs, rhs)
            return _cmp_int

        def cmp_real(flag):
            def _cmp_real(builder, lhs, rhs):
                assert lhs.type == rhs.type
                return builder.fcmp(flag, lhs, rhs)
            return _cmp_real

        op_flags = {
            'cmp.lt'    : (lc.ICMP_ULT, lc.ICMP_SLT, lc.FCMP_OLT),
            'cmp.gt'    : (lc.ICMP_UGT, lc.ICMP_SGT, lc.FCMP_OGT),
            'cmp.le'    : (lc.ICMP_ULE, lc.ICMP_SLE, lc.FCMP_OLE),
            'cmp.ge'    : (lc.ICMP_UGE, lc.ICMP_SGE, lc.FCMP_OGE),
            'cmp.eq'    : (lc.ICMP_EQ, lc.ICMP_EQ, lc.FCMP_OEQ),
            'cmp.ne'    : (lc.ICMP_NE, lc.ICMP_NE, lc.FCMP_ONE),
        }
        
        for op, (unsigned_flag, signed_flag, float_flag) in op_flags.items():
            for bits in [8, 16, 32, 64]:
                # unsigned
                ty = ('uint%d' % bits,)
                self.implement_operation(op, ty*2, cmp_uint(unsigned_flag))
                # signed
                ty = ('int%d' % bits,)
                self.implement_operation(op, ty*2, cmp_int(signed_flag))

            for ty in ['float', 'double']:
                self.implement_operation(op, ty*2, cmp_real(float_flag))

    def _default_type_implementation(self):
        def factory(cls, name, ty, cty):
            self.implement_type(cls(name, ty, cty))

        for bits in [8, 16, 32, 64]:
            ty = lc.Type.int(bits)
            scty = getattr(ctypes, "c_int%d" % bits)
            ucty = getattr(ctypes, "c_uint%d" % bits)
            factory(IntegerImplementation, 'int%d' % bits, ty, scty)
            factory(IntegerImplementation, 'uint%d' % bits, ty, ucty)

        factory(SimpleTypeImplementation, None, lc.Type.void(), None)
        factory(IntegerImplementation, 'pred', lc.Type.int(1), NotImplemented)
        factory(RealImplementation, 'float', lc.Type.float(), c_float)
        factory(RealImplementation, 'double', lc.Type.double(), c_double)
        factory(IntegerImplementation, 'address',
                lc.Type.int(self.address_width * 8), c_size_t)

    def implement_intrinsic(self, name, retty, argtys, impl):
        key = (name, tuple(argtys))
        assert key not in self.__intrimpl
        self.__intrimpl[key] = impl

        # make function
        name = 'mlvm.intrinsic.%s.%s' % (name, '.'.join(argtys))
        lretty = self._to_llvm_type(retty, 'return_type')
        largtys = [self._to_llvm_type(x, 'argument') for x in argtys]
        fnty = lc.Type.function(lretty, largtys)
        lfunc = self.__intrlib.add_function(fnty, name)

        # set function linkage, attributes & visibility
        lfunc.linkage = lc.LINKAGE_LINKONCE_ODR
        lfunc.add_attribute(lc.ATTR_ALWAYS_INLINE)
        lfunc.visibility = lc.VISIBILITY_HIDDEN

        # implement
        impl(lfunc)
        lfunc.verify()
        # optimize
        self.__intrlibfpm.run(lfunc)

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
            print op.callee
            raise NotImplementedError
        operator = op.name
        operand_types = tuple(i.type for i in op.operands)
        return self.__opimpl[(operator, operand_types)]

    def _build_intrinsic_call(self, op):
        argtys = op.callee.args
        fname = 'mlvm.intrinsic.%s.%s' % (op.callee.name, '.'.join(argtys))
        def _build(builder, *args):
            assert len(args) == len(argtys)
            module = _builder_module(builder)

            largtys = [self._to_llvm_type(x, 'argument')
                       for x in argtys]
            lretty = self._to_llvm_type(op.callee.return_type,
                                        'return_type')
            fnty = lc.Type.function(lretty, largtys)
            decl = module.get_or_insert_function(fnty, fname)
            callintr = builder.call(decl, args)
            return callintr
        return _build

    @property
    def opt(self):
        return self.__opt

    def compile(self, funcdef):
        llfunc = LLVMTranslator(self, funcdef).translate()
        module = llfunc.module

        llfunc.verify()

        # function-level optimize
        fpm = lp.FunctionPassManager.new(module)
        self.__pmb.populate(fpm)
        return llfunc

    def link(self, llfunc):
        module = llfunc.module
        # link intrinsics
        module.link_in(self.__intrlib.clone())

        # module-level optimization
        self.__pm.run(module)
        return llfunc

    def _to_llvm_type(self, ty, context):
        tyimpl = self.get_type_implementation(ty)
        impl = getattr(tyimpl, context)
        return impl(self)

def _builder_module(builder):
    module = builder.basic_block.function.module
    return module
