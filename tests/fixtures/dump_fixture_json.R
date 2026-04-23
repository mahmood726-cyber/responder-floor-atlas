# Dump the fixture as JSON to stdout using jsonlite
args <- commandArgs(trailingOnly = TRUE)
rda_path <- if (length(args) > 0) args[1] else "tests/fixtures/fixture_R001_data.rda"
env <- new.env(parent = emptyenv())
loaded <- load(rda_path, envir = env)
obj <- get(loaded[1], envir = env)
cat(jsonlite::toJSON(obj, auto_unbox = TRUE, dataframe = "rows", digits = 15))
