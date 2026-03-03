import requests
import zipfile
import io
import os
import shutil

def find_reed_solomon_files(directory, repo):
    print(repo)
    for root, dirs, files in os.walk(directory):
        for file in dirs:
            #print("fjfgj")
            if file.startswith(repo):
                return os.path.join(root, file)
    return None

def extract_verilog_files(source_dir, target_dir, lic):
# Create the target directory if it doesn't exist
     os.makedirs(target_dir, exist_ok=True)
     # Walk through the source directory
     for root, dirs, files in os.walk(source_dir):
         for file in files:
             # Check if the file has a Verilog extension
             if file.endswith(('.v', '.sv', '.vh', '.md','license.txt')):
                 source_file = os.path.join(root, file)
                 target_file = os.path.join(target_dir, file)
                 # Copy the file to the target directory
                 shutil.copy2(source_file, target_file)
                 #print(f"Copied: {source_file} to {target_file}")

def download_github_repo(repo_url, stars, lic, lic_des, des, branch, extract_to='.'):
    # Extract the owner and repo name from the URL
    owner_repo = repo_url.rstrip('/').split('/')[-2:]
    owner, repo = owner_repo[0], owner_repo[1]
    
    # GitHub URL for the zip file of the repository
    zip_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"
    
    # Send a GET request to download the zip file
    response = requests.get(zip_url)
    
    if response.status_code == 200:
        # Open the downloaded zip file as a binary stream
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            # Extract all the contents into the current directory
            z.extractall(extract_to)
        out = find_reed_solomon_files(os.path.abspath(extract_to), repo)
        print(out)
        star = str(stars)
        target = os.path.join(os.path.abspath(extract_to), repo + "_"+str(lic_des) +"_"+star)
        extract_verilog_files(out, target, lic)
        shutil.rmtree(out)
        text_loc= os.path.join(target,"Initial_description.txt" )
        with open(text_loc, 'w') as new_file:
            content = des +'\n'
            new_file.write(content)
        print(f"Repository {repo} downloaded and extracted.")
    else:
        print("Failed to download repository. Please check the URL or repository permissions.")


def run_main(url, stars, lic, des, branch):

    if lic !="None":
        licns=1
    else:
        licns= 0
    download_github_repo(url, stars, licns, lic, des, branch, extract_to='.')


















