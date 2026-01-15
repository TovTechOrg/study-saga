"""
MODULE 1: Services for Core Engine & Data Models
Handles quiz, syllabus, and combat logic
"""

import random
from typing import Optional, List
from models import (
    Question, Syllabus, KnowledgeKeeper, Enemy, CombatManager, GameState
)


# ==================== TASK 1.2: SYLLABUS & QUIZ SERVICE ====================

class SyllabusService:
    """Service for loading and managing syllabi"""
    
    def __init__(self):
        self.syllabi = {}
        self._load_hardcoded_syllabi()

    def _load_hardcoded_syllabi(self):
        """Load hardcoded syllabi for MVP (Task 1.2)"""
        
        # Biology 101 Syllabus
        biology_questions = [
            Question("What is the powerhouse of the cell?", 
                    ["Mitochondria", "Nucleus", "Ribosome", "Chloroplast"], 0),
            Question("Which organelle is responsible for protein synthesis?", 
                    ["Mitochondria", "Ribosome", "Golgi apparatus", "Lysosome"], 1),
            Question("What is the process by which plants make food?", 
                    ["Respiration", "Photosynthesis", "Fermentation", "Digestion"], 1),
            Question("How many chromosomes do humans have?", 
                    ["23", "46", "48", "52"], 1),
            Question("What is the basic unit of life?", 
                    ["Atom", "Molecule", "Cell", "Organ"], 2),
            Question("Which blood cells fight infections?", 
                    ["Red blood cells", "White blood cells", "Platelets", "Plasma"], 1),
            Question("What is the main function of the heart?", 
                    ["Digestion", "Pumping blood", "Hormone production", "Immunity"], 1),
            Question("Which enzyme breaks down starch?", 
                    ["Pepsin", "Amylase", "Lipase", "Protease"], 1),
            Question("What is the pH of stomach acid?", 
                    ["7", "3-4", "10", "14"], 1),
            Question("Which part of the brain controls balance?", 
                    ["Cerebrum", "Cerebellum", "Medulla", "Thalamus"], 1),
        ]
        self.syllabi['biology'] = Syllabus(
            "Biology 101",
            "Foundations of cellular biology and human anatomy",
            biology_questions
        )

        # History 101 Syllabus
        history_questions = [
            Question("In which year did World War II end?", 
                    ["1943", "1944", "1945", "1946"], 2),
            Question("Who was the first President of the United States?", 
                    ["Thomas Jefferson", "George Washington", "John Adams", "Benjamin Franklin"], 1),
            Question("The Renaissance began in which country?", 
                    ["France", "Italy", "Germany", "Spain"], 1),
            Question("Which empire built the Great Wall of China?", 
                    ["Sui", "Ming", "Tang", "Han"], 1),
            Question("In what year did the Declaration of Independence get signed?", 
                    ["1774", "1775", "1776", "1777"], 2),
            Question("Who discovered America in 1492?", 
                    ["Amerigo Vespucci", "Christopher Columbus", "Leif Erikson", "Ferdinand Magellan"], 1),
            Question("The Industrial Revolution started in which country?", 
                    ["France", "Germany", "United Kingdom", "United States"], 2),
            Question("Who was the author of the Declaration of Independence?", 
                    ["Benjamin Franklin", "John Adams", "Thomas Jefferson", "James Madison"], 2),
            Question("In which year did the Berlin Wall fall?", 
                    ["1987", "1988", "1989", "1990"], 2),
            Question("Which ancient wonder is still standing today?", 
                    ["Colossus of Rhodes", "Hanging Gardens", "Great Pyramid of Giza", "Lighthouse of Alexandria"], 2),
        ]
        self.syllabi['history'] = Syllabus(
            "History 101",
            "Key events and figures in world history",
            history_questions
        )

        # AI & Ethics 101 Syllabus (bonus)
        ai_questions = [
            Question("What does AI stand for?", 
                    ["Artificial Intelligence", "Augmented Integration", "Advanced Imaging", "Automated Input"], 0),
            Question("Which of these is a form of machine learning?", 
                    ["Linear regression", "All of the above", "Neural networks", "Decision trees"], 1),
            Question("What is the primary goal of data ethics?", 
                    ["Maximize profit", "Ensure fairness and transparency", "Reduce computation time", "Simplify models"], 1),
            Question("What is bias in AI?", 
                    ["Random errors", "Systematic errors favoring certain groups", "Correct predictions", "None of the above"], 1),
            Question("Which technique helps prevent overfitting?", 
                    ["Training longer", "Regularization", "Using more features", "Ignoring test data"], 1),
            Question("What does CNN stand for?", 
                    ["Central Neural Network", "Convolutional Neural Network", "Connected Neuron Network", "Continuous Normalization Net"], 1),
            Question("What is supervised learning?", 
                    ["Learning with labeled data", "Learning without labels", "Self-teaching", "Random guessing"], 0),
            Question("What does NLP stand for?", 
                    ["Natural Language Processing", "Neural Learning Platform", "Network Layer Protocol", "Normalized Learning Process"], 0),
            Question("What is the curse of dimensionality?", 
                    ["Having too many features", "Having too few samples", "Model complexity", "Both A and B"], 0),
            Question("Which metric is best for imbalanced datasets?", 
                    ["Accuracy", "F1-score", "Precision only", "Recall only"], 1),
        ]
        self.syllabi['ai'] = Syllabus(
            "AI & Ethics 101",
            "Foundations of AI, machine learning, and ethical AI",
            ai_questions
        )

    def get_all_syllabi(self) -> List[dict]:
        """Get all available syllabi (for display in Syllabus Select screen)"""
        return [
            {
                'id': syllabi_id,
                'name': syllabus.name,
                'description': syllabus.description,
                'question_count': len(syllabus.questions)
            }
            for syllabi_id, syllabus in self.syllabi.items()
        ]

    def get_syllabus(self, syllabus_id: str) -> Optional[Syllabus]:
        """Get a specific syllabus by ID"""
        return self.syllabi.get(syllabus_id)


