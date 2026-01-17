from collections import deque
import math

from Queue import QueueServer
from sampling_algorithms import Sampling_Algorithms


class Facility:
    """
    Base class for all park facilities.
    Manages queues (regular and express), capacity, and age restrictions.
    """

    def __init__(self, name, capacity, age_limit, adrenalin_level):
        self.name = name
        self.capacity = capacity  # Maximum number of people using facility at once
        self.age_limit = age_limit  # Minimum age required (0 = no restriction)
        self.adrenalin_level = adrenalin_level  # Excitement level (1-5)

        # Queue management using QueueServer for statistics tracking

        self.queue_regular = QueueServer()  # Regular queue
        self.queue_express = QueueServer()  # Express pass queue (priority)
        self.users_in_service = []  # List of visitors currently using facility

    def get_total_waiting(self):
        """Return total number of people waiting in both queues."""
        return self.queue_regular.size() + self.queue_express.size()

    def enter_queue(self, visitor, current_time):
        """
        Add visitor to appropriate queue based on express pass status.
        Express pass holders get priority.
        """
        if visitor.has_express_pass:
            self.queue_express.add(visitor, current_time)
        else:
            self.queue_regular.add(visitor, current_time)


# ============================================
# RECEPTION (PARK ENTRANCE)
# ============================================

class Reception:
    """
    Park reception for ticket purchase and wristband collection.
    Has multiple clerks to serve visitors in parallel.
    """

    def __init__(self, num_clerks=3):
        self.name = "Reception"
        self.num_clerks = num_clerks  # Number of service clerks (default: 3)
        self.clerks_busy = [False] * num_clerks  # Track which clerks are busy
        self.clerks_finish_time = [0] * num_clerks  # Track when each clerk finishes


    def get_available_clerk(self, current_time):
        """Return index of available clerk, or None if all busy."""
        for i in range(self.num_clerks):
            if not self.clerks_busy[i]:
                return i
        return None

    def get_ticket_purchase_duration(self):
        """Duration for ticket purchase: Uniform[0.5, 2] minutes."""
        return Sampling_Algorithms.sample_ticket_purchase_time()

    def get_wristband_duration(self):
        """Duration for wristband collection: Exponential(mean=2) minutes."""
        return Sampling_Algorithms.sample_wristband_time()

    def get_total_service_duration(self):
        """Total time at reception: ticket purchase + wristband collection."""
        return self.get_ticket_purchase_duration() + self.get_wristband_duration()


# ============================================
# PIPES RIVER
# ============================================

