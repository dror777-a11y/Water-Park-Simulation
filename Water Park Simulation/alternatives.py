import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
from Simulation import Simulation

# =============================================================================
# Configuration
# =============================================================================
NUM_DAYS = 30
START_DATE = datetime(2025, 1, 1, 9, 0, 0)


# =============================================================================
# Alternative 1: Baseline (Current State)
# =============================================================================
def run_baseline(day_num):
    random.seed(1000 + day_num)
    np.random.seed(1000 + day_num)

    sim_date = START_DATE + timedelta(days=day_num - 1)
    sim = Simulation(sim_date)
    sim.run()

    return sim


# =============================================================================
# Alternative 2: Website + Benefits + Wave Pool (220k)
# =============================================================================
def run_alternative2(day_num):
    random.seed(2000 + day_num)
    np.random.seed(2000 + day_num)

    sim_date = START_DATE + timedelta(days=day_num - 1)
    sim = Simulation(sim_date)

    # Change 1: Website - only wristband (no ticket)
    sim.reception.get_total_service_duration = lambda: sim.reception.get_wristband_duration()

    # Change 2: Customer benefits - rating 11
    import entities
    original_init = entities.Visitor.__init__

    def new_init(self, arrival_time):
        original_init(self, arrival_time)
        self.rating = 11.0

    entities.Visitor.__init__ = new_init

    # Change 3: Wave pool capacity 120
    sim.waves_Pool.capacity = 120

    sim.run()

    entities.Visitor.__init__ = original_init
    return sim


# =============================================================================
# Alternative 3: Big Tubes 10 + Wave Pool (220k)
# =============================================================================
def run_alternative3(day_num):
    random.seed(3000 + day_num)
    np.random.seed(3000 + day_num)

    sim_date = START_DATE + timedelta(days=day_num - 1)
    sim = Simulation(sim_date)

    # Change 1: Big pipes - 10 capacity
    sim.big_Pipes_Slide.capacity = 10
    sim.big_Pipes_Slide.tube_size = 10

    # Change 2: Wave pool capacity 120
    sim.waves_Pool.capacity = 120

    sim.run()

    return sim


# =============================================================================
# Calculate Metrics
# =============================================================================
def calculate_metrics(sim):
    # Metric 1: Average waiting time (facilities + restaurants)
    all_wait_times = []

    # Reception queue
    if sim.queue_reception.daily_avg_waiting_times:
        all_wait_times.append(sim.queue_reception.daily_avg_waiting_times[0])

    # Facility queues
    for facility in sim.facilities:
        if facility.queue_regular.daily_avg_waiting_times:
            all_wait_times.append(facility.queue_regular.daily_avg_waiting_times[0])

    # Restaurant queues ✅ NEW!
    for restaurant in sim.restaurants:
        if restaurant.queue.daily_avg_waiting_times:
            all_wait_times.append(restaurant.queue.daily_avg_waiting_times[0])

    avg_wait = np.mean(all_wait_times) if all_wait_times else 0

    # Metric 2: Average rating
    avg_rating = np.mean(sim.ratings) if sim.ratings else 0

    return avg_wait, avg_rating


# =============================================================================
# Run Simulations
# =============================================================================
print("Running simulations...")

baseline_results = []
alt2_results = []
alt3_results = []

for day in range(1, NUM_DAYS + 1):
    print(f"Day {day}/{NUM_DAYS}...", end='\r')

    # Alternative 1
    sim1 = run_baseline(day)
    wait1, rating1 = calculate_metrics(sim1)
    baseline_results.append({'wait': wait1, 'rating': rating1})

    # Alternative 2
    sim2 = run_alternative2(day)
    wait2, rating2 = calculate_metrics(sim2)
    alt2_results.append({'wait': wait2, 'rating': rating2})

    # Alternative 3
    sim3 = run_alternative3(day)
    wait3, rating3 = calculate_metrics(sim3)
    alt3_results.append({'wait': wait3, 'rating': rating3})

print("Completed!                    ")

# =============================================================================
# Create Table
# =============================================================================
data = []

for i in range(NUM_DAYS):
    data.append({
        'Run Number': i + 1,
        'Avg Wait Time - Alt 1': round(baseline_results[i]['wait'], 2),
        'Avg Rating - Alt 1': round(baseline_results[i]['rating'], 2),
        'Avg Wait Time - Alt 2': round(alt2_results[i]['wait'], 2),
        'Avg Rating - Alt 2': round(alt2_results[i]['rating'], 2),
        'Avg Wait Time - Alt 3': round(alt3_results[i]['wait'], 2),
        'Avg Rating - Alt 3': round(alt3_results[i]['rating'], 2),
    })

# Calculate means
baseline_wait_mean = np.mean([r['wait'] for r in baseline_results])
baseline_rating_mean = np.mean([r['rating'] for r in baseline_results])
alt2_wait_mean = np.mean([r['wait'] for r in alt2_results])
alt2_rating_mean = np.mean([r['rating'] for r in alt2_results])
alt3_wait_mean = np.mean([r['wait'] for r in alt3_results])
alt3_rating_mean = np.mean([r['rating'] for r in alt3_results])

# Calculate standard deviations
baseline_wait_std = np.std([r['wait'] for r in baseline_results], ddof=1)
baseline_rating_std = np.std([r['rating'] for r in baseline_results], ddof=1)
alt2_wait_std = np.std([r['wait'] for r in alt2_results], ddof=1)
alt2_rating_std = np.std([r['rating'] for r in alt2_results], ddof=1)
alt3_wait_std = np.std([r['wait'] for r in alt3_results], ddof=1)
alt3_rating_std = np.std([r['rating'] for r in alt3_results], ddof=1)

# Add summary rows
data.append({
    'Run Number': 'Mean',
    'Avg Wait Time - Alt 1': round(baseline_wait_mean, 3),
    'Avg Rating - Alt 1': round(baseline_rating_mean, 2),
    'Avg Wait Time - Alt 2': round(alt2_wait_mean, 3),
    'Avg Rating - Alt 2': round(alt2_rating_mean, 2),
    'Avg Wait Time - Alt 3': round(alt3_wait_mean, 3),
    'Avg Rating - Alt 3': round(alt3_rating_mean, 2),
})

data.append({
    'Run Number': 'Std Dev',
    'Avg Wait Time - Alt 1': round(baseline_wait_std, 3),
    'Avg Rating - Alt 1': round(baseline_rating_std, 3),
    'Avg Wait Time - Alt 2': round(alt2_wait_std, 3),
    'Avg Rating - Alt 2': round(alt2_rating_std, 3),
    'Avg Wait Time - Alt 3': round(alt3_wait_std, 3),
    'Avg Rating - Alt 3': round(alt3_rating_std, 3),
})

# Create DataFrame
df = pd.DataFrame(data)

# Print table
print("\n" + "=" * 100)
print(f"Simulation Results - {NUM_DAYS} Days")
print("=" * 100)
print(df.to_string(index=False))
print("=" * 100)

