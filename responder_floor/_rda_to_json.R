# _rda_to_json.R — called by rda_loader.py as a subprocess fallback.
# Usage: Rscript _rda_to_json.R <path/to/file.rda>
# Outputs: JSON to stdout (uses jsonlite, digits=15 to preserve precision)
args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1) {
  stop("Usage: Rscript _rda_to_json.R <path/to/file.rda>")
}
rda_path <- args[1]
env <- new.env(parent = emptyenv())
loaded <- load(rda_path, envir = env)
if (length(loaded) == 0) {
  stop("No R objects found in: ", rda_path)
}
# Take the first object
obj <- get(loaded[1], envir = env)
cat(jsonlite::toJSON(obj, auto_unbox = TRUE, dataframe = "rows", digits = 15))
