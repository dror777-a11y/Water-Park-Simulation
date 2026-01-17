"""
main.py - Main execution file for World Sea Water Park simulation

This script initializes and runs the discrete event simulation,
then displays comprehensive results including:
- Visitor statistics
- Revenue summary
- Rating distribution
- Queue waiting times per facility
- Queue waiting times per restaurant ✅ NEW!
"""

from datetime import datetime
from Simulation import Simulation


def main():
    """
    Main function to run the water park simulation.

    Process:
    1. Initialize simulation with start date/time
    2. Run simulation (processes all events chronologically)
    3. Display comprehensive results
    """

    # Set simulation start date and time
    # Park opens at 09:00 on January 1, 2025
    start_date = datetime(2025, 1, 1, 9, 0, 0)

    # Display simulation header
    print("מתחיל סימולציה של פארק המים World Sea")
    print(f"תאריך: {start_date.strftime('%d/%m/%Y')}")
    print(f"שעה: {start_date.strftime('%H:%M')}")
    print("-" * 60)

    # Create simulation instance
    sim = Simulation(start_date)

    # Run simulation (processes all events until queue empty)
    print("מריץ סימולציה...")
    sim.run()
    print("הסימולציה הסתיימה!")
    print()

    # Display results
    print("=" * 60)
    print("תוצאות הסימולציה")
    print("=" * 60)
    print()

    # Visitor statistics
    print("People arrived:", sim.total_people_arrived)
    print("Entities arrived:", sim.total_entities_arrived)
    print("People completed:", sim.total_people_completed)
    print("Entities completed:", sim.total_entities_completed)
    print("People entered park:", sim.total_people_entered)
    print("Entities entered park:", sim.total_entities_entered)
    print("Events left:", len(sim.event_queue))

    print("-" * 30)
    print(f"סה'כ הכנסות: {sim.total_revenue:,.2f} ₪")
    print("-" * 30)

    # Rating statistics
    if sim.ratings:
        avg_rating = sum(sim.ratings) / len(sim.ratings)
        print(f"דירוג ממוצע: {avg_rating:.2f}")
        print(f"דירוג מינימלי: {min(sim.ratings):.2f}")
        print(f"דירוג מקסימלי: {max(sim.ratings):.2f}")

    print()
    print("סטטיסטיקות תורים - מתקנים:")
    print("-" * 60)

    # Reception queue statistics
    if sim.queue_reception.daily_avg_waiting_times:
        print(f"קבלה - זמן המתנה ממוצע: {sim.queue_reception.daily_avg_waiting_times[0]:.2f} דקות")

    # Facility queue statistics
    for facility in sim.facilities:
        if facility.queue_regular.daily_avg_waiting_times:
            wait_time = facility.queue_regular.daily_avg_waiting_times[0]
            print(f"{facility.name} - זמן המתנה ממוצע: {wait_time:.2f} דקות")

    print()
    print("סטטיסטיקות תורים - מסעדות:")
    print("-" * 60)

    # Restaurant queue statistics ✅ NEW!
    for restaurant in sim.restaurants:
        if restaurant.queue.daily_avg_waiting_times:
            wait_time = restaurant.queue.daily_avg_waiting_times[0]
            print(f"{restaurant.name} - זמן המתנה ממוצע: {wait_time:.2f} דקות")
        else:
            print(f"{restaurant.name} - אין נתוני המתנה")

    print()
    print("=" * 60)


if __name__ == "__main__":
    main()