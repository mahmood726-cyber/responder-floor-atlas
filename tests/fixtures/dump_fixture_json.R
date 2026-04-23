# Dump the fixture as JSON to stdout using jsonlite
args <- commandArgs(trailingOnly = TRUE)
rda_path <- if (length(args) > 0) args[1] else "tests/fixtures/synthetic_one_review.rda"
load(rda_path)
# The loaded object name is 'fixture'
cat(jsonlite::toJSON(fixture, auto_unbox = TRUE, dataframe = "rows", digits = 15))
