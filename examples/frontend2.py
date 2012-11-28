# Frontend API example
#
#
#

from pprint import pprint
from mlvm.ir import *
from mlvm import irutil

def frontend_example():
    # Make a context and associate a type system
    context = Context(TypeSystem())

    ##########
    # Install float4 vector type
    context.install(Float4FrontendExt)

    ##########
    # Build a function for it
    foo = context.add_function("foo")
    # Add a definition
    # Functions can be overloaded by adding multiple definition
    # with different arguments

    # void foo(float4*, float4*)
    # Arguments are pointers to float4
    foodef = foo.add_definition("void", ("float4", "float4"))
    print "Show function"
    print foodef
    print
    
    ##########
    # Begin implementation of foo
    fooimpl = foodef.implement()

    # Add attributes to arguments
    # Attributes are string hints for optimization
    arg0, arg1 = fooimpl.args
    # arg0 will serve as input and output
    arg0.attributes.add("in")
    arg0.attributes.add("out")
    # arg1 will serve as input only
    arg1.attributes.add("in")

    # Create a Builder on the first basic block
    entryblock = fooimpl.append_basic_block()
    b = Builder(entryblock)

    # Foo will simply add two arguments and store using our intrinsic
    # Intrinsic is available in Builder
    b.add4(arg0, arg1)

    b.ret()  # optional return void
    # Like C, the last block will have a implied return void.

    ##########
    # Begin implementation of foo    print fooimpl
    print "Show implementation"
    print fooimpl
    print

    return context

class Float4FrontendExt(object):
    '''A frontend extension is any object (or even modules) that has a
    install_to_context(context) function.
    '''
    @staticmethod
    def install_to_context(context):
        # Add float4 as vector type
        context.type_system.add_type("float4")

        # Add intrinsic to add two float4
        # The result is stored in the first operand
        intr = context.add_intrinsic("add4")
        intr.add_definition("void", ("float4", "float4"))
        
        print "Show intrinsic"
        print intr
        print


if __name__ == '__main__':
    frontend_example()