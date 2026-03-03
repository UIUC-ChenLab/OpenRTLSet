import pandas as pd
import git
import os

def repoDownload():
    directory = ''
    repolist = []
    allowed_licenses = ['mit', 'apache-2.0', 'gpl-3.0', 'bsd-2-clause', 'bsd-3-clause']

    # Read the Excel file
    df = pd.read_excel('output_vhdl_license.xlsx')

    # Filter rows by license key (case-insensitive)
    df = df[df['lic_keys'].str.lower().isin(allowed_licenses)]

    repo_urls = df['Repo_url'] + '.git'
    repo_names = df['Repo_Name']

    for i in range(len(repo_urls)):
        repo_url = repo_urls.iloc[i]
        repo_name = repo_names.iloc[i]

        if repo_url not in repolist:
            repolist.append(repo_url)

            if repo_name not in os.listdir(os.getcwd()):
                try:
                    print(f"Cloning: {repo_name}")
                    git.Repo.clone_from(repo_url, repo_name)
                except Exception as e:
                    print(f"Error cloning {repo_name}: {e}")
                    continue

# Run the function
repoDownload()