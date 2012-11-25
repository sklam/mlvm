#
# Array type extension for C arrays.
# It does not do bound-check.
#
# For JIT'ed function, it accepts any object that provides a buffer-interface.
#
# Use this module as an extension for context and backend.
#

from mlvm.backend import TypeImplementation
from mlvm.utils import MEMORYVIEW_DATA_OFFSET
from mlvm.context import (_builtin_unsigned_int,
                          _builtin_signed_int,
                          _builtin_real)
from llvm.core import Type, Builder
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

ELEMENT_TYPES = _builtin_unsigned_int + _builtin_signed_int + \
                _builtin_real + ['address']

def install_to_context(context):
    array_load = context.add_intrinsic("array_load")
    array_store = context.add_intrinsic("array_store")

    for elemtype in ELEMENT_TYPES:
        arraytype = 'array_%s' % elemtype
        context.type_system.add_type(arraytype)

        array_load.add_definition(elemtype, [arraytype, 'address'])
        array_store.add_definition(None, [arraytype, elemtype, 'address'])

def install_to_backend(backend):
    for elemtype in ELEMENT_TYPES:
        arraytype = 'array_%s' % elemtype

        backend.implement_type(ArrayType(arraytype, elemtype))
        backend.implement_intrinsic('array_load',
                                    elemtype,
                                    (arraytype, 'address'),
                                    array_load_impl)
        backend.implement_intrinsic('array_store',
                                    None,
                                    (arraytype, elemtype, 'address'),
                                    array_store_impl)

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

