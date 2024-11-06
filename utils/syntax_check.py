#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
import os
import ast
import sys
import argparse
import pprint
import datetime

RED   = "\033[1;31m"  
BLUE  = "\033[1;34m"
CYAN  = "\033[1;36m"
GREEN = "\033[0;32m"
RESET = "\033[0;0m"
BOLD    = "\033[;1m"
REVERSE = "\033[;7m"
EXCLUDE = ["./static", "./bustime/static", "./addons", "./node_modules", "./.git", "./uploads", "./sounds"]

def get_file_names(folder):
    names = []
    if any(folder.startswith(excluded) for excluded in EXCLUDE):
        return names
    # uncomment to find out slow parts
    # print(datetime.datetime.now(), folder)
    for name in os.listdir(folder):
        if os.path.isfile(os.path.join(folder, name)) \
                and name.endswith('.py') \
                and not name.startswith('._'):
            names.append(os.path.join(folder, name))
        if os.path.isdir(os.path.join(folder, name)) \
                and not '.venv' in name:
            # pprint.pprint(name)
            names = names + get_file_names(os.path.join(folder, name))
    return names

def test_source_code_compatible(code_data):
    try:
        return ast.parse(code_data)
    except SyntaxError as exc: 
        # print(code_data)
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Thit script is trying to parse python file and make syntax tree")
    parser.add_argument(dest='folder', metavar='folder', nargs='?')
    parser.add_argument('-m', dest="modernize", action="store_true", help="Modernize source file")
    parser.add_argument('-p', dest="pedantic", action="store_true", help="Pedantic analyze")
    args = parser.parse_args()
    folder = "."#args.folder
    make_modern = args.modernize
    pedantic = args.pedantic
    names = get_file_names(folder)
    status = 0
    for name in names:
        if 'venv' in name: pprint.pprint(name)
        if make_modern:
            os.system('python-modernize -v -w %s' % name)

        if pedantic:
            status = os.system('pylint --load-plugins pylint_django --extension-pkg-whitelist=ujson --disable=R,C,W %s' % name)
        else:
            ast_tree = test_source_code_compatible(open(name, encoding='utf-8', errors='ignore').read())
            if not ast_tree:
                sys.stdout.write(RED)            
                print("File couldn't get loaded: %s" % name)
                os.system('pylint --load-plugins pylint_django --extension-pkg-whitelist=ujson --disable=R,C,W %s' % name)
                sys.stdout.write(RESET)
                status = 1
    exit(status)
