#main app

import db
import openai

def get_and_print_user_input():
    # get user input
    user_input = input("Enter a number: ")
    # print user input
    print("You entered: " + user_input)

def call_chat_gpt_api():
    # call chatGPT API
    print("Calling chatGPT API")

def create_chat_gpt_request(params):
    response = openai.Completion.create(
        model="gpt-3.5-turbo-instruct",
        prompt="Write a tagline for an ice cream shop."
    )
    #print out the response, but formatted nicely.
    print(response)

#create_chat_gpt_request(5)

db_manager = db.DatabaseManager()
print("updating document")
temp = db_manager.update_document({"name": "John"}, {"$set": {"name": "John"}}, True)
print("updated result")
print(temp.raw_result)
print("finding document")
found_doc = db_manager.find_document({"name": "John"})
print(found_doc)


# Path: app.py