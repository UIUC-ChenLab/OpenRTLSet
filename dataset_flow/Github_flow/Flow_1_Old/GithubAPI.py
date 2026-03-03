import json
import requests
import time

def get_res(pages, param, header, search_ur):
    all_results = []
    page = pages
    params = param
    headers = header
    search_url = search_ur
    while True:
        # Update the page parameter for pagination
        params['page'] = page

        # Make the GET request to the GitHub API
        response = requests.get(search_url, params=params, headers=headers)

        # Get rate limit remaining and reset time
        remaining_limit = int(response.headers['X-RateLimit-Remaining'])
        reset_time = int(response.headers['X-RateLimit-Reset'])

        # Print rate limit information
        print(f"Rate limit remaining: {remaining_limit}")
        print(f"Rate limit reset time: {reset_time}")

        # Check if rate limit is reached
        if remaining_limit == 0:
            print("Rate limit reached. Pausing for 1 minute...")
            time.sleep(60)  # Pause for 1 minute (60 seconds)
            continue  # Retry the request after pausing

        # Check if the request was successful
        if response.status_code == 200:
            # Parse the JSON response
            results = response.json()

            # Append the current page of results to the all_results list
            all_results.extend(results['items'])

            # Check if we've reached the last page
            if len(results['items']) < params['per_page']:
                print("Last page reached.")
                page = -1
                break

            print(f"Fetching page {page}")
            # Move to the next page
            page += 1
        elif response.status_code == 422:
            print("Validation failed or endpoint does not support pagination.")
            break
        else:
            print(f"Failed to fetch results: {response.status_code}")
            break

    return all_results, page

def main(date, file):
    # Define your GitHub personal access token
    personal_access_token = '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'

    # Define the GitHub search URL
    search_url = "https://api.github.com/search/repositories"

    # Define the search parameters
    text = 'language:Verilog created:' + date
    params = {
        'q': text,
        'sort': 'updated',
        'order': 'desc',
        'per_page': 100  # Number of results per page (maximum is 100)
    }

    # Define the headers for authentication
    headers = {
        'Authorization': f'token {personal_access_token}'
    }

    all_results = []
    page = 1
    results, page = get_res(page, params, headers, search_url)
    all_results.extend(results)
    # Print the total count of results fetched
    print(f"Total repositories fetched: {len(all_results)}")

        # Save the results to a JSON file
    with open(file, 'w') as json_file:
            json.dump(all_results, json_file, indent=4)

    print("JSON file created successfully!")

