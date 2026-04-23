# tests/fixtures/make_fixture.R
# Synthetic Pairwise70-schema review with both continuous and dichotomous MAs
# for the same outcome (KCCQ OS), so scan_dual_framing detects dual-framing.

# Three trials x two MAs (Analysis.number=1 continuous, Analysis.number=2 dichotomous).
# Same Study names across both MAs -> dual-framing.
studies <- c("T1", "T2", "T3")

# Analysis 1: KCCQ Overall Summary (continuous change from baseline)
cont <- data.frame(
  Analysis.group    = 1L,
  Analysis.number   = 1L,
  Analysis.name     = "KCCQ Overall Summary (change from baseline)",
  Subgroup          = "",
  Subgroup.number   = 1L,
  Applicability     = "",
  Study             = studies,
  Study.year        = c(2020L, 2021L, 2022L),
  GIV.Mean          = NA_real_,
  GIV.SE            = NA_real_,
  Experimental.mean = c(8, 12, 10),
  Experimental.SD   = c(15, 18, 16),
  Experimental.cases = NA_integer_,
  Experimental.N    = c(100L, 150L, 80L),
  Control.mean      = c(3, 4, 5),
  Control.SD        = c(15, 18, 16),
  Control.cases     = NA_integer_,
  Control.N         = c(100L, 150L, 80L),
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

# Analysis 2: KCCQ Overall Summary (responders)
dich <- data.frame(
  Analysis.group    = 1L,
  Analysis.number   = 2L,
  Analysis.name     = "KCCQ Overall Summary (responders)",
  Subgroup          = "",
  Subgroup.number   = 1L,
  Applicability     = "",
  Study             = studies,
  Study.year        = c(2020L, 2021L, 2022L),
  GIV.Mean          = NA_real_,
  GIV.SE            = NA_real_,
  Experimental.mean = NA_real_,
  Experimental.SD   = NA_real_,
  Experimental.cases = c(55L, 75L, 42L),
  Experimental.N    = c(100L, 150L, 80L),
  Control.mean      = NA_real_,
  Control.SD        = NA_real_,
  Control.cases     = c(40L, 55L, 32L),
  Control.N         = c(100L, 150L, 80L),
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

# The review object is the concatenated data.frame.
# Name matches filename stem (minus "_data" suffix stripped by review_id derivation).
fixture_R001_data <- rbind(cont, dich)
save(fixture_R001_data, file = "tests/fixtures/fixture_R001_data.rda")
cat("Wrote fixture_R001_data.rda --", nrow(fixture_R001_data), "rows\n")
