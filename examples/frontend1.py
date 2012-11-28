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
    # Print all default types
    print "Default types"
    pprint(context.type_system.types)

    # "pred" is a special 1-bit value.
    # "address" is a special type which is an integral type for addressing.
    # The true length of "address" is not known at known at this point.

    ##########
    # Print default cast table for implicit casting by IR Builder
    print "Default implicit cast table"
    pprint(context.type_system.implicit_cast_table)

    # The default implicit cast table allows smaller builtin integers
    # to promote to more precise builtin integers of the same sign.
    # "float" can promote to double implicitly, but not the other way.
    # "pred" can promote to any integers
    # Any builtin integers can promote to "address", but not the other way.

    ##########
    # Add new type.

    # At the frontend, a type is just a name.
    # It must match this regex: "^[a-zA-Z_][a-zA-Z0-9_]*$".
    # Pointer types are implicitly created at use
    # by appending '*' to a typename.
    context.type_system.add_type("fruit")

    # Update implicit cast table so that "uint32" can cast to "fruit"
    context.type_system.update_implicit_cast({"uint32": ["fruit"]})

    print "uint32 -> fruit:", context.type_system.can_implicit_cast("uint32",
                                                                   "fruit")

    # All types that can cast to uint32 will be able to cast to fruit

    print "uint16 -> fruit:", context.type_system.can_implicit_cast("uint16",
                                                                    "fruit")

    # But float cannot cast to fruit

    print "float -> fruit:", context.type_system.can_implicit_cast("float",
                                                                    "fruit")


    return context

if __name__ == '__main__':
    frontend_example()