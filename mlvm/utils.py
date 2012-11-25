import sys, ctypes

#
# Native address width
#
if ctypes.c_size_t == ctypes.c_uint64:
    ADDRESS_WIDTH = 8
elif ctypes.c_size_t == ctypes.c_uint32:
    ADDRESS_WIDTH = 4
else:
    raise Exception("Address width not 4 or 8 bytes?")

#
# Length of pyobject head
#
if hasattr(sys, 'getobjects'):
    PYOBJECT_HEAD_LEN = 4 * ADDRESS_WIDTH
else:
    PYOBJECT_HEAD_LEN = 2 * ADDRESS_WIDTH

#
# Offset to data pointer in a memoryview object
#
MEMORYVIEW_DATA_OFFSET = PYOBJECT_HEAD_LEN + ADDRESS_WIDTH

