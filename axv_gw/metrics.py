from prometheus_client import Counter, Histogram

rate_limit_dropped = Counter(
    "gw_rate_limit_dropped_total",
    "Requests dropped by rate limiter",
    ["path"],
)

hmac_bad_ts = Counter(
    "gw_hmac_bad_ts_total",
    "Requests rejected due to timestamp skew",
    ["path"],
)

hmac_bad_sig = Counter(  # użyjemy w kroku K2.5b w walidacji podpisu
    "gw_hmac_bad_sig_total",
    "Requests rejected due to bad HMAC signature",
    ["path"],
)

hooks_ok = Counter(
    "gw_hooks_ok_total",
    "Successful (HTTP<400) /hooks/* requests",
    ["path"],
)

hooks_duration_ms = Histogram(
    "gw_hooks_duration_ms",
    "Duration of /hooks/* requests in milliseconds",
    buckets=[5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000],
)
