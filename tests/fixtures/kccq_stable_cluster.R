# tests/fixtures/kccq_stable_cluster.R
# Known-stable cluster: 5 trials where continuous-to-responder mapping is well-behaved
# under normal approximation (symmetric, unbounded by scale limits).
# Responder count per arm = round(p * n) where p = pnorm((mean - 5)/sd) for d=+1, δ=5.
trials_cont <- data.frame(
  trial_id = paste0("T", 1:5),
  n_t = c(100, 150, 80, 120, 200),
  mean_t = c(8, 12, 10, 9, 11),
  sd_t = c(15, 18, 16, 17, 15),
  n_c = c(100, 150, 80, 120, 200),
  mean_c = c(3, 4, 5, 3.5, 4.5),
  sd_c = c(15, 18, 16, 17, 15)
)
p_t <- pnorm((trials_cont$mean_t - 5) / trials_cont$sd_t)
p_c <- pnorm((trials_cont$mean_c - 5) / trials_cont$sd_c)
trials_dich <- data.frame(
  trial_id = trials_cont$trial_id,
  events_t = round(p_t * trials_cont$n_t),
  n_t = trials_cont$n_t,
  events_c = round(p_c * trials_cont$n_c),
  n_c = trials_cont$n_c
)
fixture <- list(
  review_id = "negative_control_kccq",
  outcomes = list(
    list(label = "KCCQ Overall Summary (change)", measure_type = "MD", comparison = "drug_vs_placebo", trials = trials_cont),
    list(label = "KCCQ Overall Summary (responders)", measure_type = "RR", comparison = "drug_vs_placebo", trials = trials_dich)
  )
)
save(fixture, file = "tests/fixtures/kccq_stable_cluster.rda")
cat("Written\n")
