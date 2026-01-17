import numpy as np
from scipy import stats

# Data for the three alternatives considering ratio measurment- so normality can be assumed
n1 = 30
mean1 = 8.190
variance1 = 0.198  # Standard Deviation squared

n2 = 30
mean2 = 9.190
variance2 = 0.159  # Standard Deviation squared

n3 = 30
mean3 = 8.260
variance3 = 0.214  # Standard Deviation squared

# Pairwise differences
pairs = [
    ('Alternative 1 vs Alternative 2', mean1 - mean2, variance1, n1, variance2, n2),
    ('Alternative 1 vs Alternative 3', mean1 - mean3, variance1, n1, variance3, n3),
    ('Alternative 2 vs Alternative 3', mean2 - mean3, variance2, n2, variance3, n3)
]

# Bonferroni correction
alpha = 0.1
adjusted_alpha = alpha / 6

# Calculate and print confidence intervals for each pair
for name, mean_diff, var1, n1, var2, n2 in pairs:

    # Calculate the standard error of the difference
    standard_error = np.sqrt((var1 / n1) + (var2 / n2))

    # Degrees of freedom
    numerator = (var1/n1 + var2/n2)**2
    denominator = ( (var1**2) / ((n1**2) * (n1 - 1)) ) + ( (var2**2) / ((n2**2) * (n2 - 1)) )
    degrees_of_freedom = int(numerator / denominator)

    # Critical t-value using adjusted alpha
    t_crit = stats.t.ppf(1 - adjusted_alpha/2, degrees_of_freedom)

    # Confidence interval
    margin_of_error = t_crit * standard_error
    ci_lower = mean_diff - margin_of_error
    ci_upper = mean_diff + margin_of_error

    # Output results
    print(f"{name}:")
    print("  Difference in means:", mean_diff)
    print("  Degrees of Freedom (approx):", degrees_of_freedom)
    print("  Critical t-value:", t_crit)
    print("  Confidence Interval: ({:.4f}, {:.4f})".format(ci_lower, ci_upper))

    # Interpretation
    if ci_upper < 0:
        print("  Preferred Alternative: The second in the pair (negative difference).")
    elif ci_lower > 0:
        print("  Preferred Alternative: The first in the pair (positive difference).")
    else:
        print("  No significant difference between the alternatives.")
    print()