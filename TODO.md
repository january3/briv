 * add id keyw to rule. id means that the field name is taken from regular
   expression. that would allow stuff like '(.*): (.*)' to work and
   automatically populate the results.
 * add default behavior when no config.yaml or template.md is present
 * add defalt printer rules like {{ TABLE }} and {{ LIST }} that would
   automatically generate tables and lists without having to specify
   anything
