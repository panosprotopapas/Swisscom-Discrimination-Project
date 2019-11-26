################################
################################
######    PACKAGES      ########
################################
################################

import discrimination
import requests
import bs4
import time
import re
import pymongo

################################
################################
########  GET SEEDS ############
################################
################################

def get_seeds(timeout = 3):
    
    '''Gather all usernames from www.diary.com (main page).
    
     Parameters
    ----------
    timeout : int, default 3.
        The number of seconds for request to stop waiting for a response (assuming a part-response has already been sent).''' 

    # Make the soup
#     page = discrimination.misc.tor_request("http://www.diary.com")
    page = requests.get("http://www.diary.com", timeout = timeout)
    soup = bs4.BeautifulSoup(page.content, features="lxml")
    
    # Get the posts
    posts = soup.find_all(name="a")
    usernames = set()
    
    # For each post, check if it is indeed a post. If yes, get the username
    for post in posts:
        href = post.get("href")
        if (href[0] == "/")\
        and (re.search('\w', href[-1]) != None)\
        and (len(href.split("/")) == 2):
            user = href.split("#")[0]
            usernames.add(user)
            
    return usernames
                         
################################
################################
####   GET FOLLOWERS   #########
################################
################################
def get_followers(
    seeds,
    userlist = None,
    timeout = 3,
    group = None,
    client='mongodb://localhost:27017/',
    database='database',
    collection='url_list'
):
    
    '''Find all followers from a list of seed users. Returns a set of all users (seeds + new) and a set of new seeds (new users not included in seeds)
    
    Parameters
    ----------
    seeds                        : set.
        Set of usernames to check for followers.
    userlist                     : set, default is the empty set.
        Set of usernames that have already been found. If left empty then userlist is set equal to seeds.
    group                        : [Followers, Following], default is None.
        If set to Followers, only followers of each page are collected, if set to Following, only the pages the current page is following are collected. Both groups are collected by default.
    timeout                      : int, default 3.
        The number of seconds for request to stop waiting for a response (assuming a part-response has already been sent).
    client, database, collection : Mongo DB details to store the urls''' 
    
    # Fix userlist if None
    if userlist == None:
        userlist = seeds.copy()
    old_userlist = userlist.copy()
    
    # Counter cause this can take a while
    counter = 0
    denominator = len(seeds)
    for seed in seeds:   
        counter += 1
        print(str(round((counter/denominator)*100,1)) + "%", end=" ")     
        
        # Construct the url and make the soup
        url = "http://www.diary.com" + seed
        try:
#             page = discrimination.misc.tor_request(url)
            page = requests.get(url, timeout = timeout)
            soup = bs4.BeautifulSoup(page.content, features="lxml")

            # Some userpages are private and redirect to the main page. Don't scrap.
            if len(soup.select("a.sign-up-cta")) > 0 :
                pass
            # Otherwise get all usernames followed by the userpage.
            else:
                if group != "Followers":
                    try:                  
                        templist = soup.find("div", attrs={"id" : "following"})\
                        .find_all("div", attrs={"style": "float:left; width: 50%;"})
                        for item in templist:
                            if "Following" in item.text:
                                outwards = item
                        followers = outwards.find_all("p")
                        for follower in followers:
                            username = follower.find("a").get("href")
                            if len(username)>1:
                                userlist.add(username)
                                # Add user-page to Mongo
                                temp_url = "http://www.diary.com" + username
                                discrimination.store.url_list([temp_url], client, database, collection)

                    except:
                        pass
                if group != "Following":
                    try:                  
                        templist = soup.find("div", attrs={"id" : "following"})\
                        .find_all("div", attrs={"style": "float:left; width: 50%;"})
                        for item in templist:
                            if "Followers" in item.text:
                                inwards = item
                        followers = inwards.find_all("p")
                        for follower in followers:
                            username = follower.find("a").get("href")
                            if len(username)>1:
                                userlist.add(username)
                                # Add user-page to Mongo
                                temp_url = "http://www.diary.com" + username
                                discrimination.store.url_list([temp_url], client, database, collection)

                    except:
                        pass
        except:
            print("Page retrieval timeout", end=" ")
            pass
    
    seeds = userlist - old_userlist
    
    return seeds, userlist;

