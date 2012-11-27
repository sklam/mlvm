from mlvm.ir import *
from mlvm.jit import *
from mlvm.llvm.jit import *
from mlvm.llvm.backend import *
from mlvm.llvm.ext import arraytype as ext_arraytype
import llvm.core as lc
import numpy as np
from ctypes import *
from .support import sample_pointer_function_1, \
                     sample_pointer_cast_function_1
import math
import unittest
import logging
logger = logging.getLogger(__name__)

class TestPointer(unittest.TestCase):
    def test_pointer_1(self):
        context = Context(TypeSystem())
        context.install(ext_arraytype)

        funcdef = sample_pointer_function_1(context)

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

    def test_pointer_cast_1(self):
        context = Context(TypeSystem())
        context.install(ext_arraytype)

        funcdef = sample_pointer_cast_function_1(context)

        backend = LLVMBackend(opt=LLVMBackend.OPT_MAXIMUM)
        backend.install(ext_arraytype)

        manager = LLVMExecutionManager(opt=LLVMExecutionManager.OPT_MAXIMUM)

        jit = JIT(manager, {'': backend})
        function = jit.compile(funcdef)

        x = c_int32(123)
        ptr = byref(x)
        y = function(ptr)

        y_value = y.contents.value
        x.value = 321
        self.assertNotEqual(y_value, y.contents.value)
        x.value = 123
        self.assertEqual(y_value, y.contents.value)



if __name__ == '__main__':
    unittest.main()
