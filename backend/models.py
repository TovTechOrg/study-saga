import json
from typing import List, Dict


class Option:
    def __init__(self, text: str, is_correct: bool, feedback: str):
        self.text = text
        self.is_correct = is_correct
        self.feedback = feedback

    def to_dict(self):
        return self.__dict__

    @staticmethod
    def from_dict(data: Dict):
        return Option(**data)


class Question:
    def __init__(self, q_type: str, text: str, options: List[Option]):
        self.type = q_type
        self.text = text
        self.options = options

    def to_dict(self):
        return {"type": self.type, "text": self.text, "options": [o.to_dict() for o in self.options]}

    @staticmethod
    def from_dict(data: Dict):
        options = [Option.from_dict(o) for o in data.get("options", [])]
        return Question(data["type"], data["text"], options)


class KnowledgeKeeper:
    def __init__(self, name: str, hp: int, cap: int, abilities: List[str]):
        self.name = name
        self.hp = hp
        self.cap = cap
        self.abilities = abilities

    def to_dict(self):
        return self.__dict__

    @staticmethod
    def from_dict(data: Dict):
        return KnowledgeKeeper(**data)


class Enemy:
    def __init__(self, name: str, hp: int, stats: Dict, effects: List[str]):
        self.name = name
        self.hp = hp
        self.stats = stats
        self.effects = effects

    def to_dict(self):
        return self.__dict__

    @staticmethod
    def from_dict(data: Dict):
        return Enemy(**data)


class Syllabus:
    def __init__(self, questions: List[Question]):
        self.questions = questions

    def to_dict(self):
        return {"questions": [q.to_dict() for q in self.questions]}

    @staticmethod
    def from_dict(data: Dict):
        return Syllabus([Question.from_dict(q) for q in data.get("questions", [])])


class BattleState:
    def __init__(self, keeper: KnowledgeKeeper, enemy: Enemy, turn: int, question: Question, cap: int, feedback: str):
        self.keeper = keeper
        self.enemy = enemy
        self.turn = turn
        self.question = question
        self.cap = cap
        self.feedback = feedback

    def to_dict(self):
        return {
            "keeper": self.keeper.to_dict(),
            "enemy": self.enemy.to_dict(),
            "turn": self.turn,
            "question": self.question.to_dict(),
            "cap": self.cap,
            "feedback": self.feedback,
        }

    @staticmethod
    def from_dict(data: Dict):
        return BattleState(
            KnowledgeKeeper.from_dict(data["keeper"]),
            Enemy.from_dict(data["enemy"]),
            data["turn"],
            Question.from_dict(data["question"]),
            data["cap"],
            data["feedback"],
        )


# Quick JSON helpers
def to_json(obj) -> str:
    return json.dumps(obj.to_dict(), indent=2)

def from_json(cls, json_str: str):
    return cls.from_dict(json.loads(json_str))
