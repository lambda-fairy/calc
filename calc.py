#!/usr/bin/env python
"""The main calculator command-line interface"""

message = """
                           _     A Simple
                          /  _.| _   | _._|_ _ ._
                          \_(_||(_|_||(_| |_(_)|

                               Version 3.1
                              by Chris Wong
                           Under the Third GPL.
"""

import os
import sys

import calclib

def main():
    print >>sys.stderr, message
    try:
        while True:
            try:
                expr = raw_input('calc> ')
                if len(expr.strip()) > 0:
                    expr = calclib.tokenize(expr)
                    expr = calclib.implicit_multiplication(expr)
                    expr = calclib.to_rpn(expr)
                    res = calclib.eval_rpn(expr)
                    print ('%g' % res)
            except ValueError, ex:
                print >>sys.stderr, 'error:', ex
    except EOFError:
        print >>sys.stderr, '\ncaught EOF'
    except KeyboardInterrupt:
        print >>sys.stderr, '\ninterrupted'

if __name__ == '__main__':
    main()