class Pipes_River(Facility):
    """
    River with tubes - 2 people per tube, 60 tubes total.
    Implements special pairing logic for odd-sized groups.
    """

    def __init__(self):
        super().__init__(name="Pipes River", capacity=120, age_limit=0, adrenalin_level=1)
        self.people_per_tube = 2  # Each tube holds 2 people
        self.total_tubes = 60  # Total available tubes
        self.occupied_tubes = 0  # Currently occupied tubes

    def get_service_duration(self):
        """Activity duration: Uniform[20, 30] minutes."""
        return Sampling_Algorithms.pipes_river_duration()

    def can_enter(self, current_time, group_size=1):
        """Check if there are available tubes."""
        return self.occupied_tubes < self.total_tubes

    def find_odd_group_in_queue(self, queue_list):
        """
        Find first odd-sized group in queue.
        Returns: index of group, or None if no odd groups found.
        """
        for idx, visitor_group in enumerate(queue_list):
            if visitor_group.group_size % 2 == 1:
                return idx
        return None

    def process_entry(self, current_time):
        """
        Handle entry to river with pairing logic for odd groups.
        Odd-sized groups are paired together to maximize tube usage.
        Priority: Express queue > Regular queue

        Returns: list of groups that entered
        """
        entering_groups = []

        made_progress = True  # Track if making progress

        while self.occupied_tubes < self.total_tubes and made_progress:
            made_progress = False  # Reset at start of each iteration
            # Process express queue first (priority)
            if self.queue_express:
                group = self.queue_express[0]

                # Even group - enter directly
                if group.group_size % 2 == 0:
                    tubes_used = group.group_size // self.people_per_tube

                    if self.occupied_tubes + tubes_used <= self.total_tubes:
                        self.queue_express.pop(current_time)
                        self.occupied_tubes += tubes_used
                        entering_groups.append(group)
                        made_progress = True
                        continue
                    else:
                        break  # Not enough tubes available

                # Odd group - try to find a pair
                else:
                    # Look for another odd group in express queue (skip first)
                    express_list = list(self.queue_express)[1:]
                    odd_idx_express = self.find_odd_group_in_queue(express_list)

                    if odd_idx_express is not None:
                        # Found pair in express queue
                        odd_idx_express += 1  # Adjust for skipped first element
                        group1, _ = self.queue_express.pop(current_time)
                        group2 = list(self.queue_express)[odd_idx_express - 1]
                        self.queue_express.remove(group2, current_time)

                        total_size = group1.group_size + group2.group_size
                        tubes_used = math.ceil(total_size / self.people_per_tube)

                        if self.occupied_tubes + tubes_used <= self.total_tubes:
                            self.occupied_tubes += tubes_used

                            # Mark that these groups share tubes
                            group1.is_shared_tube = True
                            group2.is_shared_tube = True
                            group1.tube_partner = group2
                            group2.tube_partner = group1

                            entering_groups.append(group1)
                            entering_groups.append(group2)
                            made_progress = True
                            continue
                        else:
                            # Not enough space, return to queue
                            self.queue_express.insert(0, group1, current_time)
                            self.queue_express.insert(odd_idx_express, group2, current_time)
                            break

                    # Look for odd group in regular queue
                    regular_list = list(self.queue_regular)
                    odd_idx_regular = self.find_odd_group_in_queue(regular_list)

                    if odd_idx_regular is not None:
                        # Found pair: express + regular
                        group1, _ = self.queue_express.pop(current_time)
                        group2 = list(self.queue_regular)[odd_idx_regular]
                        self.queue_regular.remove(group2, current_time)

                        total_size = group1.group_size + group2.group_size
                        tubes_used = math.ceil(total_size / self.people_per_tube)

                        if self.occupied_tubes + tubes_used <= self.total_tubes:
                            self.occupied_tubes += tubes_used

                            # Mark that these groups share tubes
                            group1.is_shared_tube = True
                            group2.is_shared_tube = True
                            group1.tube_partner = group2
                            group2.tube_partner = group1

                            entering_groups.append(group1)
                            entering_groups.append(group2)
                            made_progress = True
                            continue
                        else:
                            # Not enough space, return to queue
                            self.queue_express.insert(0, group1, current_time)
                            self.queue_regular.insert(odd_idx_regular, group2, current_time)
                            break

                    # No pair found - wait for another odd group
                    break

            # Process regular queue
            elif self.queue_regular:
                group = self.queue_regular[0]

                # Even group - enter directly
                if group.group_size % 2 == 0:
                    tubes_used = group.group_size // self.people_per_tube

                    if self.occupied_tubes + tubes_used <= self.total_tubes:
                        self.queue_regular.pop(current_time)
                        self.occupied_tubes += tubes_used
                        entering_groups.append(group)
                        made_progress = True
                        continue
                    else:
                        break

                # Odd group - try to find another odd group
                else:
                    regular_list = list(self.queue_regular)[1:]
                    odd_idx = self.find_odd_group_in_queue(regular_list)

                    if odd_idx is not None:
                        # Found pair in regular queue
                        odd_idx += 1
                        group1, _ = self.queue_regular.pop(current_time)
                        group2 = list(self.queue_regular)[odd_idx - 1]
                        self.queue_regular.remove(group2, current_time)

                        total_size = group1.group_size + group2.group_size
                        tubes_used = math.ceil(total_size / self.people_per_tube)

                        if self.occupied_tubes + tubes_used <= self.total_tubes:
                            self.occupied_tubes += tubes_used

                            # Mark that these groups share tubes
                            group1.is_shared_tube = True
                            group2.is_shared_tube = True
                            group1.tube_partner = group2
                            group2.tube_partner = group1

                            entering_groups.append(group1)
                            entering_groups.append(group2)
                            made_progress = True
                            continue
                        else:
                            # Not enough space, return to queue
                            self.queue_regular.insert(0, group1, current_time)
                            self.queue_regular.insert(odd_idx, group2, current_time)
                            break

                    # No pair found - wait
                    break
            else:
                break  # No more visitors in queues

        return entering_groups

    def release_tubes(self, visitor):
        """
        Release tubes when visitors finish.
        For shared tubes, only release when LAST person exits.
        """
        # Check if this visitor shared a tube with someone
        if hasattr(visitor, 'is_shared_tube') and visitor.is_shared_tube:
            partner = getattr(visitor, 'tube_partner', None)
            if partner:
                # Check if partner already exited (not in users_in_service)
                if partner not in self.users_in_service:
                    # Partner already left, we are the last one - release the tube(s)
                    total_size = visitor.group_size + partner.group_size
                    tubes_to_release = math.ceil(total_size / self.people_per_tube)
                    self.occupied_tubes -= tubes_to_release
                # else: Partner still inside, don't release yet
        else:
            # Normal case: visitor(s) used their own tube(s)
            tubes_to_release = math.ceil(visitor.group_size / self.people_per_tube)
            self.occupied_tubes -= tubes_to_release

        # Ensure we never have negative tubes
        self.occupied_tubes = max(0, self.occupied_tubes)


