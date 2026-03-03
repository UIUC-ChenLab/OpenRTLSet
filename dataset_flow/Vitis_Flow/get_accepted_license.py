import json
import os

# Define the license keys to filter by
TARGET_LICENSE_KEYS = [
    "gpl-2.0", "gpl-3.0", "mit", "apache-2.0", "bsd-2-clause", "bsd-3-clause"
]

# Directory where the individual repository JSON files are stored
metadata_dir = "."
accepted_repos_dir = "process_accepted_batch"

# Create the 'accepted_repos' directory if it doesn't exist
os.makedirs(accepted_repos_dir, exist_ok=True)

# List to store repositories that match the target licenses
accepted_repos = []

# Iterate through all JSON files in the metadata directory
for filename in os.listdir(metadata_dir):
    if filename.endswith(".json"):
        file_path = os.path.join(metadata_dir, filename)
        
        with open(file_path, 'r') as f:
            repo_data = json.load(f)
            
            # Check each repository's license key
            for repo in repo_data:
                repo_license_key = repo.get('license', 'Unknown')  # Ensure it's in lowercase for comparison
                
                # If the license key matches, prepend 'accepted' and add to list
                if repo_license_key:
                    repo_license_key = repo_license_key['key']
                    if repo_license_key in TARGET_LICENSE_KEYS:
                        repo_license_key = repo_license_key.lower()
                        accepted_repos.append(repo)

# Save the accepted repositories data to a new JSON file in the 'accepted_repos' folder
accepted_repos_file = os.path.join(accepted_repos_dir, 'accepted_repos.json')
with open(accepted_repos_file, 'w') as f:
    json.dump(accepted_repos, f, indent=4)

print(f"Found {len(accepted_repos)} repositories with specified licenses.")
print(f"Accepted metadata saved to '{accepted_repos_file}'.")