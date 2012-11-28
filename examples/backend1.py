# Backend API example
#
#
#

from pprint import pprint
from mlvm.llvm.backend import LLVMBackend
from mlvm.backend import TypeImplementation
from mlvm.llvm.jit import LLVMExecutionManager
from mlvm.jit import JIT
from llvm.core import Builder, Type
from ctypes import *
import numpy as np
from frontend2 import frontend_example

def jit_example():
    print "Frontend".center(80, '=')
    context = frontend_example()

    print "Backend".center(80, '=')

    #########
    # Use LLVM as the backend
    backend = LLVMBackend(opt=LLVMBackend.OPT_MAXIMUM)

    # Recall we have introduced a type and a intrinsic that are still
    # unimplemented.  We will do that now by install an extension.
    backend.install(Float4BackendExt)

    ###########
    # Try compiling the function
    # This section is not necessary for JIT'ing
    foo = context.get_function("foo")
    funcdef = foo.get_definition(("float4", "float4"))

    lfunc = backend.compile(funcdef)

    print "Compiled LLVM Function"
    print lfunc
    print

    lfunc = backend.link(lfunc)

    print "Linked & Optimized LLVM Function"
    print lfunc
    print


    ############
    # JIT

    # Create an execution manager
    manager = LLVMExecutionManager(opt=LLVMExecutionManager.OPT_MAXIMUM)

    # Create a JIT engine with the manager and backend
    # A JIT engine can have multiple backends.
    # The 2nd argument is a dictionary of backends with the key being
    # the name of the backend.  Use empty string "" for default backend.
    jit = JIT(manager, {'': backend})

    # Compile the definition with the default backend
    function = jit.compile(funcdef)

    # Show ctype function arguments and return type
    print "Ctype arguments and return type"
    print function.ctype.argtypes, function.ctype.restype
    print

    #############
    # Let's test the JIT'ed function
    
    A = np.arange(4, dtype=np.float32)
    B = np.arange(4, dtype=np.float32)

    Aorig = A.copy() # keep a copy of the original data

    # Run with address of data
    function(A.ctypes.data, B.ctypes.data)

    print "Result is correct:", np.allclose(Aorig + B, A)

    Aorig = A.copy()

    # Run with numpy array
    function(A, B)

    print "Result is correct:", np.allclose(Aorig + B, A)


class Float4(TypeImplementation):

    def value(self, backend):
        '''Representation when used in a function and as a return value.
            '''
        return Type.pointer(Type.vector(Type.float(), 4))

    def argument(self, backend):
        '''Representation when used as an argument.
            '''
        return Type.pointer(Type.float())

    def precall(self, backend, builder, value):
        return builder.bitcast(value, self.argument(backend))

    def prolog(self, backend, builder, value, attrs):
        '''Convert argument to a representation that matches value()
        '''
        return builder.bitcast(value, self.value(backend))

    def use(self, backend, builder, value):
        '''Load stack allocation for variables
        '''
        return builder.load(value)

    def allocate(self, backend, builder):
        '''Stack allocation for variables
        '''
        return builder.alloca(self.value(backend))

    def assign(self, backend, builder, value, storage):
        return builder.store(value, storage)

    def ctype(self, backend):
        '''How to represent this type in a ctype Function
        '''
        return POINTER(c_float)

    def ctype_argument(self, backend, value):
        '''Defines how python object is converted to ctype argument
        '''
        if isinstance(value, int) or isinstance(value, long): # an address
            addr = value
        else:
            # assert value is numpy array
            addr = value.ctypes.data
        return cast(c_void_p(addr), self.ctype(backend))

class Float4BackendExt:
    '''A backend extension is any object (or even modules) that has
    a install_to_backend(backend) function.
        
    Frontend and backend extension can be a single object/module.
    '''

    @staticmethod
    def install_to_backend(backend):
        # Implement type
        backend.implement_type(Float4("float4"))

        # Implement intrinsic
        backend.implement_intrinsic("add4",
                                    "void", ("float4", "float4"),
                                    add4impl)

def add4impl(lfunc):
    '''For LLVMBackend, the implementation receives an empty
    llvm.core.Function to begin implementation.
    '''
    bb = lfunc.append_basic_block('entry')
    builder = Builder.new(bb)
    arg0, arg1 = lfunc.args
    pvty = Type.pointer(Type.vector(Type.float(), 4))
    v0 = builder.load(builder.bitcast(arg0, pvty))
    v1 = builder.load(builder.bitcast(arg1, pvty))
    vs = builder.fadd(v0, v1)
    builder.store(vs, builder.bitcast(arg0, pvty))
    builder.ret_void()


if __name__ == '__main__':
    jit_example()