"""Regras robots com curingas e prioridade da regra mais especifica."""

import re
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser


class RobotsPolicy:
    def __init__(self, text):
        self.legacy = RobotFileParser()
        self.legacy.parse(text.splitlines())
        self.groups = []
        agents, rules = [], []
        for line in text.splitlines() + ["User-agent: __end__"]:
            line = line.split("#", 1)[0].strip()
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key, value = key.strip().lower(), value.strip()
            if key == "user-agent":
                if rules:
                    self.groups.append((agents, rules))
                    agents, rules = [], []
                agents.append(value.lower())
            elif key in ("allow", "disallow") and agents:
                rules.append((key == "allow", value))

    def crawl_delay(self, agent):
        return self.legacy.crawl_delay(agent)

    def can_fetch(self, agent, url):
        agent = agent.lower()
        groups = []
        for agents, rules in self.groups:
            scores = [len(a) for a in agents if a != "*" and a in agent]
            score = max(scores) if scores else (0 if "*" in agents else -1)
            if score >= 0:
                groups.append((score, rules))
        if not groups:
            return True
        best = max(score for score, _ in groups)
        p = urlsplit(url)
        path = p.path or "/"
        if p.query:
            path += "?" + p.query
        matched = []
        for score, rules in groups:
            if score != best:
                continue
            for allow, pattern in rules:
                if not pattern:
                    continue
                end = pattern.endswith("$")
                raw = pattern[:-1] if end else pattern
                regex = "^" + re.escape(raw).replace(r"\*", ".*") + ("$" if end else "")
                if re.search(regex, path):
                    matched.append((len(raw.replace("*", "")), allow))
        return max(matched)[1] if matched else True
