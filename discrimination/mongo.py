################################
################################
######    PACKAGES      ########
################################
################################

import discrimination
import pymongo
import datetime
import pandas
import pickle
import os

################################
################################
####       QUERY        ########
################################
################################

def query(
    scrape_older_than = -1,
    domains = None
):
    
    ''' Creates the query for the scrape function.
           
        Parameters
        ----------
        scrape_older_than : int, default -1 (scrape only un-scraped urls).
            scrape urls that have been scraped more than X days ago.
        domains          : list, default all (scrape all domain names).
            scrape only the provided domain names.'''  
    
    if domains == None and scrape_older_than == -1:
        query = {
            "time_scraped": ""
        }
    elif domains != None and scrape_older_than == -1:
        query = {
            "domain": {"$in": domains},
            "time_scraped": ""
        }  
    elif domains == None:
        query = {
            "$or": 
            [{  "time_scraped" : {"$lt": datetime.datetime.utcnow() - datetime.timedelta(days = scrape_older_than)} },
             { "time_scraped" : "" } ]
             }
    elif domains != None:
        query = {
            "$or":
            [{"domain": {"$in": domains} , 
            "time_scraped": {"$lt": datetime.datetime.utcnow() - datetime.timedelta(days = scrape_older_than)} },
             {"domain": {"$in": domains} ,
             "time_scraped" : "" }]
        }   
                   
    return query;

################################
################################
####    COLLECTION      ########
################################
################################

def collection( 
    client            = "mongodb://localhost:27017/",
    database          = "database",
    collection        = "collection"
):

    '''Creates\switches to the selected MongoDB client\database\collection.'''
    
    db = pymongo.MongoClient(client)[database]
    table = db[collection]
    return table;
    
################################
################################
####   LIST COLLECTION  ########
################################
################################

def list_collections(
    client   = "mongodb://localhost:27017/", 
    database = "database"
    ):
    
    '''Returns a list with the collections in the provided MongoDB client and database.'''
    
    db = pymongo.MongoClient(client)[database]   
    return db.list_collection_names();

################################
################################
### PRINT X FIRST DOCUMENTS ####
################################
################################

def print_docs(
    collection,
    number   = 1,
    column  = None,
    client  = "mongodb://localhost:27017/", 
    database = "database"
    ):
    
    '''Prints the first document(s) from the provided collection.
    
    Parameters
        ----------
        collection       : str.
            The collection where the documents lie.
        number           : int, default 1.
            The number of documents to be returned.
        column.          : str, default None.
            If a column name is passed, only the values of this column are returned.
        client, database : strings.
            The location of the Mongo DB client and database.'''  
    
    table = discrimination.mongo.collection(client, database, collection)
    for x in table.find():
        if number > 0:
            if column == None:
                print(x)
            else:
                print(x[column])
            number -= 1
        else:
            break
            
################################
################################
#####  REMOVE DUPLICATES  ######
################################
################################

def remove_duplicates(
    collection,
    columns,
    keep_save = True,
    overwrite_save = False,
    client  = "mongodb://localhost:27017/", 
    database = "database"
    ):
    
    '''Removes duplicate entries from the selected Mongo DB collection. A pickle savefile with a dataframe copy of this collection is created during the process (named after the collection). 
    
    Parameters
        ----------
        collection       : str.
            The collection to check for duplicates.
        columns          : list.
            The columns provided must include hashable items (no dictionaries). Two documents are duplicates if their values in all the selected columns are identical. If non-hashable columns are entered, a savefile will be created but the original collection will not be deleted.
        keep_save        : bool, default True.
            If False, the savefile is deleted at the end of the process.
        overwrite_save.  : bool, default False.
            Unless set to True, process is aborted if the savefile already exists.
        client, database : strings.
            The location of the Mongo DB client and database.'''  
    
    savefilename = str(collection)+".p"
    if (overwrite_save == False) & (os.path.exists(savefilename) == True):
        raise SystemExit("Continuing will overwrite the savefile '"+savefilename+"'. Either set overwrite to True or manually delete this file.")
    
    table = discrimination.mongo.collection(client, database, collection)
    doc_temp = table.find_one()
    keys = list(doc_temp.keys())
    keys.remove("_id")
    list_temp = []

    # Create a dataframe with all documents in the collection and save it.
    for doc in table.find():
        dict_temp = {}
        for key in keys:
            dict_temp[key] = doc[key]
        list_temp.append(dict_temp)    
    df_temp = pandas.DataFrame(list_temp)
    pickle.dump(df_temp, open( savefilename, "wb" ) ) 
    
    # Remove the duplicates from the dataframe, keep a note of how many rows where dropped, and empty the Mongo collection.
    df_temp2 = df_temp.drop_duplicates(subset = columns).reset_index(drop=True)
    rows_dropped = df_temp.shape[0] - df_temp2.shape[0]
    table.drop()
   
    # Repopulate the collection
    for row in df_temp2.index:
        dict_temp = {}
        for col in df_temp2.columns:
            dict_temp[col] = df_temp2[col][row]
        table.insert_one(dict_temp)
        
    # Delete the save
    if keep_save == False:
        os.remove(savefilename)

    # Report number of rows deleted.
    print(str(rows_dropped)+" duplicate rows were found and deleted.")
    

