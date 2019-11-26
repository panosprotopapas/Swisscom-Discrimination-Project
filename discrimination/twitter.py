################################
################################
######    PACKAGES      ########
################################
################################

import discrimination
import bs4
import requests
import re
import pymongo
import datetime
import twitterscraper

################################
################################
####       DECIDER      ########
################################
################################

def decider(url, client, database, rescrape_old_posts):

    '''Checks each twitter url, decides if it is: (i) a Twitter search url, (ii) a Twitter acoount's page, (iii) a single tweet url, or
    (iv) something else - in which case a message of "unknown url" is printed.
    
    Parameters
    ----------
    url              : string.
        The url to check.
    client, database : strings.
        The location of the Mongo DB client and database.
    rescrape_it      : bool.
       Scrape tweets that have been scraped before. When False, start_date and end_date might be changed to avoid rescrapes.
        '''    

    #############################
    # CASE 1 : TWITTER SEARCH URL
    #############################

    # Check whether the Twitter-url is a search result page.
    check = re.findall("search\?.+\&src=typd", url)

    # If it is, find the query that produced it and use the twitter_search_scraper function to get these results.
    if len(check) >0:

        # Get the query and the language choice.
        lang = ""
        tempstr = check[0][7:-9]
        tempsplit = tempstr.split("&")   
        for item in tempsplit:
            if (len(item) == 4) and (item[:2] == "l="):
                lang = item[2:]
            elif (len(item) > 2) and (item[:2] == "q="):
                query_dirty = item[2:]

        # Get the begin and end search date strings, if these exist.
        start = re.findall("since:\d{4}-\d{2}-\d{2}", query_dirty)
        if start:
            start = start[0]
        end = re.findall("until:\d{4}-\d{2}-\d{2}", query_dirty)
        if end:
            end = end[0]

        # Separate the query from the begin\end search dates.
        if start and end:
            delete = len(start) + len(end) + 2
            query_clean = query_dirty[:-delete]
        elif not start and not end:
            query_clean = query_dirty
        else:
            delete = len(start) + len(end) + 1
            query_clean = query_dirty[:-delete]

        # Transform dates to datetime dates.
        if start:
            start = datetime.datetime.strptime(start[6:], '%Y-%m-%d').date()
        else:
            start = datetime.date(2006, 3, 21)
        if end:
            end = datetime.datetime.strptime(end[6:], '%Y-%m-%d').date()
        else:
            end = datetime.datetime.utcnow().date() + datetime.timedelta(days = 1)

        # Call the twitter scraper function and scrape the url
        discrimination.twitter.search_scrape(
            client,
            database,
            language = lang, 
            start_date = start, 
            end_date = end, 
            query = query_clean
        )

    ###############################
    # CASE 2 : TWITTER ACCOUNT PAGE
    ###############################

    # If not a search page, then either a twitter account page (twitter.com/account) or a unique tweet page (twitter.com/account/status/tweet_id)
    else: 
        tempsplit = url.split("/")
        # Since a url must contain http://xyz, tempsplit has at least 2 items.
        # If this url is a twitter account page, scrape all tweets of the user (no retweets) using the scraper
        if "twitter.com" in tempsplit[-2]:
            account = tempsplit[-1]
            discrimination.twitter.search_scrape(
                client,
                database,
                from_=[account]
            )

    #############################
    # CASE 3 : SINGLE TWEET PAGE
    #############################

        # If this is a status, the scraper doesn't allow for single tweet scrapes. Use beautiful soup directly.
        elif tempsplit[-2] == "status":

            # Get the account
            account = tempsplit[-3]

            # Make the soup
            page = requests.get(url)
            soup = bs4.BeautifulSoup(page.content, "lxml")

            # Get tweet's text
            text = soup.find("div", attrs = {"class": "js-tweet-text-container"}).find("p").text

            # Separate the pic's url, if one exists and delete the url from the text
            (text, pic_url) = discrimination.twitter.photo_url(tweet=text)
            
            # Call the scraper
            discrimination.twitter.search_scrape(
                client,
                database,
                phrase = text,
                from_ = [account],
                limit = 1,
                poolsize = 1
            )
            
        # Make sure that all twitter urls are scraped in one of the three ways
        else:
            print("The Twitter url ", url, "doesn't fall in any of the 3 Twitter url categories")

################################
################################
####      PHOTO_URL     ########
################################
################################

def photo_url(tweet):

    '''Searches the text provided for a Twitter pic url (of the form pic.twitter.com\1234567890). The url is deleted from the text. Text and url are returned.
    
    Parameters
    ----------
    tweet : string.
        The tweet's scraped text to search for a pic's url.'''    
        
    pic_url = ""
    match = re.search('pic\.twitter\.com/\w{10}', tweet)
    if match:
        if match.end(0) ==  len(tweet):
            pic_url = match.group(0)
            delete = match.start(0) - match.end(0)
            tweet = tweet[: delete]
    
    return (tweet, pic_url);