# ============================================
# SINGLE SLIDE
# ============================================

class Single_Slide(Facility):
    """
    Individual slides - 2 slides, 30 second safety interval.
    Only one person per slide, with mandatory 30s wait between entries.
    Age 14+, high adrenaline (level 5).
    """

    def __init__(self):
        super().__init__(name="Single Slide", capacity=6, age_limit=14, adrenalin_level=5)
        self.num_slides = 2  # Number of parallel slides
        self.activity_duration = 3  # 3 minutes per slide
        self.safety_interval = 0.5  # 30 seconds (0.5 minutes) between entries
        self.last_entry_times = [-1000, -1000]  # Track last entry for each slide

    def get_service_duration(self):
        """Slide duration: exactly 3 minutes."""
        return self.activity_duration

    def can_enter(self, current_time, group_size=1):
        """
        Check if can enter (capacity + safety interval).
        Must respect both global capacity and per-slide safety interval.
        """
        if len(self.users_in_service) >= self.capacity:
            return False

        # Convert current_time to minutes for comparison
        current_minutes = current_time.hour * 60 + current_time.minute + current_time.second / 60

        # Check if any slide is available (30 sec since last entry)
        for last_time in self.last_entry_times:
            if current_minutes - last_time >= self.safety_interval:
                return True
        return False

    def get_available_slide(self, current_time):
        """Return index of available slide, or None if all slides on cooldown."""
        current_minutes = current_time.hour * 60 + current_time.minute + current_time.second / 60

        for i in range(self.num_slides):
            if current_minutes - self.last_entry_times[i] >= self.safety_interval:
                return i
        return None

    def record_entry(self, slide_index, current_time):
        """Record entry time for slide (for safety interval tracking)."""
        current_minutes = current_time.hour * 60 + current_time.minute + current_time.second / 60
        self.last_entry_times[slide_index] = current_minutes


# ============================================
# BIG PIPES SLIDE
# ============================================

class Big_Pipes_Slide(Facility):
    """
    Large tube slide - exactly 8 people per tube.
    Only ONE tube can slide at a time.
    Duration: Normal(4.8, 1.8322) from MLE estimation.
    """

    def __init__(self):
        super().__init__(name="Big Pipes Slide", capacity=8, age_limit=0, adrenalin_level=2)
        self.tube_size = 8  # Must have exactly 8 people

    def get_service_duration(self):
        """Slide duration: Normal(μ=4.8, σ=1.8322) from data."""
        return Sampling_Algorithms.sample_big_pipes_slide_duration()

    def can_enter(self, current_time, group_size=1):
        """Can only enter when no one is currently sliding."""
        return len(self.users_in_service) == 0

    def get_next_batch(self, current_time):
        """
        Get next batch of EXACTLY 8 visitors.
        Strategy: Take groups sequentially until we reach exactly 8.
        If we can't reach exactly 8, don't process anyone (wait for more).

        ✅ IMPORTANT: Must have EXACTLY 8 people, no more, no less.

        Returns: list of visitors totaling exactly 8 people, or empty list
        """
        # First, check if it's even possible to make 8
        total_in_queue = 0
        for v in self.queue_express:
            total_in_queue += v.group_size
        for v in self.queue_regular:
            total_in_queue += v.group_size

        if total_in_queue < self.tube_size:
            return []  # Not enough people total

        # Try to build a batch of exactly 8
        batch = []
        batch_size = 0

        # Step 1: Take from express queue
        temp_express = []
        while self.queue_express and batch_size < self.tube_size:
            visitor = self.queue_express[0]
            if batch_size + visitor.group_size <= self.tube_size:
                v, t = self.queue_express.pop(current_time)
                temp_express.append((v, t))
                batch.append(v)
                batch_size += v.group_size

                if batch_size == self.tube_size:
                    return batch  # Perfect!
            else:
                break  # This group too large, stop here

        # Step 2: Fill remaining from regular queue
        temp_regular = []
        while self.queue_regular and batch_size < self.tube_size:
            visitor = self.queue_regular[0]
            if batch_size + visitor.group_size <= self.tube_size:
                v, t = self.queue_regular.pop(current_time)
                temp_regular.append((v, t))
                batch.append(v)
                batch_size += v.group_size

                if batch_size == self.tube_size:
                    return batch  # Perfect!
            else:
                break  # This group too large

        # Didn't reach exactly 8 - rollback everyone
        for v, t in reversed(temp_express):
            self.queue_express.insert(0, v, t)
        for v, t in reversed(temp_regular):
            self.queue_regular.insert(0, v, t)

        return []  # Can't make 8 right now


