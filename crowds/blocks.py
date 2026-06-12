class StateBlock:

    def __init__(self, state, start, end):
        self.state = state
        self.start = start
        self.end = end

    @property
    def duration(self):
        return self.end - self.start

    def to_dict(self):
        return {"type": "state", "state": self.state, "start": self.start, "end": self.end}

    @classmethod
    def from_dict(cls, data):
        return cls(state=data["state"], start=data["start"], end=data["end"])

    def __repr__(self):
        return f"StateBlock({self.state} [{self.start}-{self.end}])"


class TransitionBlock:

    def __init__(self, start, end, state_from, state_to, frames_from=None, frames_to=None):
        self.start = start
        self.end = end
        self.state_from = state_from
        self.state_to = state_to
        # Si no se especifican, se reparten 50/50
        total = end - start
        self.frames_from = frames_from if frames_from is not None else total // 2
        self.frames_to = frames_to if frames_to is not None else total - self.frames_from

    @property
    def duration(self):
        return self.end - self.start

    def to_dict(self):
        return {
            "type": "transition",
            "start": self.start,
            "end": self.end,
            "state_from": self.state_from,
            "state_to": self.state_to,
            "frames_from": self.frames_from,
            "frames_to": self.frames_to
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            start = data["start"],
            end = data["end"],
            state_from = data["state_from"],
            state_to = data["state_to"],
            frames_from = data.get("frames_from"),
            frames_to = data.get("frames_to")
        )

    def __repr__(self):
        return f"TransitionBlock({self.state_from}->{self.state_to} [{self.start}-{self.end}])"
