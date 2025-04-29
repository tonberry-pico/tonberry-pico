# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Matthias Blankertz <matthias@blankertz.org>

import asyncio
import heapq
import time


class TimerManager:
    def __init__(self, timer_debug=False):
        self.timers = []
        self.timer_debug = timer_debug
        self.task = asyncio.create_task(self._timer_worker())
        self.worker_event = asyncio.Event()

    def schedule(self, when, what):
        cur_nearest = self.timers[0][0] if len(self.timers) > 0 else None
        heapq.heappush(self.timers, (when, what))
        if cur_nearest is None or cur_nearest > self.timers[0][0]:
            # New timer is closer than previous closest timer
            if self.timer_debug:
                print(f'cur_nearest: {cur_nearest}, new next: {self.timers[0][0]}')
                print("schedule: wake")
            self.worker_event.set()

    def cancel(self, what):
        try:
            (when, _), i = next(filter(lambda item: item[0][1] == what, zip(self.timers, range(len(self.timers)))))
        except StopIteration:
            return False
        del self.timers[i]
        heapq.heapify(self.timers)
        if i == 0:
            # Cancel timer was closest timer
            if self.timer_debug:
                print("cancel: wake")
            self.worker_event.set()
        return True

    async def _timer_worker(self):
        while True:
            if len(self.timers) == 0:
                # Nothing to do
                await self.worker_event.wait()
                if self.timer_debug:
                    print("_timer_worker: event 0")
                self.worker_event.clear()
                continue
            cur_nearest = self.timers[0][0]
            wait_time = cur_nearest - time.ticks_ms()
            if wait_time > 0:
                if self.timer_debug:
                    print(f"_timer_worker: next is {self.timers[0]}, sleep {wait_time} ms")
                try:
                    await asyncio.wait_for_ms(self.worker_event.wait(), wait_time)
                    if self.timer_debug:
                        print("_timer_worker: event 1")
                    # got woken up due to event
                    self.worker_event.clear()
                    continue
                except asyncio.TimeoutError:
                    pass
            _, callback = heapq.heappop(self.timers)
            callback()
