from mlvm.ir import *
from mlvm.jit import *
from mlvm.llvm.jit import *
from mlvm.llvm.backend import *
from mlvm.llvm.ext import arraytype as ext_arraytype
import llvm
import numpy as np
from ctypes import *
from .support import sample_array_function_1, sample_array_function_2
import unittest
import logging
logger = logging.getLogger(__name__)

class TestArrayExtension(unittest.TestCase):
    def test_array_double(self):
        self._test_template_1('array_double', np.float64, c_double)

    def test_array_float(self):
        self._test_template_1('array_float', np.float32, c_float)

    def test_array_int32(self):
        self._test_template_2('array_int32', np.int32, c_int32)

    def _test_template_1(self, arraytype, dtype, ctype):
        context = Context(TypeSystem())
        context.install(ext_arraytype)

        funcdef = sample_array_function_1(context, arraytype)

        logger.debug(funcdef)
        backend = LLVMBackend(opt=LLVMBackend.OPT_MAXIMUM)
        backend.install(ext_arraytype)

        manager = LLVMExecutionManager(opt=LLVMExecutionManager.OPT_MAXIMUM)

        jit = JIT(manager, {'': backend})
        function = jit.compile(funcdef)

        # ensure a function is not duplicated
        f2 = jit.compile(funcdef)
        assert function == f2

        A = np.arange(10, dtype=dtype)
        B = A * 2
        C = np.empty_like(A)

        # call with ctypes
        c_double_p = POINTER(c_double)

        c_array_type = POINTER(ctype)
        n = function(A.ctypes.data_as(c_array_type),
                     B.ctypes.data_as(c_array_type),
                     C.ctypes.data_as(c_array_type),
                     A.shape[0])
        assert n == A.shape[0]

        Gold = (A + B) * 3.14
        self.assertTrue(np.allclose(Gold, C))

        # call with numpy array
        C = np.zeros_like(A)

        n = function(A, B, C, A.shape[0])
        self.assertTrue(n == A.shape[0])

        Gold = (A + B) * 3.14
        self.assertTrue(np.allclose(Gold, C))

    def _test_template_2(self, arraytype, dtype, ctype):
        context = Context(TypeSystem())
        context.install(ext_arraytype)

        funcdef = sample_array_function_2(context, arraytype)

        logger.debug(funcdef)
        backend = LLVMBackend(opt=LLVMBackend.OPT_MAXIMUM)
        backend.install(ext_arraytype)

        manager = LLVMExecutionManager(opt=LLVMExecutionManager.OPT_MAXIMUM)

        jit = JIT(manager, {'': backend})
        function = jit.compile(funcdef)

        # ensure a function is not duplicated
        f2 = jit.compile(funcdef)
        assert function == f2

        A = np.arange(10, dtype=dtype)
        B = A * 2
        C = np.empty_like(A)

        # call with ctypes
        c_double_p = POINTER(c_double)

        c_array_type = POINTER(ctype)
        n = function(A.ctypes.data_as(c_array_type),
                     B.ctypes.data_as(c_array_type),
                     C.ctypes.data_as(c_array_type),
                     A.shape[0])
        assert n == A.shape[0]

        Gold = (A + B) * 123
        self.assertTrue(np.allclose(Gold, C))

        # call with numpy array
        C = np.zeros_like(A)

        n = function(A, B, C, A.shape[0])
        self.assertTrue(n == A.shape[0])
        
        Gold = (A + B) * 123
        self.assertTrue(np.allclose(Gold, C))

if __name__ == '__main__':
    unittest.main()
