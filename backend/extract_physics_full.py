import os, re, shutil

PROJECT_ROOT = r"c:\\Users\\talia\\Desktop\\study-saga"
backend_dir = os.path.join(PROJECT_ROOT, "backend")

mixed_md = os.path.join(backend_dir, "automated_samples_all_88.md")
output_md = os.path.join(backend_dir, "physics_samples_md_extracted.md")

# Simple heuristic: include samples where any hint or question mentions physics keywords
physics_keywords = [
    "gravity", "force", "energy", "kinetic", "potential", "electric", "current",
    "magnetic", "wave", "particle", "mass", "acceleration", "velocity",
    "momentum", "friction", "pressure", "temperature", "heat", "light", "photon",
    "radiation", "refraction", "reflection", "lens", "mirror", "circuit", "voltage",
    "resistance", "ohm", "charge", "field", "quantum", "relativity", "orbit",
    "planet", "star", "galaxy", "cosmology", "atom", "molecule", "nucleus",
    "proton", "neutron", "electron", "photon", "spectra", "spectrometer", "laser",
    "wave", "oscillation", "frequency", "period", "amplitude", "wavelength"
]

pattern = re.compile(r"### Sample #(\d+)")

with open(mixed_md, "r", encoding="utf-8") as f:
    lines = f.readlines()

samples = []
current = []
include = False
for line in lines:
    if line.startswith("### Sample #"):
        if current:
            if include:
                samples.extend(current)
            current = []
            include = False
        current.append(line)
    else:
        current.append(line)
        # check for any physics keyword in line (case-insensitive)
        lower = line.lower()
        if any(kw in lower for kw in physics_keywords):
            include = True
# add last
if current and include:
    samples.extend(current)

with open(output_md, "w", encoding="utf-8") as f:
    f.writelines(samples)

print(f"Extracted {len([s for s in samples if s.startswith('### Sample')])} samples to {output_md}")