################################
################################
### ONE COLLECTION TO JSON  ####
################################
################################

def save_to_json_one(
    
    collection,
    filename,
    client = "localhost:27017",
    database = "database"
    ):
    
    '''Saves the selected collection, using the selected name, in the same folder with the code running the command.
    
    Parameters
        ----------
        collection       : str.
            The collection name.
        filename         : str.
            The filename to be created.
        client, database : str.
            The location of the Mongo DB client and database.'''  
    
    host = " -h " + client
    db = " -d " + database
    col = " -c " + collection
    file = " -o " + filename
    
    # Terminal command
    command = "mongoexport" + host + db + col + file + " --pretty"
    
    # Run it in Python
    os.system(command)
    
################################
################################
### ALL COLLECTIONS TO JSON  ###
################################
################################

def save_to_json_all(
    
    client = "localhost:27017",
    database = "database"
    ):
    
    '''Saves all collections of the selected database to JSON, using the same collection names ".json". In the same folder with the code running the command.
    
    Parameters
        ----------
        client, database : str.
            The location of the Mongo DB client and database.'''
    
    collections = discrimination.mongo.list_collections()
    host = " -h " + client
    db = " -d " + database
    
    for collection in collections:    
        col = " -c " + collection
        file = " -o " + collection + ".json"
        # Terminal command
        command = "mongoexport" + host + db + col + file + " --pretty"
        # Run it in Python
        os.system(command)
        
################################
################################
###   SAVE COLLECTION(S)     ###
################################
################################

def save(
    
    collection = None,
    foldername = "/Users/panos/Desktop",
    client = "localhost:27017",
    database = "database"
    ):
    
    '''Saves collection(s), in the selected folder. Make sure you have write access to this folder.
    
    Parameters
        ----------
        collection       : None or str.
            If None (default), all collections are dumped. If str, it must equal the name of the collection to be dumped.
        foldername       : str.
            The foldername in which the folder "database" will be created. Any non-existing folder will be created in the process.
        client, database : str.
            The location of the Mongo DB client and database.'''  
    
    host = " -h " + client
    db = " -d " + database
    folder = " -o /" + foldername
    
    if collection == None:
        col = ""
    else:
        col = " -c " + collection
    
    # Terminal command
    command = "mongodump" + host + db + col + folder + " --gzip"
    
    # Run it in Python
    os.system(command)
    
################################
################################
###   LOAD COLLECTION(S)     ###
################################
################################

def load(
    drop = False,
    foldername = "/Users/panos/Desktop/database",
    client = "localhost:27017",
    database = "database"    
    ):
    
    '''Loads all collection(s) from the selected folder into Mongo, saving them with the same name. 
    
    ATTENTION: THIS WILL DROP ANY COLLECTION WITH THE SAME NAME WHEN LOADING!!!
    
    Parameters
        ----------
        drop             : bool, default False.
            Whether to drop collections with the same name, if found, when loading a collection.
        foldername       : str.
            The folder containing the collection's backup (.bson file(s)).
        client, database : str.
            The location of the Mongo DB client and database.'''  
    
    if drop != True:
        print("Drop must be set to True. ATTENTION: THIS WILL DROP ANY COLLECTION(S) WITH THE SAME NAME WHEN LOADING!!!")
    else:
        host = " -h " + client
        db = " -d " + database
        if drop == True:
            drop = ""
        else:
            drop = " --drop"

        # Terminal command
        command = "mongorestore" + host + db + drop + " --gzip " + foldername

        # Run it in Python
        os.system(command)