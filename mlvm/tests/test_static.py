from mlvm.ir import *
from mlvm.jit import *
from mlvm.static import *
from mlvm.llvm.backend import *
from mlvm.llvm.static import *
from mlvm.llvm.ext import arraytype as ext_arraytype
from .support import sample_array_function_1
import unittest

import logging
logger = logging.getLogger(__name__)

class TestStaticCompiling(unittest.TestCase):
    def test_static_array_function_1(self):
        context = Context(TypeSystem())
        context.install(ext_arraytype)

        backend = LLVMBackend(opt=LLVMBackend.OPT_MAXIMUM)
        backend.install(ext_arraytype)

        compiler = Compiler(LLVMCompiler(), {'': backend})

        for elemtype in ['float', 'double']:
            arraytype = "array_%s" % elemtype
            funcdef = sample_array_function_1(context, arraytype)
            compiler.add_function(funcdef)

        logger.debug("List functions:")
        for fname, fargs in compiler.list_functions():
            logger.debug("%s(%s)", fname, ', '.join(fargs))
        logger.debug('assembly:\n%s', compiler.write_assembly())


if __name__ == '__main__':
    unittest.main()
