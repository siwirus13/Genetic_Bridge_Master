import json
import sys
import argparse
from pathlib import Path

def convert_json_to_dat(json_file_path, output_file_path=None):
    """
    Convert a bridge deal JSON file to CPLEX .dat format
    
    Args:
        json_file_path (str): Path to the input JSON file
        output_file_path (str, optional): Path for output .dat file. 
                                        If None, uses same name as input with .dat extension
    
    Returns:
        str: Path to the created .dat file
    """
    
    try:
        with open(json_file_path, 'r') as f:
            sample_json = json.load(f)
    except FileNotFoundError:
        print(f"Error: File '{json_file_path}' not found.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in file '{json_file_path}': {e}")
        sys.exit(1)
    
    required_fields = ['hands', 'declarer', 'trump', 'contract_level', 'lead']
    for field in required_fields:
        if field not in sample_json:
            print(f"Error: Missing required field '{field}' in JSON file.")
            sys.exit(1)
    
    if 'card' not in sample_json['lead'] or 'player' not in sample_json['lead']:
        print("Error: 'lead' must contain both 'card' and 'player' fields.")
        sys.exit(1)
    
    expected_players = ['N', 'S', 'E', 'W']
    for player in expected_players:
        if player not in sample_json['hands']:
            print(f"Error: Missing hand for player '{player}'.")
            sys.exit(1)
    
    if output_file_path is None:
        input_path = Path(json_file_path)
        output_file_path = input_path.with_suffix('.dat')
    
    # Convert to CPLEX-friendly .dat format
    dat_lines = [
        f"declarer := {sample_json['declarer']};",
        f"trump := {sample_json['trump']};",
        f"contract_level := {sample_json['contract_level']};",
        f"lead_card := \"{sample_json['lead']['card']}\";",
        f"lead_player := {sample_json['lead']['player']};",
        ""
    ]
    
    for player, cards in sample_json["hands"].items():
        card_list = " ".join(f"\"{c}\"" for c in cards)
        dat_lines.append(f"hand[{player}] := {card_list};")
    
    try:
        with open(output_file_path, "w") as f:
            f.write("\n".join(dat_lines))
        
        print(f"Successfully converted '{json_file_path}' to '{output_file_path}'")
        return str(output_file_path)
        
    except IOError as e:
        print(f"Error writing to file '{output_file_path}': {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="Convert bridge deal JSON files to CPLEX .dat format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  python json_to_dat.py deal1.json
  python json_to_dat.py deal1.json -o output.dat
  python json_to_dat.py /path/to/deal.json --output /path/to/output.dat
        """
    )
    
    parser.add_argument(
        'path_to_json_file',
        help='Path to the input JSON file containing the bridge deal'
    )
    
    parser.add_argument(
        '-o', '--output',
        dest='output_file',
        help='Output file path for the .dat file (optional, defaults to same name as input with .dat extension)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        print(f"Input file: {args.path_to_json_file}")
        if args.output_file:
            print(f"Output file: {args.output_file}")
        else:
            print("Output file: Auto-generated based on input filename")
    
    result_path = convert_json_to_dat(args.path_to_json_file, args.output_file)
    
    if args.verbose:
        print(f"Conversion completed successfully!")
        print(f"Output saved to: {result_path}")

if __name__ == "__main__":
    main()
