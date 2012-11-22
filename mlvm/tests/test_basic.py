from mlvm.ir import *

def main():

    numerictypes = ['int32', 'int64', 'address', 'float', 'double']

    types = ['address', 'array_double']

    # all int can cast to address
    castmap = {'int64' : ['address'], 'uint64' : ['address']}
    typesystem = TypeSystem(types)
    typesystem.update_implicit_cast(castmap)


    context = Context(typesystem)

    array_load = context.add_intrinsic("array_load")
    array_load.add_definition('double', ['array_double', 'address'])

    array_store = context.add_intrinsic("array_store")
    array_store.add_definition(None, ['array_double', 'double', 'address'])

    function = context.add_function("foo")

    retty = 'int32'
    argtys = ('array_double', 'array_double', 'array_double', 'int32')

    funcdef = function.add_definition(retty, argtys)

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

    idx_next = body.add(idx, one)
    body.assign(idx_next, idx)
    body.array_store(C, prod, idx)

    body.branch(cond.basic_block)

    #end

    end.ret(idx)

    print impl

if __name__ == '__main__':
    main()
