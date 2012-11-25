from mlvm.ir import *
from mlvm.jit import *
from mlvm.llvm.jit import *
from mlvm.llvm.backend import *
import mlvm.ext.arraytype
import llvm
import numpy as np
from ctypes import *

def main():
    context = configure()
    funcdef = frontend(context)
    backend(context, funcdef)

def configure():
    context = Context(TypeSystem())
    context.install(mlvm.ext.arraytype)
    return context

def frontend(context):
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
    backend.install(mlvm.ext.arraytype)
    
    manager = LLVMExecutionManager(opt=LLVMExecutionManager.OPT_MAXIMUM)
    
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
    
if __name__ == '__main__':
    main()
