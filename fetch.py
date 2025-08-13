import glob
import zipfile
import os
import time
import random
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By


class fetch_UNLOCODE:
    def __init__(self, config) -> None:
        self.config = config
        self.download_dir = self.config["download_path"]
        self.url = self.config["URL"]
        self.output = self.config["output_path"]

    def download_folder(self):
        options = webdriver.ChromeOptions()
        prefs = {
            "download.default_directory": self.download_dir,  # Change to your desired folder
            "download.prompt_for_download": False,
            "directory_upgrade": True
        }
        options.add_experimental_option("prefs", prefs)

        driver = webdriver.Chrome(options=options)

        try:
            driver.get(self.url)
            time.sleep(30)

            download_button = driver.find_element(By.LINK_TEXT, "csv")
            download_button.click()

            time.sleep(5)
        except Exception as e:
            print(f"An error occurred: {str(e)}")
        finally:
            driver.quit()

    def extract_folder(self):
        os.makedirs(self.output, exist_ok=True)

        zip_path = glob.glob(os.path.join(self.download_dir, "*.zip"))[0]
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(self.output)

        print(f"Files extracted to: {self.output}")

class fetch_Shipnext:
    def __init__(self, config):
        self.config = config
        self.base_url = self.config["URL"]
        self.api_url = self.config["API"]
        self.headers = self.config["headers"]
        self.params = self.config["params"]
        self.url_name = []
        self.data = []

    def _init_driver(self):
        driver = webdriver.Chrome()
        return driver
    
    def fetch_cookies(self):
        driver = self._init_driver()
        driver.get(self.base_url)
        driver.implicitly_wait(5)

        cookies = driver.get_cookies()
        cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
        cookie_string = "; ".join([f"{k}={v}" for k, v in cookie_dict.items()])

        self.headers['Referer'] = self.base_url
        self.headers['Cookie'] = cookie_string

        time.sleep(3)
        driver.quit()

    def fetch_list_port(self):
        page = 1
        while page<3:
            self.params["page"] = page
            response = requests.get(self.api_url, headers=self.headers, params=self.params)

            if response.status_code == 429:
                print("Rate limited. Waiting...")
                time.sleep(2 ** page)
                continue

            if response.status_code != 200:
                print(f"Error: {response.status_code}")
                break

            json_data = response.json()
            results = json_data.get("data", [])

            if not results:
                print("No more data.")
                break
            
            for item in results:
                self.url_name.append(item['sefName'])

            print(f"Scraped page {page}, total items: {len(self.url_name)}")  

            next_page = json_data.get("next")
            if not next_page:
                break

            page = next_page
            time.sleep(random.uniform(8, 12))

        return self.url_name

    def extract_data(self):
        for name in self.url_name:
            final_url = os.path.join(self.api_url, "public", name)
            print(final_url)

            response = requests.get(final_url, headers=self.headers)
            json_data = response.json()
            results = json_data.get("data", [])
            self.data.append(results)

            print(f"total items: {len(self.data)}, {self.data[-1]['seo']}")

            time.sleep(random.uniform(8, 12))

        return self.data

