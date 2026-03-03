## GitHub Crawling and Scraping

This project automates the discovery and collection of Verilog and MyHDL repositories on GitHub across specified date ranges. It consists of Python modules for querying the GitHub API, filtering results, and orchestrating the workflow, along with a configuration file defining date intervals.

### Project Structure

* **`GithubAPI.py`**
  Defines functions to fetch GitHub repositories containing Verilog code files. Query results are saved as JSON files.

* **`GithubAPI_hdl_Scraper.py`**
  Similar to `GithubAPI.py`, but targets repositories that include MyHDL code.

* **`findHDLfiles.py`**
  Reads in JSON outputs and filters repository links that reference MyHDL, storing the filtered URLs.

* **`Utility.py`**
  Provides helper functions for:

  * Generating date ranges.
  * Executing external commands.
  * General-purpose utilities used across scripts.

* **`Date_ranges.json`**
  Specifies a list of date intervals and corresponding JSON filenames for batch queries. Date intervals span 15 days each.

* **`Executable.py`**
  Serves as the entry point to run `GithubAPI.py` (or `GithubAPI_hdl_Scraper.py`) over each date range defined in `Date_ranges.json`, producing the result JSON files.

* **`sampler.py`**  
  Creates a sample of ~11k data points from the full dataset. This was used in our paper for a fair comparison against the MGverilog baseline.

* **`format_final.py`**  
  Builds the public‑release dataset by matching each code snippet against its originating repo and license.  
  * Annotates records with `repo_url` and `lic_name` (a link to the parent GitHub repository and its associated license)
  * Ensures every entry in the final dataset carries open‑source licensing metadata

### Data Collection Details

* **Date Intervals**: From **2010-06-29** to **2024-07-18**, in 15-day increments, to work around GitHub API's 1,000 results limit per query.
* **Total Repositories Fetched**: 82,669 repositories, corresponding to approximately 160,000 code files across all intervals.
* **Limitations**: Each API query only returns the top 1,000 results by default. Splitting the date range ensures comprehensive coverage.



## Notes

Some scripts contain multiple blocks of commented‑out code. These alternatives serve as utility snippets for sanity checks, extra logging, or side‑tasks. Feel free to uncomment and adapt them for your particular needs.