################################
################################
###  GET USERS AND STORE   ####
################################
################################
def get_users_and_store(
    no_of_passes,
    timeout = 3,
    group = None,
    client='mongodb://localhost:27017/',
    database='database',
    collection='url_list'
):
    
    '''Gather users from diary.com. The first pass gathers all users from the websites main page. Using these, it finds all their followers (2nd pass). Repeat as necessary to find followers of followers (3rd pass and beyond). Returns a set of all users (userlist) and a set of users whose followers haven't been scraped (seeds). 
     
    Parameters
    ----------
    no_of_passes                 : int.
        The number of levels of depth to look for "followers of followers". Suggested is 2 or 3.
    timeout                      : int, default 3.
        The number of seconds for request to stop waiting for a response (assuming a part-response has already been sent).
    group                        : [Followers, Following], default is None.
        If set to Followers, only followers of each page are collected, if set to Following, only the pages the current page is following are collected. Both groups are collected by default.
    client, database, collection : Mongo DB details to store the urls''' 
    
    # Need no_of_passes to be larger than 0
    if no_of_passes < 1:
        sys.exit("no_of_passes must be a positive integer!")
    else:
        
        # Keep a counter to perform the number of passes selected
        count = 0
        print("The first pass should be very fast!", end="\n\n")
        
        # For the first pass get the usernames of the main page.
        seeds = discrimination.diary.get_seeds(timeout = timeout)
        userlist = seeds.copy()
        print(str(len(seeds)) + " new users found.", end="\n\n")
        count += 1
        
        # Add all user-pages to Mongo
        temp_list = []
        for seed in seeds:
            seed_url = "http://www.diary.com" + seed
            temp_list.append(seed_url)
        discrimination.store.url_list(temp_list, client, database, collection)
        
        # Perform the remaining number of passes required by updating the seeds and userlist after every pass.
        while no_of_passes != count:
            print("Pass number " + str(count+1) + " might take time, but hey, there's a cool percentage-counter!", end="\n\n")
            (seeds, userlist) = discrimination.diary.get_followers(seeds, userlist, timeout, group, client, database, collection)
            print("\n\n" + str(len(seeds)) + " new users found.", end="\n\n")
            count += 1

################################
################################
######### GET POSTS   ##########
################################
################################
def get_posts_and_store(
    url,
    client='mongodb://localhost:27017/',
    database='database',
    collection='diary.com'
):
    
    '''Get all posts from the provided url and store them on Mongo DB.
    
    Parameters
    ----------
    url                          : A diary.com user-page.
    client, database, collection : Mongo DB details to store the urls'''
    
    # Get url and "dirty" posts
    driver = discrimination.misc.scroll_down(url)
    posts = driver.find_elements(selenium.webdriver.common.by.By.CSS_SELECTOR, "p.cta")
    
    # Clean
    text_posts = []
    for post in posts:
        text_post = post.text.replace("\n", " ")
        if (text_post[-3:] == "...") and (len(text_post) == 500):
            try:
                post.click()
                time.sleep(0.5)
                for item in driver.find_elements(selenium.webdriver.common.by.By.XPATH, "//div[@class='modal-content']"):
                    if len(item.text) >= 500:
                        temp_post = item
                        text_post = temp_post.find_element(selenium.webdriver.common.by.By.XPATH, "//li[@class='line']").text.replace("\n", " ")
                        text_posts.append(text_post)            
                buttons = driver.find_elements(selenium.webdriver.common.by.By.XPATH, "//span[@class='button icon close']")
                for button in buttons:
                    try:
                        button.click()
                    except:
                        pass
                time.sleep(0.5)
            except:
                pass
        else:
            if len(text_post)>80:
                text_posts.append(text_post)
                
    driver.quit()

    
    # Store the text of each post and the name of the user posting it in Mongo.
    table = discrimination.mongo.collection(client, database, collection)
    user = url.split("/")[-1]
    for item in text_posts:
        # Check if this post is not already stored.
        if (table.count_documents({ 
            "$and":
            [{ "text": item},
            { "account": user }]
        }) == 0):
            table.insert_one({
                        "text"    : item, 
                        "account" : user 
                    })
            

################################
################################
#########   SCRAPER   ##########
################################
################################
def scrape(
    url,
    client='mongodb://localhost:27017/',
    database='database',
    rescrape_old_posts = False
): 
    
    '''Scraper for diary.com (userpage) urls.
    
    Parameters
    ----------
    url                : A diary.com user-page.
    client, database   : Mongo DB details to store the urls
    rescrape_old_posts : Whether to re-scrape the page for posts, if it has been already scraped.'''
    
    
    # Name of collection
    collection='diary.com'
    
    # Check if url is a userpage and retrieve username
    if url[-1]=="/":
        url = url[:-1]
    if len(url.split("/")) == 4:
        userpage = True   
        username = url.split("/")[-1]
    else:
        userpage = False
        
    if userpage:
         # Check if this userpage has been scraped before
        table = discrimination.mongo.collection(client, database, collection)        
        if table.count_documents({ "account": username}) != 0:
            scraped = True

        # Scrape!
        if (rescrape_old_posts == False) & scraped:
            pass
        else:
            discrimination.diary.get_posts_and_store(url, client, database, collection)            