# ============================================
# SMALL PIPES SLIDE
# ============================================

class Small_Pipes_Slide(Facility):
    """
    Small tube slide - exactly 3 people per tube.
    Only ONE tube can slide at a time.
    Age 12+, Duration: Exponential(λ=2.10706) from MLE.
    """

    def __init__(self):
        super().__init__(name="Small Pipes Slide", capacity=3, age_limit=12, adrenalin_level=4)
        self.tube_size = 3  # Must have exactly 3 people

    def get_service_duration(self):
        """Slide duration: Exponential(λ=2.10706) from data."""
        return Sampling_Algorithms.sample_small_pipes_slide_duration()

    def can_enter(self, current_time, group_size=1):
        """Can only enter when no one is currently sliding."""
        return len(self.users_in_service) == 0

    def get_next_batch(self, current_time):
        """
        Get next batch of EXACTLY 3 visitors.
        Strategy: Take groups sequentially until we reach exactly 3.
        If we can't reach exactly 3, don't process anyone (wait for more).

        ✅ IMPORTANT: Must have EXACTLY 3 people, no more, no less.

        Returns: list of visitors totaling exactly 3 people, or empty list
        """
        # First, check if it's even possible to make 3
        total_in_queue = 0
        for v in self.queue_express:
            total_in_queue += v.group_size
        for v in self.queue_regular:
            total_in_queue += v.group_size

        if total_in_queue < self.tube_size:
            return []  # Not enough people total

        # Try to build a batch of exactly 3
        batch = []
        batch_size = 0

        # Step 1: Take from express queue
        temp_express = []
        while self.queue_express and batch_size < self.tube_size:
            visitor = self.queue_express[0]
            if batch_size + visitor.group_size <= self.tube_size:
                v, t = self.queue_express.pop(current_time)
                temp_express.append((v, t))
                batch.append(v)
                batch_size += v.group_size

                if batch_size == self.tube_size:
                    return batch  # Perfect!
            else:
                break  # This group too large, stop here

        # Step 2: Fill remaining from regular queue
        temp_regular = []
        while self.queue_regular and batch_size < self.tube_size:
            visitor = self.queue_regular[0]
            if batch_size + visitor.group_size <= self.tube_size:
                v, t = self.queue_regular.pop(current_time)
                temp_regular.append((v, t))
                batch.append(v)
                batch_size += v.group_size

                if batch_size == self.tube_size:
                    return batch  # Perfect!
            else:
                break  # This group too large

        # Didn't reach exactly 3 - rollback everyone
        for v, t in reversed(temp_express):
            self.queue_express.insert(0, v, t)
        for v, t in reversed(temp_regular):
            self.queue_regular.insert(0, v, t)

        return []  # Can't make 3 right now


# ============================================
# WAVE POOL
# ============================================

