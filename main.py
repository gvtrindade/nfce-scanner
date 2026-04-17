import sys

from camou import scrape_content
from nfce_parser import parser

def main():
    url = sys.argv[1]

    content = scrape_content(url)

    if (not content):
        print("Error, could not retreive content") 
        return
    
    parser(content)
    

if __name__ == "__main__":
    main()