import numpy as np
from datetime import datetime
from collections import deque


class QueueServer:
    """
    Queue management class with statistics tracking.
    Tracks waiting times, queue lengths, and calculates daily averages.
    Used for both regular and express queues at all facilities.
    """

    def __init__(self):
        self.server_queue = deque()  # Main queue: [(visitor, arrival_time), ...]
        self.active_hours = 10  # Default active hours (9:00-19:00)

        # Statistics tracking
        self.waiting_times = []  # List of all waiting times (minutes)
        self.total_queue_length_time = 0  # Area under queue length curve
        self.queue_lengths = [0]  # Queue length at each change
        self.queue_change_times = []  # Times when queue length changed

        # Daily statistics (calculated at end of day)
        self.daily_avg_queue_lengths = []  # Average queue length per day
        self.daily_avg_waiting_times = []  # Average waiting time per day

    def add(self, visitor, arrival_time):
        """
        Add visitor to queue and record statistics.

        Args:
            visitor: Visitor object
            arrival_time: DateTime when visitor joined queue
        """
        self.server_queue.append([visitor, arrival_time])
        self.record_queue_length(arrival_time)

    def insert(self, index, visitor, time):
        """
        Insert visitor at specific position in queue.
        Used for returning visitors to queue after failed batch formation.

        Args:
            index: Position to insert (0 = front of queue)
            visitor: Visitor object
            time: DateTime of insertion
        """
        temp_list = list(self.server_queue)
        temp_list.insert(index, [visitor, time])
        self.server_queue = deque(temp_list)
        if time is not None:
            self.record_queue_length(time)

    def remove(self, visitor, current_time):
        """
        Remove specific visitor from queue (e.g., for abandonment).

        Args:
            visitor: Visitor object to remove
            current_time: DateTime of removal
        """
        self.record_queue_length(current_time)  # Record statistics before removal

        # Find and remove visitor
        for i, (v, t) in enumerate(self.server_queue):
            if v == visitor:
                temp_list = list(self.server_queue)
                temp_list.pop(i)
                self.server_queue = deque(temp_list)
                return

    def pop(self, removing_time):
        """
        Remove and return first visitor from queue.
        Calculates waiting time if removing_time is provided.

        Args:
            removing_time: DateTime when visitor removed (None to skip statistics)

        Returns:
            (visitor, arrival_time) or (None, None) if queue empty
        """
        if self.server_queue:
            extracted = self.server_queue.popleft()

            if removing_time is not None:
                # Record statistics
                self.record_queue_length(removing_time)

                # Calculate waiting time
                wait_duration = (removing_time - extracted[1]).total_seconds() / 60  # Minutes
                self.waiting_times.append(wait_duration)

            return extracted[0], extracted[1]
        return None, None

    def record_queue_length(self, current_time):
        """
        Record queue length change for statistics.
        Updates area under queue length curve.

        Args:
            current_time: DateTime of queue length change
        """
        if self.queue_lengths and self.queue_change_times:
            # Calculate time since last change
            last_time = self.queue_change_times[-1]
            duration_hours = (current_time - last_time).total_seconds() / 3600

            # Update area under curve: queue_length * time_duration
            self.total_queue_length_time += self.queue_lengths[-1] * duration_hours

        # Record new state
        self.queue_change_times.append(current_time)
        self.queue_lengths.append(self.size())

    def size(self):
        """Return current number of visitors in queue."""
        return len(self.server_queue)

    def __len__(self):
        """Support len() operator."""
        return self.size()

    def __bool__(self):
        """Support boolean check (True if queue not empty)."""
        return self.size() > 0

    def __getitem__(self, index):
        """
        Support indexing: queue[0] returns first visitor.

        Args:
            index: Position in queue

        Returns:
            Visitor object at index
        """
        return list(self.server_queue)[index][0]

    def __iter__(self):
        """
        Support iteration over queue.

        Yields:
            Visitor objects in queue order
        """
        for visitor, time in self.server_queue:
            yield visitor

    def set_active_hours(self, opening_hour, closing_hour):
        """
        Set active hours for daily statistics calculation.

        Args:
            opening_hour: String in format "HH:MM" (e.g., "09:00")
            closing_hour: String in format "HH:MM" (e.g., "19:00")
        """
        fmt = '%H:%M'
        tdelta = datetime.strptime(closing_hour, fmt) - datetime.strptime(opening_hour, fmt)
        self.active_hours = tdelta.total_seconds() / 3600  # Convert to hours

    def calc_daily_statistics(self):
        """
        Calculate and store daily statistics.
        Called at end of simulation day.
        Resets daily counters for next day.
        """
        # Calculate average queue length (area under curve / active hours)
        daily_avg_length = self.total_queue_length_time / self.active_hours if self.active_hours > 0 else 0
        self.daily_avg_queue_lengths.append(daily_avg_length)

        # Calculate average waiting time
        daily_avg_wait = np.mean(self.waiting_times) if self.waiting_times else 0
        self.daily_avg_waiting_times.append(daily_avg_wait)

        # Reset daily counters
        self.total_queue_length_time = 0
        self.queue_change_times = []
        self.queue_lengths = [0]
        self.waiting_times = []