import os
import json
import logging
import sys
import requests
import requests_cache
from pyquery import PyQuery as pq
import concurrent.futures
from memory_profiler import memory_usage

requests_cache.install_cache('phone_cached', expire_after=900)
proxies = dict(
    http='socks4://jimmyjo:bbe8a0-ba74c9-402fe3-e5b6d4-05df22@megaproxy.rotating.proxyrack.net:222',
    https='socks4://jimmyjo:bbe8a0-ba74c9-402fe3-e5b6d4-05df22@megaproxy.rotating.proxyrack.net:222'
)
concurrentNumber = 100
executor = concurrent.futures.ThreadPoolExecutor(max_workers=concurrentNumber)


logging.basicConfig(
    filename='./logs/log.txt',
    format='%(asctime)s - %(levelname)s: %(message)s',
    level=logging.INFO
)

companyIndex = 0

def requestCheck(phoneNumber, company, data):
    try:
        domain = company['domains'][companyIndex]
        get_url = domain+company['get_url']
        string_requestverificationtoken = company['string_requestverificationtoken']
        post_url = domain+company['post_url']

        s = requests.Session()

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.97 Safari/537.36',
        }
        s.headers.update(headers)

        s.proxies = proxies

        cookieResponse = s.get(get_url)
        d = pq(cookieResponse.text)
        token = d('#hdnAntiForgeryTokens').val()
        s.cookies = cookieResponse.cookies

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

        with requests_cache.disabled():
            response = s.post(post_url, data=data)
            print(response.text)
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
        s.close()
        pass
    except Exception as e:
        logging.error("An error occurred with get cookies: " + phoneNumber + " - " + str(e))
        return False
        pass

def checkPhone(phoneNumber):
    data = {'country':phoneNumber[:2], 'number':phoneNumber[2:]}
    
    for i in range(len(companyList)):
        company = companyList[i]
        result = requestCheck(phoneNumber, company, data)
        if result:
            break
    return True

def initializer():
    global companyList
    with open('companies.json') as json_file:
        companyList = json.load(json_file)

def main():
    try:
        for subdir, dirs, files in os.walk("./raw_data"):
            for file in files:
                filepath = subdir + os.sep + file
                if filepath.endswith(".csv"):
                    logging.info("Start check file " + file)
                    with open(filepath) as filedata:
                        requests_cache.clear()
                        initializer()
                        scrape_list = list()
                        phoneList = filedata.read().split(',')
                        
                        for future in concurrent.futures.wait([executor.submit(checkPhone, phoneNumber) for phoneNumber in phoneList[:1000]]).done:
                            try:
                                data = future.result()
                            except Exception as exc:
                                print('%r generated an exception: %s' % (url, exc))
                        logging.info("End check file " + file)
    except KeyboardInterrupt:
        sys.exit(1)


if __name__ == '__main__':
    main()
    # mem_usage = memory_usage(main)
    # print('Maximum memory usage: %s' % max(mem_usage))
    # print("End check")
    logging.info("End check!")