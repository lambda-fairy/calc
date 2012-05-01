#!/usr/bin/env python
"""
calclib - Stuff used by chrisyco's Calculator
"""

# ---------------------------
#  The Process in a Nutshell
# ---------------------------
#
#             +------------+     +----------+     +------------+
# [input] >>> | tokenize() | >>> | to_rpn() | >>> | eval_rpn() | >>> [result]
#          |  +------------+  |  +----------+  |  +------------+  |
#          |                  |                |                  |
#        string         list of tokens   tokens in RPN          number

import re
import operator
import math
from copy import copy

# Python 3.x support
try:
    reduce
except NameError:
    from functools import reduce

LEFT, RIGHT = 1, 2
UNARY, BINARY = 1, 2

Number = float # I might decide to change this later

class CalcSyntaxError(ValueError):
    pass

class CalcNameError(ValueError):
    pass

class Operator(object):
    """The base class for operators.

    Do not instantiate this class directly; either inherit from this
    class and override the attributes or use create_operator_class().
    """
    name = None
    nargs = None
    rank = None
    func = None
    assoc = None
    def __init__(self, **extra_attrs):
        if self.__class__ == Operator:
            raise NotImplementedError("Operator class cannot be called directly")
        for key, value in extra_attrs.items():
            setattr(self, key, value)
    def __call__(self, *args):
        return self.__class__.func(*args)
    def __repr__(self):
        return self.__class__.__name__
    def __str__(self):
        return self.__class__.name

def fwrapper(func):
    """A little hack to change the message returned by ZeroDivisionError"""
    def newfunc(*args):
        try:
            return func(*args)
        except ZeroDivisionError:
            raise ZeroDivisionError("division by zero")
    return newfunc

def create_operator_class(clsname, name_, nargs_, rank_, func_, assoc_):
    """Create a new operator class."""
    class newop(Operator):
        name = name_
        nargs = nargs_
        rank = rank_
        func = staticmethod(fwrapper(func_))
        assoc = assoc_
    newop.__name__ = clsname
    return newop

def factorial(num):
    if num != int(num):
        raise ValueError("cannot calculate factorial of %s: number must be an integer" % num)
    elif num < 0:
        raise ValueError("cannot calculate factorial of %s: number must be non-negative" % num)
    else:
        return reduce(operator.mul, range(2, int(num)+1), 1)

binary = {
    '^': create_operator_class('Exponent',       '^', 2, 1, operator.pow,     RIGHT),
    '/': create_operator_class('Division',       '/', 2, 2, operator.truediv, LEFT),
    '*': create_operator_class('Multiplication', '*', 2, 2, operator.mul,     LEFT),
    '+': create_operator_class('Addition',       '+', 2, 3, operator.add,     LEFT),
    '-': create_operator_class('Subtraction',    '-', 2, 3, operator.sub,     LEFT),
}

unary = {
    '!':    create_operator_class('Factorial',   '!', 1, -2, factorial,      LEFT),
    '-':    create_operator_class('Negative',    '-', 1, -1, operator.neg,   RIGHT),
    '+':    create_operator_class('Positive',    '+', 1, -1, operator.pos,   RIGHT),
    'sqrt': create_operator_class('SquareRoot',  'sqrt',   1, -1, math.sqrt, RIGHT),
    'sin':  create_operator_class('Sine',        'sin',    1, -1, math.sin,  RIGHT),
    'cos':  create_operator_class('Cosine',      'cos',    1, -1, math.cos,  RIGHT),
    'tan':  create_operator_class('Tangent',     'tan',    1, -1, math.tan,  RIGHT),
    'asin': create_operator_class('InverseSine', 'arcsin', 1, -1, math.asin, RIGHT),
    'acos': create_operator_class('InverseCosine', 'arccos', 1, -1, math.acos, RIGHT),
    'atan': create_operator_class('InverseTangent', 'arctan', 1, -1, math.atan, RIGHT),
}
unary['arcsin'] = unary['asin']
unary['arccos'] = unary['acos']
unary['arctan'] = unary['atan']

LeftParenthesis = \
    create_operator_class('LeftParenthesis', '(', 0, 9999, None, 0)
RightParenthesis = \
    create_operator_class('RightParenthesis', ')', 0, 9999, None, 0)

constants = {
    'e': Number(math.e),
    'pi': Number(math.pi),
}

token_re = re.compile(r"""
    (?:
        (?P<word>   [a-z]+) # sequence of letters
      | (?P<number>
                    \d+(?:\.\d*)? # digits [ decimal-point more-digits ]
                    |\.\d+      # or decimal-point digits
        )
      | (?P<symbol> [^\s]) # anything that didn't match the others
    )
    \s*
""", re.UNICODE | re.VERBOSE)

