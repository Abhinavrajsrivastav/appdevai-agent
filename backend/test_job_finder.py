import requests
import json
import webbrowser
import time

API_BASE_URL = 'http://localhost:8000'

def test_job_finder():
    """Test the job finder API and verify application links"""
    # Test resume content
    resume_content = """
    John Smith
    Software Developer
    
    Experience:
    - Software Engineer at Tech Corp (2019-Present)
    - Junior Developer at Code Solutions (2017-2019)
    
    Skills:
    - Python, JavaScript, React, Node.js
    - AWS, Docker, Git
    """
    
    # Prepare form data
    files = {'resume': ('resume.txt', resume_content)}
    data = {
        'experience_years': 5,
        'location': 'New York',
        'job_type': 'Full-time'
    }
    
    print("Sending request to job finder API...")
    # Make the API call
    response = requests.post(f"{API_BASE_URL}/tools/job_finder", files=files, data=data)
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        # Print the response
        try:
            jobs = response.json()
            
            if isinstance(jobs, list):
                print(f"✅ Received {len(jobs)} jobs")
                
                # Check for application links
                valid_links = 0
                invalid_links = 0
                
                for i, job in enumerate(jobs):
                    print(f"\nJob {i+1}: {job.get('job_title')} at {job.get('company_name')}")
                    link = job.get('application_link', '')
                    
                    # Check if the link seems valid
                    if (link and link != '#' and 
                        not link.startswith('http://localhost') and 
                        not link.startswith('http://127.0.0.1') and
                        not 'example.com' in link and
                        not 'index.html' in link):
                        
                        valid_links += 1
                        print(f"✅ Valid application link: {link}")
                        
                        # Ask to open the link
                        if i < 2:  # Only ask for the first two jobs to avoid too many prompts
                            open_link = input(f"Open this link in browser? (y/n): ")
                            if open_link.lower() == 'y':
                                webbrowser.open(link)
                                time.sleep(1)  # Wait a bit between opening links
                    else:
                        invalid_links += 1
                        print(f"❌ Invalid application link: {link}")
                
                print(f"\nSummary: {valid_links} valid links, {invalid_links} invalid links")
                if invalid_links == 0:
                    print("🎉 All application links are valid!")
                else:
                    print("⚠️ Some application links are invalid.")
            else:
                print("⚠️ Response is not a list of jobs")
                print(json.dumps(jobs, indent=2))
        except Exception as e:
            print(f"❌ Error parsing response: {e}")
            print("Raw response:", response.text[:500])
    else:
        print("❌ Error response:", response.text)

if __name__ == "__main__":
    test_job_finder()
