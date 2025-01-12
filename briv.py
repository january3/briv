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
import logging

def flatfile_load(file_path):
    """Create the dictionary from the flat file, one path per line"""
    
    if file_path:
        with open(file_path) as f:
            paths = [ f.strip() for f in f.readlines() ]
    else:
        # read from stdin
        paths = [ f.strip() for f in sys.stdin.readlines() ]

    names = [ os.path.basename(p) for p in paths ]

    ret = [ { 'name': names[i], 'path': paths[i] } for i in range(len(paths)) ]

    return ret

def default_config():
    """ Default configuration """

    config = {
            'parser': {
                'rules': {
                    'default': {
                        'regex': r"^([^:=]*) *[:=] *(.*)$",
                        'key': 1,
                        'match': 2
                        }
                    }
                }
            }

    return config

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

    logger.debug(f"loading function: {function_name} from {file_path}")
    spec = importlib.util.spec_from_file_location("custom_functions", file_path)
    module = importlib.util.module_from_spec(spec)

    try:
        spec.loader.exec_module(module)
        return getattr(module, function_name)
    except Exception as e:
        logger.debug(f"Error loading function '{function_name}' from {file_path}: {e}")
        sys.exit(1)

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

def process_match_keyword(match, match_rule):
    """ Process the 'match' keyword """

    if isinstance(match_rule, int):
        return match.group(match_rule)

    if not isinstance(match_rule, dict):
        raise ValueError(f"Invalid match rule: {match_rule}")

    ret = { }

    for k, v in match_rule.items():
        ret[k] = match.group(v)

    return ret

def process_match(obj, rule, field, funcs, match, blob):
    """ apply a rule to a blob of text """

    logger.debug(f" > --- processing rule {rule} for field {field}")

    if not match:
        logger.debug(f"Warning: no match for rule")

    # convert a_b_c into [a][b][c]... structure
    cur, field = parse_field(obj, field)

    if match and 'key' in rule:
        logger.debug(f"   --- setting key to match.group({rule['key']}) = {match.group(rule['key'])}")
        field = match.group(rule['key'])

    # rules trump everything and exclude any other processing
    if 'rules' in rule:
        logger.debug("   + --- Applying rules")
        cur[field] = { } if cur.get(field) is None else cur[field]
        logger.debug(f"Calling apply_rules with cur[field]={cur[field]}")
        apply_rules(cur[field], rule['rules'], funcs = funcs, blob = blob, match = match)
        return

    if 'string' in rule:
        cur[field] = rule['string']
    elif 'count' in rule:
        if field not in cur or not isinstance(cur[field], int):
            cur[field] = 0
        cur[field] += 1
    elif 'function' in rule:
        if match:
            logger.debug(f"Field: {field}")
            logger.debug(f"Match groups: {match.groups()}")
            logger.debug(f"Function: {rule['function']}")
            tmp = funcs[rule['function']](match)
            logger.debug(f"Function result: {tmp}")
            logger.debug(f"cur: {cur}")
            cur[field] = tmp
        else:
            cur[field] = funcs[rule['function']](blob)
    elif match:
        if 'match' in rule:
            cur[field] = process_match_keyword(match, rule['match'])
        else:
            n = len(match.groups())
            cur[field] = match.group(n)

    logger.debug("   + obj is now: \n", obj)
    return

def apply_rules(obj, rules, funcs, blob = None, match = None):
    """ applies a set of rules to a blob of text """

    if blob is None and match is None:
        logger.debug("!!! apply_rules(): No blob or match provided ==================<<<<<")
        #raise ValueError("apply_rules(): No blob or match provided")

    # apply the rules
    for field, rule in rules.items():
        bt, mt = blob is not None, match is not None

        logger.debug(f'=== Processing rule named "{field}" ===')
        logger.debug(f'    blob: {bt}, match: {mt}')

        if isinstance(rule, str):
            # rule *is* the regex
            rule = { 'regex': rule }

        if 'regex' not in rule:
            #raise ValueError(f"No regex section in rule {field} of the parser config")
            logger.debug(f"Warning: no regex section in rule '{field}' of the parser config")
            logger.debug(f"calling process_match with obj={obj}, match=={mt} and blob=={bt}")
            process_match(obj, rule, field, funcs, match, blob = blob)
            continue

        blob_cur = blob

        # for sub-rules, use the appropriate blob
        if match:
            logger.debug(f"= match is {match}")
            if 'group' not in rule:
                raise ValueError(f"No group section in rule {field} of the parser config")
            blob_cur = match.group(rule['group'])
            logger.debug(f"= + blob is now {blob_cur}")

        for curmatch in re.finditer(rule['regex'], blob_cur, flags = re.MULTILINE):
            logger.debug(f"= + Match found for {field}")
            logger.debug(f"= + Match groups: {curmatch.groups()}")
            logger.debug(f"calling process_match with obj={obj}")
            process_match(obj, rule, field, funcs, match = curmatch, blob = None)

    return


