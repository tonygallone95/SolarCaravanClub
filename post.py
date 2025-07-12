#!/usr/bin/env python3
"""
post.py

Reads keywords from a CSV and for each:
 1. Generates a 1,500+ word SEO-optimized article via OpenAI
 2. Publishes it as a draft to WordPress via REST API

Environment variables:
 - OPENAI_API_KEY
 - WP_SITE (e.g., https://solarcaravanclub.com)
 - WP_USER
 - WP_APP_PASS
 - KEYWORD_CSV (optional, defaults to "keywords.csv")
"""

import os
import sys
import csv
import requests
from requests.auth import HTTPBasicAuth
import openai


def generate_article(keyword, title):
    """
    Call OpenAI to generate a 1,500+ word SEO-friendly article for the given keyword and title.
    """
    prompt = f"""
Write a 1,500-word beginner-friendly caravan/RV blog post optimized for SEO.
Target keyword: \"{keyword}\"
Use short paragraphs, clear headings, bullet lists, product recommendations with
Amazon affiliate links (tag caravansolarnation-20), pros & cons, FAQs, practical tips,
and a strong call to action at the end to check Amazon.

Title: {title}
"""
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful SEO content generator for caravans."},
            {"role": "user",   "content": prompt}
        ],
        temperature=0.7,
        max_tokens=4000
    )
    return response.choices[0].message.content


def post_to_wp(title, content, slug=None, category_id=None, tag_ids=None):
    """
    Publish the given HTML content as a draft post on WordPress.
    """
    endpoint = f"{WP_SITE.rstrip('/')}/wp-json/wp/v2/posts"
    payload = {
        "title": title,
        "content": content,
        "status": "draft"
    }
    if slug:
        payload["slug"] = slug
    if category_id:
        try:
            payload["categories"] = [int(category_id)]
        except ValueError:
            print(f"⚠️ Invalid category_id '{category_id}', skipping")
    if tag_ids:
        try:
            payload["tags"] = [int(t.strip()) for t in tag_ids.split(",") if t.strip()]
        except ValueError:
            print(f"⚠️ Invalid tag_ids '{tag_ids}', skipping")

    resp = requests.post(
        endpoint,
        auth=HTTPBasicAuth(WP_USER, WP_APP_PASS),
        json=payload
    )
    if resp.status_code == 201:
        link = resp.json().get("link")
        print(f"✅ Draft created: {title}\n→ {link}\n")
    else:
        print(f"❌ Failed to create '{title}': {resp.status_code} {resp.text}")


def main():
    # Load configuration from environment
    global WP_SITE, WP_USER, WP_APP_PASS
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    WP_SITE         = os.getenv("WP_SITE")
    WP_USER         = os.getenv("WP_USER")
    WP_APP_PASS     = os.getenv("WP_APP_PASS")
    KEYWORD_CSV     = os.getenv("KEYWORD_CSV", "keywords.csv")

    # Check required env vars
    missing = [v for v in ("OPENAI_API_KEY","WP_SITE","WP_USER","WP_APP_PASS") if not os.getenv(v)]
    if missing:
        print(f"❌ Missing required environment variables: {', '.join(missing)}")
        sys.exit(1)

    openai.api_key = OPENAI_API_KEY

    try:
        with open(KEYWORD_CSV, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                keyword     = row.get("keyword")
                title       = row.get("title") or keyword
                slug        = row.get("slug")
                category_id = row.get("category_id")
                tag_ids     = row.get("tag_ids")

                if not keyword:
                    print("⚠️ Skipping row with no keyword")
                    continue

                print(f"📝 Generating article for '{keyword}' …")
                article = generate_article(keyword, title)

                print(f"🚀 Posting draft for '{title}' …")
                post_to_wp(title, article, slug, category_id, tag_ids)

    except FileNotFoundError:
        print(f"❌ Keyword CSV file not found: {KEYWORD_CSV}")
        sys.exit(1)


if __name__ == "__main__":
    main()
