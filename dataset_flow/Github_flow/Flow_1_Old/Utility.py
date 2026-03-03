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
        if filename.startswith("verilog_repositories"):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                    content = file.read()
                    count += content.lower().count(word.lower())
    return count

def total_repo_count():
    folder_path = 'C:\\Users\\drpro\\Downloads\\Verilog_Dataset\\Github_scraping\\Scraped_data'
    word = '"license"'+": null"
    total_count = count_word_in_files(folder_path, word)

    print(f"The word '{word}' occurs {total_count} times in files starting with 'verilog_repositories'.")




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
    #key name spdx_id url node_id
    #Create a new file for each item in the JSON
    for item in repo_data:
        url = item['html_url']
        name.append(item['name'])
        urls.append(item['html_url'])
        description = item['description']
        if description is None:
            description="None"
        else:
            description=description.replace('"',"'")
        stars = item['stargazers_count']
        lic = item['license']
        branch = item['default_branch']
        lics=""
        license_info = item['license']
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
    return name, urls,lic_key, lic_name,lic_spdx_id, lic_url, lic_node_id






def create_executable_Repo(): 
    #Specify the JSON file
    folder_path = 'C:\\Users\\drpro\\Downloads\\Verilog_Dataset\\Github_scraping\\Scraped_data'
    namef=[]
    urlsf=[]
    lic_keyf=[]
    lic_namef=[]
    lic_spdx_idf=[]
    lic_urlf=[]
    lic_node_idf=[]
    with open("run_download.py", 'a', errors='ignore') as new_file:
            content = "from download_File import run_main"+"\n"+"tasks = ["+"\n"
            new_file.write(content)        
    for filename in os.listdir(folder_path):
        if filename.startswith("verilog_repositories"):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):
                print(file_path)
                name, urls,lic_key, lic_name,lic_spdx_id, lic_url, lic_node_id = Get_repo_details_from_json(file_path)
                namef += name
                urlsf+=urls
                lic_keyf +=lic_key
                lic_namef+=lic_name
                lic_spdx_idf+=lic_spdx_id
                lic_urlf+=lic_url
                lic_node_idf+=lic_node_id
    with open("run_download.py", 'a', errors='ignore') as new_file:
            content = "\n"+"]"+"\n"+"for task in tasks:"+"\n"+"     try:"+"\n"+"                run_main(*task)"+"\n"+"     except Exception as e:"+"\n"+'              with open("errors.txt", "a") as textfile:'+"\n"+"                       textfile.write(*task)"
            new_file.write(content)    
    data= {"Repo_Name":namef,"Repo_url":urlsf,"lic_keys":lic_keyf, "lic_name":lic_namef, "lic_spdx_id":lic_spdx_idf, "lic_url":lic_urlf, "lic_node_id":lic_node_idf}
    df = pd.DataFrame(data)
    df.to_excel('output.xlsx', index=False)
       



create_executable_Repo()
#total_repo_count()
#create_final()
#date_intevals_json()
#create_executable()