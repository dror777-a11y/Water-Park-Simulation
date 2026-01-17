from datetime import timedelta

from entities import Family, create_family, create_teen_group, create_single_visitor, SubGroup, TeenGroup
from facilities import Pipes_River, Snorkel_Tour
from sampling_algorithms import Sampling_Algorithms


class Event:
    """
    Base class for all simulation events.
    Events are ordered by time in priority queue.
    """

    def __init__(self, time):
        self.time = time  # DateTime when event should occur

    def __lt__(self, other):
        """Comparison operator for priority queue ordering."""
        if self.time == other.time:
            return id(self) < id(other)  # Deterministic tiebreaker
        return self.time < other.time

    def handle(self, simulation):
        """Process event (must be implemented by subclasses)."""
        raise NotImplementedError


# ============================================
# ARRIVAL EVENTS
# ============================================

class FamilyArrivalEvent(Event):
    """
    Family arrival event.
    Families arrive 09:00-12:00 with exponential inter-arrival time (40/hour).
    """

    def handle(self, simulation):
        simulation.clock = self.time

        # Create new family
        visitor = create_family(self.time)
        simulation.total_entities_arrived += 1
        simulation.total_people_arrived += visitor.group_size

        # Check if reception clerk available
        clerk = simulation.reception.get_available_clerk(self.time)
        if clerk is not None and simulation.queue_reception.size() == 0:
            # Clerk available and no queue - start service immediately
            simulation.reception.clerks_busy[clerk] = True
            service_minutes = simulation.reception.get_total_service_duration()
            end_time = self.time + timedelta(minutes=service_minutes)
            simulation.add_event(EndReceptionEvent(end_time, visitor, clerk))
        else:
            # All clerks busy or queue exists - join queue
            simulation.queue_reception.add(visitor, self.time)

        # Schedule next family arrival (exponential inter-arrival)
        dt_min = Sampling_Algorithms.sample_family_interarrival_time()
        next_time = self.time + timedelta(minutes=dt_min)
        if next_time.hour < 12:  # Only until 12:00
            simulation.add_event(FamilyArrivalEvent(next_time))


class TeensGroupArrivalEvent(Event):
    """
    Teen group arrival event.
    Teen groups arrive 10:00-16:00 with exponential inter-arrival (500/day).
    """

    def handle(self, simulation):
        simulation.clock = self.time

        # Create new teen group
        visitor = create_teen_group(self.time)
        simulation.total_entities_arrived += 1
        simulation.total_people_arrived += visitor.group_size

        # Check if reception clerk available
        clerk = simulation.reception.get_available_clerk(self.time)
        if clerk is not None and simulation.queue_reception.size() == 0:
            # Clerk available and no queue - start service immediately
            simulation.reception.clerks_busy[clerk] = True
            service_minutes = simulation.reception.get_total_service_duration()
            end_time = self.time + timedelta(minutes=service_minutes)
            simulation.add_event(EndReceptionEvent(end_time, visitor, clerk))
        else:
            # All clerks busy or queue exists - join queue
            simulation.queue_reception.add(visitor, self.time)

        # Schedule next teen group arrival (exponential inter-arrival)
        dt_min = Sampling_Algorithms.sample_teens_group_interarrival_time()
        next_time = self.time + timedelta(minutes=dt_min)
        if next_time.hour < 16:  # Only until 16:00
            simulation.add_event(TeensGroupArrivalEvent(next_time))


class SingleGroupArrivalEvent(Event):
    """
    Single visitor arrival event.
    Single visitors arrive 09:00-18:30 with exponential inter-arrival (40/hour).
    """

    def handle(self, simulation):
        simulation.clock = self.time

        # Create new single visitor
        visitor = create_single_visitor(self.time)
        simulation.total_entities_arrived += 1
        simulation.total_people_arrived += 1

        # Check if reception clerk available
        clerk = simulation.reception.get_available_clerk(self.time)
        if clerk is not None and simulation.queue_reception.size() == 0:
            # Clerk available and no queue - start service immediately
            simulation.reception.clerks_busy[clerk] = True
            service_minutes = simulation.reception.get_total_service_duration()
            end_time = self.time + timedelta(minutes=service_minutes)
            simulation.add_event(EndReceptionEvent(end_time, visitor, clerk))
        else:
            # All clerks busy or queue exists - join queue
            simulation.queue_reception.add(visitor, self.time)

        # Schedule next single visitor arrival (exponential inter-arrival)
        dt_min = Sampling_Algorithms.sample_single_visitor_interarrival_time()
        next_time = self.time + timedelta(minutes=dt_min)
        if next_time.hour < 18 or (next_time.hour == 18 and next_time.minute <= 30):  # Until 18:30
            simulation.add_event(SingleGroupArrivalEvent(next_time))


