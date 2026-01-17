import math
import random


class Sampling_Algorithms:
    """
    Collection of sampling algorithms for simulation.
    Implements various probability distributions using:
    - Inverse Transform Method
    - Box-Muller Transform (for normal distribution)
    - Acceptance-Rejection Algorithm
    - Composition Method
    """

    # ============================================
    # BASIC MATHEMATICAL ALGORITHMS
    # ============================================

    @staticmethod
    def sample_uniform(a, b):
        """
        Sample from Uniform(a, b) using inverse transform method.

        Args:
            a: Lower bound
            b: Upper bound

        Returns:
            Random value in [a, b]
        """
        u = random.random()  # U(0,1)
        return a + (b - a) * u

    @staticmethod
    def sample_exponential(lambda_param):
        """
        Sample from Exponential(lambda) using inverse transform method.

        Args:
            lambda_param: Rate parameter (λ)

        Returns:
            Random value from exponential distribution
        """
        u = Sampling_Algorithms.sample_uniform(0, 1)
        return -math.log(1 - u) / lambda_param

    @staticmethod
    def sample_normal(mu, sigma):
        """
        Sample from Normal(mu, sigma) using Box-Muller transform.

        Args:
            mu: Mean
            sigma: Standard deviation

        Returns:
            Random value from normal distribution
        """
        u1 = Sampling_Algorithms.sample_uniform(0, 1)
        u2 = Sampling_Algorithms.sample_uniform(0, 1)
        z = math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)
        return mu + sigma * z

    # ============================================
    # VISITOR GENERATION
    # ============================================

    @staticmethod
    def get_number_kids():
        """
        Sample number of kids in family.
        Distribution: Discrete Uniform[1,5]

        Returns:
            Number of kids (1-5, equal probability)
        """
        u = random.random()
        if u < 0.2:
            return 1
        elif u < 0.4:
            return 2
        elif u < 0.6:
            return 3
        elif u < 0.8:
            return 4
        else:
            return 5

    @staticmethod
    def get_kid_age():
        """
        Sample kid age.
        Distribution: Continuous Uniform[2,18]

        Returns:
            Kid age in years (continuous, 2-18)
        """
        return Sampling_Algorithms.sample_uniform(2, 18)

    @staticmethod
    def sample_family_interarrival_time():
        """
        Sample time between family arrivals.
        Distribution: Exponential with rate 40/hour

        Returns:
            Inter-arrival time in MINUTES
            Mean = 1.5 minutes
        """
        # Rate = 40 per hour = 40/60 per minute = 2/3 per minute
        # Mean time between arrivals = 60/40 = 1.5 minutes
        return Sampling_Algorithms.sample_exponential(40 / 60)

    @staticmethod
    def get_family_departure_time():
        """
        Sample family departure time using inverse transform.
        PDF: f(x) = (2/9)(x-16), 16 ≤ x ≤ 19

        Returns:
            Departure hour (16.0 to 19.0)
        """
        u = Sampling_Algorithms.sample_uniform(0, 1)
        return 3 * math.sqrt(u) + 16

    @staticmethod
    def get_teen_group_size():
        """
        Sample teen group size.
        Distribution:
        - P(2-3) = 0.4
        - P(4-5) = 0.5
        - P(6) = 0.1

        Returns:
            Group size (2-6 people)
        """
        u = Sampling_Algorithms.sample_uniform(0, 1)
        if u <= 0.2:
            return 2
        elif u <= 0.4:
            return 3
        elif u <= 0.65:
            return 4
        elif u <= 0.9:
            return 5
        else:
            return 6

    @staticmethod
    def sample_teens_group_interarrival_time():
        """
        Sample time between teen group arrivals.
        Distribution: Exponential with 500 groups/day on average
        Day = 6 hours (10:00-16:00) = 360 minutes

        Returns:
            Inter-arrival time in MINUTES
        """
        return Sampling_Algorithms.sample_exponential(500 / 360)

    @staticmethod
    def sample_single_visitor_interarrival_time():
        """
        Sample time between single visitor arrivals.
        Distribution: Exponential with rate 10 per 15 minutes = 40/hour

        Returns:
            Inter-arrival time in MINUTES
        """
        return Sampling_Algorithms.sample_exponential(40 / 60)

    @staticmethod
    def should_buy_express_on_entry():
        """
        Determine if visitor buys express pass on entry.
        Probability: 0.25

        Returns:
            True if buying express pass, False otherwise
        """
        u = Sampling_Algorithms.sample_uniform(0, 1)
        return u <= 0.25

    # ============================================
    # FACILITY ACTIVITY DURATIONS
    # ============================================

    @staticmethod
    def pipes_river_duration():
        """
        Sample Pipes River activity duration.
        Distribution: Uniform[20, 30] minutes

        Returns:
            Activity duration in minutes
        """
        return Sampling_Algorithms.sample_uniform(20, 30)

    @staticmethod
    def sample_big_pipes_slide_duration():
        """
        Sample Big Pipes Slide duration.
        Distribution: Normal(μ=4.8, σ=1.8322)
        Parameters from Maximum Likelihood Estimation

        Returns:
            Slide duration in minutes
        """
        mu = 4.8
        sigma = 1.8322
        return Sampling_Algorithms.sample_normal(mu, sigma)

    @staticmethod
    def sample_small_pipes_slide_duration():
        """
        Sample Small Pipes Slide duration.
        Distribution: Exponential(λ=2.10706)
        Parameter from Maximum Likelihood Estimation

        Returns:
            Slide duration in minutes
        """
        lambda_param = 2.10706
        return Sampling_Algorithms.sample_exponential(lambda_param)

    # ============================================
    # COMPLEX SAMPLING ALGORITHMS
    # ============================================

    @staticmethod
    def get_wave_pool_duration():
        """
        Sample Wave Pool duration using Acceptance-Rejection algorithm.

        PDF:
        - f(x) = x/2700, 0 ≤ x ≤ 10
        - f(x) = 0, 10 < x < 30
        - f(x) = (60-x)/2700 + 1/30, 30 ≤ x ≤ 50
        - f(x) = (60-x)/2700, 50 < x ≤ 60

        Returns:
            Pool duration in minutes
        """
        # Maximum of f(x)
        M = 2.0 / 45.0

        while True:
            # Generate candidate
            x = Sampling_Algorithms.sample_uniform(0, 60)

            # Evaluate PDF at x
            if 0 <= x <= 10:
                f_x = x / 2700.0
            elif 10 < x < 30:
                f_x = 0
            elif 30 <= x <= 50:
                f_x = (60 - x) / 2700.0 + 1.0 / 30.0
            elif 50 < x <= 60:
                f_x = (60 - x) / 2700.0
            else:
                f_x = 0

            # Accept/reject
            u = Sampling_Algorithms.sample_uniform(0, 1)
            if u <= f_x / M:
                return x

    @staticmethod
    def sample_kids_pool_duration():
        """
        Sample Kids Pool stay duration using inverse transform.

        PDF (piecewise):
        - f(x) = 16/3(x-1), 1 ≤ x < 1.25
        - f(x) = 4/3, 1.25 ≤ x < 1.75
        - f(x) = 16/3(2-x), 1.75 ≤ x ≤ 2

        Formula is in hours, result returned in minutes.

        Returns:
            Pool duration in minutes
        """
        u = Sampling_Algorithms.sample_uniform(0, 1)

        # Select formula part based on u value
        if 0 <= u < 1 / 6:
            # First range (1 to 1.25 hours)
            duration_hours = 1 + math.sqrt((3 * u) / 8)

        elif 1 / 6 <= u < 5 / 6:
            # Middle range (1.25 to 1.75 hours)
            duration_hours = 0.75 * u + 1.125

        else:
            # Last range (1.75 to 2 hours)
            duration_hours = 2 - math.sqrt((3 * (1 - u)) / 8)

        # Convert hours to minutes
        return duration_hours * 60

    # ============================================
    # ADDITIONAL SAMPLING METHODS
    # ============================================

    @staticmethod
    def sample_ticket_purchase_time():
        """
        Sample ticket purchase duration.
        Distribution: Uniform[0.5, 2] minutes

        Returns:
            Purchase time in minutes
        """
        return Sampling_Algorithms.sample_uniform(0.5, 2)

    @staticmethod
    def sample_wristband_time():
        """
        Sample wristband reception duration.
        Distribution: Exponential(mean=2 minutes)

        Returns:
            Reception time in minutes
        """
        return Sampling_Algorithms.sample_exponential(1.0 / 2.0)

    @staticmethod
    def sample_restaurant_service_time():
        """
        Sample restaurant service duration.
        Distribution: Normal(μ=5, σ=1.5) minutes

        Returns:
            Service time in minutes
        """
        return Sampling_Algorithms.sample_normal(5, 1.5)

    @staticmethod
    def sample_meal_duration():
        """
        Sample meal eating duration.
        Distribution: Uniform[15, 35] minutes

        Returns:
            Eating duration in minutes
        """
        return Sampling_Algorithms.sample_uniform(15, 35)

    @staticmethod
    def sample_snorkel_tour_duration():
        """
        Sample snorkel tour duration.
        Distribution: Normal(μ=30, σ=10) minutes

        Returns:
            Tour duration in minutes
        """
        return Sampling_Algorithms.sample_normal(30, 10)

    # ============================================
    # VISITOR BEHAVIOR & DECISION-MAKING
    # ============================================

    @staticmethod
    def should_teens_buy_express_after_abandon():
        """
        Determine if teen group buys express pass after abandoning queue.
        Probability: 0.6

        Returns:
            True if buying express pass, False otherwise
        """
        u = Sampling_Algorithms.sample_uniform(0, 1)
        return u <= 0.6

    @staticmethod
    def had_good_experience():
        """
        Determine if visitor had good experience at attraction.
        Probability: 0.5

        Returns:
            True if good experience, False otherwise
        """
        u = Sampling_Algorithms.sample_uniform(0, 1)
        return u <= 0.5

    @staticmethod
    def calculate_positive_rating(group_size, adrenaline_level):
        """
        Calculate rating increase after good experience.

        Formula: score = (GS-1)/5 * 0.3 + (A-1)/4 * 0.7

        Args:
            group_size: Number of people in group (GS)
            adrenaline_level: Facility adrenaline level 1-5 (A)

        Returns:
            Rating increase value
        """
        return ((group_size - 1) / 5.0) * 0.3 + ((adrenaline_level - 1) / 4.0) * 0.7

    @staticmethod
    def should_eat_lunch():
        """
        Determine if visitor chooses to eat lunch.
        Probability: 0.7

        Returns:
            True if eating lunch, False otherwise
        """
        u = Sampling_Algorithms.sample_uniform(0, 1)
        return u <= 0.7

    @staticmethod
    def choose_restaurant():
        """
        Choose restaurant based on visitor preferences.

        Distribution:
        - 3/8 (37.5%) → Burger
        - 1/4 (25%) → Pizza
        - 3/8 (37.5%) → Salad

        Returns:
            Restaurant choice: "burger", "pizza", or "salad"
        """
        u = Sampling_Algorithms.sample_uniform(0, 1)
        if u < 3.0 / 8.0:
            return "burger"
        elif u < 3.0 / 8.0 + 1.0 / 4.0:
            return "pizza"
        else:
            return "salad"

    @staticmethod
    def is_meal_unsatisfactory():
        """
        Determine if meal is unsatisfactory.
        Probability: 0.1 (leads to rating -0.8)

        Returns:
            True if meal unsatisfactory, False otherwise
        """
        u = Sampling_Algorithms.sample_uniform(0, 1)
        return u <= 0.1

    @staticmethod
    def get_photo_purchase_decision(final_rating):
        """
        Determine photo package purchase based on final park rating.

        Rating tiers:
        - < 6: No purchase
        - 6-7.5: 1 photo (20₪)
        - 7.5-8.5: 10 photos (100₪)
        - 8.5+: 10 photos + video (120₪)

        Args:
            final_rating: Visitor's final park rating (0-10)

        Returns:
            (package_type, price) tuple
        """
        if final_rating < 6:
            return None, 0
        elif final_rating < 7.5:
            return "1_photo", 20
        elif final_rating < 8.5:
            return "10_photos", 100
        else:
            return "10_photos_video", 120

    @staticmethod
    def should_family_split():
        """
        Determine if family splits into subgroups.
        Probability: 0.6

        Returns:
            True if splitting, False otherwise
        """
        u = Sampling_Algorithms.sample_uniform(0, 1)
        return u <= 0.6

    @staticmethod
    def get_num_split_groups():
        """
        Determine number of groups if family splits.
        Distribution: 2 or 3 groups (equal probability)

        Returns:
            Number of subgroups (2 or 3)
        """
        u = Sampling_Algorithms.sample_uniform(0, 1)
        return 2 if u <= 0.5 else 3