# World Sea Water Park Simulation 🌊

## Overview
This project is a **Discrete Event Simulation (DES)** of the "World Sea" water park, developed as part of Industrial Engineering and Management studies. The simulation models visitor behavior, facility operations, and financial performance to optimize park management.

## Key Technical Features
* **Stochastic Modeling:** Custom implementation of probability distributions including:
    * **Inverse Transform Method** (Exponential, Uniform, and piecewise distributions).
    * **Box-Muller Transform** for Normal distributions.
    * **Acceptance-Rejection Algorithm** for complex durations like the Wave Pool.
* **Complex Visitor Logic:** Models different visitor types (Families with splitting logic, Teen Groups with abandonment/express-pass purchase logic, and Single Visitors).
* **Statistical Analysis:** Performance evaluation of operational changes using **Welch's Test** and Bonferroni correction to ensure statistical significance.

## Project Structure
* `Simulation.py`: Core engine managing the event priority queue and system clock.
* `entities.py`: Logic for visitor types, ratings, and group decision-making.
* `facilities.py`: Operational models for reception, slides, pools, and restaurants.
* `sampling_algorithms.py`: Mathematical implementations for all stochastic variables.

## Metrics Tracked
* Average waiting times for facilities and restaurants.
* Total park revenue and photo package sales.
* Visitor satisfaction levels through a dynamic Rating system.
