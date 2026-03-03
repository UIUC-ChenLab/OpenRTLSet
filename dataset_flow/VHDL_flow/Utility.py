import json
from datetime import datetime, timedelta
import os
import pandas as pd


def date_intevals_json():
    #Start and end dates
    start_date = datetime(2024, 6, 30)
    end_date = datetime(2010, 6, 30)

    #List to hold the date ranges
    date_ranges = []

    #Generate 15-day intervals
    while start_date > end_date:
        end_interval = start_date - timedelta(days=15)
        date_range = f"{end_interval.strftime('%Y-%m-%d')}..{start_date.strftime('%Y-%m-%d')}"
        file_name = f"verilog_repositories_{start_date.strftime('%y%m%d')}.json"
        date_ranges.append({"date_range": date_range, "file_name": file_name})
        start_date = end_interval

    #Save to JSON file
    with open('date_ranges.json', 'w') as json_file:
        json.dump(date_ranges, json_file, indent=4)

    print("JSON file created successfully!")


def create_files_from_json(json_file):
    #Load the JSON data
    with open(json_file, 'r') as file:
        date_ranges = json.load(file)
   #Create a new file for each item in the JSON
    for item in date_ranges:
        date_range = item['date_range']
        file_name = item['file_name']
        
        with open("mne.py", 'a') as new_file:
            content = 'time.sleep(60)'+'\n'+"main("+'"'+date_range+'", "'+file_name+'")' +'\n'
            new_file.write(content)
        
        print(f"Created file: {file_name}")
def create_executable(): 
    #Specify the JSON file
    json_file = 'date_ranges.json'
    #Create files from JSON data
    create_files_from_json(json_file)


def count_word_in_files(folder_path, word):
    count = 0
    for filename in os.listdir(folder_path):
        if filename.startswith("hdlRepos"):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                    content = file.read()
                    count += content.lower().count(word.lower())
    return count

def total_repo_count():
    folder_path = ''
    word = '"license": null'
    total_count = count_word_in_files(folder_path, word)

    print(f"The word '{word}' occurs {total_count} times in files starting with 'hdlRepos'.")




def merge_json_files(folder_path, output_file):
    merged_data = []
    
    for filename in os.listdir(folder_path):
        if filename.startswith("verilog_repositories") and filename.endswith(".json"):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):
                with open(file_path, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    merged_data.append(data)
    
    with open(output_file, 'w', encoding='utf-8') as output:
        json.dump(merged_data, output, ensure_ascii=False, indent=4)

def create_final():
    folder_path = 'C:\\Users\\drpro\\Downloads\\github'
    output_file = 'merged.json'
    merge_json_files(folder_path, output_file)

    print(f"All JSON files have been merged into {output_file}.")



def Get_repo_details_from_json(json_file):
    #Load the JSON data
  with open(json_file, 'r', encoding='utf-8', errors='ignore') as file:
    repo_data = json.load(file)
    name=[]
    urls=[]
    lic_key=[]
    lic_name=[]
    lic_spdx_id=[]
    lic_url=[]
    lic_node_id=[]
    descriptions = []
    #key name spdx_id url node_id
    #Create a new file for each item in the JSON
    licensesList = ["apache-2.0", "bsl-1.0", "bsd-3-clause", "bsd-2-clause", "cc0-1.0", "cc-by-4.0", "cc-by-sa-4.0", "wtfpl", "epl-2.0", "mit", "gpl-3.0", "isc"]
    for item in repo_data:
            license_info = item['license']
            if license_info is not None and license_info['key'] in licensesList and isinstance(license_info, dict):
                url = item['html_url']
                name.append(item['name'])
                urls.append(item['html_url'])
                description = item['description']
                if description is None:
                    description="None"
                else:
                    description=description.replace('"',"'")
                descriptions.append(description)
                stars = item['stargazers_count']
                lic = item['license']
                branch = item['default_branch']
                lics=""
                if license_info is not None and isinstance(license_info, dict):
                    for key, value in license_info.items():
                        if key=="spdx_id":
                            lics+= str(value)+"_"
                    lic_key.append(license_info['key'])
                    lic_name.append(license_info['name'])
                    lic_spdx_id.append(license_info['spdx_id'])
                    lic_url.append(license_info['url'])
                    lic_node_id.append(license_info['node_id'])
                else:
                    lics="None"
                    lic_key.append("none")
                    lic_name.append("none")
                    lic_spdx_id.append("none")
                    lic_url.append("none")
                    lic_node_id.append("none")

                #print(lics)
                lics = lics.replace('"',"").replace(" ","__").replace("�", "")
                with open("run_download.py", 'a', errors='ignore') as new_file:
                    content = ","+"\n"+ "   ("+'"'+url+'", "'+str(stars)+'", "'+lics+'", "'+description+'", "'+branch+'")' 
                    new_file.write(content)        
                #print(f"Created file: {file_name}")
    return name, urls,lic_key, lic_name,lic_spdx_id, lic_url, lic_node_id, descriptions

def Get_repo_details_from_json(file_path):
    with open(file_path, 'r', errors='ignore') as f:
        data_list = json.load(f)

    name, urls, desc = [], [], []
    lic_key, lic_name, lic_spdx_id, lic_url, lic_node_id = [], [], [], [], []

    for data in data_list:
        name.append(data.get('name', ''))
        urls.append(data.get('html_url', ''))
        desc.append(data.get('description', ''))

        license_info = data.get('license') or {}
        lic_key.append(license_info.get('key', ''))
        lic_name.append(license_info.get('name', ''))
        lic_spdx_id.append(license_info.get('spdx_id', ''))
        lic_url.append(license_info.get('url', ''))
        lic_node_id.append(license_info.get('node_id', ''))

    return name, urls, lic_key, lic_name, lic_spdx_id, lic_url, lic_node_id, desc


def create_executable_Repo(): 
    #Specify the JSON file

    # Current folder or change to your actual folder path
    folder_path = r''
    namef, urlsf, descf = [], [], []
    lic_keyf, lic_namef, lic_spdx_idf, lic_urlf, lic_node_idf = [], [], [], [], []

    for filename in os.listdir(folder_path):
        if filename.startswith("vhdl_repositories") and filename.endswith('.json'):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):
                print(f"Processing: {file_path}")
                name, urls, lic_key, lic_name, lic_spdx_id, lic_url, lic_node_id, desc = Get_repo_details_from_json(file_path)
                namef += name
                urlsf += urls
                descf += desc
                lic_keyf += lic_key
                lic_namef += lic_name
                lic_spdx_idf += lic_spdx_id
                lic_urlf += lic_url
                lic_node_idf += lic_node_id

    # Compile into Excel
    data = {
        "Repo_Name": namef,
        "Repo_url": urlsf,
        "lic_keys": lic_keyf,
        "lic_name": lic_namef,
        "lic_spdx_id": lic_spdx_idf,
        "lic_url": lic_urlf,
        "lic_node_id": lic_node_idf,
        "descriptions": descf
    }

    df = pd.DataFrame(data)
    print(f"Total repositories processed: {len(df)}")
    df.to_excel('output_vhdl_license.xlsx', index=False)
       

create_executable_Repo()
# total_repo_count()
#create_final()
#date_intevals_json()
#create_executable()