class QuizService:
    """Service for quiz operations (Task 1.2)"""

    @staticmethod
    def get_random_question(syllabus: Syllabus, exclude_texts: list = None) -> Optional[Question]:
        """
        Task 1.2: Get a random question from the syllabus
        Excludes already-asked questions to prevent repeats
        Returns a single Question object with shuffled answer options
        """
        if not syllabus or not syllabus.questions:
            return None
        
        exclude_texts = exclude_texts or []
        available_questions = [q for q in syllabus.questions if q.question_text not in exclude_texts]
        
        # If we've exhausted all questions in this combat, return None to avoid repeats
        if not available_questions:
            return None

        return random.choice(available_questions)


# ==================== TASK 1.3: COMBAT MANAGER ====================

class CombatService:
    """Service for managing combat flow and actions (Module 3 integration)"""

    def __init__(self, combat_manager: CombatManager):
        self.combat = combat_manager

    # ========== TASK 3.1: Player Attack Action ==========
    def player_attack(self) -> dict:
        """
        Wire the "Attack" button action
        Consumes CAP and prepares quiz question
        """
        result = {
            'success': False,
            'message': '',
            'cap_cost': 3,
            'question': None
        }

        # Check if player has enough CAP
        if self.combat.player.current_cap < 3:
            result['message'] = 'Not enough CAP to attack!'
            return result

        # Consume CAP
        self.combat.player.consume_cap(3)
        result['cap_cost'] = 3
        
        # Draw next question from the per-combat queue to avoid repeats within a cycle
        question = self._draw_next_question()
        if not question:
            result['message'] = 'No questions available'
            return result

        self.combat.current_question = question
        result['success'] = True
        result['question'] = {
            'text': question.question_text,
            'options': question.get_shuffled_options(),
            'explanation': 'Answer the question to deal damage!'
        }

        return result

    # ========== TASK 3.2: Player Recharge Action ==========
    def player_recharge(self) -> dict:
        """
        Wire the "Recharge (CAP)" button action
        Restores CAP and ends player's turn
        """
        result = {
            'success': True,
            'message': 'CAP recharged!',
            'cap_restored': 5,
            'new_cap': 0
        }

        # Restore CAP
        self.combat.player.restore_cap(5)
        result['new_cap'] = self.combat.player.current_cap

        # End player's turn
        self.combat.transition_to(GameState.ENEMY_TURN)

        return result

    # ========== TASK 3.3: Player Use Ability Action ==========
    def player_use_ability(self) -> dict:
        """
        Wire the "Use Ability" button action
        Implements "Simplify Question" ability
        """
        result = {
            'success': False,
            'message': '',
            'cap_cost': 5
        }

        # Check if player has enough CAP
        if self.combat.player.current_cap < 5:
            result['message'] = 'Not enough CAP to use ability!'
            return result

        # Consume CAP
        self.combat.player.consume_cap(5)

        # Set simplify flag
        self.combat.player.is_simplify_active = True
        result['success'] = True
        result['message'] = 'Simplify Question activated! One random answer will be hidden.'

        # Trigger attack action
        attack_result = self.player_attack()
        result['question'] = attack_result.get('question')

        return result

    def _draw_next_question(self) -> Optional[Question]:
        """Draw the next question without repeats until the pool is exhausted."""
        # Refill the queue when empty (new cycle)
        if not self.combat.question_queue:
            self.combat.question_queue = list(self.combat.syllabus.questions)
            random.shuffle(self.combat.question_queue)
            self.combat.asked_questions = []

        if not self.combat.question_queue:
            return None

        # Avoid immediate repeat of the last question when possible
        if (
            self.combat.last_question_text
            and len(self.combat.question_queue) > 1
            and self.combat.question_queue[0].question_text == self.combat.last_question_text
        ):
            self.combat.question_queue.append(self.combat.question_queue.pop(0))

        question = self.combat.question_queue.pop(0)
        self.combat.asked_questions.append(question.question_text)
        self.combat.last_question_text = question.question_text
        return question

    # ========== TASK 3.4: Quiz Resolution Logic ==========
    def resolve_quiz_answer(self, selected_option_index: int) -> dict:
        """
        When player clicks an answer:
        - Check if correct
        - Apply damage
        - Return result for feedback modal
        """
        result = {
            'is_correct': False,
            'message': '',
            'damage_dealt': 0,
            'damage_taken': 0,
            'correct_answer': '',
            'player_hp': 0,
            'enemy_hp': 0
        }

        if not self.combat.current_question:
            result['message'] = 'No question to resolve'
            return result

        question = self.combat.current_question

        # Check answer correctness
        is_correct = question.is_answer_correct(selected_option_index)
        result['is_correct'] = is_correct
        result['correct_answer'] = question.get_correct_answer_text()

        if is_correct:
            # Deal cognitive damage to enemy
            damage = self.combat.player.cognitive_power
            self.combat.enemy.take_damage(damage)
            result['damage_dealt'] = damage
            result['message'] = 'Correct! You dealt cognitive damage!'
        else:
            # Deal confusion damage to player
            damage = 10
            self.combat.player.take_damage(damage)
            result['damage_taken'] = damage
            result['message'] = 'Incorrect! You took confusion damage!'

        # Update HPs
        result['player_hp'] = self.combat.player.current_hp
        result['enemy_hp'] = self.combat.enemy.current_hp

        # Reset simplify flag
        self.combat.player.is_simplify_active = False

        # Transition to enemy turn (will be called after feedback modal closes)
        self.combat.transition_to(GameState.ENEMY_TURN)

        return result

    # ========== TASK 3.5: Enemy AI Turn ==========
    def execute_enemy_turn(self) -> dict:
        """
        MVP Enemy AI: Deal basic damage to player
        """
        result = {
            'success': True,
            'message': '',
            'enemy_action': 'Attack',
            'damage_dealt': self.combat.enemy.attack_power,
            'player_hp': 0
        }

        # Enemy deals damage
        self.combat.player.take_damage(self.combat.enemy.attack_power)
        result['player_hp'] = self.combat.player.current_hp
        result['message'] = f'{self.combat.enemy.name} attacked for {self.combat.enemy.attack_power} damage!'

        # Increment turn counter
        self.combat.turn_count += 1

        # Check for game over conditions
        game_over = self.combat.check_game_over()
        if game_over:
            result['game_over'] = game_over

        # Transition back to player turn
        self.combat.transition_to(GameState.PLAYER_TURN)

        return result

    # ========== TASK 3.6: Win/Loss Condition ==========
    def check_game_over(self) -> Optional[str]:
        """
        Check for win/lose conditions
        Returns: 'win', 'lose', or None
        """
        return self.combat.check_game_over()

    def get_combat_state(self) -> dict:
        """Get current combat state for UI updates"""
        game_over = self.combat.check_game_over()
        state = {
            'player': self.combat.player.to_dict(),
            'enemy': self.combat.enemy.to_dict(),
            'game_state': self.combat.current_state,
            'turn': self.combat.turn_count,
            'game_over': game_over is not None,
            'result': 'victory' if game_over == GameState.WIN else 'defeat' if game_over == GameState.LOSE else None
        }
        return state