def file_parser(obj, funcs, config):
    """ parse a single file """

    file_path = obj['path']
    logger.debug(f"\n  |----------------|\n  |- Parsing file -| {file_path}\n  |----------------|")

    # read the file to be parsed
    with open(file_path, 'r') as stream:
        blob = stream.read()

    logger.debug(f"Calling apply_rules with obj={obj}")
    apply_rules(obj, config['parser']['rules'], funcs = funcs, blob = blob)

    logger.debug("[file_parser()] ret is now", obj)
    return

def parser_check_rules(rules):
    """ Check the parser configuration """

    filtered_rules = { }

    for k, v in rules.items():
        if 'regex' not in v:
            logger.debug(f"Warning: no regex section in {k} of the parser config")
        filtered_rules[k] = v
        if 'subkeys' in v and ('function' in v or 'group' in v):
           logger.debug(f"Warning: parser key {k}: subkeys ignored if function or group already present")

    return filtered_rules

def parser_get_funcs_rules(rules, functions_file, funcs_obj):
    """ Extract functions from a set of rules """

    for k, v, in rules.items():
        logger.debug(f"[parser_get_funcs_rules()]: checking rule {k}")

        if 'function' in v:
            func = v['function']
            funcs_obj[func] = load_function_from_file(functions_file, func)
        if 'rules' in v:
            parser_get_funcs_rules(v['rules'], functions_file, funcs_obj)


def parser_get_funcs(parser, functions_file):
    """ Get the functions to call """

    # preloading functions and checking the parser definition
    funcs = { }

    # go through config, collect the functions to call
    parser_get_funcs_rules(parser['rules'], functions_file, funcs)

    # preloading the post processing function
    if 'post_file' in parser: 
        for func in parser['post_file']:
            f = func['function']
            funcs[f] = load_function_from_file(functions_file, f)

    if 'post_parser' in parser: 
        for func in parser['post_parser']:
            f = func['function']
            funcs[f] = load_function_from_file(functions_file, f)

    return funcs

def new_parser(files, functions_file, config):
    """ Fully configurable README parser """

    # checking the parser definition
    config['parser']['rules'] = parser_check_rules(config['parser']['rules'])

    funcs = parser_get_funcs(config['parser'], functions_file)
    logger.debug("Functions:", funcs)

    # go over the files and parse them
    
    for i in range(len(files)):
        f = files[i]
        if 'path' in f:
            file_parser(f, funcs, config)
            if 'post_file' in config['parser']: 
                for post in config['parser']['post_file']:
                    func_name = post['function']
                    logger.debug(f"Calling post function {func_name}")
                    args = post['args'] if 'args' in post else [ ]
                    kwargs = post['kwargs'] if 'kwargs' in post else { }
                    ret = funcs[func_name](f, *args, **kwargs)
                    files[i] = ret

    logger.debug("\n  |================|\n  |- Parsing done -| \n  |================|")

    if 'post_parser' in config['parser']:
        for post in config['parser']['post_parser']:
            func_name = post['function']
            logger.debug(f"Calling post parser function {func_name}")
            args = post['args'] if 'args' in post else [ ]
            kwargs = post['kwargs'] if 'kwargs' in post else { }
            files = funcs[func_name](files, *args, **kwargs)

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

