import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
from datetime import datetime
import time
import re
import xml.etree.ElementTree as ET

def scrape_ibm_deprecated_models():
    """
    Scrape the IBM Watson documentation to extract deprecated foundation models table.
    Returns structured data of the deprecated models.
    """
    
    url = 'https://www.ibm.com/docs/en/watsonx/saas?topic=model-foundation-lifecycle#foundation-model-deprecation'
    
    # Headers to mimic a real browser request
    headers = {
        'User-Agent': 'curl/8.5.0 (x86_64-pc-linux-gnu)'
    }
    
    try:
        print(f"Fetching data from: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for the specific table with deprecated models
        # The table should have a caption or be near text about deprecated models
        tables = soup.find_all('table')
        
        deprecated_models = []
        
        for table in tables:
            # Check if this table contains deprecated model information
            table_text = table.get_text().lower()
            if 'deprecated' in table_text and 'foundation model' in table_text:
                print("Found deprecated models table!")
                
                # Extract table data
                rows = table.find_all('tr')
                
                for row in rows[1:]:  # Skip header row
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 5:  # Ensure we have all expected columns
                        model_data = {
                            'foundation_model_name': cells[0].get_text(strip=True),
                            'availability_date': cells[1].get_text(strip=True),
                            'deprecation_date': cells[2].get_text(strip=True),
                            'withdrawal_date': cells[3].get_text(strip=True),
                            'recommended_alternative': cells[4].get_text(strip=True)
                        }
                        deprecated_models.append(model_data)
        
        if not deprecated_models:
            print("No deprecated models table found. Trying alternative approach...")
            # Fallback: look for any table with model information
            for table in tables:
                rows = table.find_all('tr')
                if len(rows) > 1:
                    first_row = rows[0]
                    headers = [th.get_text(strip=True).lower() for th in first_row.find_all(['th', 'td'])]
                    
                    if any('model' in header for header in headers) and any('date' in header for header in headers):
                        print(f"Found potential table with headers: {headers}")
                        
                        for row in rows[1:]:
                            cells = row.find_all(['td', 'th'])
                            if len(cells) >= 3:
                                model_data = {
                                    'foundation_model_name': cells[0].get_text(strip=True),
                                    'availability_date': cells[1].get_text(strip=True) if len(cells) > 1 else '',
                                    'deprecation_date': cells[2].get_text(strip=True) if len(cells) > 2 else '',
                                    'withdrawal_date': cells[3].get_text(strip=True) if len(cells) > 3 else '',
                                    'recommended_alternative': cells[4].get_text(strip=True) if len(cells) > 4 else ''
                                }
                                deprecated_models.append(model_data)
        
        return deprecated_models
        
    except requests.RequestException as e:
        print(f"Error fetching the webpage: {e}")
        return []
    except Exception as e:
        print(f"Error parsing the webpage: {e}")
        return []

def save_data_to_files(data, base_filename='ibm_deprecated_models'):
    """
    Save the scraped data to multiple formats for easy access.
    """
    if not data:
        print("No data to save.")
        return
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save as CSV
    df = pd.DataFrame(data)
    csv_filename = f"{base_filename}_{timestamp}.csv"
    df.to_csv(csv_filename, index=False)
    print(f"Data saved to CSV: {csv_filename}")
    
    # Save as JSON
    json_filename = f"{base_filename}_{timestamp}.json"
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Data saved to JSON: {json_filename}")
    
    # Save as Excel (if pandas supports it)
    try:
        excel_filename = f"{base_filename}_{timestamp}.xlsx"
        df.to_excel(excel_filename, index=False)
        print(f"Data saved to Excel: {excel_filename}")
    except ImportError:
        print("Excel export not available (openpyxl not installed)")
    
    return csv_filename, json_filename

def convert_to_rss_xml(data, base_filename='ibm_deprecated_models'):
    """
    Convert the scraped data to RSS XML format for RSS readers.
    """
    if not data:
        print("No data to convert to RSS.")
        return None
    
    # Create RSS root element
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    
    # Add channel metadata
    ET.SubElement(channel, "title").text = "IBM Watson Deprecated Foundation Models"
    ET.SubElement(channel, "link").text = "https://www.ibm.com/docs/en/watsonx/saas?topic=model-foundation-lifecycle#foundation-model-deprecation"
    ET.SubElement(channel, "description").text = "List of deprecated foundation models from IBM WatsonX documentation with deprecation dates and recommended alternatives."
    ET.SubElement(channel, "language").text = "en-us"
    ET.SubElement(channel, "lastBuildDate").text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")
    
    # Add items for each model
    for model in data:
        item = ET.SubElement(channel, "item")
        
        # Create title from model name
        title = model['foundation_model_name']
        ET.SubElement(item, "title").text = title
        
        # Create description with all model details
        description = f"""
        <strong>Model:</strong> {model['foundation_model_name']}<br/>
        <strong>Availability Date:</strong> {model['availability_date']}<br/>
        <strong>Deprecation Date:</strong> {model['deprecation_date']}<br/>
        <strong>Withdrawal Date:</strong> {model['withdrawal_date']}<br/>
        <strong>Recommended Alternative:</strong> {model['recommended_alternative']}
        """
        ET.SubElement(item, "description").text = description.strip()
        
        # Use withdrawal date as pubDate if available, otherwise use current date
        if model['withdrawal_date'] and model['withdrawal_date'] != '–':
            # Try to parse the date and format it for RSS
            try:
                # Simple date parsing for common formats
                date_str = model['withdrawal_date']
                if 'January' in date_str:
                    month = '01'
                elif 'February' in date_str:
                    month = '02'
                elif 'March' in date_str:
                    month = '03'
                elif 'April' in date_str:
                    month = '04'
                elif 'May' in date_str:
                    month = '05'
                elif 'June' in date_str:
                    month = '06'
                elif 'July' in date_str:
                    month = '07'
                elif 'August' in date_str:
                    month = '08'
                elif 'September' in date_str:
                    month = '09'
                elif 'October' in date_str:
                    month = '10'
                elif 'November' in date_str:
                    month = '11'
                elif 'December' in date_str:
                    month = '12'
                else:
                    month = '01'
                
                # Extract day and year
                parts = date_str.split()
                day = parts[0] if parts[0].isdigit() else '01'
                year = parts[-1] if parts[-1].isdigit() else '2025'
                
                # Format as RSS date
                pub_date = f"{day} {month} {year} 00:00:00 GMT"
                ET.SubElement(item, "pubDate").text = pub_date
            except:
                # Fallback to current date
                ET.SubElement(item, "pubDate").text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")
        else:
            ET.SubElement(item, "pubDate").text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")
        
        # Add unique GUID
        ET.SubElement(item, "guid").text = f"ibm-model-{hash(model['foundation_model_name'])}"
        
        # Add category
        ET.SubElement(item, "category").text = "AI/ML Models"
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    xml_filename = f"{base_filename}_{timestamp}.xml"
    
    # Write XML to file
    tree = ET.ElementTree(rss)
    tree.write(xml_filename, encoding='utf-8', xml_declaration=True)
    print(f"RSS feed saved to: {xml_filename}")
    
    return xml_filename

def display_results(data):
    """
    Display the scraped data in a formatted way.
    """
    if not data:
        print("No data to display.")
        return
    
    print(f"\n{'='*80}")
    print(f"FOUND {len(data)} DEPRECATED FOUNDATION MODELS")
    print(f"{'='*80}")
    
    for i, model in enumerate(data, 1):
        print(f"\n{i}. Model: {model['foundation_model_name']}")
        print(f"   Availability: {model['availability_date']}")
        print(f"   Deprecation: {model['deprecation_date']}")
        print(f"   Withdrawal: {model['withdrawal_date']}")
        print(f"   Alternative: {model['recommended_alternative']}")
        print("-" * 60)

def main():
    """
    Main function to orchestrate the scraping process.
    """
    print("IBM Watson Foundation Models Deprecation Scraper")
    print("=" * 50)
    
    # Scrape the data
    data = scrape_ibm_deprecated_models()
    
    if data:
        # Display results
        display_results(data)
        
        # Save to files
        save_data_to_files(data)
        
        # Convert to RSS XML
        rss_file = convert_to_rss_xml(data)
        
        print(f"\nScraping completed successfully! Found {len(data)} deprecated models.")
        if rss_file:
            print(f"RSS feed created: {rss_file}")
            print("You can now import this XML file into any RSS reader!")
    else:
        print("No data was scraped. The website structure might have changed or the content is not accessible.")

if __name__ == '__main__':
    main()