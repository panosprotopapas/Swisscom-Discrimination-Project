################################
################################
######    PACKAGES      ########
################################
################################

import discrimination
import re
import datetime
import pytumblr
import lxml
import itertools

################################
################################
####       SCRAPE       ########
################################
################################

def scrape(url, client, database, rescrape_old_posts):
    
    '''Tumblr SubScraper, to be used by the scraper function.
    
    Parameters
    ----------
    url                 : string.
        The tumblr url to be scraped (all available pages will be scraped).
    client, database    : strings.
        The location of the Mongo DB client and database.
    rescrape_old_posts  : bool.
        When False it stops scraping at the first item that has been rescraped.'''  
        
    # Set the scraped flag to True. It will be set to False, if API limit is reached.
    scraped = True    
    
    # Switch to the correct mongoDB collection
    table = discrimination.mongo.collection(client, database, collection = "tumblr")

    # Get the tumblr blog name from the url. Split first by "." to keep the part before "tumblr",
    # and then by "//" to ensure we don't end up with "http://blogname" instead of "blogname". 
    split = url.split(".")
    tumblr_position = split.index("tumblr")
    dirty_blogname = split[tumblr_position -1]
    split = dirty_blogname.split("//")
    blogname = split[-1]

    # Handshake with the Tumblr API
    client = pytumblr.TumblrRestClient(
      'NjammIhHH7Rg8sjsZcpEAFeVSTZypVn4u6OrzP0lVJBDrIb5rV',
      'Tj7VYdOXqYcZhfVPdowZeJhfqyFSmRJFxhQjVscaHoaEVo3u9U',
      '9klxKw2pZ4C7YgTu4gmdJG3HATbocHosXtgsf5igQrNrcGPIbG',
      'TFTS7TPU8BDuZL3hYnBTUdELVEdd2WjFvmJwhWlVL6goymlDtj'
    )

    # Set offset to 0 since no posts gathered yet. Set n_posts to NOT 0 for while loop to run at least once.
    offset = 0
    n_posts = -1

    while n_posts != 0:
        
        r = client.posts(blogname, limit = 50, offset = offset)
        
        # Check if the API query limit has been reached (1000 per hour, 5000 per day).
        # If it has, set scraped to False.
        try:
            if r['meta']['msg'] == "Limit Exceeded":
                n_posts = 0
                scraped = False
        
        except:

            # Set n_post to number retrieved and change offset accordingly.
            n_posts = len( r['posts'] )
            offset += n_posts

            # scrape information per post retrieved
            for i in range( n_posts ):

            # Url needs some recoding (e.g. ç appears as %C3%A7).
                url = r['posts'][i]['post_url']
                url = discrimination.misc.url_decode(url)   

            # Time of post is converted to datetime and kept.
                time_of_post = datetime.datetime.fromtimestamp(r['posts'][i]['timestamp'])

            # The whole post is retrieved and cleaned
                post = r['posts'][i]                
                text = discrimination.tumblr.clean_text(post)

            # Only add to Mongo DB if the post-url does not exist already (if it exists, then the post has been scraped before and
            # so have all other posts that come afterwards; therefore stop scraping this Tumblr).
                if (table.count_documents({ "url": str(url).lower() }) != 0) and (rescrape_old_posts == False):
                    n_posts = 0
                    break
                else:
                    table.insert_one({
                        "url"          : str(url).lower(), 
                        "blogname"     : str(blogname).lower(), 
                        "time_of_post" : time_of_post,
                        "post"         : post,
                        "text"         : text
                    })

    return scraped;

################################
################################
####      CLEAN TEXT    ########
################################
################################

def clean_text(post):            
    
    '''Extract the text from a json "tumblr-post" object. Probably it will work in the future with other domains as well.
    
    Parameters
    ----------
    post : string.
        The json tumblr-post object where the text will be extracted from.'''  
    
    # The process completes after two cleaning steps.
    
    ##################
    ## FIRST STEP ##
    #################
    
    # Three lists are needed for the cleaning (extraction) process
    list1, list2, list3 = [], [], []
    
    # To create the 1st list, loop through all the elements of all the items in the json object.
    for i in post.items():
        for k in i:
            # Only keep strings
            if isinstance(k, str) == True:
                # That are at least 2 words long (i.e. include one space)
                if len(k.split(" ")) > 1:
                    # And at least 50% of their characters are not digits (need to get rid of datetime-strings)
                    if sum(c.isdigit() for c in k)/len(k) < 0.5:
                        list1.append(k)
    
    # To create the 2nd list, loop through the 1st list
    for lmnt in list1:
        # "Decode" html into plain text
        new_lmnt = lxml.html.fromstring(lmnt).text_content()
        # Replace new-line and space codes with regural whitespace and delete double whitespaces.
        new_lmnt = new_lmnt.replace("\n", " ")     
        new_lmnt = new_lmnt.replace("\xa0", " ")
        new_lmnt = re.sub('\s+', ' ', new_lmnt)
        list2.append(new_lmnt)
    # Finally delete duplicates by transforming list -> set -> list
    list2 = list(set(list2)) 
    
    # To create the 3rd list, first loop through the 2nd list and concatenate all strings in a single variable.
    test_text = ""
    for lmnt in list2:
        test_text += lmnt
    # Then only keep elements from the 2nd list that don't appear more than once in this single variable.
    # (In order to keep the "Computer: Hello World!" element and delete the "Hello World!" one). Also,
    # delete text that ends with "..." as this implies (as far as I've seen) that this text element is a
    # summary (subset) of another text piece.
    for lmnt in list2:
        if test_text.count(lmnt) == 1 and lmnt[-3:] != "...":
            list3.append(lmnt)
               
    ##################
    ## SECOND STEP ##
    #################
    
    # Needed lists for this second step
    list4 = []
    delete = []
    
    # For each element in list3 (created in step 1) create a set containing all words of 4+ characters.
    # Store these sets in list4.
    for i in list3:
        list4.append( set( re.findall(r'\b\w{4,}\b', i) ) )
    
    # For each unique pair of sets (i, j) in list4:
    #
    # (i) delete i if i = j.
    #
    # (ii) delete i if i < j. Similarly delete j.
    #
    # (iii) Find how similar i is to the intersection of i and j 
    #       (e.g. 50% implies half of the words in i are included in the intersection).
    #       Find how similar is j to the intersection.
    #       If i is more similar than j, and i is more than 80% similar, delete i.
    #       Similarly delete j.
    
    for i,j in itertools.combinations(range(len(list4)), 2):
        if list4[i] == list4[j]:
            delete.append(i)
        elif list4[i].issubset(list4[j]) == True:
            delete.append(i)
        elif list4[j].issubset(list4[i]) == True:
            delete.append(j)
        else:
            x = (len( list4[i].intersection(list4[j]) ) / len( list4[i] ))
            y = (len( list4[i].intersection(list4[j]) ) / len( list4[j] ))
            if (x >= y) and (max(x, y) >= 0.8):
                         delete.append(i)
            elif (x <= y) and (max(x, y) >= 0.8):
                         delete.append(j)

    # Making the list into a set to avoid double entries.
    delete = set(delete)
    for i in delete:
        del list3[i]
        
    # Combining all the sentences in one string. Adding a "\n" between each sentence.
    # Notice that since all pre-existing "\n" instances have been removed, this could
    # prove useful later. Finally, removing the last unneeded "\n".
    text = ""
    for sentence in list3:
        text += sentence + " \n"
    text = text[:-2]
        
    return text;