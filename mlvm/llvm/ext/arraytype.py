#
# Array type extension for C arrays.
# It does not do bound-check.
#
# For JIT'ed function, it accepts any object that provides a buffer-interface.
#
# Use this module as an extension for context and backend.
#

from mlvm.backend import TypeImplementation
from mlvm.utils import MEMORYVIEW_DATA_OFFSET, ADDRESS_WIDTH
from mlvm.context import (_builtin_unsigned_int,
                          _builtin_signed_int,
                          _builtin_real)
from llvm.core import (Type, Builder, Constant, ICMP_ULT,
                       MetaData, MetaDataString, ATTR_NO_ALIAS)
from ctypes import *

class ArrayType(TypeImplementation):
    def __init__(self, name, elemtype):
        super(ArrayType, self).__init__(name)
        self.__elemtype = elemtype

    @property
    def element(self):
        return self.__elemtype

    def ctype(self, backend):
        typeimpl = backend.get_type_implementation(self.element)
        c_elem_t = typeimpl.ctype(backend)
        return POINTER(c_elem_t)

    def ctype_argument(self, backend, value):
        if isinstance(value, self.ctype(backend)):
            return value
        else:
            view = memoryview(value)
            assert view.ndim == 1
            ctelem = self.ctype(backend)
            address = cast(c_void_p(id(view) + MEMORYVIEW_DATA_OFFSET),
                           POINTER(c_uint64))[0]
            data = cast(c_void_p(address), ctelem)
            return data
        assert False

    def use(self, backend, builder, value):
        return builder.load(value)

    def value(self, backend):
        elemimpl = backend.get_type_implementation(self.element)
        elem = elemimpl.value(backend)
        return Type.pointer(elem)

    def argument(self, backend):
        return self.value(backend)

    def allocate(self, backend, builder):
        return builder.alloca(self.value(backend))

    def assign(self, backend, builder, value, storage):
        assert storage.type.pointee == value.type
        builder.store(value, storage)

    def prolog(self, backend, builder, value, attrs):
        return value

INTEGER_TYPES = _builtin_unsigned_int + _builtin_signed_int + ['address']
REAL_TYPES = _builtin_real
ELEMENT_TYPES = INTEGER_TYPES + REAL_TYPES

def install_to_context(context):
    array_load = context.add_intrinsic("array_load")
    array_store = context.add_intrinsic("array_store")
    array_add = context.add_intrinsic("array_add")

    for elemtype in ELEMENT_TYPES:
        arraytype = 'array_%s' % elemtype
        context.type_system.add_type(arraytype)

        array_load.add_definition(elemtype, [arraytype, 'address'])
        array_store.add_definition("void", [arraytype, elemtype, 'address'])
        array_add.add_definition("void",
                                 [arraytype, arraytype, arraytype, 'address'])

def install_to_backend(backend):
    for elemtype in ELEMENT_TYPES:
        arraytype = 'array_%s' % elemtype

        backend.implement_type(ArrayType(arraytype, elemtype))
        backend.implement_intrinsic('array_load',
                                    elemtype,
                                    (arraytype, 'address'),
                                    array_load_impl)
        backend.implement_intrinsic('array_store',
                                    'void',
                                    (arraytype, elemtype, 'address'),
                                    array_store_impl)
    for elemtype in INTEGER_TYPES:
        arraytype = 'array_%s' % elemtype
        backend.implement_intrinsic(
                                'array_add',
                                'void',
                                (arraytype, arraytype, arraytype, 'address'),
                                array_arith_impl(Builder.add, elemtype))

    for elemtype in REAL_TYPES:
        arraytype = 'array_%s' % elemtype
        backend.implement_intrinsic(
                                'array_add',
                                'void',
                                (arraytype, arraytype, arraytype, 'address'),
                                array_arith_impl(Builder.fadd, elemtype))

def array_load_impl(lfunc):
    bb = lfunc.append_basic_block('entry')
    builder = Builder.new(bb)
    array, idx = lfunc.args
    elem = builder.gep(array, [idx])
    builder.ret(builder.load(elem))

def array_store_impl(lfunc):
    bb = lfunc.append_basic_block('entry')
    builder = Builder.new(bb)
    array, value, idx = lfunc.args
    elem = builder.gep(array, [idx])
    builder.store(value, elem)
    builder.ret_void()


def array_arith_impl(operator, elemtype):
    def _array_arith_impl(lfunc):
        intp = Type.int(ADDRESS_WIDTH * 8)
        ZERO = Constant.int(intp, 0)
        ONE = Constant.int(intp, 1)

        bbentry = lfunc.append_basic_block('entry')
        bbbody = lfunc.append_basic_block('body')
        bbexit = lfunc.append_basic_block('exit')
        
        builder = Builder.new(bbentry)
        step = ONE

        builder.branch(bbbody)

        builder.position_at_end(bbbody)
        
        idx = builder.phi(intp, name='idx')
        idx.add_incoming(ZERO, bbentry)

        lary, rary, dary, elemct  = lfunc.args
        lary.add_attribute(ATTR_NO_ALIAS)
        rary.add_attribute(ATTR_NO_ALIAS)
        dary.add_attribute(ATTR_NO_ALIAS)
        

        tbaaroot = MetaData.get(lfunc.module,
                                [MetaDataString.get(lfunc.module, "mlvm.tbaa")])
        tbaa_dst = MetaData.get(lfunc.module,
                                [MetaDataString.get(lfunc.module, elemtype),
                                 tbaaroot,
                                 ZERO])
        tbaa_src = MetaData.get(lfunc.module,
                                [MetaDataString.get(lfunc.module,
                                                    "const %s" % elemtype),
                                 tbaaroot,
                                 ONE])

        lval = builder.load(builder.gep(lary, [idx]))
        lval.set_metadata("tbaa", tbaa_src)
        rval = builder.load(builder.gep(rary, [idx]))
        rval.set_metadata("tbaa", tbaa_src)

        res = operator(builder, lval, rval)

        store = builder.store(res, builder.gep(dary, [idx]))
        store.set_metadata("tbaa", tbaa_dst)


        idx_next = builder.add(idx, step, name='idx_next')
        idx.add_incoming(idx_next, bbbody)

        pred = builder.icmp(ICMP_ULT, idx, elemct)
        builder.cbranch(pred, bbbody, bbexit)

        builder.position_at_end(bbexit)
        builder.ret_void()
    return _array_arith_impl
