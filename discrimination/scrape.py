################################
################################
######    PACKAGES      ########
################################
################################

import discrimination
import time
import pymongo
import datetime

################################
################################
####      SCRAPE        ########
################################
################################

def scrape(
    client = "mongodb://localhost:27017/", 
    database = "database", 
    limit_rows = None, 
    scrape_older_than = -1,
    rescrape_old_posts = False,
    domains = None,
    report_missing_subscraper = True,
    page_number = 1
):

    ''' Checks the Mongo DB client for a url and domain columns in the chosen table. For each row, it checks the domain name and calls 
        the sub-scraper assigned for this domain, if one exists, to scrape the url. When the sub-scraper is done, it records the time of scraping.
           
        Parameters
        ----------
        client, database             : strings.
            Location of the Mongo DB client and database.
        limit_rows                   : int, default empty (scrape all rows).
            scrape only the first n rows. Depends on scrape_older_than and domains parameter values.
        scrape_older_than            : int, default -1 (scrape only un-scraped urls).
            scrape urls that have been scraped more than X days ago (on the scraper level). More info after the parameters.
        rescrape_old_posts            : bool, default False.
            If False, does not scrape items scraped in the past (on the sub-scraper level). More info after the parameters. 
        domain                      : list, default all (scrape all domain names).
            scrape only the provided domain names.
        report_missing_subscraper    : bool, default True.
            Report domain names with no subscraper assigned. Once per domain name.
        page_number                  : int, default 1.
            This is used only for everydaysexism subscraper at the moment. To manually re-initiate scraping from where the blacklisting occured.
            
        Scrape older than & Rescrape old posts
        --------------------------------------
        On the scraper level, "scrape_older_than" controls which urls will be sent to the relevant sub-scrapers for scraping (e.g. Twitter-scraper). On some of the sub-scrapers, "rescrape_old_posts" decides which posts present on the sent urls will be rescraped. To check if a sub-scraper offers this, see its description.'''  
    
    # Setup Mongo DB connection
    collection = "url_list"
    table = discrimination.mongo.collection(client, database, collection)
    
    # Make domains parameter lowercase.
    if domains != None:
        domains = [x.lower() for x in domains]   

    # Get the query needed
    query = discrimination.mongo.query(scrape_older_than, domains)
    
    if limit_rows == None:
        data = table.find( query , {"_id": 0, "url": 1, "domain": 1})
        n_rows = table.count_documents(query)
    else:
        data = table.find( query , {"_id": 0, "url": 1, "domain": 1}).limit(limit_rows)
        n_rows = min(table.count_documents(query), limit_rows)
        
    # Make a list with the url-list data (the query seems to time-out, this should fix this)
    row_list = []
    for i in range(n_rows):
        row_list.append(data.next())
    
    # Needed for the timer
    i = 1

    # List containing non-existing domain scrapers. Needed so that unavailable scrapers are reported only once.
    list_unavailable = []
    
    # For each row that must be scraped collect some data and then check what must be done
    for row in row_list:
        
        # Print a percentage of completion (tqdm library was buggy)
        percentage = round(( i / n_rows)*100, 2)
        print(str(percentage) + "%", end=" ")
        i += 1
        
        domain = row["domain"]
        url = row["url"]
      
        #############################
        ########## TUMBLR ##########
        ###########################
        if domain == 'tumblr':
            
            # Set the scraped flag for the url to not-scraped
            scraped = False
            
            # While the flag remains not-scraped
            while scraped == False:
                # Call the subscraper and check if url was succesfully scraped
                scraped = discrimination.tumblr.scrape(url, client, database, rescrape_old_posts)
                
                # The url is scraped if the API limit hasn't been reached
                if scraped == True:
                    table.update_one(
                          row,
                          { "$set": { "time_scraped" : datetime.datetime.utcnow() } } )

                # If scraped = False, then the API limit has been reached (1000 queries per hour, 5000 per day).
                else:
                    # Sleep for an hour. If the daily limit is reached, then this step will be repeated a few times!
                    time.sleep(3600)
                        
        #############################
        ######### TWITTER ##########
        ############################        
        elif domain == 'twitter':
            discrimination.twitter.decider(url, client, database, rescrape_old_posts)
            table.update_one(
                          row,
                          { "$set": { "time_scraped" : datetime.datetime.utcnow() } } )

        #############################
        ###### EVERYDAYSEXISM ######
        ############################        
        elif domain == 'everydaysexism':
            discrimination.everydaysexism.scrape(url, client, database, rescrape_old_posts, page_number)
            table.update_one(
                          row,
                          { "$set": { "time_scraped" : datetime.datetime.utcnow() } } )
            
        #############################
        ######   DIARY.COM    ######
        ############################        
        elif domain == 'diary':
            discrimination.diary.scrape(url, client, database, rescrape_old_posts)
            table.update_one(
                          row,
                          { "$set": { "time_scraped" : datetime.datetime.utcnow() } } )
            
        #############################
        ######   MY-DIARY.COM  ######
        ############################        
        elif domain == 'my-diary':
            scraped = discrimination.mydiary.scrape(url, client, database)
            if scraped == True:
                table.update_one(
                              row,
                              { "$set": { "time_scraped" : datetime.datetime.utcnow() } } )
                       
        #############################
        ####### ANYTHNG ELSE #######
        ###########################         
        elif report_missing_subscraper == True and domain not in list_unavailable:              
                list_unavailable.append(domain)
                print("A scraper for", domain, "does not exist.")