# ============================================
# RECEPTION EVENTS
# ============================================

class EndReceptionEvent(Event):
    """
    Event when visitor completes reception service (ticket + wristband).
    Calculates revenue and sends visitor to first facility.
    """

    def __init__(self, time, visitor, clerk_index):
        super().__init__(time)
        self.visitor = visitor
        self.clerk_index = clerk_index

    def handle(self, simulation):
        simulation.clock = self.time

        # Free up clerk
        simulation.reception.clerks_busy[self.clerk_index] = False
        simulation.total_entities_entered += 1
        simulation.total_people_entered += self.visitor.group_size

        # Calculate revenue based on visitor type
        if isinstance(self.visitor, Family):
            # Family: 2 adults @ 150₪ + kids @ 75₪
            adults = 2
            kids = self.visitor.num_kids
            revenue = adults * 150 + kids * 75
            if self.visitor.has_express_pass:
                revenue += (adults + kids) * 50  # Express pass: 50₪ per person
            simulation.total_revenue += revenue
        else:
            # Teen group or single visitor: 150₪ per person
            revenue = self.visitor.group_size * 150
            if self.visitor.has_express_pass:
                revenue += self.visitor.group_size * 50
            simulation.total_revenue += revenue

        # Try to find the first facility.
        first_facility = simulation.choose_facility(self.visitor, is_first_visit=True)

        if first_facility:
            # Option A: Facility found -> Go there
            simulation.add_event(ArriveAtFacilityEvent(self.time, self.visitor, first_facility))
        else:
            # Option B: No facility found -> EXIT PARK IMMEDIATELY
            self.visitor.update_rating_negative(0.5)
            simulation.visitors_completed.append(self.visitor)
            simulation.ratings.append(self.visitor.rating)
            simulation.total_entities_completed += 1
            simulation.total_people_completed += self.visitor.group_size

        # Process next visitor in reception queue
        if simulation.queue_reception.size() > 0:
            next_visitor, arrival_time = simulation.queue_reception.pop(self.time)
            simulation.reception.clerks_busy[self.clerk_index] = True
            service_minutes = simulation.reception.get_total_service_duration()
            end_time = self.time + timedelta(minutes=service_minutes)
            simulation.add_event(EndReceptionEvent(end_time, next_visitor, self.clerk_index))


# ============================================
# FACILITY EVENTS
# ============================================

class ArriveAtFacilityEvent(Event):
    """
    Event when visitor arrives at facility and joins queue.
    Creates abandonment event for non-express visitors.
    """

    def __init__(self, time, visitor, facility):
        super().__init__(time)
        self.visitor = visitor
        self.facility = facility

    def handle(self, simulation):
        simulation.clock = self.time

        # Add to appropriate queue (express or regular)
        if self.visitor.has_express_pass:
            self.facility.queue_express.add(self.visitor, self.time)
        else:
            self.facility.queue_regular.add(self.visitor, self.time)

        # Record queue entry time
        self.visitor.time_entered_queue = self.time

        # Schedule abandonment event for non-express visitors
        if not self.visitor.has_express_pass:
            threshold = self.visitor.get_abandonment_threshold()
            simulation.add_event(
                AbandonmentEvent(self.time + timedelta(minutes=threshold), self.visitor, self.facility))

        # Try to start service immediately if possible
        simulation.try_start_facility(self.facility, self.time)


