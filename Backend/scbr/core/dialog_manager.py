# scbr/core/dialog_manager.py
from collections import defaultdict

class DialogManager:
    def __init__(self, max_turns: int = 8):
        self.sessions = defaultdict(lambda: {"turns": [], "problem_accu": ""})
        self.max_turns = max_turns

    def append_user(self, sid: str, user_query: str):
        s = self.sessions[sid]
        s["turns"].append({"role":"user","content":user_query})
        s["problem_accu"] = f"{s['problem_accu']}；{user_query}" if s["problem_accu"] else user_query
        return s

    def append_assistant(self, sid: str, text: str):
        self.sessions[sid]["turns"].append({"role":"assistant","content":text})

    def get_problem_accu(self, sid: str) -> str:
        return self.sessions[sid]["problem_accu"]

    def reset(self, sid: str):
        self.sessions.pop(sid, None)

    def turn_index(self, sid: str) -> int:
        return len(self.sessions[sid]["turns"])//2
