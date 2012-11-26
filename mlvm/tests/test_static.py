from mlvm.ir import *
from mlvm.jit import *
from mlvm.static import *
from mlvm.llvm.backend import *
from mlvm.llvm.static import *
from mlvm.llvm.ext import arraytype as ext_arraytype
from .support import sample_array_function_1
import unittest
import tempfile
import subprocess
import os
import logging
logger = logging.getLogger(__name__)

class TestStaticCompiling(unittest.TestCase):
    def test_static_array_function_1(self):
        context = Context(TypeSystem())
        context.install(ext_arraytype)

        backend = LLVMBackend(opt=LLVMBackend.OPT_MAXIMUM)
        backend.install(ext_arraytype)

        header = LLVMCWrapperGenerator()
        compiler = Compiler(LLVMCompiler(), {'': backend},
                            wrapper=header)

        for elemtype in ['float', 'double']:
            arraytype = "array_%s" % elemtype
            funcdef = sample_array_function_1(context, arraytype)
            compiler.add_function(funcdef)

        logger.debug("List functions:")

        for fname, fargs in compiler.list_functions():
            logger.debug("%s(%s)", fname, ', '.join(fargs))

        logger.debug("Assembly:\n%s", compiler.write_assembly())

        curdir = os.path.dirname(os.path.abspath(__file__))
        def local_dir(x):
            return os.path.join(curdir, "test_static_array_function_1", x)
    
        with open(local_dir("foo.o"), "wb") as fout:
            compiler.write_object(fout)

        with open(local_dir("foo.h"), "wb") as fout:
            header.write(fout)

        # compile it
        subprocess.check_call(["gcc",
                               "-Wl,-no_pie", # suppress warning on darwin
                               "-o",
                               local_dir("test_foo"),
                               local_dir("test_foo.c"),
                               local_dir("foo.o")])
        # run test
        subprocess.check_call(local_dir("test_foo"))

if __name__ == '__main__':
    unittest.main()