class EndFacilityEvent(Event):
    """
    Event when visitor finishes using facility.
    Handles rating updates, departure checks, and routing to next activity.
    """

    def __init__(self, time, visitor, facility, instructor_idx=None):
        super().__init__(time)
        self.visitor = visitor
        self.facility = facility
        self.instructor_idx = instructor_idx  # For snorkel tours

    def handle(self, simulation):
        simulation.clock = self.time

        # Remove visitor from facility
        if self.visitor in self.facility.users_in_service:
            self.facility.users_in_service.remove(self.visitor)

        # Mark facility as visited
        if hasattr(self.visitor, 'visited_facilities'):
            if self.facility not in self.visitor.visited_facilities:
                self.visitor.visited_facilities.append(self.facility)

        # Special cleanup for specific facilities
        if isinstance(self.facility, Pipes_River):
            # Release tubes (handles shared tube logic)
            self.facility.release_tubes(self.visitor)

        elif isinstance(self.facility, Snorkel_Tour) and self.instructor_idx is not None:
            # Send instructor on break after tour
            self.facility.finish_tour(self.instructor_idx, self.time)
            simulation.add_event(
                InstructorBreakEndEvent(self.time + timedelta(minutes=30), self.instructor_idx, self.facility))

        # Update visitor rating based on experience
        if Sampling_Algorithms.had_good_experience():
            # Good experience: rating increases
            self.visitor.update_rating_positive(self.visitor.group_size, self.facility.adrenalin_level)
        else:
            # Bad experience: rating decreases slightly
            self.visitor.update_rating_negative(0.1)

        # --- NEW SPLITTING LOGIC (Moved here from Reception) ---
        entities_to_process = [self.visitor]  # Default: continue as is

        # If it's a full Family, check if they should split now (after first ride)
        if isinstance(self.visitor, Family):
            split_result = self.visitor.check_and_split()  # Returns list of subgroups or [self]
            if len(split_result) > 1:
                entities_to_process = split_result  # Logic split happened!

        # --- Process Next Step for each entity ---
        for entity in entities_to_process:

            # A. Determine Departure Time
            current_departure_time = None
            if isinstance(entity, SubGroup):
                current_departure_time = entity.parent_family.departure_time
            else:
                current_departure_time = entity.departure_time

            should_leave = False

            # Check Time
            if current_departure_time:
                dep_hour = int(current_departure_time)
                dep_min = int((current_departure_time % 1) * 60)
                dep_dt = simulation.clock.replace(hour=dep_hour, minute=dep_min, second=0)
                if simulation.clock >= dep_dt:
                    should_leave = True

            # B. Try to find next facility
            next_facility = None
            if not should_leave:
                next_facility = simulation.choose_facility(entity, is_first_visit=False)
                if next_facility is None:
                    should_leave = True  # No more rides available -> Leave

            # C. Execute Move (Leave or Next Facility)
            if should_leave:
                # --- EXIT LOGIC ---
                if isinstance(entity, (Family, SubGroup)):
                    original = entity if isinstance(entity, Family) else entity.parent_family

                    if isinstance(entity, SubGroup):
                        original.active_subgroups_count -= 1
                    else:
                        original.active_subgroups_count = 0

                    # Only "Complete" the family if everyone is out
                    if original.active_subgroups_count == 0:
                        package, price = Sampling_Algorithms.get_photo_purchase_decision(original.rating)
                        if package:
                            simulation.total_revenue += price
                        simulation.visitors_completed.append(original)
                        simulation.ratings.append(original.rating)
                        simulation.total_entities_completed += 1
                        simulation.total_people_completed += original.group_size
                else:
                    # Single/Teen exit
                    package, price = Sampling_Algorithms.get_photo_purchase_decision(entity.rating)
                    if package:
                        simulation.total_revenue += price
                    simulation.visitors_completed.append(entity)
                    simulation.ratings.append(entity.rating)
                    simulation.total_entities_completed += 1
                    simulation.total_people_completed += entity.group_size

            else:
                # --- NEXT FACILITY / LUNCH ---
                # Check for Lunch (13:00-15:00)
                current_hour = self.time.hour + self.time.minute / 60
                if 13 <= current_hour < 15 and Sampling_Algorithms.should_eat_lunch():
                    restaurant_choice = Sampling_Algorithms.choose_restaurant()
                    if restaurant_choice == "burger":
                        restaurant = simulation.burger_Restaurant
                    elif restaurant_choice == "pizza":
                        restaurant = simulation.pizza_Restaurant
                    else:
                        restaurant = simulation.salad_Restaurant
                    simulation.add_event(ArriveAtRestaurantEvent(self.time, entity, restaurant))
                else:
                    simulation.add_event(ArriveAtFacilityEvent(self.time, entity, next_facility))


