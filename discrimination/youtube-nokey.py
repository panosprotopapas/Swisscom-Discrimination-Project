################################
################################
######    PACKAGES      ########
################################
################################

import re
import os
import json
import pymongo
import discrimination
import googleapiclient.discovery
import pickle

################################
################################
#########  SCRAPER    ##########
################################
################################

def scrape(
    url,
    client = "mongodb://localhost:27017/", 
    database = "database",
    collection = "youtube",
    googleapikey = "",
    token = ""
    ):
    

    
    '''Scrape all comments from the provided youtube url and save them in Mongo DB.
    
    Parameters
        ----------
        url : str.
            The youtube video url.
        client, database, collection : strings.
            Location of the Mongo DB client, database and collection.
        googleapikey: string.
            The key to access google's API.
        token: string
            The next page string provided when scraping youtube. If left empty scraping starts from the beginning of the comments.'''
    
    # Get video id
    video_id = re.findall('v=.{11}', url)[0][-11:]
        
    # Scraped flag and counter
    scraped = False
    counter = 0
    
    # Google's API settings
    api_service_name = "youtube"
    api_version = "v3"
    DEVELOPER_KEY = googleapikey
    
    # Set-up
    youtube = googleapiclient.discovery.build(
        api_service_name, api_version, developerKey = DEVELOPER_KEY)
   
    
    # As long as the last page hasn't been reached (next page token is None in the last page)...
    while token != None:
        
        # Counter + 1
        counter += 1
        
        # Set-up the request and make it
        request = youtube.commentThreads().list(
              part = "snippet,replies",
              maxResults = 100,
              videoId = video_id,
              pageToken = token
              )
        r = request.execute()

        # Save texts here
        texts = []      

        # Append comments (and replies to comments) in the list created
        for item in r["items"]:
            comment = item["snippet"]["topLevelComment"]["snippet"].get("textOriginal")
            texts.append(comment)
            replies = item.get("replies")
            if replies != None :
                for subitem in replies["comments"]:
                    reply = subitem["snippet"].get("textOriginal")
                    texts.append(reply)

        # Get the next page token (next 100 comments)
        token = r.get("nextPageToken")

        # Save the text and video_id to Mongo (if they don't exist)
        table = discrimination.mongo.collection(client, database, collection)
        for text in texts:
            if table.count_documents({
                        "text"     : text, 
                        "video_id" : video_id}) == 0:

                    table.insert_one({
                        "text"     : text, 
                        "video_id" : video_id,
                        "sexist"   : -1
                    })
                    
        # Keep track of the next page token by saving it in Mongo
        table = discrimination.mongo.collection(client, database, "youtubetemp")
        table.insert_one({
                        "token"   : token, 
                        "counter" : counter
        })

    # Change scraped flag
    scraped = True
    return(scraped);  
