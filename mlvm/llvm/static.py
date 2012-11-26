import llvm.core as lc
from mlvm.static import CompilerInterface
from ctypes import *

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

import logging
logger = logging.getLogger(__name__)

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


class CannotMapType(Exception):
    pass

class LLVMCWrapperGenerator(object):
    _scalar_map_ = {
        c_int8   : 'int8_t',
        c_int16  : 'int16_t',
        c_int32  : 'int32_t',
        c_int64  : 'int64_t',

        c_uint8  : 'uint8_t',
        c_uint16 : 'uint16_t',
        c_uint32 : 'uint32_t',
        c_uint64 : 'uint64_t',

        c_float : 'float',
        c_double : 'double',
        }
    
    def __init__(self):
        self.__raw = []
        self.__simple = []
        self.__names = {}

    def add_function(self, backend, funcdef, llfunc):
        # process types
        get_ctype = lambda x: self.__get_ctype(backend, x)
        ct_args = map(get_ctype, funcdef.args)
        ct_retty = get_ctype(funcdef.return_type)

        c_args = map(self.map_type, ct_args)
        c_retty = self.map_type(ct_retty)

        # process name
        name = funcdef.name
        ct = self.__names.get(name, 0)
        self.__names[name] = ct + 1
        if ct:
            name = "%s%d" % (name, ct + 1)

        # process args
        args = ', '.join("%s arg%d" % (t, i)
                         for i, t in enumerate(c_args))
        argvalues = ', '.join("arg%d" % i
                              for i in range(len(c_args)))
        data = {
            'ret' : c_retty,
            'args': args,
            'name': name,
            'raw' : llfunc.name,
            'argvalues' : argvalues,
        }

        self.__raw.append("%(ret)s %(raw)s(%(args)s);" % data)
        self.__simple.append('''
inline 
%(ret)s %(name)s(%(args)s){
    return %(raw)s(%(argvalues)s);
}           
''' % data)

    def __get_ctype(self, backend, ty):
        tyimpl = backend.get_type_implementation(ty)
        return tyimpl.ctype(backend)

    def map_type(self, cty):
        if hasattr(cty, 'contents'):
            try:
                return '%s*' % self.map_type(cty._type_)
            except CannotMapType:
                logger.warn("Mapping unknown pointer type to void*")
                return 'void*' # map unknown pointer to void *
        else:
            try:
                return self._scalar_map_[cty]
            except KeyError:
                raise CannotMapType(cty)

    def write(self, file):
        for i in self.__raw:
            file.write(i)
            file.write('\n')
        for i in self.__simple:
            file.write(i)
            file.write('\n')

    def __str__(self):
        sio = StringIO()
        self.write(sio)
        sio.flush()
        str = sio.getvalue()
        sio.close()
        return str