# ============================================
# ABANDONMENT EVENT
# ============================================

class AbandonmentEvent(Event):
    """
    Event when visitor abandons queue due to excessive waiting.
    Only triggers if visitor is still in queue (wasn't served yet).
    """

    def __init__(self, time, visitor, facility):
        super().__init__(time)
        self.visitor = visitor
        self.facility = facility

    def handle(self, simulation):
        simulation.clock = self.time

        # Check if visitor is still in queue
        visitor_in_regular = any(v == self.visitor for v in self.facility.queue_regular)
        visitor_in_express = any(v == self.visitor for v in self.facility.queue_express)

        if not visitor_in_regular and not visitor_in_express:
            return  # Visitor already started service - cancel event

        # Remove from queue
        if visitor_in_regular:
            self.facility.queue_regular.remove(self.visitor, self.time)
        else:
            self.facility.queue_express.remove(self.visitor, self.time)

        # Update rating (abandonment penalty)
        self.visitor.update_rating_negative(0.8)

        # Special handling for teen groups
        if isinstance(self.visitor, TeenGroup):
            action = self.visitor.handle_abandonment(self.facility)

            if action == "buy_express_and_return":
                # Teen group bought express pass - return to SAME facility with express queue
                simulation.total_revenue += 50 * self.visitor.group_size
                simulation.add_event(ArriveAtFacilityEvent(self.time, self.visitor, self.facility))
            else:
                # Didn't buy express - move to next facility
                next_facility = simulation.choose_facility(self.visitor, is_first_visit=False)
                if next_facility:
                    simulation.add_event(ArriveAtFacilityEvent(self.time, self.visitor, next_facility))
                else:
                    # No more facilities - leave park
                    package, price = Sampling_Algorithms.get_photo_purchase_decision(self.visitor.rating)
                    if package:
                        simulation.total_revenue += price
                    simulation.ratings.append(self.visitor.rating)
                    simulation.visitors_completed.append(self.visitor)
                    simulation.total_entities_completed += 1
                    simulation.total_people_completed += self.visitor.group_size

        else:
            # Other visitor types: move to next facility
            next_facility = simulation.choose_facility(self.visitor, is_first_visit=False)
            if next_facility:
                simulation.add_event(ArriveAtFacilityEvent(self.time, self.visitor, next_facility))
            else:
                # No more facilities - leave park
                package, price = Sampling_Algorithms.get_photo_purchase_decision(self.visitor.rating)
                if package:
                    simulation.total_revenue += price
                simulation.ratings.append(self.visitor.rating)
                simulation.visitors_completed.append(self.visitor)
                simulation.total_entities_completed += 1
                simulation.total_people_completed += self.visitor.group_size


# ============================================
# RESTAURANT EVENTS
# ============================================

class ArriveAtRestaurantEvent(Event):
    """Event when visitor arrives at restaurant to order food."""

    def __init__(self, time, visitor, restaurant):
        super().__init__(time)
        self.visitor = visitor
        self.restaurant = restaurant

    def handle(self, simulation):
        simulation.clock = self.time
        self.restaurant.enter_queue(self.visitor, self.time)  # ✅ CHANGED: Pass current_time

        # Check if service station available
        station = self.restaurant.get_available_station(self.time)
        if station is not None:
            # Start service immediately
            self.restaurant.stations_busy[station] = True
            total_time = self.restaurant.get_total_time(self.visitor)
            end_time = self.time + timedelta(minutes=total_time)
            simulation.add_event(EndRestaurantServiceEvent(end_time, self.visitor, self.restaurant, station))


