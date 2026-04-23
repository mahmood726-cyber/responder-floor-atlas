# tests/fixtures/kccq_stable_cluster.R
# Known-stable cluster: 5 trials where continuous-to-responder mapping is well-behaved
# under normal approximation (symmetric, unbounded by scale limits).
# Responder count per arm = round(p * n) where p = pnorm((mean - 5)/sd) for d=+1, delta=5.
# Flat Pairwise70-schema: two Analysis.numbers (1=continuous, 2=dichotomous), same Study names.

studies  <- paste0("T", 1:5)
mean_t   <- c(8, 12, 10, 9, 11)
sd_t     <- c(15, 18, 16, 17, 15)
n_t      <- c(100L, 150L, 80L, 120L, 200L)
mean_c   <- c(3, 4, 5, 3.5, 4.5)
sd_c     <- c(15, 18, 16, 17, 15)
n_c      <- n_t

p_t <- pnorm((mean_t - 5) / sd_t)
p_c <- pnorm((mean_c - 5) / sd_c)
events_t <- as.integer(round(p_t * n_t))
events_c <- as.integer(round(p_c * n_c))

# Analysis 1: continuous change from baseline
cont <- data.frame(
  Analysis.group    = 1L,
  Analysis.number   = 1L,
  Analysis.name     = "KCCQ Overall Summary (change)",
  Subgroup          = "",
  Subgroup.number   = 1L,
  Applicability     = "",
  Study             = studies,
  Study.year        = 2020L + seq_along(studies) - 1L,
  GIV.Mean          = NA_real_,
  GIV.SE            = NA_real_,
  Experimental.mean = mean_t,
  Experimental.SD   = sd_t,
  Experimental.cases = NA_integer_,
  Experimental.N    = n_t,
  Control.mean      = mean_c,
  Control.SD        = sd_c,
  Control.cases     = NA_integer_,
  Control.N         = n_c,
  O.E               = NA_real_,
  Variance          = NA_real_,
  Weight            = NA_real_,
  Mean              = NA_real_,
  CI.start          = NA_real_,
  CI.end            = NA_real_,
  Footnotes         = "",
  review_url        = "",
  review_doi        = "",
  stringsAsFactors  = FALSE
)

# Analysis 2: responders (dichotomous, analytically derived event counts)
dich <- data.frame(
  Analysis.group    = 1L,
  Analysis.number   = 2L,
  Analysis.name     = "KCCQ Overall Summary (responders)",
  Subgroup          = "",
  Subgroup.number   = 1L,
  Applicability     = "",
  Study             = studies,
  Study.year        = 2020L + seq_along(studies) - 1L,
  GIV.Mean          = NA_real_,
  GIV.SE            = NA_real_,
  Experimental.mean = NA_real_,
  Experimental.SD   = NA_real_,
  Experimental.cases = events_t,
  Experimental.N    = n_t,
  Control.mean      = NA_real_,
  Control.SD        = NA_real_,
  Control.cases     = events_c,
  Control.N         = n_c,
  O.E               = NA_real_,
  Variance          = NA_real_,
  Weight            = NA_real_,
  Mean              = NA_real_,
  CI.start          = NA_real_,
  CI.end            = NA_real_,
  Footnotes         = "",
  review_url        = "",
  review_doi        = "",
  stringsAsFactors  = FALSE
)

kccq_stable_cluster_data <- rbind(cont, dich)
save(kccq_stable_cluster_data, file = "tests/fixtures/kccq_stable_cluster_data.rda")
cat("Written kccq_stable_cluster_data.rda --", nrow(kccq_stable_cluster_data), "rows\n")
