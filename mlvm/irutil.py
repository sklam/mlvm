import contextlib
from mlvm.ir import Builder

@contextlib.contextmanager
def for_loop(builder):
    bbentry = builder.basic_block
    bbcond = builder.append_basic_block()
    bbbody = builder.append_basic_block()
    bbstep = builder.append_basic_block()
    bbend = builder.append_basic_block()
    class loop:
        '''
        Use loop.cond(), loop.body() and loop.step() in a with-context.
        '''
        @contextlib.contextmanager
        def cond(self):
            '''
            Begin implementation of for-condition block.
            '''
            assert builder.basic_block is bbentry
            builder.branch(bbcond)
            builder.set_basic_block(bbcond)
            def setcond(pred):
                '''
                Set the predicate that controls the entrance to the loop body.
                '''
                self.predicate = pred
            yield setcond
            builder.condition_branch(self.predicate, bbbody, bbend)

        @contextlib.contextmanager
        def body(self):
            '''
            Begin implementation of for-body block.
            '''
            builder.set_basic_block(bbbody)
            yield

        @contextlib.contextmanager
        def step(self):
            '''
            Begin implementation of for-step block.
            '''
            builder.set_basic_block(bbstep)
            yield
            builder.branch(bbcond)

        def break_loop(self):
            '''Break out of the the loop-body
            '''
            builder.branch(bbend)

        def continue_loop(self):
            '''Skip ahead into step block
            '''
            builder.branch(bbstep)

    yield loop()
    builder.set_basic_block(bbend)


@contextlib.contextmanager
def for_range(builder, index, stop, step=None):
    step = step or builder.const(index.type, 1)
    with for_loop(builder) as loop:
        with loop.cond() as setcond:
            pred = builder.compare('<', index, stop)
            setcond(pred)
        with loop.body():
            yield
        with loop.step():
            index_next = builder.add(index, step)
            builder.assign(index_next, index)

@contextlib.contextmanager
def if_else(builder, pred):
    bbentry = builder.basic_block
    bbtrue = builder.append_basic_block()
    bbfalse = builder.append_basic_block()
    bbend = builder.append_basic_block()

    builder.condition_branch(pred, bbtrue, bbfalse)

    class ifelse:
        @contextlib.contextmanager
        def true(self):
            builder.set_basic_block(bbtrue)
            yield
            builder.branch(bbend)
        
        @contextlib.contextmanager
        def false(self):
            builder.set_basic_block(bbfalse)
            yield
            builder.branch(bbend)

    yield ifelse()
    builder.set_basic_block(bbend)
