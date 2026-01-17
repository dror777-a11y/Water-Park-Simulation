import heapq
import numpy as np
import matplotlib.pyplot as plt
from datetime import timedelta

from Event import FamilyArrivalEvent, TeensGroupArrivalEvent, SingleGroupArrivalEvent, EndOfDayEvent, EndFacilityEvent
from Queue import QueueServer
from entities import SubGroup, Family, TeenGroup, SingleVisitor
from facilities import Reception, Pipes_River, Single_Slide, Big_Pipes_Slide, Small_Pipes_Slide, Snorkel_Tour, \
    Kids_Pool, Waves_Pool, Pizza_Restaurant, Burger_Restaurant, Salad_Restaurant
from sampling_algorithms import Sampling_Algorithms


class Simulation:
    """
    Main simulation class for World Sea Water Park.
    Manages all facilities, events, and visitor flow through the park.
    Uses discrete event simulation with priority queue.
    """

    def __init__(self, start_date):
        # Import facilities

        # Initialize all facilities
        self.reception = Reception(num_clerks=3)
        self.pipes_River = Pipes_River()
        self.single_Slide = Single_Slide()
        self.big_Pipes_Slide = Big_Pipes_Slide()
        self.small_Pipes_Slide = Small_Pipes_Slide()
        self.waves_Pool = Waves_Pool()
        self.kids_Pool = Kids_Pool()
        self.snorkel_Tour = Snorkel_Tour()

        # Initialize restaurants
        self.pizza_Restaurant = Pizza_Restaurant()
        self.burger_Restaurant = Burger_Restaurant()
        self.salad_Restaurant = Salad_Restaurant()

        # Facility lists for easy iteration
        self.facilities = [
            self.pipes_River,
            self.single_Slide,
            self.big_Pipes_Slide,
            self.small_Pipes_Slide,
            self.waves_Pool,
            self.kids_Pool,
            self.snorkel_Tour
        ]

        self.restaurants = [
            self.pizza_Restaurant,
            self.burger_Restaurant,
            self.salad_Restaurant
        ]

        # Event queue (priority queue based on event time)
        self.event_queue = []

        # Simulation clock
        self.clock = start_date
        self.end_time = self.clock + timedelta(hours=10)

        # Reception queue (separate from facility queues)
        self.queue_reception = QueueServer()

        # Set active hours for all queues (for statistics)
        self.queue_reception.set_active_hours("09:00", "19:00")
        for facility in self.facilities:
            facility.queue_regular.set_active_hours("09:00", "19:00")
            facility.queue_express.set_active_hours("09:00", "19:00")

        # Simulation statistics
        self.total_people_arrived = 0      # Total number of people who arrived (counting heads)
        self.total_entities_arrived = 0    # # Total number of entities who arrived (Family / Teen / Single)
        self.total_people_completed = 0    # Total number of people who completed
        self.total_entities_completed = 0  # Total number of entities who completed
        self.total_people_entered = 0 # Total number of people who enterd the park (counting heads)
        self.total_entities_entered = 0 # Total number of entities who enterd the park


        self.total_revenue = 0
        self.ratings = []
        self.visitors_completed = []       # List of visitors who completed their visit (Family / Teen / Single)


        # Schedule initial arrival events
        self._schedule_initial_arrivals()

   #     self.reception_queue_history = [] # Queue history saving list


    def _schedule_initial_arrivals(self):
        """
        Schedule initial arrival events for each visitor type.
        Families start at 09:00, Teens at 10:00, Singles at 09:00.
        """

        self.add_event(FamilyArrivalEvent(self.clock))  # Start at 09:00
        self.add_event(TeensGroupArrivalEvent(self.clock + timedelta(hours=1)))  # Start at 10:00
        self.add_event(SingleGroupArrivalEvent(self.clock))  # Start at 09:00

    def add_event(self, event):
        """Add event to priority queue (ordered by event time)."""
        heapq.heappush(self.event_queue, event)

    def run(self):
        """
        Run simulation until end_time reached.
        EndOfDayEvent is scheduled daily at 19:00 to close daily statistics.
        """

        # schedule first end-of-day (19:00 of current day)
        first_day_end = self.clock.replace(hour=19, minute=0, second=0, microsecond=0)
        if first_day_end <= self.clock:
            first_day_end += timedelta(days=1)
        self.add_event(EndOfDayEvent(first_day_end))

        while self.event_queue and self.clock < self.end_time:

            # (optional) save reception queue length history
            try:
                current_length = len(self.queue_reception)
            except:
                current_length = len(self.queue_reception.items) if hasattr(self.queue_reception, 'items') else 0
        #    self.reception_queue_history.append(current_length)

            event = heapq.heappop(self.event_queue)

            # stop if next event is beyond simulation end time
            if event.time > self.end_time:
                break

            self.clock = event.time
            event.handle(self)

        # force everyone to leave only at FINAL end of simulation
        self.force_close_park()

        # IMPORTANT: do NOT call calc_daily_stats() here, EndOfDayEvent already does it daily
        # self.calc_daily_stats()

    def calc_daily_stats(self):
        """Calculate daily statistics for all queues."""
        self.queue_reception.calc_daily_statistics()
        for facility in self.facilities:
            facility.queue_regular.calc_daily_statistics()
            facility.queue_express.calc_daily_statistics()

    def force_close_park(self):
        """
        Force all visitors still inside the park to leave at closing time (19:00).
        Counts ONLY visitors who entered the park and were not counted yet.
        """
        completed_entities = set(self.visitors_completed)

        for facility in self.facilities:

            # Visitors currently using the facility
            for visitor in list(facility.users_in_service):
                if visitor not in completed_entities:
                    self._complete_visitor(visitor)
                    completed_entities.add(visitor)

            # Visitors waiting in queues
            for queue in [facility.queue_regular, facility.queue_express]:
                for visitor in list(queue):
                    if visitor not in completed_entities:
                        self._complete_visitor(visitor)
                        completed_entities.add(visitor)


    def _complete_visitor(self, visitor):
        package, price = Sampling_Algorithms.get_photo_purchase_decision(visitor.rating)
        if package:
            self.total_revenue += price

        self.ratings.append(visitor.rating)
        self.visitors_completed.append(visitor)
        self.total_entities_completed += 1
        self.total_people_completed += visitor.group_size


    def choose_facility(self, visitor, is_first_visit=False):
        """
        Choose next facility for visitor based on type and constraints.

        Rules:
        - Families (first visit): ONLY facilities with age_limit=0 (no age restriction)
        - Families (after split): Any facility matching age, shortest queue
        - Teen groups: Adrenaline level 3+, shortest queue
        - Single visitors (first): age_limit >= 12, shortest queue
        - Single visitors (after): All except Kids Pool, shortest queue
        - Always exclude already visited facilities

        Returns: Facility object or None if no eligible facilities
        """

        # Check if visitor has visited all eligible facilities
        if hasattr(visitor, 'visited_facilities'):
            remaining_facilities = [f for f in self.facilities
                                    if f not in visitor.visited_facilities
                                    and f.age_limit <= visitor.get_min_age()]

            if not remaining_facilities:
                return None  # All facilities visited

        # ✅ CRITICAL FIX: Families on FIRST visit must go to age_limit=0 facilities ONLY
        if is_first_visit and isinstance(visitor, (Family, SubGroup)):
            eligible = [f for f in self.facilities
                        if f.age_limit == 0  # ONLY no-restriction facilities (Pipes River, Big Pipes)
                        and f not in getattr(visitor, 'visited_facilities', [])]
            if eligible:
                return min(eligible, key=lambda f: f.get_total_waiting())

        # Teen groups: Adrenaline 3+, age appropriate
        if isinstance(visitor, TeenGroup):
            eligible = [f for f in self.facilities
                        if f.adrenalin_level >= 3  # High adrenaline only
                        and f.age_limit <= visitor.get_min_age()
                        and f not in getattr(visitor, 'visited_facilities', [])]
            if eligible:
                return min(eligible, key=lambda f: f.get_total_waiting())

        # Single visitors: First visit prefers age_limit >= 12
        if isinstance(visitor, SingleVisitor):
            if is_first_visit:
                eligible = [f for f in self.facilities
                            if f.age_limit >= 12  # Prefer adult facilities
                            and f not in getattr(visitor, 'visited_facilities', [])]
            else:
                # After first visit: All except Kids Pool
                eligible = [f for f in self.facilities
                            if f.name != "Kids Pool"
                            and f not in getattr(visitor, 'visited_facilities', [])]

            if eligible:
                return min(eligible, key=lambda f: f.get_total_waiting())

        # Default case: Any age-appropriate facility
        eligible = [f for f in self.facilities
                    if f.age_limit <= visitor.get_min_age()
                    and f not in getattr(visitor, 'visited_facilities', [])]
        if eligible:
            return min(eligible, key=lambda f: f.get_total_waiting())

        return None  # No eligible facilities

    def try_start_facility(self, facility, current_time):
        """
        Attempt to start service at facility.
        Each facility type has different entry logic:
        - Pipes River: Pairing logic for odd groups
        - Single Slide: Per-slide cooldown
        - Big/Small Pipes: Exact capacity batching
        - Wave/Kids Pool: Capacity-based entry
        - Snorkel Tour: Instructor availability
        """

        # PIPES RIVER: Process entry with pairing logic
        if isinstance(facility, Pipes_River):
            entering = facility.process_entry(current_time)
            for group in entering:
                duration = facility.get_service_duration()
                facility.users_in_service.append(group)
                self.add_event(EndFacilityEvent(current_time + timedelta(minutes=duration), group, facility))

        # SINGLE SLIDE: Check per-slide availability
        elif isinstance(facility, Single_Slide):
            while facility.queue_express or facility.queue_regular:
                slide_idx = facility.get_available_slide(current_time)
                if slide_idx is None:
                    break  # All slides on cooldown

                # Priority: Express > Regular
                visitor = None
                if facility.queue_express:
                    visitor, _ = facility.queue_express.pop(current_time)
                elif facility.queue_regular:
                    visitor, _ = facility.queue_regular.pop(current_time)

                if visitor:
                    facility.record_entry(slide_idx, current_time)
                    facility.users_in_service.append(visitor)
                    duration = facility.get_service_duration()
                    self.add_event(EndFacilityEvent(current_time + timedelta(minutes=duration), visitor, facility))

        # BIG PIPES SLIDE: Batch exactly 8 people
        elif isinstance(facility, Big_Pipes_Slide):
            if facility.can_enter(current_time):
                batch = facility.get_next_batch(current_time)  # ✅ FIXED: Pass current_time
                if batch:
                    for visitor in batch:
                        facility.users_in_service.append(visitor)
                    duration = facility.get_service_duration()
                    for visitor in batch:
                        self.add_event(EndFacilityEvent(current_time + timedelta(minutes=duration), visitor, facility))

        # SMALL PIPES SLIDE: Batch exactly 3 people
        elif isinstance(facility, Small_Pipes_Slide):
            if facility.can_enter(current_time):
                batch = facility.get_next_batch(current_time)  # ✅ FIXED: Pass current_time
                if batch:
                    for visitor in batch:
                        facility.users_in_service.append(visitor)
                    duration = facility.get_service_duration()
                    for visitor in batch:
                        self.add_event(EndFacilityEvent(current_time + timedelta(minutes=duration), visitor, facility))

        # WAVE POOL: Capacity-based entry
        elif isinstance(facility, Waves_Pool):
            entered_anyone = True
            while entered_anyone and (facility.queue_express or facility.queue_regular):
                entered_anyone = False

                # Try express queue first
                if facility.queue_express:
                    temp_queue = list(facility.queue_express)
                    for i in range(len(temp_queue)):
                        next_visitor = temp_queue[i]
                        if facility.can_enter(current_time, next_visitor.group_size):
                            if i == 0:
                                visitor, _ = facility.queue_express.pop(current_time)
                            else:
                                facility.queue_express.remove(next_visitor, current_time)
                                visitor = next_visitor

                            facility.users_in_service.append(visitor)
                            duration = facility.get_service_duration()
                            self.add_event(
                                EndFacilityEvent(current_time + timedelta(minutes=duration), visitor, facility))
                            entered_anyone = True
                            break

                # Try regular queue if express didn't enter anyone
                if not entered_anyone and facility.queue_regular:
                    temp_queue = list(facility.queue_regular)
                    for i in range(len(temp_queue)):
                        next_visitor = temp_queue[i]
                        if facility.can_enter(current_time, next_visitor.group_size):
                            if i == 0:
                                visitor, _ = facility.queue_regular.pop(current_time)
                            else:
                                facility.queue_regular.remove(next_visitor, current_time)
                                visitor = next_visitor

                            facility.users_in_service.append(visitor)
                            duration = facility.get_service_duration()
                            self.add_event(
                                EndFacilityEvent(current_time + timedelta(minutes=duration), visitor, facility))
                            entered_anyone = True
                            break

        # KIDS POOL: Capacity-based entry
        elif isinstance(facility, Kids_Pool):
            entered_anyone = True
            while entered_anyone and (facility.queue_express or facility.queue_regular):
                entered_anyone = False

                # Try express queue first
                if facility.queue_express:
                    temp_queue = list(facility.queue_express)
                    for i in range(len(temp_queue)):
                        next_visitor = temp_queue[i]
                        if facility.can_enter(current_time, next_visitor.group_size):
                            if i == 0:
                                visitor, _ = facility.queue_express.pop(current_time)
                            else:
                                facility.queue_express.remove(next_visitor, current_time)
                                visitor = next_visitor

                            facility.users_in_service.append(visitor)
                            duration = facility.get_service_duration()
                            self.add_event(
                                EndFacilityEvent(current_time + timedelta(minutes=duration), visitor, facility))
                            entered_anyone = True
                            break

                # Try regular queue if express didn't enter anyone
                if not entered_anyone and facility.queue_regular:
                    temp_queue = list(facility.queue_regular)
                    for i in range(len(temp_queue)):
                        next_visitor = temp_queue[i]
                        if facility.can_enter(current_time, next_visitor.group_size):
                            if i == 0:
                                visitor, _ = facility.queue_regular.pop(current_time)
                            else:
                                facility.queue_regular.remove(next_visitor, current_time)
                                visitor = next_visitor

                            facility.users_in_service.append(visitor)
                            duration = facility.get_service_duration()
                            self.add_event(
                                EndFacilityEvent(current_time + timedelta(minutes=duration), visitor, facility))
                            entered_anyone = True
                            break

        # SNORKEL TOUR: Instructor-based tours
        elif isinstance(facility, Snorkel_Tour):
            instructor_idx = facility.get_available_instructor(current_time)
            if instructor_idx is not None and (facility.queue_express or facility.queue_regular):
                tour_group = []
                tour_size = 0

                # Fill tour up to capacity (30 people)
                while tour_size < facility.tour_capacity and (facility.queue_express or facility.queue_regular):
                    visitor = None

                    # Priority: Express > Regular
                    if facility.queue_express:
                        next_visitor = facility.queue_express[0]
                        if tour_size + next_visitor.group_size <= facility.tour_capacity:
                            visitor, _ = facility.queue_express.pop(current_time)
                        else:
                            break  # Group too large
                    elif facility.queue_regular:
                        next_visitor = facility.queue_regular[0]
                        if tour_size + next_visitor.group_size <= facility.tour_capacity:
                            visitor, _ = facility.queue_regular.pop(current_time)
                        else:
                            break

                    if visitor:
                        tour_group.append(visitor)
                        tour_size += visitor.group_size
                    else:
                        break

                # Start tour if we have at least one visitor
                if tour_group:
                    duration = facility.get_service_duration()
                    facility.start_tour(instructor_idx, current_time, duration)
                    for visitor in tour_group:
                        facility.users_in_service.append(visitor)
                        self.add_event(EndFacilityEvent(current_time + timedelta(minutes=duration), visitor, facility,
                                                        instructor_idx))
    def welch_cumulative_avg(self, data):
        data = np.array(data, dtype=float)
        if len(data) == 0:
            return data
        return np.cumsum(data) / (np.arange(len(data)) + 1)

    def plot_heating_time_days(self, data, title):
        welch_line = self.welch_cumulative_avg(data)

        plt.figure(figsize=(10, 6))
        plt.plot(range(1, len(data) + 1), data, label="Daily values")
        plt.plot(range(1, len(data) + 1), welch_line, "--", label="Welch (cumulative avg)")
        plt.xlabel("Days")
        plt.ylabel("Value")
        plt.title(title)
        plt.legend()
        plt.show()
