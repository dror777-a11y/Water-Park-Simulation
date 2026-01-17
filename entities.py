from sampling_algorithms import Sampling_Algorithms


class Visitor:
    """
    Base class for all park visitors.
    Handles rating system, express pass, and queue management.
    """


    def __init__(self, arrival_time):
        self.id = id(self)  # Unique identifier for the visitor
        self.arrival_time = arrival_time  # DateTime when visitor arrived at park
        self.rating = 10.0
        self.has_express_pass = False  # Whether visitor purchased express pass
        self.time_entered_queue = None  # Track when visitor entered current queue
        self.current_facility = None  # Current facility visitor is queuing for
        self.departure_time = None  # Scheduled departure time

    def update_rating_positive(self, group_size, adrenaline_level):
        """
        Increase rating after good experience at facility.
        Formula: score = (GS-1)/5 * 0.3 + (A-1)/4 * 0.7
        """
        increase = Sampling_Algorithms.calculate_positive_rating(group_size, adrenaline_level)
        self.rating += increase

    def update_rating_negative(self, amount=0.1):
        """
        Decrease rating (e.g., after bad experience or queue abandonment).
        Rating cannot go below 0.
        """
        self.rating -= amount
        self.rating = max(0, self.rating)

    def get_abandonment_threshold(self):
        """
        Return maximum waiting time in minutes before abandoning queue.
        Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclass must implement abandonment threshold")

    def should_abandon(self, current_time):
        """
        Check if visitor should abandon current queue based on waiting time.
        Express pass holders never abandon.
        """
        if self.time_entered_queue is None:
            return False
        if self.has_express_pass:
            return False
        waiting_time = current_time - self.time_entered_queue
        return waiting_time >= self.get_abandonment_threshold()

    def enter_queue(self, facility, current_time):
        """
        Add visitor to facility queue (regular or express based on pass).
        """
        self.time_entered_queue = current_time
        self.current_facility = facility
        facility.enter_queue(self)

    def reset_queue_time(self):
        """Reset queue entry time (e.g., after leaving queue)."""
        self.time_entered_queue = None


class Family(Visitor):
    """
    Represents a family group (2 parents + 1-5 kids).
    Can split into subgroups based on children's ages.
    """

    def __init__(self, arrival_time):
        super().__init__(arrival_time)

        # Generate family composition
        self.num_kids = Sampling_Algorithms.get_number_kids()  # Discrete Uniform[1,5]
        self.total_size = self.num_kids + 2  # Kids + 2 parents
        self.group_size = self.total_size

        # Generate ages for all kids
        self.kids_ages = []
        for _ in range(self.num_kids):
            age = Sampling_Algorithms.get_kid_age()  # Uniform[2,18]
            self.kids_ages.append(age)

        # Family departure time: f(x) = 2/9(x-16), 16≤x≤19
        self.departure_time = Sampling_Algorithms.get_family_departure_time()

        # Splitting management
        self.is_split = False  # Whether family has split into subgroups
        self.subgroups = []  # List of SubGroup objects if split
        self.active_subgroups_count = 1  # Number of active subgroups (for tracking completion)

        # Track which facilities have been visited
        self.visited_facilities = []

        # 25% chance to buy express pass on entry
        if Sampling_Algorithms.should_buy_express_on_entry():
            self.has_express_pass = True

    def get_abandonment_threshold(self):
        """Families abandon queue after 15 minutes."""
        return 15

    def check_and_split(self):
        """
        Determine if family splits into subgroups (60% probability).
        Splitting rules:
        - Kids under 8 must be with a parent
        - Kids 12+ can supervise younger siblings
        - Split into 2 or 3 groups (equal probability)

        Returns: List containing either [self] or list of SubGroup objects
        """
        # 40% chance family stays together
        if not Sampling_Algorithms.should_family_split():
            return [self]

        self.is_split = True
        num_groups = Sampling_Algorithms.get_num_split_groups()  # 2 or 3 groups

        # Categorize kids by age
        kids_under_8 = [age for age in self.kids_ages if age < 8]
        kids_8_to_12 = [age for age in self.kids_ages if 8 <= age < 12]
        kids_over_12 = [age for age in self.kids_ages if age >= 12]

        subgroups = []

        # Group 1: Kids under 8 with one parent (mandatory if any kids under 8)
        if kids_under_8:
            group = SubGroup(
                parent_family=self,
                size=1 + len(kids_under_8),  # 1 parent + kids
                min_age=min(kids_under_8),
                has_express_pass=self.has_express_pass
            )
            subgroups.append(group)

        # Group 2: Kids 12+ can go independently
        if kids_over_12 and len(subgroups) < num_groups:
            group = SubGroup(
                parent_family=self,
                size=len(kids_over_12),
                min_age=min(kids_over_12),
                has_express_pass=self.has_express_pass
            )
            subgroups.append(group)

        # Group 3: Remaining kids (8-12) with remaining parent
        if len(subgroups) < num_groups:
            remaining_size = self.total_size - sum(g.group_size for g in subgroups)
            if remaining_size > 0:
                remaining_ages = kids_8_to_12 if kids_8_to_12 else [14]
                group = SubGroup(
                    parent_family=self,
                    size=remaining_size,
                    min_age=min(remaining_ages) if remaining_ages else 14,
                    has_express_pass=self.has_express_pass
                )
                subgroups.append(group)

        # If couldn't create at least 2 groups, don't split
        if len(subgroups) < 2:
            self.is_split = False
            return [self]

        # Store subgroups and set counter for completion tracking
        self.subgroups = subgroups
        self.active_subgroups_count = len(subgroups)
        return subgroups

    def get_min_age(self):
        """Return minimum age in family (youngest kid)."""
        return min(self.kids_ages) if self.kids_ages else 14


class SubGroup(Visitor):
    """
    Represents a portion of a split family.
    Maintains reference to parent family for coordination.
    """

    def __init__(self, parent_family, size, min_age, has_express_pass):
        super().__init__(parent_family.arrival_time)
        self.parent_family = parent_family  # Reference to original Family object
        self.group_size = size
        self.min_age = min_age
        self.has_express_pass = has_express_pass
        self.rating = parent_family.rating  # Share rating with parent family
        self.departure_time = parent_family.departure_time  # Share departure time

        # Track which facilities have been visited
        self.visited_facilities = []

    def get_abandonment_threshold(self):
        """SubGroups abandon queue after 15 minutes (same as families)."""
        return 15

    def get_min_age(self):
        """Return minimum age in this subgroup."""
        return self.min_age


class TeenGroup(Visitor):
    """
    Represents a group of teenagers (2-6 people, age 14+).
    Prefer high-adrenaline facilities (level 3+).
    Can purchase express pass after abandoning queue.
    """

    def __init__(self, arrival_time):
        super().__init__(arrival_time)

        # Group composition
        self.group_size = Sampling_Algorithms.get_teen_group_size()  # 2-6 people
        self.min_age = 14  # All teens are 14+

        # Abandonment tracking
        self.abandoned_facilities = []  # List of facilities they abandoned
        self.abandon_count = 0  # Number of times they've abandoned queues

        # Track which facilities have been visited
        self.visited_facilities = []

        # Teens leave at park closing (19:00)
        self.departure_time = 19.0

        # 25% chance to buy express pass on entry
        if Sampling_Algorithms.should_buy_express_on_entry():
            self.has_express_pass = True

    def get_abandonment_threshold(self):
        """Teen groups abandon queue after 20 minutes."""
        return 20

    def handle_abandonment(self, facility):
        """
        Handle queue abandonment for teen group.
        60% chance they buy express pass and return to same facility.
        Otherwise, they move to next facility.

        Returns: "buy_express_and_return" or "move_to_next"
        """
        self.abandoned_facilities.append(facility)
        self.abandon_count += 1

        # If don't have express pass yet, 60% chance to buy one
        if not self.has_express_pass:
            if Sampling_Algorithms.should_teens_buy_express_after_abandon():
                self.has_express_pass = True
                return "buy_express_and_return"

        return "move_to_next"

    def get_min_age(self):
        """Return minimum age (always 14 for teen groups)."""
        return self.min_age


class SingleVisitor(Visitor):
    """
    Represents an individual adult visitor (age 18-70).
    Prefer facilities with age restriction 12+.
    """

    def __init__(self, arrival_time):
        super().__init__(arrival_time)

        self.group_size = 1
        self.min_age = Sampling_Algorithms.sample_uniform(18, 70)  # Random adult age

        # Track which facilities have been visited
        self.visited_facilities = []

        # Single visitors leave at park closing (19:00)
        self.departure_time = 19.0

        # 25% chance to buy express pass on entry
        if Sampling_Algorithms.should_buy_express_on_entry():
            self.has_express_pass = True

    def get_abandonment_threshold(self):
        """Single visitors abandon queue after 30 minutes."""
        return 30

    def get_min_age(self):
        """Return visitor's age."""
        return self.min_age


# Factory functions for creating visitors
def create_family(arrival_time):
    """Create and return a new Family object."""
    return Family(arrival_time)


def create_teen_group(arrival_time):
    """Create and return a new TeenGroup object."""
    return TeenGroup(arrival_time)


def create_single_visitor(arrival_time):
    """Create and return a new SingleVisitor object."""
    return SingleVisitor(arrival_time)