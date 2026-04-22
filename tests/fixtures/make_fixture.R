# tests/fixtures/make_fixture.R
# Generate a tiny RDA with one review having both continuous and dichotomous MAs,
# where each MA carries per-trial arm-level stats.
review_id <- "fixture_R001"
trials_cont <- data.frame(
  trial_id = c("T1", "T2", "T3"),
  n_t = c(100, 150, 80),
  mean_t = c(8, 12, 10),
  sd_t = c(15, 18, 16),
  n_c = c(100, 150, 80),
  mean_c = c(3, 4, 5),
  sd_c = c(15, 18, 16)
)
trials_dich <- data.frame(
  trial_id = c("T1", "T2", "T3"),
  events_t = c(55, 75, 42),
  n_t = c(100, 150, 80),
  events_c = c(40, 55, 32),
  n_c = c(100, 150, 80)
)
fixture <- list(
  review_id = review_id,
  outcomes = list(
    list(label = "KCCQ Overall Summary (change from baseline)",
         measure_type = "MD",
         comparison = "drug_vs_placebo",
         trials = trials_cont),
    list(label = "KCCQ Overall Summary (responders)",
         measure_type = "RR",
         comparison = "drug_vs_placebo",
         trials = trials_dich)
  )
)
save(fixture, file = "tests/fixtures/synthetic_one_review.rda")
cat("Saved tests/fixtures/synthetic_one_review.rda\n")
