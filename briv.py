#!/usr/bin/env python3

import yaml
import os
import sys
import re
import time
import csv
import argparse
import hashlib
import importlib.util

def flatfile_load(file_path):
    """Create the dictionary from the flat file, one path per line"""
    
    with open(file_path) as f:
        paths = [ f.strip() for f in f.readlines() ]

    names = [ os.path.basename(os.path.dirname(p)) for p in paths ]

    ret = [ { 'name': names[i], 'path': paths[i] } for i in range(len(paths)) ]

    return ret

def yaml_load(file_path):
    """ Load the file list master yaml file"""

    with open(file_path, 'r') as stream:
        return yaml.safe_load(stream)

def read_template(file_path):
    """ Read the template markdown file """

    with open(file_path, 'r') as stream:
        return stream.read()

def load_function_from_file(file_path, function_name):
    """ Dyna load function from file """

    print(f"loading function: {function_name} from {file_path}", file = sys.stderr)
    spec = importlib.util.spec_from_file_location("custom_functions", file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return getattr(module, function_name)

def parse_field(ret, field):
    """ convert a_b_c into [a][b][c]... structure
        and fill in the necessary structure """

    # the idea here is that we can use a single field like 
    # "a_b_c" to create a nested structure in the dictionary
    
    key_stru = field.split("_")

    cur = ret

    # convert a_b_c into [a][b][c]... structure
    if len(key_stru) > 1:
        for i in range(len(key_stru) - 1):
            if key_stru[i] not in cur:
                cur[key_stru[i]] = { }
            cur = cur[key_stru[i]]
        field = key_stru[-1]

    return cur, field

def file_parser(file, funcs, config):
    """ parse a single file """

    file_path = file['path']
    print(f"Parsing file {file_path}", file = sys.stderr)

    ret = file.copy()

    # read the file to be parsed
    with open(file_path, 'r') as stream:
        blob = stream.read()

    # apply the rules
    for field, rule in config['parser']['rules'].items():

        match = re.search(rule['regex'], blob)

        if not match:
            print(f"Warning: no match for rule {field} in {file_path}", file = sys.stderr)
            continue

        # convert a_b_c into [a][b][c]... structure
        cur, field = parse_field(ret, field)

        # simple flat key
        if 'group' in rule:
            cur[field] = match.group(rule['group'])
            continue

        if 'function' in rule:
            cur[field] = funcs[rule['function']](match)
            continue

        # multiple subkeys
        if 'subkeys' in rule:
            if field not in cur:
                cur[field] = { }
            for subkey, subkey_group in rule['subkeys'].items():
                if 'function' in subkey_group:
                    cur[field][subkey] = funcs[subkey_group['function']](match)
                elif 'group' in subkey_group:
                    cur[field][subkey] = match.group(subkey_group['group'])

    return ret

def parser_check_rules(rules):
    """ Check the parser configuration """

    filtered_rules = { }

    for k, v in rules.items():
        if 'regex' not in v:
            print(f"Warning: no regex section in {k} of the parser config", file = sys.stderr)
        else:
            filtered_rules[k] = v
            if 'subkeys' in v and ('function' in v or 'group' in v):
               print(f"Warning: parser key {k}: subkeys ignored if function or group already present", file = sys.stderr)

    return filtered_rules

def parser_get_funcs(parser, functions_file):
    """ Get the functions to call """

    # preloading functions and checking the parser definition
    funcs = { }

    # go through config, collect the functions to call
    for k, v in parser['rules'].items():

        if 'function' in v:
            func = v['function']
            funcs[func] = load_function_from_file(functions_file, func)

        if 'subkeys' in v:
            for _, group in v["subkeys"].items():
                if 'function' in group:
                    func = group['function']
                    funcs[func] = load_function_from_file(functions_file, func)

    # preloading the post processing function
    if 'post' in parser and 'function' in config['parser']['post']:
        func = parser['post']['function']
        funcs[func] = load_function_from_file(functions_file, func)

    return funcs

def new_parser(files, functions_file, config):
    """ Fully configurable README parser """

    # checking the parser definition
    config['parser']['rules'] = parser_check_rules(config['parser']['rules'])

    funcs = parser_get_funcs(config['parser'], functions_file)
    print("Functions:", funcs, file = sys.stderr)

    # go over the files and parse them
    for f in files:
        if 'path' in f:
            parsed = file_parser(f, funcs, config)
            if 'post' in config['parser'] and 'function' in config['parser']['post']:
                func = config['parser']['post']['function']
                parsed = funcs[func](parsed)
            #print(parsed, file = sys.stderr)
            f.update(parsed)

    return files

# ------------------ Export functions ------------------

def flatten_dict(d, parent = "", sep = "_"):
    """ Flatten a dictionary """

    items = [ ]
    for k, v in d.items():
        newk = parent + sep + k if parent != "" else k

        if isinstance(v, dict):
            items.extend(flatten_dict(v, newk, sep = sep).items())
        else:
            items.append((newk, v))

    return dict(items)

def replace_nones(d, repl = "???"):
    """ Replace None values in a dictionary """

    for k, v in d.items():
        if v is None:
            d[k] = repl

    return d

def extract_all_keys(cols):
    """ Extract all keys from a format dictionary """

    vals = [ c['contents'] for c in cols ]
    keys = [ ]

    for v in vals:
        keys.extend(re.findall(r'{(\w+)}', v))

    return { k: None for k in set(keys) }

def filter_dict(pflat, keys):
    """ Filter a dictionary by keys """

    for p in pflat:
        yield { k: p.get(k) for k in keys }

def save_csv(files, file_path, config):
    """ Save the parsed file data as a CSV file """

    pflat = [ flatten_dict(f) for f in files ]

    fields = config.get('export', {}).get('csv', {}).get('fields')

    if not fields:
        fields = set()
        for p in pflat:
            fields.update(p.keys())

        # text contains the record as yaml, we don't want that
        fields = [ k for k in fields if k not in ['text'] ]

    def write_csv(file, fields, pflat):
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(filter_dict(pflat, fields))

    if not file_path:
        write_csv(sys.stdout, fields, pflat)
    else:
        with open(file_path, 'w', newline="", encoding="utf-8") as file:
            write_csv(file, fields, pflat)

    return file_path

def make_table(pflat, columns):
    """ Make the table for the output """

    all_fields = extract_all_keys(columns)
    headers = [ v['header'] for v in columns ]

    # table format string
    table_fmt = '| ' + (" | ").join([ f"{v['contents']}" for v in columns ]) + " |\n"

    # header and separator
    table = '| ' + (" | ").join(headers) + " |\n"
    table += '|-' + ("-|-").join([ '-' * len(k) for k in headers ]) + "-|\n"

    for p in pflat:
        # not all keys may be defined in the data
        p = { **all_fields, **p }

        # choose a representation for "None"
        replace_nones(p)

        # add the row
        table += table_fmt.format(**p)

    return table

def make_list(pflat, item):
    """ Make the list for the output """

    all_keys = re.findall(r'{(\w+)}', item)

    # make a dict from all_keys
    all_fields = { k: None for k in all_keys }

    output_list = ""

    for p in pflat:

        p = { **all_fields, **p }
        output_list += item.format(**p)

    return output_list


def remove_duplicates(files):
    """Check for duplicate paths, keep only the last one"""

    # reverse the list to keep the last one
    files.reverse()

    seen = set()
    files = [x for x in files if x['path'] not in seen and not seen.add(x['path'])]

    # reverse back
    files.reverse()

    return files

def generate_ids(files):
    """generate unique ids for the files"""

    for f in files:
        f['id'] =  hashlib.md5(f['path'].encode()).hexdigest()

    return files

def realpaths(files):
    """Convert the paths into absolute full paths, following symlinks etc."""

    for f in files:
        f['path'] = os.path.realpath(f['path'])

    return files

def filter_by_condition(files, condition, all_fields):
    """Filter the files by a pattern"""

    condition = condition.strip()

    if condition == "-":
        return files

    field, operator, value = re.split(r'\s*(~|!~|==|!=|<|>|<=|>=)\s*', condition)
    # check whether split was effective

    if field not in all_fields:
        print(f"Warning: probably invalid key {key}, ignoring filter `{condition}`", file = sys.stderr)
        return files

    if len(field) == 0 or len(operator) == 0 or len(value) == 0:
        print(f"Invalid condition {condition}", file = sys.stderr)
        return files

    value = int(value) if value.isdigit() else value.strip('"')

    if operator == "<":
        return [p for p in files if p[field] < value]
    elif operator == "<=":
        return [p for p in files if p[field] <= value]
    elif operator == ">":
        return [p for p in files if p[field] > value]
    elif operator == ">=":
        return [p for p in files if p[field] >= value]
    elif operator == "==":
        return [p for p in files if p[field] == value]
    elif operator == "!=":
        return [p for p in files if p[field] != value]
    elif operator == "~":
        return [p for p in files if p.get(field) and re.search(value, p.get(field))]
    elif operator == "!~":
        return [p for p in files if p.get(field) and not re.search(value, p.get(field))]
    else:
        raise ValueError(f"Unsupported operator: {operator}")

def filter_files(files, pattern_str, all_fields):
    """Filter the files by a pattern"""

    conditions = re.split(r'\s*,\s*', pattern_str)

    for c in conditions:
        files = filter_by_condition(files, c, all_fields)

    return files

def match_replace(match, files, printer, all_fields, func_file):
    """ Process a match to a moustache and produce replacement """

    m = match.groupdict()

    rule = m['rule']
    params = m['params'].strip()

    filt = m['filter'].strip() if m['filter'] else None
    sort = m['sort'].strip() if m['sort'] else None
    desc = True if m['desc'] else False

    print_style = printer[rule].get('style', 'table')

    if print_style == "function":
        func = printer[rule].get('function')
        if not func:
            return f"ERROR: No function defined for {rule}"
        func = load_function_from_file(func_file, func)
        return func(files, params)

    if filt:
        files = filter_files(files, m['filter'], all_fields)

    if sort:
        files = sorted(files, key = lambda x: x.get(sort))

        if desc:
            files.reverse()

    if print_style == "table":
        return make_table(files, printer[rule].get('columns'))
    elif print_style == "list":
        return make_list(files, printer[rule].get('item'))


def moustache_replace(printer, cont, files, func_file):
    """Replace moustache placeholders in a string"""

    if not printer:
        raise ValueError("No printer section in the config")

    files = [ flatten_dict(p) for p in files ]

    printer_rules = '|'.join(printer.keys())

    # first, these without a pattern
    pattern = r"{{ +(?P<rule>" + printer_rules + r")(?P<params>| +\| +(?P<filter>[^|\n]+)(| +\| +((?P<desc>desc) +|)(?P<sort>.+))) +}}"

    # get all possible keys
    all_fields = set()
    for p in files:
        all_fields.update(p.keys())

    def replace(match):
        """ function called to process the replacement """

        return match_replace(match, files, printer, all_fields, func_file)

    ret = re.sub(pattern, replace, cont)

    return ret

# ------------------ Main ------------------

if __name__ == '__main__':

    # parse arguments
    description = """
Generate a summary file from a list of parsed files

You can provide a list of files in a text file or in a yaml file. The files
are then processed according to the rules in the config file. The output is
then generated as one of the following:

    - template: a parsed template with customized output
    - csv: a CSV file with the fields identified in the file
    - yaml: a YAML file with the fields identified in the file

You need the config file to process the files. Please look at examples for
the config files and the template files distributed with this program.

    """
    parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--format', '-f', help='Output format: template, csv, yaml (default: template)', default = "template")
    parser.add_argument('--template', '-t', help='Path to the template (default template.md)', default = "template.md")
    parser.add_argument('--list', '-l', help='Path to the file list (text, default None)', default = None)
    parser.add_argument('--yaml', '-y', help='Path to the file list as yaml (default file_list.yaml; use "none" to ignore)', default = "list.yaml")
    parser.add_argument('--output', '-o', help='File to generate (default: stdout)', default = None)
    parser.add_argument('--config', '-c', help='Config file (default config.yaml)', default = "config.yaml")
    parser.add_argument('--functions', '-F', help='Functions file (default: custom_functions.py)', default = 'custom_functions.py')

    args = parser.parse_args()

    yaml_file = args.yaml
    list_file = args.list

    config = yaml_load(args.config)
    if not config:
        raise ValueError(f"Cannot parse {args.config}")

    if not 'parser' in config:
        raise ValueError(f"No parser section in {args.config}")

    if not os.path.exists(yaml_file) and not (list_file and os.path.exists(list_file)):
        print(f"Neither {yaml_file} nor {list_file} found", file = sys.stderr)
        sys.exit(1)

    # Load the file list file
    files = [ ]
    files += flatfile_load(args.list) if args.list and os.path.exists(args.list) else [ ]
    files += yaml_load(args.yaml)['files'] if args.yaml.lower() != "none" and os.path.exists(args.yaml) else [ ]

    # get the real paths of the files
    files = realpaths(files)

    # Check duplicates
    files = remove_duplicates(files)

    # Generate unique ids
    files = generate_ids(files)

    # parse the files
    files = new_parser(files, args.functions, config)

    if args.format == 'template' or args.format == 'yaml':
        if args.format == 'template':
            if not os.path.exists(args.template):
                print(f"Template file {args.template} not found", file = sys.stderr)
                sys.exit(1)

            # process the template
            template = read_template(args.template)
            cont = moustache_replace(config.get('printer'), template, files, args.functions)

        else:
            cont = yaml.dump(files, default_flow_style=False, sort_keys=False)

        # write to README.md or stdout
        if not args.output:
            print(cont)
        else:
            with open(args.output, 'w') as stream:
                stream.write(cont)

    elif args.format == 'csv':
        save_csv(files, args.output, config)

    else:
        raise ValueError(f"Unsupported format: {args.format}")