class Waves_Pool(Facility):
    """
    Wave pool - capacity 80 people (or 120 with upgrade).
    Age 12+, multiple visitors can use simultaneously.
    Duration sampled using Acceptance-Rejection algorithm.
    """

    def __init__(self, capacity=80):
        super().__init__(name="Wave Pool", capacity=capacity, age_limit=12, adrenalin_level=3)

    def get_service_duration(self):
        """Duration sampled using acceptance-rejection algorithm."""
        return Sampling_Algorithms.get_wave_pool_duration()

    def can_enter(self, current_time, group_size=1):
        """Check if pool has space for this group."""
        current_occupancy = sum(v.group_size for v in self.users_in_service)
        return current_occupancy + group_size <= self.capacity


# ============================================
# KIDS POOL
# ============================================

class Kids_Pool(Facility):
    """
    Kids pool - age 4 and under only, capacity 30 kids.
    Duration: 1-2 hours sampled using inverse transform.
    """

    def __init__(self):
        super().__init__(name="Kids Pool", capacity=30, age_limit=4, adrenalin_level=1)
        self.max_age = 4  # Only kids 4 and under allowed

    def get_service_duration(self):
        """
        Duration in hours, sampled using inverse transform.
        Returns: duration in minutes (converted from hours).
        """
        return Sampling_Algorithms.sample_kids_pool_duration()

    def can_enter(self, current_time, group_size=1):
        """Check if pool has space for this group."""
        current_occupancy = sum(v.group_size for v in self.users_in_service)
        return current_occupancy + group_size <= self.capacity


# ============================================
# SNORKEL TOUR
# ============================================

class Snorkel_Tour(Facility):
    """
    Snorkeling tour with instructors - age 6+.
    2 instructors, max 30 people per tour.
    Instructors take 30min break after each tour.
    MANDATORY lunch break: 13:00-14:00 (NO tours during this time).
    Tours cannot start between 12:20-13:00 to avoid overlap with lunch.
    """

    def __init__(self, num_instructors=2):
        super().__init__(name="Snorkel Tour", capacity=30, age_limit=6, adrenalin_level=3)
        self.num_instructors = num_instructors
        self.tour_capacity = 30  # Max people per tour

        # Track instructor states
        self.instructor_states = []
        for i in range(num_instructors):
            self.instructor_states.append({
                'available': True,  # Can start new tour
                'on_tour': False,  # Currently leading tour
                'on_break': False,  # On 30-min break after tour
                'on_lunch': False,  # On lunch break (13:00-14:00)
                'finish_time': 0  # Time when current activity finishes (in minutes)
            })

    def get_service_duration(self):
        """Tour duration: Normal(30, 10) minutes."""
        return Sampling_Algorithms.sample_snorkel_tour_duration()

    def get_available_instructor(self, current_time):
        """
        Return index of available instructor, or None if all busy.
        ✅ FIXED: Check if current time is in restricted period (12:20-13:00 or 13:00-14:00).
        """
        current_minutes = current_time.hour * 60 + current_time.minute

        # ✅ CRITICAL: No tours can start between 12:20-14:00
        # 12:20-13:00: Buffer to prevent tours from running into lunch
        # 13:00-14:00: Mandatory lunch break
        if (12 * 60 + 20) <= current_minutes < (14 * 60):  # 12:20 to 14:00
            return None  # No instructor available during restricted hours

        for i, state in enumerate(self.instructor_states):
            if state['available'] and current_minutes >= state['finish_time']:
                return i
        return None

    def start_tour(self, instructor_idx, current_time, tour_duration):
        """Start a tour with given instructor."""
        current_minutes = current_time.hour * 60 + current_time.minute
        self.instructor_states[instructor_idx]['available'] = False
        self.instructor_states[instructor_idx]['on_tour'] = True
        self.instructor_states[instructor_idx]['finish_time'] = current_minutes + tour_duration

    def finish_tour(self, instructor_idx, current_time):
        """
        Finish tour and send instructor on break.
        After break, instructor goes to lunch if it's lunch time (13:00-14:00).
        """
        current_minutes = current_time.hour * 60 + current_time.minute
        self.instructor_states[instructor_idx]['on_tour'] = False
        self.instructor_states[instructor_idx]['on_break'] = True
        self.instructor_states[instructor_idx]['finish_time'] = current_minutes + 30  # 30 min break

    def finish_break(self, instructor_idx, current_time):
        """
        Instructor finishes break.
        If it's lunch time (13:00-14:00), go to lunch.
        Otherwise, become available.

        NOTE: If going to lunch, Event.py must create InstructorLunchEndEvent!
        """
        self.instructor_states[instructor_idx]['on_break'] = False

        # Check if it's lunch time (13:00-14:00)
        hour = current_time.hour
        if 13 <= hour < 14:
            # It's lunch time - go to lunch
            current_minutes = current_time.hour * 60 + current_time.minute
            self.instructor_states[instructor_idx]['on_lunch'] = True
            # Lunch ends at 14:00, so calculate remaining time until 14:00
            lunch_end = 14 * 60  # 14:00 in minutes
            remaining_lunch_time = lunch_end - current_minutes
            self.instructor_states[instructor_idx]['finish_time'] = current_minutes + remaining_lunch_time
            # Return True to signal that lunch end event should be created
            return True  # ✅ SIGNAL: Create lunch end event!
        else:
            # Not lunch time - become available
            self.instructor_states[instructor_idx]['available'] = True
            return False

    def finish_lunch(self, instructor_idx):
        """Instructor finishes lunch and becomes available."""
        self.instructor_states[instructor_idx]['on_lunch'] = False
        self.instructor_states[instructor_idx]['available'] = True


