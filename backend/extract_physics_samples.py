import pathlib, re, json

# Input file with mixed subjects
INPUT = r"C:/Users/talia/Desktop/study-saga/backend/automated_samples_all_88_audit.md"
# Output file for physics‑only samples
OUTPUT = r"C:/Users/talia/Desktop/study-saga/backend/physics_samples_audit.md"

# Keywords that indicate a physics sample (lowercase)
PHYSICS_KEYWORDS = [
    'gravity', 'kinetic', 'energy', 'electric', 'current', 'wavelength', 'force',
    'friction', 'refraction', 'light', 'density', 'ice', 'boiling', 'water',
    'conservation', 'mass', 'velocity', 'acceleration', 'pressure',
    'thermodynamic', 'thermostat', 'magnet', 'circuit', 'voltage', 'amperage',
    'photon', 'radiation', 'wave', 'frequency', 'speed of light', 'potential',
    'momentum', 'torque', 'buoyancy'
]

text = pathlib.Path(INPUT).read_text(encoding='utf-8')
lines = text.splitlines()

physics_blocks = []
block = []
record = False
for i, line in enumerate(lines):
    if line.startswith('### Sample #'):
        # when a new sample begins, finish previous block
        if block:
            # decide if previous block is physics
            critique = ''
            for blk_line in block:
                if blk_line.lstrip().startswith('- **Critique**:'):
                    critique = blk_line.lower()
                    break
            if any(k in critique for k in PHYSICS_KEYWORDS):
                physics_blocks.extend(block)
                physics_blocks.append('')  # blank line between samples
            block = []
        block.append(line)
        record = True
    elif record:
        block.append(line)
        # stop recording after we hit a blank line separating samples? We'll keep until next sample header.
        # No extra logic needed.
    # else ignore lines before first sample (header etc.)

# handle last block
if block:
    critique = ''
    for blk_line in block:
        if blk_line.lstrip().startswith('- **Critique**:'):
            critique = blk_line.lower()
            break
    if any(k in critique for k in PHYSICS_KEYWORDS):
        physics_blocks.extend(block)
        physics_blocks.append('')

# Write to output
pathlib.Path(OUTPUT).write_text('\n'.join(physics_blocks).strip() + '\n', encoding='utf-8')

# Stats
result = {
    "physics_samples_extracted": len([b for b in physics_blocks if b.startswith('### Sample #')]),
    "total_samples_in_input": len(re.findall(r"^### Sample #", text, flags=re.MULTILINE)),
    "output_path": OUTPUT
}
print(json.dumps(result, indent=2))