def auto_columns(pflat):
    """ Get all fields from a list of flattened dictionaries """

    tmp = { }
    for p in pflat:
        for k in p.keys():
            tmp[k] = k
    columns = [ ]

    for c in tmp.keys():
        columns.append( { 'header': c, 'contents': '{' + c + '}' } )

    return columns

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

    if columns == 'all':
        columns = auto_columns(pflat)

    logger.debug(columns)
    all_fields = extract_all_keys(columns)
    headers = [ v['header'] for v in columns ]

    logger.debug(all_fields)
    logger.debug(headers)

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
        logger.debug(f"Warning: probably invalid field {field}, ignoring filter `{condition}`")
        return files

    if len(field) == 0 or len(operator) == 0 or len(value) == 0:
        logger.debug(f"Invalid condition {condition}")
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

def sort_files(files, sort, desc, all_fields):
    """Sort the files by a field"""

    if not sort in all_fields:
        logger.debug(f"Warning: probably invalid field {sort}, ignoring sort")
        return files

    files = sorted(files, key = lambda x: x.get(sort))

    if desc:
        files.reverse()

    return files

def match_replace(match, printer, files, all_fields, func_file):
    """ 
    Process a match to a moustache and produce replacement 

    match: the match object
    printer: dictionary with the printer rules
    files: list of file dictionaries to process
    all_fields: set of all fields in the files
    func_file: file with the functions to call
    """

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
        files = filter_files(files, filt, all_fields)

    if sort:
        files = sort_files(files, sort, desc, all_fields)

    if print_style == "table":
        return make_table(files, printer[rule].get('columns'))
    elif print_style == "list":
        return make_list(files, printer[rule].get('item'))


def moustache_replace(printer, template, files, func_file):
    """
    Replace moustache placeholders in a string

    printer: dictionary with the printer rules
    template: the string to process
    files: list of file dictionaries to process
    func_file: file with the functions to call
    """

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

        return match_replace(match, printer, files, all_fields, func_file)

    ret = re.sub(pattern, replace, template)

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
    parser.add_argument('--format', '-f', help='Output format: csv, template, yaml (default: yaml)', default = "yaml")
    parser.add_argument('--template', '-t', help='Path to the template (required if format is template; implies format=template)', default = None)
    parser.add_argument('--list', '-l', help='Path to the file list (text, default None)', default = None)
    parser.add_argument('--yaml', '-y', help='Path to the file list as yaml (default file_list.yaml; use "none" to ignore)', default = "list.yaml")
    parser.add_argument('--output', '-o', help='File to generate (default: stdout)', default = None)
    parser.add_argument('--config', '-c', help='Config file')
    parser.add_argument('--functions', '-F', help='Functions file (default: custom_functions.py)', default = 'custom_functions.py')
    parser.add_argument('--debug', '-d', help='Debug mode', action = 'store_true', default = False)

    args = parser.parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level, format='%(levelname)s: %(funcName)s: %(message)s')
    logger = logging.getLogger(__name__)
    if args.debug:
        logging.debug("Debug mode on")


    if args.format == 'template' and not args.template:
        logger.debug("Template file (option -t) required for template output")
        sys.exit(1)

    if args.template:
        args.format = 'template'

    yaml_file = args.yaml
    list_file = args.list

    if not args.config:
        config = default_config()
    else:
        config = yaml_load(args.config)

    if not 'parser' in config:
        raise ValueError(f"No parser section in {args.config}")

    # Load the file list file
    files = [ ]

    if not yaml_file and not list_file:
        logger.debug(f"Neither yaml_file nor list_file provided")
        sys.exit(1)

    if args.list == '-':
        logger.debug("Reading from stdin")
        files += flatfile_load(None)
        logger.debug(f"Read {len(files)} files from stdin")
    elif args.list:
        if os.path.exists(args.list):
            files += flatfile_load(args.list)
            logger.debug(f"Read {len(files)} files from {args.list}")
        else:
            logger.debug(f"List file {args.list} not found")
            sys.exit(1)

    files += yaml_load(args.yaml)['files'] if args.yaml.lower() != "none" and os.path.exists(args.yaml) else [ ]

    if len(files) == 0:
        logger.debug(f"No files paths read, check options -y or -l")
        sys.exit(1)

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
                logger.debug(f"Template file {args.template} not found")
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
