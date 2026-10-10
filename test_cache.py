from cache_manager import check_cache, save_to_cache, get_total_cached_count

print("1. Prüfe Datenbank...")
count_start = get_total_cached_count()
print(f"Aktuell gespeicherte Wechselwirkungen in SQLite: {count_start}")

print("\n2. Speichere Test-Eintrag für 'Ramipril' + 'Ibuprofen'...")
save_to_cache("Ramipril", "Ibuprofen", {
    "severity": "Hoch",
    "system": "Niere & Blutdruck",
    "effect": "Akuter Zusammenbruch des Filtrationsdrucks in den Glomeruli.",
    "mechanism": "Ramipril dilatiert das Vas efferens, Ibuprofen verengt das Vas afferens.",
    "source": "SQLite-DB"
})

print("3. Lese Eintrag aus SQLite aus...")
res = check_cache("Ibuprofen", "Ramipril")  # Absichtlich umgekehrte Reihenfolge!
print("Gefundener Datensatz:")
print(res)

count_end = get_total_cached_count()
print(f"\nGesamtzahl nach Test: {count_end}")