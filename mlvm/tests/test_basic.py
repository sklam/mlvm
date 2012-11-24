from mlvm.ir import *
from mlvm.execute import *
from mlvm.backend import LLVMBackend, TypeImplementation
import llvm

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

    def deallocate(self, backend, builder):
        pass

    def assign(self, backend, builder, value, storage):
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

    idx_next = body.add(idx, one)
    body.assign(idx_next, idx)
    body.array_store(C, prod, idx)

    body.branch(cond.basic_block)

    #end

    end.ret(idx)

    return funcdef

def backend(context, funcdef):
    print funcdef
    manager = LLVMExecutionManager(LLVMBackend(opt=LLVMBackend.OPT_MAXIMUM))
    manager.backend.implement_type(ArrayType('array_double', 'double'))
    manager.backend.implement_intrinsic('array_load', 'double',
                                        ('array_double', 'address'),
                                        array_load_impl)
    manager.backend.implement_intrinsic('array_store', None,
                                        ('array_double', 'double', 'address'),
                                        array_store_impl)
    jit = JIT(manager, context)
    function = jit.compile(funcdef)
    print function

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
