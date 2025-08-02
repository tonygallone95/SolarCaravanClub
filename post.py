#!/usr/bin/env python3
"""
WordPress Post Publisher with HTML Support

Quick script to publish HTML files as WordPress posts
Supports Gutenberg blocks (hopefully lol)

TODO: Add support for custom fields maybe?
"""

import os
import json
import requests
from base64 import b64encode
from datetime import datetime
from bs4 import BeautifulSoup
import re
import sys

# had to install beautifulsoup4 for this btw
# pip install beautifulsoup4 requests


class WordPressPublisher:
    def __init__(self):
        # grab env vars
        self.site = os.environ.get('WP_SITE')
        self.user = os.environ.get('WP_USER') 
        self.app_pass = os.environ.get('WP_APP_PASS')  # this is the application password, not your actual password!!
        
        # default to draft cause who wants to accidentally publish garbage
        self.publish_status = os.environ.get('PUBLISH_STATUS', 'draft')
        
        self.html_file = os.environ.get('HTML_FILE', '')
        self.post_title = os.environ.get('POST_TITLE', '')
        
        # check if we have what we need
        if not self.site or not self.user or not self.app_pass:
            raise ValueError("Yo, you need to set WP_SITE, WP_USER, and WP_APP_PASS environment variables!")
        
        # auth stuff - wordpress uses basic auth with app passwords
        creds = f"{self.user}:{self.app_pass}"
        token = b64encode(creds.encode()).decode('ascii')
        self.headers = {
            'Authorization': f'Basic {token}',
            'Content-Type': 'application/json'
        }
        
        # make sure we don't have trailing slash
        self.api_url = self.site.rstrip('/') + '/wp-json/wp/v2'
        
        # debug print
        # print(f"API URL: {self.api_url}")
        
    def read_html_file(self, filename):
        """Read HTML file and return content"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
                return content
        except FileNotFoundError:
            print(f"❌ Can't find file: {filename}")
            return None
        except Exception as e:
            print(f"❌ Something went wrong reading file: {e}")
            return None
    
    def html_to_gutenberg_blocks(self, html_content):
        """
        Convert HTML to Gutenberg blocks
        This is where the magic happens (or breaks)
        """
        
        # parse the html
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # try to find a title if we don't have one
        if not self.post_title:
            # first check for title tag
            title_tag = soup.find('title')
            if title_tag:
                self.post_title = title_tag.text.strip()
            else:
                # ok maybe there's an h1?
                h1 = soup.find('h1')
                if h1:
                    self.post_title = h1.text.strip()
                else:
                    # fine, just use timestamp
                    self.post_title = f"Post from {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        # get the body or just use everything
        body = soup.find('body')
        if body:
            content = str(body)
        else:
            # no body tag? weird but ok
            content = html_content
        
        content = self.clean_html(content)
        
        blocks = []
        
        # convert to soup again for processing
        soup_content = BeautifulSoup(content, 'html.parser')
        
        # go through each element and convert to blocks
        for elem in soup_content.children:
            if isinstance(elem, str):
                # just text, needs to be in a paragraph
                text = elem.strip()
                if text:  # only if there's actual content
                    blocks.append(f'<!-- wp:paragraph -->\n<p>{text}</p>\n<!-- /wp:paragraph -->')
                    
            elif elem.name:
                # handle different html elements
                tag = elem.name
                
                if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    # heading
                    level = tag[1]  # get the number
                    blocks.append(f'<!-- wp:heading {{"level":{level}}} -->\n{str(elem)}\n<!-- /wp:heading -->')
                    
                elif tag == 'p':
                    blocks.append(f'<!-- wp:paragraph -->\n{str(elem)}\n<!-- /wp:paragraph -->')
                    
                elif tag == 'img':
                    # wrap images in figure
                    blocks.append(f'<!-- wp:image -->\n<figure class="wp-block-image">{str(elem)}</figure>\n<!-- /wp:image -->')
                    
                elif tag == 'ul' or tag == 'ol':
                    blocks.append(f'<!-- wp:list -->\n{str(elem)}\n<!-- /wp:list -->')
                    
                elif tag == 'blockquote':
                    blocks.append(f'<!-- wp:quote -->\n{str(elem)}\n<!-- /wp:quote -->')
                    
                elif tag == 'pre':
                    # code blocks, nice
                    blocks.append(f'<!-- wp:code -->\n{str(elem)}\n<!-- /wp:code -->')
                    
                elif tag == 'table':
                    # tables need figure wrapper too
                    blocks.append(f'<!-- wp:table -->\n<figure class="wp-block-table">{str(elem)}</figure>\n<!-- /wp:table -->')
                    
                else:
                    # everything else just shove in html block
                    # print(f"Unknown tag: {tag}, using HTML block")
                    blocks.append(f'<!-- wp:html -->\n{str(elem)}\n<!-- /wp:html -->')
        
        # fallback - if we got nothing, just wrap it all
        if len(blocks) == 0:
            blocks.append(f'<!-- wp:html -->\n{content}\n<!-- /wp:html -->')
        
        # join with double newlines (gutenberg likes space)
        return '\n\n'.join(blocks)
    
    def clean_html(self, html):
        """Clean up the HTML a bit"""
        
        # strip body tags
        html = re.sub(r'</?body[^>]*>', '', html, flags=re.IGNORECASE)
        
        # definitely remove scripts
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.IGNORECASE | re.DOTALL)
        
        # remove styles? nah, might want to keep those
        # html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.IGNORECASE | re.DOTALL)
        
        # TODO: maybe strip out onclick handlers and stuff?
        
        return html.strip()
    
    def create_post_from_html(self, html_file):
        """Main method to create post from HTML"""
        
        # read the file
        html_content = self.read_html_file(html_file)
        if not html_content:
            return None
            
        # convert to blocks
        print("Converting to Gutenberg blocks...")
        block_content = self.html_to_gutenberg_blocks(html_content)
        
        # build post data
        post_data = {
            'title': self.post_title,
            'content': block_content,
            'status': self.publish_status,
            'format': 'standard',  # could also be aside, gallery, etc
            'comment_status': 'open',
            'ping_status': 'open'
        }
        
        # create it!
        return self.create_post(post_data)
    
    def create_post_from_json(self, json_file):
        """Alternative: create from JSON file with post data"""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                post_data = json.load(f)
            
            # make sure we have a status
            if not 'status' in post_data:
                post_data['status'] = self.publish_status
            
            return self.create_post(post_data)
            
        except Exception as e:
            print(f"❌ Couldn't read JSON: {e}")
            return None
    
    def create_post(self, post_data):
        """Actually create the post via API"""
        
        print("Sending to WordPress...")
        
        try:
            resp = requests.post(
                f"{self.api_url}/posts",
                headers=self.headers,
                json=post_data
            )
            
            if resp.status_code == 201:
                # success!
                post = resp.json()
                
                result = {
                    'success': True,
                    'post_id': post['id'],
                    'post_url': post['link'],
                    'status': post['status'],
                    'title': post['title']['rendered']
                }
                
                print(f"✅ Post created!")
                print(f"   ID: {result['post_id']}")
                print(f"   URL: {result['post_url']}")
                print(f"   Status: {result['status']}")
                
                return result
                
            else:
                # something went wrong
                error = response.json().get('message', response.text) if 'response' in locals() else resp.json().get('message', resp.text)
                print(f"❌ Failed: {error}")
                
                return {
                    'success': False,
                    'error': error,
                    'status_code': resp.status_code
                }
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def run(self):
        """Main entry point"""
        
        results = []
        
        # check if specific file provided
        if self.html_file:
            print(f"📝 Processing: {self.html_file}")
            result = self.create_post_from_html(self.html_file)
            if result:
                results.append(result)
        else:
            # process all files in directory
            files_found = False
            
            # get all html files
            html_files = [f for f in os.listdir('.') if f.endswith('.html')]
            for file in html_files:
                files_found = True
                print(f"📝 Processing: {file}")
                
                # reset title for each file
                self.post_title = ''
                
                result = self.create_post_from_html(file)
                if result:
                    results.append(result)
            
            # also check for json files
            json_files = [f for f in os.listdir('.') if f.endswith('.json') and f != 'publish_result.json']
            for file in json_files:
                files_found = True
                print(f"📝 Processing JSON: {file}")
                result = self.create_post_from_json(file)
                if result:
                    results.append(result)
            
            if not files_found:
                print("⚠️  No files to process!")
                print("    Put some .html or .json files in this directory")
        
        # save results
        if results:
            with open('publish_result.json', 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\nSaved results to publish_result.json")
        
        # figure out exit code
        if not results:
            sys.exit(1)  # nothing done
        
        success_count = sum(1 for r in results if r.get('success'))
        if success_count == len(results):
            sys.exit(0)  # all good
        elif success_count > 0:
            sys.exit(0)  # some worked, good enough
        else:
            sys.exit(1)  # all failed :(

# run it
if __name__ == '__main__':
    try:
        publisher = WordPressPublisher()
        publisher.run()
    except KeyboardInterrupt:
        print("\n\nCancelled!")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Something broke: {e}")
        # import traceback
        # traceback.print_exc()
        sys.exit(1)
