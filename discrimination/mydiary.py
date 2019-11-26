################################
################################
######    PACKAGES      ########
################################
################################

import discrimination
import requests
import bs4
import time
import pymongo
import itertools

################################
################################
#SEEDS FROM MAIN&POPULAR PAGES##
################################
################################

def get_seed_urls():
    
    '''Gather page seeds from "main" and "popular" my-diary.org page. All urls are returned in a list to be fed to the gather posts function.''' 

    # Urls to be scraped for seeds
    urls = ["https://www.my-diary.org/surf/", "https://www.my-diary.org/surf/top"]
    seeds = []
    
    for url in urls:
        page = requests.get(url)
        soup = bs4.BeautifulSoup(page.content, "lxml")
        selection = soup.find_all("a", attrs={"rel": "ugc"})
        for item in selection:
            specific_url = item.get("href")
            # The urls we need all end in blue. Perhaps the administrator really likes a certain Picasso's period.
            if specific_url[-4:] == "blue":
                delete = specific_url.split("/")[-1]
                url = "https://www.my-diary.org" + specific_url[:-len(delete)]
                seeds.append(url)
    
    # Before returning, remove double-entries.
    return list(set(seeds));
                         
################################
################################
##  GET POST URLS AND STORE   ##
################################
################################
def get_post_urls_and_store(
    seeds,
    client='mongodb://localhost:27017/',
    database='database',
    collection='url_list'
):
    
    '''Find the urls of all posts in the seed-userpages. Store each url in Mongo DB.
    
    Parameters
    ----------
    seeds                        : list.
        List of all seed urls returned by get_seed_urls function.
    client, database, collection : Mongo DB details to store the urls''' 
    
    counter = 1
    
    # For each seed, find all post-urls
    for seed in seeds:
        print(str(counter) + "/" + str(len(seeds)), sep=" ")
        counter += 1
        page = requests.get(seed, timeout = 10)
        
        # Make sure page has been returned correctly
        for _ in itertools.repeat(None, 6):
            if page.status_code not in [200, 410]:
                print("Sleeping for 10 seconds, " + url + " not accessible (code "+ str(page.status_code) + ").")
                time.sleep(10)
                page = requests.get(seed)
        
        # Make the soup
        soup = bs4.BeautifulSoup(page.content, "lxml")
        selection = soup.select_one("div#entrylist-inner.box_in").select_one("ul#slide").select("a")
        post_urls =[]
        
        # Find the correct url and save it in a list
        for item in selection:
            if item.get("href")[-4:] == "blue":
                delete = item.get("href").split("/")[-1]
                post_url = "https://www.my-diary.org" + item.get("href")[:-len(delete)]
                post_urls.append(post_url)
            
        # Once all post-urls of a userpage are gathered, save them in Mongo DB
        discrimination.store.url_list(post_urls, client, database, collection)

################################
################################
###   GET POSTS AND STORE   ####
################################
################################
def scrape(
    url,
    client='mongodb://localhost:27017/',
    database='database'
): 
    
    '''Scraper for my-diary.org post-urls.
    
    Parameters
    ----------
    url              : A my-diary.org post-url.
    client, database : Mongo DB details to store the urls'''
    
    # Mongo collection to store posts in
    collection = "my-diary.org"
    scraped = False   
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.89 Safari/537.36"}
#     headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.1 Safari/605.1.15"}
#     headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 13_1_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.1 Mobile/15E148 Safari/604.1"}
#     headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML like Gecko) Chrome/51.0.2704.79 Safari/537.36 Edge/14.14931"}
    # Get page and if return code is not 200 keep trying for sixty seconds.
    try:
        page = discrimination.misc.tor_request(url, timeout = 5, headers = headers)
#         page = requests.get(url, timeout = 5, headers = headers)
        for _ in itertools.repeat(None, 6):
            if page.status_code == 429:
                print("Sleeping for 10 seconds, " + url + " not accessible (code "+ str(page.status_code) + ").")
                time.sleep(10)
                page = discrimination.misc.tor_request(url, timeout = 5, headers=headers)
#                 page = requests.get(url, timeout = 5, headers = headers)

        # If page has been correctly retrieved
        if page.status_code == 200:    
            try:
                soup = bs4.BeautifulSoup(page.content, "lxml")

                # Get post
                html_post = soup.select("div#blue")[0].select("div#entry div.col-md-12 p")
                post = ""
                for item in html_post:
                    post += item.get_text() + " \n "

                # Get account (diaryname)
                account = soup.select_one("h1.heading.text-center").get_text()

                # Store info on Mongo DB
                table = discrimination.mongo.collection(client, database, collection)
                # Check if this post is not already stored.
                if (table.count_documents({ 
                    "$and":
                    [{ "text": post},
                    { "account": account }]
                    }) == 0):
                    table.insert_one({
                            "text"    : post, 
                            "account" : account 
                            })
                scraped = True

            except:
                pass

        # If page is private\removed
        if page.status_code == 410:
            scraped = True
    
    except:
        pass
        
    return scraped;