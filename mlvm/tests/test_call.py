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

class TestCall(unittest.TestCase):
    def test_call_function_1(self):
        context = Context(TypeSystem())
        context.install(ext_arraytype)

        funcdef = sample_call_function_1(context)

        logger.debug(funcdef)

        # implement float sin(float) directly into the llvm module
        sinmodule = lc.Module.new('sin.impl')
        fnty = lc.Type.function(lc.Type.float(), [lc.Type.float()])
        mangled = LLVMBackend.mangle_function('sin', ('float',))
        sinf = sinmodule.add_function(fnty, mangled)
        b = lc.Builder.new(sinf.append_basic_block('entry'))
        intr = lc.Function.intrinsic(sinmodule, lc.INTR_SIN, [lc.Type.float()])
        retval = b.call(intr, [sinf.args[0]])
        b.ret(retval)

        # do jit
        backend = LLVMBackend(opt=LLVMBackend.OPT_MAXIMUM)
        backend.install(ext_arraytype)
        backend.add_extra_library(sinmodule)

        manager = LLVMExecutionManager(opt=LLVMExecutionManager.OPT_MAXIMUM)

        jit = JIT(manager, {'': backend})
        function = jit.compile(funcdef)

        logger.debug("jit'ed funciton\n%s", function)

        # test the function
        X = np.random.random(100.)
        expect = np.sin(X)
        got = np.vectorize(lambda X: function(X))(X)
        self.assertTrue(np.allclose(expect, got))

    def test_call_function_2(self):
        context = Context(TypeSystem())
        context.install(ext_arraytype)

        funcdef = sample_call_function_2(context)

        logger.debug(funcdef)

        # implement int32 incr(int32)
        incrdef = context.get_function("incr").get_definition(('int32',))
        incrimpl = incrdef.implement()
        incrimpl.attributes.add('in')
        b = Builder(incrimpl.append_basic_block())
        b.ret(b.add(incrimpl.args[0], b.const('int32', 1)))

        # do jit
        backend = LLVMBackend(opt=LLVMBackend.OPT_MAXIMUM)
        backend.install(ext_arraytype)
        
        manager = LLVMExecutionManager(opt=LLVMExecutionManager.OPT_MAXIMUM)

        jit = JIT(manager, {'': backend})
        jit.compile(incrdef)
        function = jit.compile(funcdef)

        logger.debug("jit'ed funciton\n%s", function)
        
        # test the function
        X = np.arange(100)
        expect = X + 1
        got = np.vectorize(lambda X: function(X))(X)
        self.assertTrue(np.allclose(expect, got))

if __name__ == '__main__':
    unittest.main()
