from mlvm.ir import *
from mlvm.jit import *
from mlvm.llvm.jit import *
from mlvm.llvm.backend import *
from mlvm.llvm.ext import arraytype as ext_arraytype
import llvm.core as lc
import numpy as np
from ctypes import *
from .support import sample_call_function_1, sample_call_function_2
import math
import unittest
import logging
logger = logging.getLogger(__name__)

class TestPointer(unittest.TestCase):
    def test_pointer_1(self):

        context = Context(TypeSystem())
        context.install(ext_arraytype)


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

        backend = LLVMBackend(opt=LLVMBackend.OPT_MAXIMUM)
        backend.install(ext_arraytype)

        manager = LLVMExecutionManager(opt=LLVMExecutionManager.OPT_MAXIMUM)

        jit = JIT(manager, {'': backend})
        function = jit.compile(funcdef)

        x, y = 321, 123
        a = c_int(x)
        b = function(byref(a), y)

        # the value should be swapped
        self.assertEqual(x, b)
        self.assertEqual(y, a.value)

if __name__ == '__main__':
    unittest.main()
