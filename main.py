import os
import json
import logging
import sys
import requests
import requests_cache
import random
import time
import datetime
from multiprocessing import Pool
from urllib3.util.retry import Retry
from pyquery import PyQuery as pq
from dotenv import load_dotenv
load_dotenv()

requests_cache.install_cache('phone_cached', expire_after=900)

concurrent = int(os.getenv("CONCURRENT_PROCESS"))
companyIndex = int(os.getenv("COMPANY_INDEX"))
proxyUrl = os.getenv("PROXY_URL")

logging.basicConfig(
    filename='./logs/log.txt',
    format='%(asctime)s - %(levelname)s: %(message)s',
    level=logging.INFO
)

def generateSessionList(companyList):
    companySessionList = []
    for i in range(len(companyList)):
        company = companyList[i]
        domain = company['domains'][companyIndex]
        get_url = domain+company['get_url']
        string_requestverificationtoken = company['string_requestverificationtoken']

        retries = Retry(
            total=5,
            backoff_factor=0.1,
            status_forcelist=[500, 502, 503, 504],
            method_whitelist=frozenset(['GET', 'POST'])
        )
        s = requests.Session()
        s.proxies = proxyUrl
        s.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.97 Safari/537.36',
        })

        try:
            cookieResponse = s.get(get_url)
            s.cookies = cookieResponse.cookies
            d = pq(cookieResponse.text)
            token = d('#hdnAntiForgeryTokens').val()

            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Host': domain.replace('https://', '', 1).replace('http://', '', 1),
                'Origin': domain,
                'Referer': get_url,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.97 Safari/537.36',
                'X-Requested-With': 'XMLHttpRequest',
            }
            headers[string_requestverificationtoken] = token
            s.headers.update(headers)
            companySessionList.append(s)
            pass
        except Exception as e:
            logging.error("An error occurred on get Cookies: " + domain + " - " + str(e))
            companySessionList.append(False)
            pass
    return companySessionList

def requestCheck(phoneNumber, company, data, s):
    try:
        with requests_cache.disabled():
            domain = company['domains'][companyIndex]
            post_url = domain+company['post_url']

            response = s.post(post_url, data=data)
            try:
                responseJson = json.loads(response.text)
                
                if responseJson['Code'] != 0:
                    f = open("./results/results.csv", "a")
                    f.write(str(phoneNumber)+"\n")
                    f.close()
                    return True
                else:
                    return False
                pass
            except Exception as e:
                logging.error("An error occurred with json parse: " + phoneNumber + " - " + domain + " - " + str(e))
    except Exception as e:
        logging.error("An error occurred: " + phoneNumber + " - " + str(e))
        return False
        pass

def refreshCompanySession():
    global companySessionList
    global companySessionListGenerateTime
    companySessionList = generateSessionList(companyList)
    companySessionListGenerateTime = datetime.datetime.now()

def checkPhone(phoneNumber):
    data = {'country':phoneNumber[:2], 'number':phoneNumber[2:]}
    
    if (datetime.datetime.now() - companySessionListGenerateTime) > datetime.timedelta(minutes=15):
        refreshCompanySession()
    
    for i in range(len(companyList)):
        company = companyList[i]

        if companySessionList[i] != False:
            result = requestCheck(phoneNumber, company, data, companySessionList[i])
            if result:
                break

def initializer():
    global companyList
    global companySessionList
    global companySessionListGenerateTime
    with open('companies.json') as json_file:
        companyList = json.load(json_file)
        companySessionList = generateSessionList(companyList)
        companySessionListGenerateTime = datetime.datetime.now()

def main(p):
    try:
        for subdir, dirs, files in os.walk("./raw_data"):
            for file in files:
                filepath = subdir + os.sep + file
                if filepath.endswith(".csv"):
                    logging.info("Start check file " + file)
                    with open(filepath) as filedata:
                        i = 0
                        scrape_list = list()
                        phoneList = filedata.read().split(',')
                        p.map(checkPhone, phoneList)
                        p.terminate()
                        p.join()
                        logging.info("End check file " + file)
            logging.info("End check!")
    except KeyboardInterrupt:
        sys.exit(1)


if __name__ == '__main__':
    p = Pool(concurrent, initializer, ())
    main(p)