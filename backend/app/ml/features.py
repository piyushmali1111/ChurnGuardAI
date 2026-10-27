FEATURE_COLS = [
    "DaysSinceLastOrder",
    "OrderCount",
    "TotalSpent",
    "ComplaintCount",
    "SatisfactionScore",
    "TenureMonths",
    "ReturnRate",
    "DiscountUsageRate",
]

# Monotonic constraints for XGBoost, same order as FEATURE_COLS
# 1 = positive, -1 = negative, 0 = unrestricted
MONOTONE = (1, -1, -1, 1, -1, 0, 1, 0)
