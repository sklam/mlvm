# Backend API example
#
#
#
from pprint import pprint
from mlvm.llvm.backend import LLVMBackend
from mlvm.backend import TypeImplementation
from mlvm.llvm.jit import LLVMExecutionManager
from mlvm.static import Compiler
from mlvm.llvm.static import LLVMCompiler, LLVMCWrapperGenerator
import numpy as np

from frontend2 import frontend_example
from backend1 import Float4BackendExt

def static_compile_example():
    print "Frontend".center(80, '=')
    context = frontend_example()

    print "Backend".center(80, '=')

    ###########
    # Use LLVM as the backend
    backend = LLVMBackend(opt=LLVMBackend.OPT_MAXIMUM)
    backend.install(Float4BackendExt)

    #############
    # Static compiling

    # Create C Header Generator
    header = LLVMCWrapperGenerator()

    # Create static compiler
    compiler = Compiler(LLVMCompiler(), {'': backend}, wrapper=header)

    # Compile our function
    foo = context.get_function("foo")
    funcdef = foo.get_definition(("float4", "float4"))
    compiler.add_function(funcdef)

    # Show results
    print "Show assembly"
    print compiler.write_assembly()
    print

    print "Show C header"
    print header
    print

if __name__ == '__main__':
    static_compile_example()