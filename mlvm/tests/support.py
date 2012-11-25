from mlvm.ir import *
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


def sample_array_function_2(context, arraytype):
    '''Equivalent to array expression C = (A + B) * 123

    context --- must have installed mlvm.llvm.ext.arraytype
    arraytype --- element type must be int type.
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

    scale = body.const(lval.type, 123)

    sum = body.add(lval, rval)

    prod = body.mul(sum, scale)

    body.array_store(C, prod, idx)

    idx_next = body.add(idx, one)
    body.assign(idx_next, idx)
    
    body.branch(cond.basic_block)
    
    #end
    end.ret(idx)
    return funcdef


