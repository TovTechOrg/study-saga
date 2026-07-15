import json
import os

kb_path = r'c:\Users\talia\Desktop\study-saga\backend\kb_external.json'

new_bio_hints = [
    {"question": "Which nitrogenous base pairs with Adenine in DNA?", "hint": "Think of the base that is replaced by Uracil in RNA."},
    {"question": "Which blood component is primarily responsible for clotting?", "hint": "Focus on small, colorless cell fragments that clump together at injury sites."},
    {"question": "Which part of the plant is responsible for gas exchange?", "hint": "Look for microscopic pores found on the under-surface of leaves."},
    {"question": "Who is considered the father of genetics?", "hint": "Consider the Augustinian friar who studied inheritance traits in pea plants."},
    {"question": "What is the structural and functional unit of the kidney?", "hint": "This microscopic structure performs the vital task of blood filtration."},
    {"question": "Which theory explains the origin of mitochondria and chloroplasts?", "hint": "This theory suggests these organelles originated as free-living bacteria."},
    {"question": "What type of cell division produces gametes?", "hint": "Consider a specialized form of division that results in four non-identical daughter cells."},
    {"question": "What is the standard name for 'junk DNA' that doesn't code for proteins?", "hint": "These sequences are transcribed but not translated into protein sequences."},
    {"question": "Which are parts of the central nervous system?", "hint": "This system consists of the main control center and the primary link to the rest of the body."},
    {"question": "What is the primary function of the large intestine?", "hint": "Look for the final stage of digestion where fluids are reclaimed before waste disposal."}
]

new_math_hints = [
    {"question": "What is the median of the set {2, 5, 8, 12, 15}?", "hint": "Arrange the numbers in order and identify the middle value."},
    {"question": "What is the value of pi to two decimal places?", "hint": "Think of the ratio of a circle's circumference to its diameter, starting with 3.1..."},
    {"question": "What is the area of a circle with radius 3? (Use pi = 3.14)", "hint": "Apply the formula: Area = pi times the square of the radius."},
    {"question": "Solve for x: 5x - 7 = 18", "hint": "Add 7 to both sides, then divide the result by 5."},
    {"question": "What is the slope of a line passing through (1, 2) and (3, 6)?", "hint": "Calculate the change in y divided by the change in x (rise over run)."},
    {"question": "What is the sum of 1/3 and 1/6?", "hint": "Find a common denominator, such as 6, before adding the numerators."},
    {"question": "How many degrees are in a right angle?", "hint": "Consider the angle formed by two perpendicular lines."},
    {"question": "What is the volume of a cube with side length 4?", "hint": "Calculate the side length multiplied by itself three times (s^3)."},
    {"question": "What is the value of 5! (5 factorial)?", "hint": "Multiply 5 by 4, then by 3, by 2, and finally by 1."},
    {"question": "What is 15% of 200?", "hint": "Find 10% first, then add half of that value to reach 15%."}
]

new_chem_hints = [
    {"question": "What is the chemical symbol for Helium?", "hint": "A two-letter symbol derived from its name, common in balloons."},
    {"question": "What is the atomic number of Carbon?", "hint": "The number of protons found in this basic building block of organic life."},
    {"question": "Which gas is used in light bulbs to prevent the filament from burning?", "hint": "Look for a noble gas that is more common and cheaper than Krypton."},
    {"question": "What is the common name for Sodium Chloride?", "hint": "A mineral substance essential for life, often found on your dinner table."},
    {"question": "What is the formula for Sulfuric Acid?", "hint": "A strong mineral acid with two hydrogen atoms and a sulfate group."},
    {"question": "Which element is the primary component of steel?", "hint": "The most common metal used in construction, often alloyed with carbon."},
    {"question": "What is the most reactive metal on the periodic table?", "hint": "A radioactive alkali metal found at the bottom of Group 1."},
    {"question": "Which subatomic particle has a negative charge?", "hint": "The particle that orbits the nucleus in specialized shells or regions."},
    {"question": "What is the process of a solid turning directly into a gas?", "hint": "Consider the transition that skips the liquid phase entirely."},
    {"question": "What is the main gas responsible for global warming?", "hint": "A gas produced by combustion and respiration, captured by plants."},
    {"question": "Which metal is liquid at room temperature?", "hint": "Commonly used in traditional thermometers; also known as quicksilver."},
    {"question": "What is the result of an acid reacting with a base?", "hint": "Think of a neutralization reaction producing two common inorganic compounds."},
    {"question": "What is the hardest natural substance on Earth?", "hint": "An allotrope of carbon with atoms arranged in a rigid crystal lattice."},
    {"question": "Which element is known as the 'Building Block of Life'?", "hint": "The element capable of forming four stable covalent bonds, essential for complex molecules."},
    {"question": "What gas is produced when magnesium reacts with hydrochloric acid?", "hint": "A highly flammable gas that burns with a characteristic 'pop' sound."}
]

