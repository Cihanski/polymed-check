from drug_translator import translate_to_inn

test_inputs = [
    "Aspirin Protect 100mg",
    "Pantozol 40 ratiopharm",
    "Beloc-zok",
    "Marcumar",
    "Ben-u-ron 500",
    "Zocor Hexal",
    "Metoprololsuccinat 95",
    "Lithium"
]

print("--- TEST: Deutsche Namen -> openFDA-Wirkstoffe ---")
for inp in test_inputs:
    inn = translate_to_inn(inp)
    print(f"Eingabe: '{inp}' ──> openFDA-Wirkstoff: '{inn}'")