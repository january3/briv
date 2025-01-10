This is a simple script which generates a table of projects based on the
project metadata in the README.md files of the projects. It is not very
clever.

First, you need a list of all README files that you wish to process. Either
generate a flat text file called `projects.txt` with one path per line, or a yaml file 
called `projects_list.yaml` with the following structure:

```yaml
projects:
 - name: project_name
   readme: /path/to/README.md
   category: BIH
 - name: another_project
   readme: (etc)
   category: Something_Else_Entirely
```

The YAML has the advantage that you can specify explicitly the name and you
can add category and other information.

## Information sourced from README.md files

Following lines of the README.md of a project can be parsed by the script:

```markdown
- P.I.: [First Last](mailto:first.last@charite.de)
- CUBI contact e-mail: [First Last](mailto:first.last@bih-charite.de)
- Client contact e-mail: [First Last](mailto:firs.last@charite.de)
- SODAR project UUID: 1234-1234-1234
- SODAR URL: https://sodar.bihealth.org/project/1234-1234-1234/
- CUBI gitlab URL:
- HPCC directory: /data/cephfs-1/work/groups/cubi/projects/project-dir
- HPCC tier 2: /data/cephfs-2/work/groups/cubi/projects/project-dir
```

Some of the missing information (like the tier 1 directory or SODAR URL)
are filled out automatically if missing.

The directories, if defined, are checked for presence on the file system.
If a directory cannot be found, it will not be shown. However, if the
directory is missing, the directory in which the README file is found will
be used as a fallback. The script recognizes whether README is in tier 1
(/data/cephfs-1) or tier 2 (/data/cephfs-2).

In addition, the script tries to guess the latest modification date based
on the last file or directory modification date in the main (tier 1)
project directory (plus tier 2 if defined), however disregarding README.md
(that is, modifications to README do not count).

## Running the script

Running the script is a bit weird because I wanted to be able to run it
without providing any arguments.
 
By default, the script will look for a file called `project_list.yaml` to
process, and a file called `README_template.md` to use as a template. It
will then produce the file README.md. In addition, the script will create a
CSV file called `projects.csv` with the same information.

This is because I would like to get a gitlab page with my projects with minimal hassle. 

However, you can specify all sorts of options.

## Template

The readme template is a markdown file with placeholders which will be
replaced by the respective project information. The placeholders are
currently defined as follows:

```
{{ PROJECT_[TABLE|LIST][ | <filter>[, <filter2> [,...] ] [|[ desc] sort_key ] }}
```

That means, projects can be represented either as a table (`PROJECT_TABLE`) or as a list
(`PROJECT_LIST`). In addition, filters and sorting can be applied to the projects.

### Filtering

A filter consists of a key, an operator, and a value. The key is one of the
fields in the project metadata, the operator is one of `=`, `!=`, `>`, `<`,
`>=`, `<=`, `~` (contains) and `!~` (does not contain). Filters may be
joined by commas which is equivalent to a logical AND. For anything more
complex, use the CSV file.

For example, the following will attempt to only show projects that were
modified since beginning of 2024 and which contain the string "Sara" in any
of the fields (like project name, client name, etc.):

```
{{ PROJECT_TABLE | last_update > "2024-01-01", text ~ "Sara" }}
```

If a key is not found in a record, that counts as no match (i.e. the record
will be suppressed); if the key is invalid (i.e., not found in any of the records),
then no records will be shown.

The valid keys can be glimpsed in the CSV file. You can add any number of
additional keys to the projects yaml file.

### Sorting


## Parsing

By default, the script uses a parsing configuration that is suitable for
our standard readme files. However, the parsing is fully configurable.

The parser is defined in the config.yaml file (you can load alternative
parsers using the -c / --config option), in section 'parser'. 

Each entry of the parser defines one key to be processed. The result of
the parsing can one main key or multiple sub-keys, depending on the
configuration of the key.

In order to work, a key must define a regular expression which is applied
to the text of the README file. The matching groups can be taken directly
as values, or can be passed on to a custom function.

Here is the simplest variant. The key 'name' will be extracted from the
first matching group of the regular expression:


```yaml
parser:
  rules:
    name:
      regex: "^NAME: (.*)$"
      group: 1
```

This entry will result in defining the key `name` with value from the first matching group of the
README file.

More than one groups can be defined and used if you use the `subkeys`
keyword (see below).


Alternatively, the whole match result (returned by `re.match`) can be passed to a
custom function which can be defined in a separate python file (by default
it is called `custom_functions.py`, but that can be changed with the -f /
--functions parameter).

The function must take one value as argument. The first and only argument
is the whole regex match (returned by `re.match`).

The function must return either a value or a dictionary. In the latter
case, the keys of the dictionary are used to construct the final keys, so
for example if the main key is "name", and the dictionary returned by the
function contains keys `first` and `last`, the final keys will be
`name_first` and `name_last`. For example, consider the following python
function:

```python
def parse_pi(match):
    name = match.group(1)
    email = match.group(2)
    return {"name": name, "email": email}
```

and the following YAML parser specification:

```yaml
parser:
  rules:
    pi:
      regex: 'PI: \[(.*)\]\(mailto:(.*)\)$'
      function: parse_pi
```

Here we extract name and e-mail from a markdown link. Note the use of
single quotes and backslashes to escape the parentheses in the regex.
The above code will define two keys, `pi_name` and `pi_email`, with the
respective values from the matching groups.

#### Subkeys

When a regex is matched, multiple group values can be extracted and used as subkeys. For example, consider the following

```yaml
parser:
  rules:
    pi:
      regex: 'pi: \[(.*)\]\(mailto:(.*)\)$'
      subkeys:
        name:
          group: 1
        email:
          group: 2
        link:
          function: get_link
```

This will define two keys, `pi_name` and `pi_email`, with the respective values from the matching groups.

Similarly, we can define a function which returns an additional value (or a
dictionary) which will be used as a subkey. For example, consider the following python function which constructs
an alternative link:

```python
import html

def get_link(match):
    name = html.escape(match.group(1))
    email = match.group(2)
    return f"mailto:{email}?subject=Project%20inquiry%20for%20{name}"
```
