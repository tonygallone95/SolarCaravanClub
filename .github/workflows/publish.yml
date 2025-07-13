name: Auto Publish Articles
on:
  workflow_dispatch:
    inputs:
      publish_status:
        description: 'Publish Status'
        required: true
        default: 'draft'
        type: choice
        options:
        - draft
        - publish
        - private
      categories:
        description: 'Category IDs (comma-separated, e.g., 1,5,12)'
        required: false
        default: ''
      tags:
        description: 'Tags (comma-separated, e.g., solar,caravan,RV)'
        required: false
        default: 'solar,caravan,RV,off-grid'
      content_source:
        description: 'Content Source'
        required: true
        default: 'article.html'
        type: choice
        options:
        - article.html
        - content.json
        - latest_file
  schedule:
    - cron: '0 12 * * *'  # Daily at noon UTC (adjust as needed)

jobs:
  auto-publish:
    runs-on: ubuntu-latest
    steps:
      - name: Check out repository
        uses: actions/checkout@v3
        
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
          
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install requests beautifulsoup4
          
      - name: List available content files
        run: |
          echo "📁 Available content files:"
          find . -name "*.html" -o -name "*.json" | grep -E "(article|content)" | head -10
          
      - name: Validate content exists
        run: |
          if [ "${{ github.event.inputs.content_source }}" = "article.html" ] && [ ! -f "article.html" ]; then
            echo "❌ article.html not found!"
            exit 1
          elif [ "${{ github.event.inputs.content_source }}" = "content.json" ] && [ ! -f "content.json" ]; then
            echo "❌ content.json not found!"
            exit 1
          fi
          echo "✅ Content source validated"
          
      - name: Show content preview
        run: |
          echo "📄 Content preview (first 500 characters):"
          if [ -f "article.html" ]; then
            head -c 500 article.html
          elif [ -f "content.json" ]; then
            head -c 500 content.json
          fi
          echo ""
          echo "..."
          
      - name: Run publishing script
        env:
          WP_SITE: ${{ secrets.WP_SITE }}
          WP_USER: ${{ secrets.WP_USER }}
          WP_APP_PASS: ${{ secrets.WP_APP_PASS }}
          PUBLISH_STATUS: ${{ github.event.inputs.publish_status || 'draft' }}
          POST_CATEGORIES: ${{ github.event.inputs.categories }}
          POST_TAGS: ${{ github.event.inputs.tags }}
          CONTENT_SOURCE: ${{ github.event.inputs.content_source || 'article.html' }}
        run: |
          python post.py
          
      - name: Upload publish results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: publish-results
          path: |
            publish_result.json
            *.log
          retention-days: 30
          
      - name: Post-publish cleanup
        if: success()
        run: |
          echo "🧹 Cleaning up..."
          # Optional: Archive or move processed files
          if [ -f "article.html" ]; then
            mkdir -p processed
            mv article.html "processed/article_$(date +%Y%m%d_%H%M%S).html"
            echo "✅ Moved article.html to processed/"
          fi
          
      - name: Notify on success
        if: success()
        run: |
          echo "🎉 Article published successfully!"
          echo "📊 Pipeline completed at $(date)"
          if [ -f "publish_result.json" ]; then
            echo "📋 Post details:"
            cat publish_result.json | python3 -m json.tool
          fi
          
      - name: Notify on failure  
        if: failure()
        run: |
          echo "💥 Pipeline failed!"
          echo "📊 Check the logs above for details"
          echo "🔧 Common issues:"
          echo "  - Check WordPress credentials in secrets"
          echo "  - Verify content file exists"
          echo "  - Check WordPress site is accessible"
