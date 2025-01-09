#!/usr/bin/env python3
""" Convert a list of README paths into a YAML file. """
""" Reads from STDIN and writes to STDOUT. """

import os
import yaml
import sys

if __name__ == '__main__':
    if len(sys.argv) > 2:
        print("Usage: cat file.txt | python3 list2yaml.py [category] > file.yaml")
        sys.exit(1)

    if len(sys.argv) == 2:
        category = sys.argv[1]
    else:
        category = None

    # read filenames from STDIN
    lines = sys.stdin.readlines()
    lines = [ line.strip() for line in lines ]

    # tilde expansion
    lines = [ os.path.expanduser(line) for line in lines ]

    # warning to stderr for every non-existent file
    for line in lines:
        if not os.path.exists(line):
            print("Warning: file does not exist: " + line, file=sys.stderr)

    # remove dirs which do not exist
    lines = [ line for line in lines if os.path.exists(line) ]

    projects = [ { 'name': os.path.basename(os.path.dirname(line)), 'readme': os.path.realpath(line) } for line in lines ]

    if category:
        projects = [ { 'name': project['name'], 'readme': project['readme'], 'category': category } for project in projects ]

    print("projects:")

    for p in projects:
        print("  - name: " + p['name'])
        print("    readme: " + p['readme'])
        if category:
            print("    category: " + category)
