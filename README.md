# briv – tiny script for summarizing files

Briv is a tiny script that combines a simple parser and formatter in order
to summarize files. I use it to summarize README files in my projects.

Other than Python 3, it does not have any requirements, however for it to
be useful, you need to know at least a bit of regular expressions. It helps
to know Python but that is not necessary.

## Quick start

### Running briv with no rules

Go to the [simple example](examples/simple) directory and run the following
code:

```bash
briv.py -l file_list.txt
```

This will go through the files listed in `file_list` and summarize them in
YAML format: 

```yaml
- name: testing
  path: /home/january/Projects/Python/briv/examples/simple/file1.txt
  id: 8ce47521533250a87769cef1a51e61c6
  description: first testing project
  url: https://example.com/testing
- name: training
  path: /home/january/Projects/Python/briv/examples/simple/file2.txt
  id: 509ae8aeab3ad6d05c45fd9d595248d9
  description: The training project
  url: https://example.com/training
```

By default, briv looks for a regular expression that consists
of two words separated by a colon or equal sign. Here, the files are of the
form:

```text
name: testing
description: first testing project
url: https://example.com/testing
```

Say, you would like to summarize a number of R projects in tabular form.
R projects have a file called `DESCRIPTION` that contains metadata about
the project. You can start by generating a list of all `DESCRIPTION` files:

```bash
find . -name DESCRIPTION > descriptions.txt
```

You can find an example in the [examples/Rprojects](examples/Rprojects) directory.

Second, you need a YAML configuration file that specifies how to parse the
DESCRIPTION files. The YAML file has a `parser` section that contains the
regular expressions used to find the fields. Here is how it might look
like:

```yaml
parser:
  rules: 
    package:
      regex: 'Package: (.+)'
      group: 1
    version:
      regex: 'Version: (.+)'
      group: 1
    title:
      regex: 'Title: (.+)'
      group: 1
```

Save it as `config.yaml` and you can run briv like this:

```bash
briv -l descriptions.txt -f csv
```

briv requires a config file, and the default name is `config.yaml`. The 
`-f csv` means that the output will be in CSV format. You can also use
`-f json` or `-f yaml`.

However, the actual use scenario allows to process a template, for example
a markdown file. This template may be as simple as this:


## Details

each rule must be named

The rule might either contain a regex or another dictionary.

If the rule simply consists of a regex, then the rule will apply the regex
to the input and use the value of the first match group as the value of the
resulting object. The name of the resulting object will be the name of the
rule. Example:

```yaml
parser:
  rules:
    name: '^name: (\w+)$'
```

Following keywords may be specified in a rule:

regex: this matches the input string (file contents or subgroup in case of
sub-rules). The match can be used subsequently to specify the value of the
field, the name of the field, and apply sub-rules to the matched fragments.

key: indicates how the resulting object should be named.
  if absent, it is the name of the rule. Alternatively, it is the #no of the
  match group from the regex. this allows to create rules producing multiple
  key-val pairs by repeatedly matching the same pattern. Use 0 to match the
  full regex. 

  However: if the rule name contains underscores, then the value
  specified by key will only replace the last part. So if the rule name is
  "foo_bar_baz", and the key matches the string "quack", then the resulting
  object will end up being "foo_bar_quack". See the 
  [INI parser example](examples/ini).

group: this is only useful in sub-rules. It indicates the partial match on
which the rule should act. Therefore, it is possible to use a rule to catch
a fragment of the file (e.g. a section or a single line), and then apply
other rules to that fragment. If group is 0, the whole match is used.

The next keys are used to specify the value of the resulting object and at
most one of them may be present. If none of them is present, a silent
'match' is assumed, using the last group found in the regex.

 * string: This sets the value to the given string.
 * count: records the number of times the regex matched. If you combine
   this with the 'key' keyword, you can for example count the occurences of
   different words matching the same pattern.
 * match: this is the number of the group from the regex, in which case
          the result is a simple key-val pair. OR it is a dict, in which
          case the result is a dict. The dict must only contain keys and
          group numbers, and the keys will be assigned the values of the
          corresponding groups.
Example:

```yaml
parser:
  rules:
    website: '^url: (https://([^/\n]+)(.+))$'
    match:
      url: 1
      domain: 2
      relative: 3
```

 * rules: it is a dict containing further rules. Now each rule must have a group as well as a
          regex key. group indicates the matched fragment which this rule
          works on. If group is absent, the whole text will be used. Other than that, it has the same syntax (i.e., it can
          contain the key, value, function and rules keywords).
 * function: This function will then be called with the match object as argument and the result 
             will be inserted into the result under
             the given field.
