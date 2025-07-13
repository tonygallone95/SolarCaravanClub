#!/usr/bin/env python3
"""
WordPress Post Publisher with HTML Support
Publishes HTML files as WordPress posts with Gutenberg blocks
"""

import os
import json
import requests
from base64 import b64encode
from datetime import datetime
from bs4 import BeautifulSoup
import re
import sys

class WordPressPublisher:
    def __init__(self):
        self.site = os.environ.get('WP_SITE')
        self.user = os.environ.get('WP_USER')
        self.app_pass = os.environ.get('WP_APP_PASS')
        self.publish_status = os.environ.get('PUBLISH_STATUS', 'draft')
        self.html_file = os.environ.get('HTML_FILE', '')
        self.post_title = os.environ.get('POST_TITLE', '')
        
        if not all([self.site, self.user, self.app_pass]):
            raise ValueError("Missing required environment variables: WP_SITE, WP_USER, WP_APP_PASS")
        
        # Create auth header
        credentials = f"{self.user}:{self.app_pass}"
        token = b64encode(credentials.encode()).decode('ascii')
        self.headers = {
            'Authorization': f'Basic {token}',
            'Content-Type': 'application/json'
        }
        
        self.api_url = f"{self.site.rstrip('/')}/wp-json/wp/v2"
        
    def read_html_file(self, filename):
        """Read and parse HTML file"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"❌ HTML file not found: {filename}")
            return None
        except Exception as e:
            print(f"❌ Error reading HTML file: {e}")
            return None
    
    def html_to_gutenberg_blocks(self, html_content):
        """Convert HTML to Gutenberg block format"""
        # Parse HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract title if not provided
        if not self.post_title:
            title_tag = soup.find('title')
            if title_tag:
                self.post_title = title_tag.text.strip()
            else:
                h1_tag = soup.find('h1')
                if h1_tag:
                    self.post_title = h1_tag.text.strip()
                else:
                    self.post_title = f"Post from {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        # Extract body content
        body = soup.find('body')
        if body:
            content = str(body)
        else:
            content = html_content
        
        # Clean up the HTML
        content = self.clean_html(content)
        
        # Convert to Gutenberg blocks
        blocks = []
        
        # Split content into blocks based on top-level elements
        soup_content = BeautifulSoup(content, 'html.parser')
        
        for element in soup_content.children:
            if isinstance(element, str) and element.strip():
                # Text content - wrap in paragraph block
                blocks.append(f'<!-- wp:paragraph -->\n<p>{element.strip()}</p>\n<!-- /wp:paragraph -->')
            elif element.name:
                if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    # Heading block
                    level = element.name[1]
                    blocks.append(f'<!-- wp:heading {{"level":{level}}} -->\n{str(element)}\n<!-- /wp:heading -->')
                elif element.name == 'p':
                    # Paragraph block
                    blocks.append(f'<!-- wp:paragraph -->\n{str(element)}\n<!-- /wp:paragraph -->')
                elif element.name == 'img':
                    # Image block
                    blocks.append(f'<!-- wp:image -->\n<figure class="wp-block-image">{str(element)}</figure>\n<!-- /wp:image -->')
                elif element.name in ['ul', 'ol']:
                    # List block
                    blocks.append(f'<!-- wp:list -->\n{str(element)}\n<!-- /wp:list -->')
                elif element.name == 'blockquote':
                    # Quote block
                    blocks.append(f'<!-- wp:quote -->\n{str(element)}\n<!-- /wp:quote -->')
                elif element.name == 'pre':
                    # Code block
                    blocks.append(f'<!-- wp:code -->\n{str(element)}\n<!-- /wp:code -->')
                elif element.name == 'table':
                    # Table block
                    blocks.append(f'<!-- wp:table -->\n<figure class="wp-block-table">{str(element)}</figure>\n<!-- /wp:table -->')
                else:
                    # For any other HTML, use the HTML block
                    blocks.append(f'<!-- wp:html -->\n{str(element)}\n<!-- /wp:html -->')
        
        # If no blocks were created, wrap everything in an HTML block
        if not blocks:
            blocks.append(f'<!-- wp:html -->\n{content}\n<!-- /wp:html -->')
        
        return '\n\n'.join(blocks)
    
    def clean_html(self, html):
        """Clean HTML content"""
        # Remove body tags if present
        html = re.sub(r'</?body[^>]*>', '', html, flags=re.IGNORECASE)
        
        # Remove script tags
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove style tags (optional - comment out if you want to keep styles)
        # html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.IGNORECASE | re.DOTALL)
        
        return html.strip()
    
    def create_post_from_html(self, html_file):
        """Create a WordPress post from an HTML file"""
        # Read HTML file
        html_content = self.read_html_file(html_file)
        if not html_content:
            return None
        
        # Convert to Gutenberg blocks
        block_content = self.html_to_gutenberg_blocks(html_content)
        
        # Create post data
        post_data = {
            'title': self.post_title,
            'content': block_content,
            'status': self.publish_status,
            'format': 'standard',
            'comment_status': 'open',
            'ping_status': 'open'
        }
        
        return self.create_post(post_data)
    
    def create_post_from_json(self, json_file):
        """Create a WordPress post from a JSON file"""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                post_data = json.load(f)
            
            # Ensure status is set
            if 'status' not in post_data:
                post_data['status'] = self.publish_status
            
            return self.create_post(post_data)
        except Exception as e:
            print(f"❌ Error reading JSON file: {e}")
            return None
    
    def create_post(self, post_data):
        """Create a post via WordPress REST API"""
        try:
            response = requests.post(
                f"{self.api_url}/posts",
                headers=self.headers,
                json=post_data
            )
            
            if response.status_code == 201:
                post = response.json()
                result = {
                    'success': True,
                    'post_id': post['id'],
                    'post_url': post['link'],
                    'status': post['status'],
                    'title': post['title']['rendered']
                }
                print(f"✅ Post created successfully!")
                print(f"   ID: {result['post_id']}")
                print(f"   URL: {result['post_url']}")
                print(f"   Status: {result['status']}")
                return result
            else:
                error_msg = response.json().get('message', response.text)
                print(f"❌ Failed to create post: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': response.status_code
                }
                
        except Exception as e:
            print(f"❌ Error creating post: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def run(self):
        """Main execution"""
        results = []
        
        # If specific HTML file is provided
        if self.html_file:
            print(f"📝 Processing HTML file: {self.html_file}")
            result = self.create_post_from_html(self.html_file)
            if result:
                results.append(result)
        else:
            # Process all HTML and JSON files in the directory
            files_processed = False
            
            # Process HTML files
            for file in os.listdir('.'):
                if file.endswith('.html'):
                    files_processed = True
                    print(f"📝 Processing HTML file: {file}")
                    result = self.create_post_from_html(file)
                    if result:
                        results.append(result)
            
            # Process JSON files
            for file in os.listdir('.'):
                if file.endswith('.json') and file != 'publish_result.json':
                    files_processed = True
                    print(f"📝 Processing JSON file: {file}")
                    result = self.create_post_from_json(file)
                    if result:
                        results.append(result)
            
            if not files_processed:
                print("⚠️  No HTML or JSON files found to process")
        
        # Save results
        with open('publish_result.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        # Exit with appropriate code
        if results and all(r.get('success') for r in results):
            sys.exit(0)
        elif results and any(r.get('success') for r in results):
            sys.exit(0)  # Partial success
        else:
            sys.exit(1)  # Complete failure

if __name__ == '__main__':
    try:
        publisher = WordPressPublisher()
        publisher.run()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)
