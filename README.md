# briv – tiny script for summarizing files

Briv is a tiny script that combines a simple parser and formatter in order
to summarize files. I use it to summarize README files in my projects.

Other than Python 3, it does not have any requirements, however for it to
be useful, you need to know at least a bit of regular expressions. It helps
to know Python but that is not necessary.

## Quick start

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

