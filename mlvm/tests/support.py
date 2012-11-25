from mlvm.ir import *
from mlvm import irutil
import logging
logger = logging.getLogger(__name__)

def sample_array_function_1(context, arraytype):
    ''' Equivalent to array expression C = (A + B) * 3.14
        
    context --- must have installed mlvm.llvm.ext.arraytype
    arraytype --- element type must be real number.
    '''
    function = context.add_function("foo")

    retty = 'int32'
    argtys = (arraytype, arraytype, arraytype, 'int32')

    funcdef = function.add_definition(retty, argtys)

    logger.debug("mlvm def\n%s" % funcdef)

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
    with irutil.for_range(b, idx, stop):
        lval = b.array_load(A, idx)
        rval = b.array_load(B, idx)
        scale = b.const('float', 3.14)
        sum = b.add(lval, rval)
        prod = b.mul(sum, scale)
        b.array_store(C, prod, idx)


    b.ret(idx)
    return funcdef


def sample_array_function_2(context, arraytype):
    '''Equivalent to array expression C = (A + B) * 123

    context --- must have installed mlvm.llvm.ext.arraytype
    arraytype --- element type must be int type.
    '''
    function = context.add_function("foo")

    retty = 'int32'
    argtys = (arraytype, arraytype, arraytype, 'int32')

    funcdef = function.add_definition(retty, argtys)

    logger.debug("mlvm def\n%s", funcdef)

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
    with irutil.for_range(b, idx, stop):
        lval = b.array_load(A, idx)
        rval = b.array_load(B, idx)
        scale = b.const(lval.type, 123)
        sum = b.add(lval, rval)
        prod = b.mul(sum, scale)
        b.array_store(C, prod, idx)

    b.ret(idx)
    return funcdef


