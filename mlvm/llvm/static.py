import llvm.core as lc
from mlvm.static import CompilerInterface

class LLVMCompiler(CompilerInterface):
    def __init__(self):
        self.__fatmod = lc.Module.new("static.%X" % id(self))

    def add_function(self, llfunc):
        self.__fatmod.link_in(llfunc.module)
        return llfunc.name

    def write_assembly(self, file):
        self.__fatmod.to_native_assembly(file)

    def write_object(self, file):
        self.__fatmod.to_native_object(file)
