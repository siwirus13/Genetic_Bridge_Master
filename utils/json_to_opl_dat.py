import json
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


def main(json_path: str, output_path: str = None) -> str:
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"File '{json_path}' does not exist.")

    with open(json_path, "r") as f:
        data = json.load(f)

    opl_dat = generate_opl_dat(data)

    if output_path:
        with open(output_path, "w") as f:
            f.write(opl_dat)
    return opl_dat


# Example usage inside code:
# dat_content = main("deal.json")
# print(dat_content)
# Or to save to file:
# main("deal.json", "deal.dat")
main('deals/4H.json', 'deals/4H.dat')