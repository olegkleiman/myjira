import datetime
import os
from atlassian import Jira

from my_jira import MyJira
from my_confluence import MyConfluence

def run():

    my_api_token = os.getenv("JIRA_API_TOKEN")
    my_email = os.getenv("E_MAIL")
    jira_base_url = os.getenv("JIRA_BASE_URL")
    my_squad_name = os.getenv("SQUAD_NAME")

    myJira = MyJira(my_api_token, my_email, jira_base_url, my_squad_name)
    fromDate = datetime.datetime.now() - datetime.timedelta(days=7)
    epics = myJira.epics(limit=50, fromDate=fromDate)

    # # gpp_project = jira.projects(name = 'GPP2'
    # my_projects = jira.projects()
    # print(f"Projects: {my_projects}")

    confluence_base_url = os.getenv("CONFLUENCE_BASE_URL")
    myConfluence = MyConfluence(my_api_token, my_email, confluence_base_url)
    # page_hierarchy = myConfluence.page_hierarchy
    grandparent_title = 'Execution Reviews'
    grandparent_page = myConfluence.get_page_by_title(space='EEE', title=grandparent_title)
    if not grandparent_page:
        print(f"Grandparent page '{grandparent_title}' not found.")
        raise ValueError("Grandparent page not found.")     
    
    grandparent_page_id = grandparent_page['id']
    print(f"Grandparent page '{grandparent_title}' found with ID: {grandparent_page_id}")

    new_page = myConfluence.create_page(space='EEE', title='delete_me', 
                            body='<p>Content is storage format</p>', 
                            parent_id=grandparent_page_id, representation='storage')
    print(f"New page created with ID: {new_page['id']} and title: {new_page['title']}")

if __name__ == "__main__":
    run()