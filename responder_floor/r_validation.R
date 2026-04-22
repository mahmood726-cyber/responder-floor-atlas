# responder_floor/r_validation.R
# Reads effects + variances CSV, writes metafor REML+HKSJ results as JSON.
suppressMessages(library(metafor))
suppressMessages(library(jsonlite))

args <- commandArgs(trailingOnly = TRUE)
in_csv <- args[1]
out_json <- args[2]

d <- read.csv(in_csv)
res <- rma(yi = d$yi, vi = d$vi, method = "REML", test = "knha")

k <- res$k
pi_df <- k - 2
t_pi <- qt(0.975, df = pi_df)
pi_se <- sqrt(res$se^2 + res$tau2)

out <- list(
  k = k,
  estimate = res$b[1],
  se = res$se,
  ci_lower = res$ci.lb,
  ci_upper = res$ci.ub,
  tau2 = res$tau2,
  q_stat = res$QE,
  q_df = res$k - 1,
  pi_lower = res$b[1] - t_pi * pi_se,
  pi_upper = res$b[1] + t_pi * pi_se,
  pi_df = pi_df
)
writeLines(toJSON(out, auto_unbox = TRUE, digits = 15), out_json)