class EndRestaurantServiceEvent(Event):
    """Event when visitor receives food and starts eating."""

    def __init__(self, time, visitor, restaurant, station):
        super().__init__(time)
        self.visitor = visitor
        self.restaurant = restaurant
        self.station = station

    def handle(self, simulation):
        simulation.clock = self.time

        # Free up service station
        self.restaurant.stations_busy[self.station] = False

        # Charge for food
        price = self.restaurant.get_price(self.visitor)
        simulation.total_revenue += price

        # Check if meal was unsatisfactory (10% chance)
        if Sampling_Algorithms.is_meal_unsatisfactory():
            self.visitor.update_rating_negative(0.8)

        # Visitor starts eating
        meal_duration = self.restaurant.get_meal_duration()
        simulation.add_event(EndMealEvent(self.time + timedelta(minutes=meal_duration), self.visitor))

        # Process next visitor in restaurant queue
        if self.restaurant.queue.size() > 0:  # ✅ CHANGED: Use .size() instead of len()
            next_visitor, arrival_time = self.restaurant.queue.pop(self.time)  # ✅ CHANGED: Use .pop() instead of .popleft()
            self.restaurant.stations_busy[self.station] = True
            total_time = self.restaurant.get_total_time(next_visitor)
            end_time = self.time + timedelta(minutes=total_time)
            simulation.add_event(EndRestaurantServiceEvent(end_time, next_visitor, self.restaurant, self.station))


class EndMealEvent(Event):
    """Event when visitor finishes eating and resumes park activities."""

    def __init__(self, time, visitor):
        super().__init__(time)
        self.visitor = visitor

    def handle(self, simulation):
        simulation.clock = self.time

        # Get departure time correctly based on visitor type
        if isinstance(self.visitor, SubGroup):
            departure_time_val = self.visitor.parent_family.departure_time
        else:
            departure_time_val = self.visitor.departure_time

        # Check if it's time to leave
        if departure_time_val:
            departure_hour = int(departure_time_val)
            departure_minute = int((departure_time_val % 1) * 60)
            departure_datetime = simulation.clock.replace(hour=departure_hour, minute=departure_minute, second=0)

            if simulation.clock >= departure_datetime:
                # Time to leave
                if isinstance(self.visitor, (Family, SubGroup)):
                    original_family = self.visitor if isinstance(self.visitor, Family) else self.visitor.parent_family
                    original_family.active_subgroups_count -= 1

                    if original_family.active_subgroups_count == 0:
                        package, price = Sampling_Algorithms.get_photo_purchase_decision(original_family.rating)
                        if package:
                            simulation.total_revenue += price
                        simulation.ratings.append(original_family.rating)
                        simulation.visitors_completed.append(original_family)
                        simulation.total_entities_completed += 1
                        simulation.total_people_completed += original_family.group_size

                else:
                    package, price = Sampling_Algorithms.get_photo_purchase_decision(self.visitor.rating)
                    if package:
                        simulation.total_revenue += price
                    simulation.ratings.append(self.visitor.rating)
                    simulation.visitors_completed.append(self.visitor)
                    simulation.total_entities_completed += 1
                    simulation.total_people_completed += self.visitor.group_size

                return

        # Check if finished all facilities
        next_facility = simulation.choose_facility(self.visitor, is_first_visit=False)

        if next_facility is None:
            # Finished all facilities - leave
            if isinstance(self.visitor, (Family, SubGroup)):
                original_family = self.visitor if isinstance(self.visitor, Family) else self.visitor.parent_family
                original_family.active_subgroups_count -= 1

                if original_family.active_subgroups_count == 0:
                    package, price = Sampling_Algorithms.get_photo_purchase_decision(original_family.rating)
                    if package:
                        simulation.total_revenue += price
                    simulation.ratings.append(original_family.rating)
                    simulation.visitors_completed.append(original_family)
                    simulation.total_entities_completed += 1
                    simulation.total_people_completed += original_family.group_size

            else:
                package, price = Sampling_Algorithms.get_photo_purchase_decision(self.visitor.rating)
                if package:
                    simulation.total_revenue += price
                simulation.ratings.append(self.visitor.rating)
                simulation.visitors_completed.append(self.visitor)
                simulation.total_entities_completed += 1
                simulation.total_people_completed += self.visitor.group_size

        else:
            # Continue to next facility
            simulation.add_event(ArriveAtFacilityEvent(self.time, self.visitor, next_facility))


# ============================================
# INSTRUCTOR EVENTS
# ============================================