def tokenize(s):
    """Convert a string into a list of tokens."""
    s = s.strip()
    pos = 0
    len_s = len(s)
    tokens = []
    while pos < len_s:
        m = token_re.match(s, pos)
        d = m.groupdict()
        if d["number"] is not None:
            tokens.append(Number(d["number"]))
        elif d["symbol"]:
            key = d["symbol"]
            # special-case ( )
            if key == "(":
                tokens.append(LeftParenthesis(pos=m.start()))
            elif key == ")":
                tokens.append(RightParenthesis(pos=m.start()))
            else:
                last = tokens[-1] if len(tokens) > 0 else None
                if (len(tokens) == 0
                    or isinstance(last, LeftParenthesis)
                    or (isinstance(last, Operator)
                        and (last.nargs == 2
                             or last.assoc == RIGHT))):
                    if key in unary and unary[key].assoc == RIGHT:
                        tokens.append(unary[key](pos=m.start()))
                    else:
                        if key not in unary and key not in binary:
                            raise CalcSyntaxError("invalid operator: %s" % key)
                        else:
                            raise CalcSyntaxError("operator '%s' is in the wrong place" % key)
                else:
                    if key in unary and unary[key].assoc == LEFT:
                        tokens.append(unary[key](pos=m.start()))
                    elif key in binary:
                        tokens.append(binary[key](pos=m.start()))
                    else:
                        if key not in unary and key not in binary:
                            raise CalcSyntaxError("invalid operator: %s" % key)
                        else:
                            raise CalcSyntaxError("operator '%s' is in the wrong place" % key)
        elif d["word"]:
            key = d["word"]
            if key in constants:
                tokens.append(constants[key])
            elif key in unary:
                tokens.append(unary[key](pos=m.start()))
            else:
                raise CalcNameError("I don't know what '%s' means" % key)
        pos = m.end()
    return tokens

def implicit_multiplication(tokens):
    """Insert bits and pieces to support implicit multiplication."""
    tokens = tokens[:]
    i = 0
    while i < len(tokens)-1:
        if isinstance(tokens[i], (RightParenthesis, Number)) and \
           isinstance(tokens[i+1], (LeftParenthesis, Number)):
            tokens.insert(i+1, binary['*']())
        i += 1
    return tokens

def to_rpn(tokens):
    """Convert a list of tokens to reverse Polish notation using the
    shunting yard algorithm.

    See <http://en.wikipedia.org/wiki/Shunting_yard_algorithm>
    """
    out = []
    stack = []
    for token in tokens:
        if isinstance(token, Number):
            out.append(token)
        elif isinstance(token, LeftParenthesis):
            stack.append(token)
        elif isinstance(token, RightParenthesis):
            try:
                while not isinstance(stack[-1], LeftParenthesis):
                    out.append(stack.pop())
            except IndexError:
                raise CalcSyntaxError("too many right parentheses")
            else:
                stack.pop() # the left parenthesis
        elif isinstance(token, Operator):
            while (stack and
                   ((token.assoc == LEFT and token.rank >= stack[-1].rank)
                    or (token.assoc == RIGHT and token.rank > stack[-1].rank))):
                out.append(stack.pop())
            stack.append(token)
        else:
            raise ValueError("found foreign object: %s" % repr(token))
    while stack:
        operator = stack.pop()
        if isinstance(operator, LeftParenthesis):
            raise CalcSyntaxError("too many left parentheses")
        else:
            out.append(operator)
    return out

def eval_rpn(tokens):
    stack = []
    for token in tokens:
        if isinstance(token, Number):
            stack.append(token)
        elif isinstance(token, Operator):
            if len(stack) < token.nargs:
                raise CalcSyntaxError("not enough values for %s" % token)
            else:
                stack[-token.nargs:] = [token(*stack[-token.nargs:])]
        else:
            raise ValueError("found strange object: %s" % repr(token))
    if len(stack) != 1:
        raise CalcSyntaxError("I don't understand what you're trying to say")
    else:
        return stack[0]

def main():
    """
    Test a few things.
    """
    # test the tokenizer
    for s in ("123", "5.5", ".15", "26.", # individual tokens
              "- 66.1+ 2",        # basic expression
              "-sin (-pi )",    # words
              "2! + -5!",
              "-2^2",
              "4.2e"           # implied multiplication
              ):
        print(s.ljust(12) + " ==> " + str(eval_rpn(to_rpn(implicit_multiplication(tokenize(s))))))

if __name__ == "__main__":
    main()
