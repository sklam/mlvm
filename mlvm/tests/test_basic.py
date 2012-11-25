from mlvm.ir import *
from mlvm.jit import *
from mlvm.backend import TypeImplementation
from mlvm.llvm.jit import *
from mlvm.llvm.backend import *
import llvm
import numpy as np
from ctypes import *

def main():
    context = configure()
    funcdef = frontend(context)
    backend(context, funcdef)

def configure():
    types = ['array_double']
    typesystem = TypeSystem(types)
    context = Context(typesystem)
    return context

class ArrayType(TypeImplementation):
    def __init__(self, name, elemtype):
        super(ArrayType, self).__init__(name)
        self.__elemtype = elemtype

    @property
    def element(self):
        return self.__elemtype

    def ctype(self, backend):
        from ctypes import POINTER
        typeimpl = backend.get_type_implementation(self.element)
        c_elem_t = typeimpl.ctype(backend)
        return POINTER(c_elem_t)

    def ctype_argument(self, backend, value):
        from ctypes import c_void_p, cast
        from mlvm.utils import MEMORYVIEW_DATA_OFFSET

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
        return llvm.core.Type.pointer(elem)

    def argument(self, backend):
        return self.value(backend)

    def allocate(self, backend, builder):
        return builder.alloca(self.value(backend))

    def assign(self, backend, builder, value, storage):
        assert storage.type.pointee == value.type
        builder.store(value, storage)

    def prolog(self, backend, builder, value, attrs):
        return value

def frontend(context):

    array_load = context.add_intrinsic("array_load")
    array_load.add_definition('double', ['array_double', 'address'])

    array_store = context.add_intrinsic("array_store")
    array_store.add_definition(None, ['array_double', 'double', 'address'])

    function = context.add_function("foo")

    retty = 'int32'
    argtys = ('array_double', 'array_double', 'array_double', 'int32')

    funcdef = function.add_definition(retty, argtys)

    print funcdef

    impl = funcdef.implement(FunctionImplementation)

    A, B, C, stop = impl.args
    A.attributes.add('in')
    B.attributes.add('in')
    C.attributes.add('out')
    stop.attributes.add('in')

    block = impl.append_basic_block()

    b = Builder(block)

    zero = b.const('int32', 0)
    one = b.const('int32', 1)

    idx = b.var('int32')
    idx.initializer = zero

    # for loop
    cond = Builder(impl.append_basic_block())
    body = Builder(impl.append_basic_block())
    end = Builder(impl.append_basic_block())

    b.branch(cond.basic_block)

    # condition
    pred = cond.compare('<', idx, stop)
    cbr = cond.condition_branch(pred, body.basic_block, end.basic_block)

    # body
    lval = body.array_load(A, idx)
    rval = body.array_load(B, idx)

    pi = body.const('float', 3.14)

    sum = body.add(lval, rval)
    prod = body.mul(sum, pi)

    body.array_store(C, prod, idx)

    idx_next = body.add(idx, one)
    body.assign(idx_next, idx)

    body.branch(cond.basic_block)

    #end
    end.ret(idx)
    return funcdef


def backend(context, funcdef):
    print funcdef
    backend = LLVMBackend(opt=LLVMBackend.OPT_MAXIMUM)
    manager = LLVMExecutionManager(opt=LLVMExecutionManager.OPT_MAXIMUM)
    backend.implement_type(ArrayType('array_double', 'double'))
    backend.implement_intrinsic('array_load',
                                'double',
                                ('array_double', 'address'),
                                array_load_impl)
    backend.implement_intrinsic('array_store',
                                None,
                                ('array_double', 'double', 'address'),
                                array_store_impl)
    jit = JIT(manager, {'': backend})
    function = jit.compile(funcdef)

    # ensure a function is not duplicated
    f2 = jit.compile(funcdef)
    assert function == f2

    A = np.arange(10, dtype=np.float64)
    B = A * 2
    C = np.empty_like(A)

    # call with ctypes
    c_double_p = POINTER(c_double)

    n = function(A.ctypes.data_as(c_double_p), B.ctypes.data_as(c_double_p),
                 C.ctypes.data_as(c_double_p), A.shape[0])
    assert n == A.shape[0]

    Gold = (A + B) * 3.14
    assert np.allclose(Gold, C)

    # call with numpy array
    C = np.zeros_like(A)

    n = function(A, B, C, A.shape[0])
    assert n == A.shape[0]

    Gold = (A + B) * 3.14
    assert np.allclose(Gold, C)


def array_load_impl(lfunc):
    from llvm.core import Builder
    bb = lfunc.append_basic_block('entry')
    builder = Builder.new(bb)
    array, idx = lfunc.args
    elem = builder.gep(array, [idx])
    builder.ret(builder.load(elem))

def array_store_impl(lfunc):
    from llvm.core import Builder
    bb = lfunc.append_basic_block('entry')
    builder = Builder.new(bb)
    array, value, idx = lfunc.args
    elem = builder.gep(array, [idx])
    builder.store(value, elem)
    builder.ret_void()

    
if __name__ == '__main__':
    main()
