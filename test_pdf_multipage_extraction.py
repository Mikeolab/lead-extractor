#!/usr/bin/env python3
"""
Test script to verify multi-page PDF extraction
Tests that all pages are extracted, not just the first page
"""
import sys
from pathlib import Path
import pdfplumber
import httpx
import io

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

def test_pdf_extraction(pdf_url: str):
    """Test extracting text from all pages of a PDF"""
    print(f"\n🧪 Testing PDF extraction: {pdf_url}")
    print("=" * 60)
    
    try:
        # Download PDF
        print("📥 Downloading PDF...")
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            response = client.get(pdf_url)
            if response.status_code != 200:
                print(f"❌ Failed to download PDF (HTTP {response.status_code})")
                return False
            pdf_bytes = io.BytesIO(response.content)
            print(f"✅ Downloaded {len(response.content)} bytes")
        
        # Extract text from all pages
        print("\n📖 Extracting text from PDF...")
        text_parts = []
        pages_with_text = 0
        
        with pdfplumber.open(pdf_bytes) as pdf:
            total_pages = len(pdf.pages)
            print(f"📄 PDF has {total_pages} page(s)")
            
            for page_num, page in enumerate(pdf.pages[:100]):  # Max 100 pages
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                        pages_with_text += 1
                        char_count = len(page_text)
                        
                        # Show progress every 10 pages or on first/last page
                        if page_num == 0 or page_num == total_pages - 1 or (page_num + 1) % 10 == 0:
                            print(f"  ✅ Page {page_num + 1}/{total_pages}: {char_count} chars")
                    else:
                        print(f"  ⚠️ Page {page_num + 1}/{total_pages}: No text found")
                except Exception as e:
                    print(f"  ❌ Page {page_num + 1} error: {str(e)[:50]}")
                    continue
        
        # Combine all text
        full_text = "\n".join(text_parts)
        total_chars = len(full_text)
        
        print("\n" + "=" * 60)
        print("📊 RESULTS:")
        print(f"  Total pages in PDF: {total_pages}")
        print(f"  Pages with text extracted: {pages_with_text}")
        print(f"  Total characters extracted: {total_chars:,}")
        print(f"  Average chars per page: {total_chars // pages_with_text if pages_with_text > 0 else 0:,}")
        
        # Check if we got more than just the first page
        if pages_with_text > 1:
            print(f"\n✅ SUCCESS: Extracted from {pages_with_text} pages (not just first page)")
            
            # Show sample from different pages
            if len(text_parts) >= 2:
                print(f"\n📄 Sample from page 1 (first 100 chars):")
                print(f"  {text_parts[0][:100]}...")
                print(f"\n📄 Sample from page {pages_with_text} (first 100 chars):")
                print(f"  {text_parts[-1][:100]}...")
            
            return True
        elif pages_with_text == 1:
            print(f"\n⚠️ WARNING: Only extracted from 1 page (might be single-page PDF or extraction issue)")
            return False
        else:
            print(f"\n❌ FAILED: No text extracted from any pages")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🧪 Multi-Page PDF Extraction Test")
    print("=" * 60)
    
    # Test with a known multi-page PDF
    test_urls = [
        "https://assets.usesi.com/product-media/catalogs/USESI_857302_catalog.pdf",  # 102 pages
        "https://flyingdiscmuseum.com/flyingdiscmagazine_issue-3.pdf",  # 100 pages
    ]
    
    print("\nChoose a test PDF:")
    print("1. USESI Catalog (102 pages)")
    print("2. Flying Disc Magazine (100 pages)")
    print("3. Custom URL")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        url = test_urls[0]
    elif choice == "2":
        url = test_urls[1]
    elif choice == "3":
        url = input("Enter PDF URL: ").strip()
    else:
        print("Invalid choice, using default...")
        url = test_urls[0]
    
    success = test_pdf_extraction(url)
    
    if success:
        print("\n✅ Test PASSED: Multi-page extraction is working!")
        sys.exit(0)
    else:
        print("\n❌ Test FAILED: Check the output above")
        sys.exit(1)

