################################
################################
######    PACKAGES      ########
################################
################################

import discrimination
import random
import re
import wikipedia
import requests

################################
################################
########   SEARCH   ############
################################
################################

def search(
    query, 
    results = 500, 
    language = "en", 
    client = 'mongodb://localhost:27017/',
    database ='database'
):
    
    '''Search Wikipedia using the provided query and return (up to) 500 results (page titles). Also saves the titles in Mongo.
    
     Parameters
    ----------
    query              : str.
    results            : int, default = 500. The number of results to return (500 is max).
    language           : str, default = "en", English. The language in which to search in.
    client, database   : Mongo DB details to store the urls'''

    
    wikipedia.set_lang(language)
    titles = wikipedia.search(query, results)
    
    # Save titles in Mongo
    table = discrimination.mongo.collection(client, database, collection = "wiki")
    for title in titles:
        if table.count_documents({"title" : title}) == 0:
                table.insert_one({"title" : title})
    
    print(len(titles), "page-titles collected.")

################################
################################
######  RELATED TITLES  ########
################################
################################

def related(
    titles, 
    language = "en",
    client = 'mongodb://localhost:27017/',
    database ='database'
):
    
    """Search all provided Wikipedia page-titles, for the "See also" section's titles. All page-titles must be from the same Wiki country website.
    Return all new titles found (i.e. not included in the input), saves them to Mongo, and labels the inputted ones as "related_checked".
    
    Parameters
    ----------
    titles : list containing the page-titles.
    language : str, default = "en", English. The language in which the pages are written in.
    client, database   : Mongo DB details to store the urls"""
    
    related_titles = []
    timer = 1
        
    for title in titles:
       
        # Construct url
        a = "https://"
        b = language
        c = ".wikipedia.org/w/api.php?action=parse&prop=sections&page="
        d = title
        e = "&format=json"
        url = a + b + c + d + e
        
        # Get json file
        r = requests.get(url)
        j = r.json()
        
        # Find the index number, if it exists
        index = -1
        try:
            for sec in j["parse"]["sections"]:
                if sec["line"] == "See also":
                    index = sec["index"]
        except:
            pass
        
        # If index exists, get all related page-titles
        if index != -1:
            # Construct url
            c = ".wikipedia.org/w/api.php?action=parse&prop=links&page="
            e = "&section="
            f = index
            g = "&format=json"
            url = a + b + c + d + e + f + g
            
            # Get json file
            r = requests.get(url)
            j = r.json()
            
            # Get related titles
            try:
                for link in j["parse"]["links"]:
                    if link["ns"] == 0:
                        related_titles.append(link["*"])
            except:
                pass
                    
        # Counter
        print(timer, "pages checked for related pages.", end="\r", flush= True)
        timer += 1
    
    # Make a list of the new page-titles collected
    new_titles = list(
        set(related_titles) - set(titles)
    )
    
    # Save new titles in Mongo
    table = discrimination.mongo.collection(client, database, collection = "wiki")
    for title in new_titles:
        if table.count_documents({"title" : title}) == 0:
                table.insert_one({"title" : title})
    # Label inputted titles that related have been scraped
    for title in titles:
        if table.count_documents({"title" : title}) == 0:
            table.insert_one({"title" : title, "related_scraped": True})
        else: 
            table.update_one({"title" : title}, {'$set': {"related_scraped": True}} )
    
    print("\n\n", len(new_titles), "new page-titles collected.")
    
################################
################################
#### GET PAGE-TITLE'S INFO #####
################################
################################

def get_info(
    titles, 
    language = "en",
    client = 'mongodb://localhost:27017/',
    database ='database'
):
    
    """Scrape the provided Wikipedia page-titles, for information (url and text). Saves these in Mongo, and label the page as scraped for info.
    If the page is not an article (but "resolves" a page-title ambiguity), then label the page-title as "ambiguous".
    
    Parameters
    ----------
    titles : list containing the page-titles.
    language : str, default = "en", English. The language in which the pages are written in.
    client, database   : Mongo DB details to store the urls"""
    
    
    # Mongo table to save the information gathered.
    table = discrimination.mongo.collection(client, database, collection = "wiki")
    # Language
    wikipedia.set_lang(language)
    # Timer
    timer = 1
    
    for title in titles:
        try:
            # Request page and find url and text
            page = wikipedia.page(title)
            url = page.url
            text = page.content
            # Clean text
            rgx1 = re.findall('== See also[\s\S]+', text)
            rgx2 = re.findall('== References[\s\S]+', text)
            rgx3 = re.findall('== External links[\s\S]+', text)
            if len(rgx1) != 0:
                text = text.replace(rgx1[0], "")
            elif len(rgx2) != 0:
                text = text.replace(rgx2[0], "")
            elif len(rgx3) != 0:
                text = text.replace(rgx3[0], "")
            headers = re.findall('==.+==', text)
            for header in headers:
                text = text.replace(header, "")
            # Store information in Mongo
            if table.count_documents({"title" : title, "scraped" : True}) == 0: 
                table.update_one({"title" : title}, {'$set': 
                                                     {"scraped": True, 
                                                      "url" : url,
                                                      "text" : text}})
        
        # If page is ambiguous, make a note in Mongo
        except Exception:
            if table.count_documents({"title" : title, "scraped" : True}) == 0: 
                table.update_one({"title" : title}, {'$set': 
                                                     {"scraped": True, 
                                                      "ambiguous" : True}}) 
            
        # Counter
        print(timer, "titles scraped.", end="\r", flush=True)
        timer += 1