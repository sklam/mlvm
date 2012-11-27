from distutils.core import setup

setup(
      name = "mlvm",
      license = "BSD",
      description = "Mid-Level Virtual Machine",
      packages = ['mlvm',
                  'mlvm.tests',
                  'mlvm.llvm',],
      version = "0.1",
)
