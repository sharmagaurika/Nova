"""Guides the user to a person wearing a given colour, by voice, for a limited time."""
import threading
import time

import scene
from voice import say


class Finder:
    def __init__(self, state, seconds, every_s, on_reached=None):
        self.state = state
        self.on_reached = on_reached or (lambda: None)
        self.seconds = seconds
        self.every_s = every_s
        self.colour = None
        self._stop = threading.Event()

    def start(self, colour):
        self.stop()
        self._stop = threading.Event()
        self.colour = colour
        threading.Thread(target=self._loop, args=(colour, self._stop), daemon=True).start()

    def stop(self):
        self._stop.set()
        self.colour = None

    def _match(self, colour):
        """Biggest (closest) person whose shirt is this colour, or None."""
        frame, dets = self.state.get("frame"), self.state.get("all_detections", [])
        if frame is None:
            return None, None
        people = [d for d in dets if d[0] == "person" and scene.shirt_colour(frame, d[2]) == colour]
        if not people:
            return None, frame.shape
        return max(people, key=lambda d: d[2][3] - d[2][1]), frame.shape

    def _loop(self, colour, stop):
        end = time.time() + self.seconds
        last_msg, last_said, misses = None, 0, 0
        while not stop.is_set() and time.time() < end:
            person, shape = self._match(colour)
            if person:
                misses = 0
                where, how_far = scene.direction(person[2], shape[1]), scene.distance(person[2], shape[0])
                if how_far == "right in front of you" and where == "straight ahead":
                    self.on_reached()
                    say(f"You've reached the person in {colour}. They're right in front of you.")
                    break
                msg = f"Person in {colour} {where}, {how_far}."
            else:
                misses += 1
                msg = f"No one in {colour} yet. Turn slowly." if misses >= 3 else None
            # Speak when the guidance changes, or repeat it every few seconds
            if msg and (msg != last_msg or time.time() - last_said > 5):
                say(msg)
                last_msg, last_said = msg, time.time()
                if not person:
                    misses = 0
            stop.wait(self.every_s)
        else:
            if not stop.is_set():
                say(f"I stopped looking for the person in {colour}.")
        self.colour = None
