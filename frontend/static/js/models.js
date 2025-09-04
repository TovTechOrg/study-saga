class Option {
  constructor(text, isCorrect, feedback) {
    this.text = text;
    this.isCorrect = isCorrect;
    this.feedback = feedback;
  }
}

class Question {
  constructor(type, text, options = []) {
    this.type = type;
    this.text = text;
    this.options = options;
  }
}

class KnowledgeKeeper {
  constructor(name, hp, cap, abilities = []) {
    this.name = name;
    this.hp = hp;
    this.cap = cap;
    this.abilities = abilities;
  }
}

class Enemy {
  constructor(name, hp, stats = {}, effects = []) {
    this.name = name;
    this.hp = hp;
    this.stats = stats;
    this.effects = effects;
  }
}

class Syllabus {
  constructor(name, questions = []) {
    this.name = name;
    this.questions = questions;
  }
}

class BattleState {
  constructor(keeper, enemy, turn, question, cap, feedback) {
    this.keeper = keeper;
    this.enemy = enemy;
    this.turn = turn;
    this.question = question;
    this.cap = cap;
    this.feedback = feedback;
  }
}

// JSON helpers
function toJson(obj) {
  return JSON.stringify(obj, null, 2);
}

function fromJson(cls, jsonStr) {
  const data = JSON.parse(jsonStr);
  if (cls === KnowledgeKeeper) return new KnowledgeKeeper(data.name, data.hp, data.cap, data.abilities);
  if (cls === Enemy) return new Enemy(data.name, data.hp, data.stats, data.effects);
  if (cls === Question) return new Question(data.type, data.text, data.options.map(o => new Option(o.text, o.isCorrect, o.feedback)));
  if (cls === Syllabus) return new Syllabus(data.name, data.questions.map(q => fromJson(Question, JSON.stringify(q))));
  if (cls === BattleState) return new BattleState(
    fromJson(KnowledgeKeeper, JSON.stringify(data.keeper)),
    fromJson(Enemy, JSON.stringify(data.enemy)),
    data.turn,
    fromJson(Question, JSON.stringify(data.question)),
    data.cap,
    data.feedback
  );
  return null;
}
