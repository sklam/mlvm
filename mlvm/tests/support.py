from mlvm.ir import *
from mlvm import irutil
import logging
logger = logging.getLogger(__name__)

def sample_array_function_1(context, arraytype):
    ''' Equivalent to array expression C = (A + B) * 3.14
        
    context --- must have installed mlvm.llvm.ext.arraytype
    arraytype --- element type must be real number.
    '''
    function = context.get_or_insert_function("foo")

    retty = 'int32'
    argtys = (arraytype, arraytype, arraytype, 'int32')

    funcdef = function.add_definition(retty, argtys)

    logger.debug("mlvm def\n%s" % funcdef)

    impl = funcdef.implement()

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
    function = context.get_or_insert_function("foo")

    retty = 'int32'
    argtys = (arraytype, arraytype, arraytype, 'int32')

    funcdef = function.add_definition(retty, argtys)

    logger.debug("mlvm def\n%s", funcdef)

    impl = funcdef.implement()

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


def sample_call_function_1(context):
    '''
    Declares float sin(float) and define float foo(float x) which
    simply return sin(x)
    '''

    # delcare a float sin(float)
    sin = context.get_or_insert_function("sin")

    retty = 'float'
    argtys = ('float', )
    funcdef = sin.add_definition(retty, argtys)

    function = context.add_function("foo")

    # define a float foo(float x) { return sin(x); }
    retty = 'float'
    argtys = ('float', )

    funcdef = function.add_definition(retty, argtys)

    logger.debug("mlvm def\n%s", funcdef)

    impl = funcdef.implement()

    arg0 = impl.args[0]
    arg0.attributes.add('in')

    block = impl.append_basic_block()

    b = Builder(block)
    retval = b.call(sin, arg0)
    b.ret(retval)

    return funcdef


def sample_call_function_2(context):
    '''
        Declares int32 incr(int32) and define int32 foo(int32 x) which
        simply return incr(x)
        '''

    # delcare a int32 sin(int32)
    incr = context.get_or_insert_function("incr")

    retty = 'int32'
    argtys = ('int32', )
    funcdef = incr.add_definition(retty, argtys)

    function = context.add_function("foo")

    # define a int32 foo(int32 x) { return sin(x); }
    retty = 'int32'
    argtys = ('int32', )

    funcdef = function.add_definition(retty, argtys)

    logger.debug("mlvm def\n%s", funcdef)

    impl = funcdef.implement()

    arg0 = impl.args[0]
    arg0.attributes.add('in')

    block = impl.append_basic_block()

    b = Builder(block)
    retval = b.call(incr, arg0)
    b.ret(retval)
    
    return funcdef

def sample_pointer_function_1(context):
    function = context.add_function("foo")

    retty = 'int32'
    argtys = ('int32*', 'int32')

    funcdef = function.add_definition(retty, argtys)

    logger.debug("mlvm def\n%s", funcdef)

    impl = funcdef.implement()

    arg0, arg1 = impl.args
    arg0.attributes.add('in')
    arg0.attributes.add('out')
    arg1.attributes.add('in')

    block = impl.append_basic_block()

    b = Builder(block)
    retval = b.load(arg0)
    b.store(arg1, arg0)
    b.ret(retval)

    return funcdef

def sample_pointer_cast_function_1(context):
    function = context.add_function("foo")

    retty = 'float*'
    argtys = ('int32*', )

    funcdef = function.add_definition(retty, argtys)

    logger.debug("mlvm def\n%s", funcdef)

    impl = funcdef.implement()

    arg0 = impl.args[0]
    arg0.attributes.add('in')

    block = impl.append_basic_block()

    b = Builder(block)
    retval = b.cast(arg0, retty)
    b.ret(retval)

    return funcdef