new_physics_hints = [
    {"question": "What is the unit of electric current?", "hint": "The base SI unit for the flow of electric charge per second."},
    {"question": "Which particle is responsible for electricity in wires?", "hint": "The fundamental charge carrier in metallic conductors."},
    {"question": "What is the primary factor that determines the resistance of a wire?", "hint": "Consider the physical dimensions and the nature of the conduction material."},
    {"question": "What is the law that relates voltage, current, and resistance?", "hint": "A fundamental electrical law often expressed as V = I times R."},
    {"question": "What is the frequency of human hearing (range)?", "hint": "The standard range of vibrations per second detectable by the human ear."},
    {"question": "Which colors are the primary colors of light?", "hint": "The three additive colors used in digital displays and television."},
    {"question": "What lens is used to correct farsightedness?", "hint": "A lens that is thicker in the middle than at the edges (converging)."},
    {"question": "What is the energy of position referred to as?", "hint": "The energy stored in an object due to its location in a field, like gravity."},
    {"question": "What describes the rate of work done?", "hint": "The measure of energy transfer per unit of time."},
    {"question": "Which subatomic particle is found in the nucleus and is neutral?", "hint": "The particle that provides stability to the nucleus without adding charge."},
    {"question": "What is the temperature at which water boils (in Celsius)?", "hint": "The standard reference point for water transition at one atmosphere of pressure."},
    {"question": "Which part of the electromagnetic spectrum has the longest wavelength?", "hint": "Low-frequency waves used for long-distance communication and broadcasting."},
    {"question": "What describes a material that allows electricity to flow easily?", "hint": "Consider materials like copper or silver that have high free electron density."},
    {"question": "What is the force that opposes motion between two surfaces?", "hint": "The resistance encountered when one surface slides or rolls over another."},
    {"question": "What happens to the density of water when it turns to ice?", "hint": "Reflect on why ice cubes float on the surface of a glass of water."},
    {"question": "What is the boiling point of water in Kelvin?", "hint": "Add 273.15 to the Celsius boiling point for the absolute scale equivalent."},
    {"question": "What is the first law of thermodynamics?", "hint": "The principle stating that energy in an isolated system is constant."},
    {"question": "What is the term for the bending of light as it enters a new medium?", "hint": "The change in direction of a wave due to a change in its transmission speed."},
    {"question": "What is the value of acceleration due to gravity on Earth (approx)?", "hint": "The rate at which objects accelerate toward the ground in free fall (approx 9.8)."},
    {"question": "What is the fundamental unit of length in the SI system?", "hint": "The base unit of distance, originally defined by a fraction of the Earth's circumference."}
]

with open(kb_path, 'r', encoding='utf-8') as f:
    kb = json.load(f)

# Combine all new hints
all_new_hints = new_bio_hints + new_math_hints + new_chem_hints + new_physics_hints

# Deduplicate (just in case they already exist)
existing_questions = {h['question'] for h in kb}
to_add = [h for h in all_new_hints if h['question'] not in existing_questions]

kb.extend(to_add)

with open(kb_path, 'w', encoding='utf-8') as f:
    json.dump(kb, f, indent=4)

print(f"Added {len(to_add)} new entries to Knowledge Base.")