################################
################################
####    SEARCH_SCRAPE    ########
################################
################################
def search_scrape( 
    client           = "mongodb://localhost:27017/", 
    database         = "database", 
    language         = "",
    all_words        = [],
    any_words        = [],
    none_words       = [],
    phrase           = "",
    tags             = [],
    tag_operator     = "and",
    from_            = [],
    to               = [],
    to_operator      = "or",
    mention          = [],
    mention_operator = "or",
    place            = "",
    place_rad_km     = 10,
    start_date       = datetime.date(2006, 3, 21),
    end_date         = datetime.datetime.utcnow().date() + datetime.timedelta(days = 1),
    limit            = None,
    query            = None,
    poolsize         = 20
):

    '''Searches Twitter, scraps all resulting tweets (NO RETWEETS), and saves per tweet text, url, time, and user in Mongo DB.
    
    Parameters
    ----------
    client, database : strings.
        Location of the Mongo DB client and database.
    language         : "en" (english) | "fr" (french) | "de" (german) | "it" (italian) | "el" (greek), optional.
        The language that tweets must be written in. More choices are available (check Twitter's advanced search). 
    all_words        : list, optional.
        Must all be present.
    any_words        : list, optional.
        Some must be present.
    none_words       : list, optional.
        None must be present.
    phrase           : string, optional.
        The exact phrase must be present.
    tags             : list, optional.
        These hashtags must be present. Do not include the hash "#" symbol!
    tag_operator     : "and" | "or", default "and".
        Whether some or all of the hashtags must be present.
    from_            : list, optional.
        The twitter account(s) where the tweets originated from. Do not include the at "@" symbol!
    to               : list, optional.
        The twitter account(s) where the tweets are directed to. Do not include the at "@" symbol!
    to_operator      : "and" | "or", default "or".
        Whether the tweets are directed at some or all of these twitter accounts.
    mention          : list, optional.
        The twitter account(s) mentioned in the tweet. Do not include the at "@" symbol!
    mention_operator : "and" | "or", default "or".
        Whether some or all of these twitter accounts are mentioned.
    place            : string, optional.
        Search for tweets originating from this place.
    place_rad_km     : integer, default 10.
        The radius around the selected place. Measured in kilometers.
    start_date       : datetime date, default 21-3-2006 (first tweet).
        The oldest date to include in the search.
    end_date         : datetime date, default is tomorrow.
        The most recent date "minus 1" to include in the search (e.g. to capture today use tomorrow).
    limit            : integer, default is None.
        Limit the number of results (not in chronological order). If no limit is set (by default) all results are returned.
    query            : str, default is None.
        If a string is passed, then this query is used when searching. Therefore, only the client, datebase, start_date, end_date, limit, and rescrape variables are taken into account.
    poolsize         : int, default is 20.
        Number of parallel search processes.'''      
    
    # Check if a query is passed, if not then construct the query.
    if query == None:        
        
        # Set all_words   
        if len(all_words) == 0:
            all_words = ""
        else:
            text = ""
            for word in all_words:
                text += word + " "
            text = text[:-1]
            all_words = text

        # Set any_words    
        if len(any_words) == 0:
            any_words = ""
        else:
            text = ""
            for word in any_words:
                text += word + " OR "
            text = text[:-4]
            any_words = text

        # Set none_words    
        if len(none_words) == 0:
            none_words = ""
        else:
            text = ""
            for word in none_words:
                text += "-" + word + " "
            text = text[:-1]
            none_words = text

        # Set phrase
        if len(phrase) != 0:
            phrase = "\"" + phrase + "\""

        # Set hashtags
        if len(tags) == 0:
            tags = ""
        else:
            text = ""
            if tag_operator == "and":
                for tag in tags:
                    text += "#" + tag + " AND "
                text = text[:-5]
            elif tag_operator == "or":
                for tag in tags:
                    text += "#" + tag + " OR "
                text = text[:-4]
            tags = text

        # Set from_
        if len(from_) == 0:
            from_ = ""
        else:
            text = ""
            for account in from_:
                text += "from:" + account + " OR "
            text = text[:-4]
            from_ = text

        # Set to
        if len(to) == 0:
            to = ""
        else:
            text = ""
            if to_operator == "and":
                for account in to:
                    text += "to:" + account + " AND "
                text = text[:-5]
            elif to_operator == "or":
                for account in to:
                    text += "to:" + account + " OR "
                text = text[:-4]
            to = text

        # Set mention
        if len(mention) == 0:
            mention = ""
        else:
            text = ""
            if mention_operator == "and":
                for account in mention:
                    text += "@" + account + " AND "
                text = text[:-5]
            elif mention_operator == "or":
                for account in mention:
                    text += "@" + account + " OR "
                text = text[:-4]
            mention = text

        # Set place
        if len(place) == 0:
            place = ""
        else:
            place = "near:\"" + place + "\" within:" + str(place_rad_km) + "km"   

        # Construct query
        query = all_words + " " + phrase + " " + any_words + " " + none_words + " " + tags + " " + from_ + " " + to + " " + mention + " " + place

    # Feed results to twitterscraper
    tweets = twitterscraper.query_tweets(query, limit, start_date, end_date, poolsize, language)
    
    # Save the tweets in Mongo DB
    table = discrimination.mongo.collection(client, database, collection = "twitter")
    
    # Get information. Store it in Mongo DB
    for tweet in tweets:
        text = tweet.text
        url = tweet.tweet_url
        time = tweet.timestamp
        user = tweet.username
        
        # Check if a pic url exists in the text. 
        (text, pic_url) = discrimination.twitter.photo_url(tweet = text)
        
        # Check if this tweet is not already stored.
        if (table.count_documents({ 
            "$and":
            [{ "text": text},
            { "account": user }]
        }) == 0):
            table.insert_one({
                        "text"          : text, 
                        "tweet_url"     : url, 
                        "time_of_tweet" : time,
                        "account"       : user,
                        "pic_url"       : pic_url
                    })
            
    # Save the query and date of scrape in Mongo DB to avoid tweet rescrapes in the future
    table = discrimination.mongo.collection(client, database, collection = "twitter_queries_scraped")
    time_scraped = datetime.datetime.utcnow()
    # If the query has been used in the past, then only update the date scraped.
    if (table.count_documents({ "query": query }) != 0):
        table.update_one( 
            { "query": query },  
            { "$set": 
             { "time_scraped" : time_scraped } 
            })
    else:
        table.insert_one({
                        "query"      : query, 
                        "time_scraped" : time_scraped
                    })