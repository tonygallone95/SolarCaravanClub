#!/usr/bin/env python3
"""
WordPress Auto-Publishing Script for GitHub Actions
Publishes HTML content to WordPress via REST API
"""

import os
import sys
import json
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
import time

class WordPressPublisher:
    def __init__(self):
        # Get environment variables
        self.wp_site = os.getenv('WP_SITE', 'https://solarcaravanclub.com')
        self.username = os.getenv('WP_USER', 'admin1')
        self.app_password = os.getenv('WP_APP_PASS')
        
        if not self.app_password:
            raise ValueError("WP_APP_PASS environment variable is required")
        
        self.wp_api_url = f"{self.wp_site}/wp-json/wp/v2/posts"
        
        print(f"✅ WordPress Publisher initialized for: {self.wp_site}")

    def publish_post(self, title, content, status="draft", categories=None, tags=None):
        """
        Publish a post to WordPress
        
        Args:
            title (str): Post title
            content (str): Post content (HTML)
            status (str): Post status - 'draft', 'publish', 'private'
            categories (list): List of category IDs
            tags (list): List of tag names
        
        Returns:
            dict: Response from WordPress API
        """
        
        # Prepare post data
        post_data = {
            "title": title,
            "content": content,
            "status": status,
            "format": "standard"
        }
        
        # Add categories if provided
        if categories:
            post_data["categories"] = categories
            
        # Add tags if provided  
        if tags:
            post_data["tags"] = tags
        
        print(f"📝 Publishing post: '{title}' as {status}")
        
        try:
            response = requests.post(
                self.wp_api_url,
                auth=HTTPBasicAuth(self.username, self.app_password),
                json=post_data,
                timeout=30
            )
            
            if response.status_code == 201:
                post_info = response.json()
                print(f"✅ Post created successfully!")
                print(f"📋 Post ID: {post_info.get('id')}")
                print(f"🔗 Post URL: {post_info.get('link')}")
                print(f"📅 Published: {post_info.get('date')}")
                return post_info
            else:
                print(f"❌ Failed to create post:")
                print(f"Status Code: {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error occurred: {e}")
            return None

    def get_categories(self):
        """Get all available categories"""
        categories_url = f"{self.wp_site}/wp-json/wp/v2/categories"
        
        try:
            response = requests.get(categories_url, timeout=10)
            if response.status_code == 200:
                categories = response.json()
                print("📂 Available categories:")
                for cat in categories:
                    print(f"   - {cat['name']} (ID: {cat['id']})")
                return categories
            else:
                print(f"❌ Failed to fetch categories: {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ Error fetching categories: {e}")
            return []

    def create_category(self, name, description=""):
        """Create a new category"""
        categories_url = f"{self.wp_site}/wp-json/wp/v2/categories"
        
        category_data = {
            "name": name,
            "description": description
        }
        
        try:
            response = requests.post(
                categories_url,
                auth=HTTPBasicAuth(self.username, self.app_password),
                json=category_data,
                timeout=10
            )
            
            if response.status_code == 201:
                category = response.json()
                print(f"✅ Category '{name}' created with ID: {category['id']}")
                return category
            else:
                print(f"❌ Failed to create category: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Error creating category: {e}")
            return None


def load_html_content():
    """
    Load HTML content from various sources
    Priority: 
    1. article.html file
    2. Environment variable ARTICLE_HTML
    3. stdin input
    """
    
    # Try to load from file first
    if os.path.exists('article.html'):
        print("📄 Loading content from article.html")
        with open('article.html', 'r', encoding='utf-8') as f:
            return f.read()
    
    # Try environment variable
    article_html = os.getenv('ARTICLE_HTML')
    if article_html:
        print("📄 Loading content from ARTICLE_HTML environment variable")
        return article_html
    
    # Try loading from content.json if it exists
    if os.path.exists('content.json'):
        print("📄 Loading content from content.json")
        with open('content.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('content', '')
    
    print("❌ No content source found. Please provide:")
    print("   - article.html file")
    print("   - ARTICLE_HTML environment variable") 
    print("   - content.json file with 'content' field")
    return None


def extract_title_from_html(html_content):
    """Extract title from HTML content"""
    import re
    
    # Try to find h1 tag first
    h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', html_content, re.IGNORECASE | re.DOTALL)
    if h1_match:
        title = re.sub(r'<[^>]+>', '', h1_match.group(1)).strip()
        return title
    
    # Try title tag
    title_match = re.search(r'<title[^>]*>(.*?)</title>', html_content, re.IGNORECASE | re.DOTALL)
    if title_match:
        title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
        return title
    
    # Default title with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"Solar Caravan Article - {timestamp}"


def main():
    """Main execution function"""
    print("🚀 Starting WordPress Auto-Publisher")
    print("=" * 50)
    
    try:
        # Initialize publisher
        publisher = WordPressPublisher()
        
        # Load content
        html_content = load_html_content()
        if not html_content:
            sys.exit(1)
        
        print(f"📊 Content loaded: {len(html_content)} characters")
        
        # Extract or set title
        title = extract_title_from_html(html_content)
        print(f"📝 Post title: {title}")
        
        # Get publish status from environment (default to draft)
        publish_status = os.getenv('PUBLISH_STATUS', 'draft')
        
        # Optional: Get categories and tags from environment
        categories_env = os.getenv('POST_CATEGORIES', '')
        categories = [int(cat.strip()) for cat in categories_env.split(',') if cat.strip().isdigit()] if categories_env else None
        
        tags_env = os.getenv('POST_TAGS', '')
        tags = [tag.strip() for tag in tags_env.split(',') if tag.strip()] if tags_env else None
        
        if categories:
            print(f"📂 Categories: {categories}")
        if tags:
            print(f"🏷️  Tags: {tags}")
        
        # Publish the post
        result = publisher.publish_post(
            title=title,
            content=html_content,
            status=publish_status,
            categories=categories,
            tags=tags
        )
        
        if result:
            print("\n🎉 SUCCESS! Article published to WordPress")
            
            # Save result to file for potential use in other steps
            with open('publish_result.json', 'w') as f:
                json.dump(result, f, indent=2)
            
            print(f"💾 Result saved to publish_result.json")
        else:
            print("\n💥 FAILED! Could not publish article")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