# ============================================
# RESTAURANTS
# ============================================

class Restaurant:
    """
    Base restaurant class.
    Single service station for ordering and payment.
    Service time: Normal(5, 1.5) minutes.
    ✅ NOW USES QueueServer for statistics tracking.
    """

    def __init__(self, name, service_stations=1):
        self.name = name
        self.queue = QueueServer()  # ✅ CHANGED: Use QueueServer instead of deque
        self.service_stations = service_stations
        self.stations_busy = [False] * service_stations
        self.stations_finish_time = [0] * service_stations

    def enter_queue(self, visitor, current_time):
        """Add visitor to restaurant queue."""
        self.queue.add(visitor, current_time)  # ✅ CHANGED: Use .add() instead of .append()

    def get_available_station(self, current_time):
        """Return index of available service station, or None if all busy."""
        for i in range(self.service_stations):
            if not self.stations_busy[i]:
                return i
        return None

    def get_preparation_time(self, visitor):
        """Get food preparation time (must be overridden by subclasses)."""
        raise NotImplementedError

    def get_service_time(self):
        """Service time: Normal(5, 1.5) minutes."""
        return Sampling_Algorithms.sample_restaurant_service_time()

    def get_total_time(self, visitor):
        """Total time = food preparation + service."""
        return self.get_preparation_time(visitor) + self.get_service_time()

    def get_meal_duration(self):
        """Eating duration: Uniform[15, 35] minutes."""
        return Sampling_Algorithms.sample_meal_duration()


class Pizza_Restaurant(Restaurant):
    """
    Pizza restaurant.
    Preparation: Uniform[4, 6] minutes.
    Price: 40₪ individual, 100₪ family tray.
    """

    def __init__(self):
        super().__init__(name="Pizza", service_stations=1)

    def get_preparation_time(self, visitor):
        """Uniform[4, 6] minutes per order."""
        return Sampling_Algorithms.sample_uniform(4, 6)

    def get_price(self, visitor):
        """Individual 40₪, Family tray 100₪."""
        if visitor.group_size == 1:
            return 40
        else:
            return 100  # Family tray


class Burger_Restaurant(Restaurant):
    """
    Burger restaurant.
    Preparation: Uniform[3, 4] minutes per person.
    Price: 100₪ per person (burger + fries + drink).
    """

    def __init__(self):
        super().__init__(name="Burger", service_stations=1)

    def get_preparation_time(self, visitor):
        """Uniform[3, 4] minutes per person."""
        return Sampling_Algorithms.sample_uniform(3, 4)

    def get_price(self, visitor):
        """100₪ per person."""
        return 100 * visitor.group_size


class Salad_Restaurant(Restaurant):
    """
    Salad and healthy food restaurant.
    Preparation: Uniform[3, 7] minutes per person.
    Price: 65₪ per person (salad + drink).
    """

    def __init__(self):
        super().__init__(name="Salad", service_stations=1)

    def get_preparation_time(self, visitor):
        """Uniform[3, 7] minutes per person."""
        return Sampling_Algorithms.sample_uniform(3, 7)

    def get_price(self, visitor):
        """65₪ per person."""
        return 65 * visitor.group_size