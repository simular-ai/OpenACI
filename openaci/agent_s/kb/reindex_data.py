import os
import json

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Construct the full path to the JSON file
file_path = os.path.join(script_dir, "perplexica_rag_knowledge.json")

# Load the JSON file
with open(file_path, "r") as file:
    data = json.load(file)

# Reindex the JSON
reindexed_data = {v["instruction"]: v["search_result"] for k, v in data.items()}

# Save the reindexed JSON to a new file
reindexed_file_path = os.path.join(script_dir, "instruction_indexed_perplexica_rag_knowledge.json")
with open(reindexed_file_path, "w") as reindexed_file:
    json.dump(reindexed_data, reindexed_file, indent=4)

print(f"Reindexed JSON saved to {reindexed_file_path}")
