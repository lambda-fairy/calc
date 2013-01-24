#!/usr/bin/env python
"""calclib - Stuff used by calc"""

from __future__ import print_function

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

# Python 3.x support
try:
    reduce
except NameError:
    from functools import reduce

LEFT, RIGHT = 1, 2
UNARY, BINARY = 1, 2

class Number(float):
    def __new__(cls, value, pos=None):
        self = float.__new__(Number, value)
        self.pos = pos
        return self

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

    def __init__(self, pos=None):
        if self.__class__ is Operator:
            raise NotImplementedError("Operator class is abstract; it cannot be called directly")
        self.pos = pos

    def __call__(self, *args):
        """Call the operator with the specified arguments."""
        return self.__class__.func(*args)

    def __repr__(self):
        return self.__class__.__name__

    def __str__(self):
        return self.__class__.name

def wrap_div_by_zero(func):
    """A little hack to change the message returned by ZeroDivisionError.

    The default message is "float division by zero", which sounds
    confusing (what's a "float"?) so this wrapper changes it to simply
    "division by zero" instead.
    """
    def newfunc(*args):
        try:
            return func(*args)
        except ZeroDivisionError:
            raise ZeroDivisionError("division by zero")
    return newfunc

def create_operator_class(clsname, name_, nargs_, rank_, func_, assoc_):
    """Factory function for creating a new operator class."""
    class newop(Operator):
        name = name_
        nargs = nargs_
        rank = rank_
        func = staticmethod(wrap_div_by_zero(func_))
        assoc = assoc_
    newop.__name__ = clsname
    return newop

def factorial(num):
    """Factorial function."""
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

# Parentheses aren't technically operators, but it's easier on the
# parser to treat them that way
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

def should_be_right_unary(prev_token):
    """Helper function for tokenize()."""
    # A symbol should be interpreted as a right associative unary operator if:
    # 1. It is the first symbol in the expression
    return (prev_token is None
    # 2. It is preceded by a '('
            or isinstance(prev_token, LeftParenthesis)
    # 3. It is preceded by a binary operator or another right associative unary operator
            or (isinstance(prev_token, Operator)
                and (prev_token.nargs == 2 or prev_token.assoc == RIGHT)))

def tokenize(s):
    """Convert a string into a list of tokens."""
    s = s.strip()
    pos = 0
    tokens = []

    while pos < len(s):
        # Match the regex against the string
        m = token_re.match(s, pos)
        d = m.groupdict()

        # Numbers
        if d["number"] is not None:
            tokens.append(Number(d["number"], pos))

        # Symbols are interpreted as operators
        elif d["symbol"]:
            key = d["symbol"]

            # Special-case '(' and ')'
            if key == "(":
                tokens.append(LeftParenthesis(pos))
            elif key == ")":
                tokens.append(RightParenthesis(pos))

            # Decide what type of operator we have
            else:
                prev_token = tokens[-1] if len(tokens) > 0 else None
                # Right associative unary operators follow funny rules
                if should_be_right_unary(prev_token):
                    if key in unary and unary[key].assoc == RIGHT:
                        tokens.append(unary[key](pos))
                    else:
                        if key not in unary and key not in binary:
                            raise CalcSyntaxError("invalid operator: %s" % key)
                        else:
                            raise CalcSyntaxError("operator '%s' is in the wrong place" % key)
                else:
                    if key in unary and unary[key].assoc == LEFT:
                        tokens.append(unary[key](pos))
                    elif key in binary:
                        tokens.append(binary[key](pos))
                    else:
                        if key not in unary and key not in binary:
                            raise CalcSyntaxError("invalid operator: %s" % key)
                        else:
                            raise CalcSyntaxError("operator '%s' is in the wrong place" % key)

        # Words can be interpreted as either...
        elif d["word"]:
            key = d["word"]
            # ... variables
            if key in constants:
                tokens.append(constants[key])
            # ... or functions.
            elif key in unary:
                tokens.append(unary[key](pos))
            else:
                raise CalcNameError("I don't know what '%s' means" % key)

        # Update the position to read the next token
        pos = m.end()
    return tokens

def implicit_multiplication(tokens):
    """Insert bits and pieces to support implicit multiplication."""
    tokens = tokens[:]
    i = 0
    while i < len(tokens)-1:
        if isinstance(tokens[i], (RightParenthesis, Number)) and \
           isinstance(tokens[i+1], (LeftParenthesis, Number)):
            tokens.insert(i+1, binary['*'](pos=tokens[i+1].pos))
        i += 1
    return tokens

def to_rpn(tokens):
    """Convert a list of tokens to reverse Polish notation using the
    shunting yard algorithm.

    See <http://en.wikipedia.org/wiki/Shunting_yard_algorithm>
    """
    # Output, in reverse Polish order
    out = []
    # Operator stack
    stack = []

    for token in tokens:

        # Number
        if isinstance(token, Number):
            # Write directly to output
            out.append(token)

        # Left bracket
        elif isinstance(token, LeftParenthesis):
            # Push onto the stack
            stack.append(token)

        # Right bracket
        elif isinstance(token, RightParenthesis):
            # Pop off operators, appending them to the output, until we hit a left bracket
            try:
                while not isinstance(stack[-1], LeftParenthesis):
                    out.append(stack.pop())
            except IndexError:
                raise CalcSyntaxError("too many right parentheses")
            else:
                stack.pop() # the left parenthesis

        # Other operators
        elif isinstance(token, Operator):
            # Pop off any lower ranking operators
            while (stack and
                   ((token.assoc == LEFT and token.rank >= stack[-1].rank)
                    or (token.assoc == RIGHT and token.rank > stack[-1].rank))):
                out.append(stack.pop())
            # Then push the current operator onto the stack
            stack.append(token)

        else:
            raise ValueError("found foreign object: %s" % repr(token))

    # Finally, pop off anything still on the stack
    while stack:
        operator = stack.pop()
        if isinstance(operator, LeftParenthesis):
            raise CalcSyntaxError("too many left parentheses")
        else:
            out.append(operator)

    return out

def eval_rpn(tokens):
    """Evaluate a list of tokens in reverse Polish order."""
    stack = []

    for token in tokens:
        if isinstance(token, Number):
            stack.append(token)
        elif isinstance(token, Operator):
            if len(stack) < token.nargs:
                raise CalcSyntaxError("not enough values for %s" % token)
            else:
                # Replace the operator's arguments with the result
                stack[-token.nargs:] = [token(*stack[-token.nargs:])]
        else:
            raise ValueError("found alien object: %s" % repr(token))

    # At the end of the computation, there should be exactly one value
    # left on the stack
    if len(stack) != 1:
        raise CalcSyntaxError("I don't understand what you're trying to say")
    else:
        return stack[0]

def main():
    """Test a few things."""
    # test the tokenizer
    for s in ("123", "5.5", ".15", "26.", # individual tokens
              "- 66.1+ 2",        # basic expression
              "-sin (-pi )",    # words
              "2! + -5!",
              "-2^2",
              "4.2e"           # implied multiplication
              ):
        print('testing', s)
        print(s.ljust(12), "==>", eval_rpn(to_rpn(implicit_multiplication(tokenize(s)))))

if __name__ == "__main__":
    main()