class InstructorBreakEndEvent(Event):
    """Event when snorkel instructor finishes break."""

    def __init__(self, time, instructor_idx, facility):
        super().__init__(time)
        self.instructor_idx = instructor_idx
        self.facility = facility

    def handle(self, simulation):
        simulation.clock = self.time

        # Instructor finishes break (may go to lunch if it's lunch time)
        goes_to_lunch = self.facility.finish_break(self.instructor_idx, self.time)

        # If instructor goes to lunch, create lunch end event
        if goes_to_lunch:
            # Calculate remaining time until 14:00
            current_minutes = self.time.hour * 60 + self.time.minute
            lunch_end = 14 * 60  # 14:00 in minutes
            remaining_lunch_time = lunch_end - current_minutes

            if remaining_lunch_time > 0:
                simulation.add_event(
                    InstructorLunchEndEvent(
                        self.time + timedelta(minutes=remaining_lunch_time),
                        self.instructor_idx,
                        self.facility
                    )
                )
        else:
            # Not lunch time - try to start new tour if instructor available
            simulation.try_start_facility(self.facility, self.time)


class InstructorLunchEndEvent(Event):
    """Event when snorkel instructor finishes lunch break."""

    def __init__(self, time, instructor_idx, facility):
        super().__init__(time)
        self.instructor_idx = instructor_idx
        self.facility = facility

    def handle(self, simulation):
        simulation.clock = self.time

        # Instructor finishes lunch and becomes available
        self.facility.finish_lunch(self.instructor_idx)

        # Try to start new tour
        simulation.try_start_facility(self.facility, self.time)


class VisitorDepartureEvent(Event):
    """
    Event when visitor leaves park at scheduled departure time.
    (Currently not used - departure handled in EndFacilityEvent/EndMealEvent)
    """

    def __init__(self, time, visitor):
        super().__init__(time)
        self.visitor = visitor

    def handle(self, simulation):
        simulation.clock = self.time

        # Process photo purchase
        package, price = Sampling_Algorithms.get_photo_purchase_decision(self.visitor.rating)
        if package:
            simulation.total_revenue += price

        # Record rating and completion
        simulation.ratings.append(self.visitor.rating)
        simulation.visitors_completed.append(self.visitor)


class EndOfDayEvent(Event):
    """Closes daily statistics for all queues once per day and schedules the next day closure."""

    def __init__(self, time, park_close_hour=19, park_close_minute=0):
        super().__init__(time)
        self.park_close_hour = park_close_hour
        self.park_close_minute = park_close_minute

    def handle(self, simulation):
        simulation.clock = self.time
        day_start = self.time.replace(hour=9, minute=0, second=0, microsecond=0)

        # 1) Reception queue daily stats
        q = simulation.queue_reception

        if not q.queue_change_times:
            q.queue_change_times = [self.time.replace(hour=9, minute=0, second=0, microsecond=0)]
            q.queue_lengths = [q.size()]

        q.record_queue_length(self.time)
        q.calc_daily_statistics()

        # 2) Facility queues daily stats
        for f in simulation.facilities:
            for q in [f.queue_regular, f.queue_express]:
                if not q.queue_change_times:
                    q.queue_change_times = [day_start]
                    q.queue_lengths = [q.size()]

                q.record_queue_length(self.time)
                q.calc_daily_statistics()

        # 3) Restaurant queues daily stats ✅ NEW!
        for restaurant in simulation.restaurants:
            q = restaurant.queue
            if not q.queue_change_times:
                q.queue_change_times = [day_start]
                q.queue_lengths = [q.size()]

            q.record_queue_length(self.time)
            q.calc_daily_statistics()

        # --- Schedule next day arrivals ---
        next_day_start = (self.time + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)

        simulation.add_event(FamilyArrivalEvent(next_day_start))
        simulation.add_event(SingleGroupArrivalEvent(next_day_start))
        simulation.add_event(TeensGroupArrivalEvent(next_day_start + timedelta(hours=1)))  # 10:00

        # Schedule next day end
        next_day_end = (self.time + timedelta(days=1)).replace(hour=self.park_close_hour,
                                                                 minute=self.park_close_minute, second=0, microsecond=0)
        simulation.add_event(self.__class__(next_day_end, self.park_close_hour, self.park_close_minute))