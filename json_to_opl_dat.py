import json
import sys
import os


def generate_opl_dat(data: dict) -> str:
    output = []

    output.append(f'declarer = "{data["declarer"]}";')
    output.append(f'trump = "{data["trump"]}";')
    output.append(f'contract_level = {data["contract_level"]};')
    output.append(f'lead_card = "{data["lead"]["card"]}";')
    output.append(f'lead_player = "{data["lead"]["player"]}";')
    output.append("")

    output.append("hand = [")
    for player in ["N", "S", "E", "W"]:
        cards = data["hands"][player]
        cards_str = "{" + ", ".join(f'"{card}"' for card in cards) + "}"
        output.append(f'  {cards_str}, // {player}')
    output.append("];")

    return "\n".join(output)


def main():
    if len(sys.argv) < 2:
        print("Użycie: python json_to_opl_dat.py path/to/input.json [output.dat]")
        sys.exit(1)

    json_path = sys.argv[1]

    if not os.path.exists(json_path):
        print(f"Błąd: Plik '{json_path}' nie istnieje.")
        sys.exit(1)

    try:
        with open(json_path, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Błąd: Nieprawidłowy format JSON: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Błąd podczas odczytu pliku: {e}")
        sys.exit(1)

    try:
        opl_dat = generate_opl_dat(data)
    except KeyError as e:
        print(f"Błąd: Brakuje wymaganego klucza w JSON: {e}")
        sys.exit(1)

    output_path = sys.argv[2] if len(sys.argv) > 2 else "output.dat"

    try:
        with open(output_path, "w") as f:
            f.write(opl_dat)
        print(f"Plik .dat zapisany jako: {output_path}")
    except Exception as e:
        print(f"Błąd podczas zapisu pliku: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

# Usage example:
# python json_to_opl_dat.py deal.json deal.dat
