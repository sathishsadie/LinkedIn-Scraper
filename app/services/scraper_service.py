"""
services/scraper_service.py - LinkedIn Scraper Service
Uses the existing scraper code
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
from typing import Dict, List, Optional
import os


class LinkedInScraperService:
    def __init__(self):
        self.email = os.getenv("LINKEDIN_EMAIL", "sathishsysgenpro@gmail.com")
        self.password = os.getenv("LINKEDIN_PASSWORD", "idQX#G=~DR!^9sw")
        self.driver = None
        self.is_logged_in = False
        
    def _setup_driver(self):
        """Setup Chrome WebDriver"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.maximize_window()
        
    def login(self):
        """Login to LinkedIn"""
        if self.is_logged_in:
            return True
            
        if not self.driver:
            self._setup_driver()
            
        print("Logging in to LinkedIn...")
        self.driver.get("https://www.linkedin.com/login")
        time.sleep(2)
        
        try:
            email_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            email_field.send_keys(self.email)
            
            password_field = self.driver.find_element(By.ID, "password")
            password_field.send_keys(self.password)
            
            login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_button.click()
            time.sleep(5)
            
            if "feed" in self.driver.current_url or "mynetwork" in self.driver.current_url:
                print("Login successful!")
                self.is_logged_in = True
                return True
            else:
                print("Login may have failed.")
                return False
                
        except Exception as e:
            print(f"Login error: {str(e)}")
            return False
    
    def scrape_company_page(self, company_id: str) -> Dict:
        """Scrape company page data"""
        url = f"https://www.linkedin.com/company/{company_id}/"
        print(f"Scraping company page: {url}")
        
        self.driver.get(url)
        time.sleep(3)
        
        company_data = {"page_id": company_id, "url": url}
        
        try:
            try:
                name = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h1.org-top-card-summary__title"))
                ).text.strip()
                company_data["name"] = name
            except:
                company_data["name"] = None
            
            try:
                tagline = self.driver.find_element(By.CSS_SELECTOR, "p.org-top-card-summary__tagline").text.strip()
                company_data["description"] = tagline
            except:
                company_data["description"] = None
            
            try:
                followers_text = self.driver.find_element(By.CSS_SELECTOR, "div.org-top-card-summary-info-list__info-item").text
                followers = int(''.join(filter(str.isdigit, followers_text)))
                company_data["followers_count"] = followers
            except:
                company_data["followers_count"] = 0
            
            try:
                logo = self.driver.find_element(By.CSS_SELECTOR, "img.org-top-card-primary-content__logo").get_attribute("src")
                company_data["profile_image_url"] = logo
            except:
                company_data["profile_image_url"] = None
            
            self.driver.execute_script("window.scrollTo(0, 800);")
            time.sleep(2)
            
            try:
                website = self.driver.find_element(By.CSS_SELECTOR, "a[data-tracking-control-name='about_website']").get_attribute("href")
                company_data["website"] = website
            except:
                company_data["website"] = None
            
            try:
                industry_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.org-page-details__definition-text")
                for elem in industry_elements:
                    text = elem.text.strip()
                    if text and len(text) < 100:
                        company_data["industry"] = text
                        break
            except:
                company_data["industry"] = None
            
            try:
                size_text = self.driver.find_element(By.XPATH, "//dt[contains(text(), 'Company size')]/following-sibling::dd").text.strip()
                company_data["headcount"] = size_text
            except:
                company_data["headcount"] = None
            
            try:
                location = self.driver.find_element(By.XPATH, "//dt[contains(text(), 'Headquarters')]/following-sibling::dd").text.strip()
                company_data["location"] = location
            except:
                company_data["location"] = None
            
            try:
                founded_text = self.driver.find_element(By.XPATH, "//dt[contains(text(), 'Founded')]/following-sibling::dd").text.strip()
                company_data["founded_year"] = int(founded_text)
            except:
                company_data["founded_year"] = None
            
            try:
                specialties_text = self.driver.find_element(By.XPATH, "//dt[contains(text(), 'Specialties')]/following-sibling::dd").text.strip()
                specialties = [s.strip() for s in specialties_text.split(',')]
                company_data["specialities"] = specialties
            except:
                company_data["specialities"] = []
            
            print(f"Successfully scraped company: {company_data.get('name')}")
            return company_data
            
        except Exception as e:
            print(f"Error scraping company page: {str(e)}")
            return company_data
    
    def scrape_company_posts(self, company_id: str, max_posts: int = 15) -> List[Dict]:
        """Scrape recent posts from company page"""
        url = f"https://www.linkedin.com/company/{company_id}/posts/"
        print(f"Scraping posts: {url}")
        
        self.driver.get(url)
        time.sleep(3)
        
        posts = []
        
        try:
            for _ in range(3):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
            
            post_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.feed-shared-update-v2")
            
            for idx, post_elem in enumerate(post_elements[:max_posts]):
                try:
                    post_data = {}
                    
                    try:
                        post_link = post_elem.find_element(By.CSS_SELECTOR, "a[data-control-name='view_linkedin_post']")
                        permalink = post_link.get_attribute("href")
                        post_data["permalink"] = permalink
                        post_data["linkedin_post_id"] = permalink.split(":")[-1] if ":" in permalink else f"{company_id}-post-{idx}"
                    except:
                        post_data["linkedin_post_id"] = f"{company_id}-post-{idx}"
                        post_data["permalink"] = None
                    
                    try:
                        content = post_elem.find_element(By.CSS_SELECTOR, "div.feed-shared-update-v2__description").text.strip()
                        post_data["content"] = content
                    except:
                        post_data["content"] = ""
                    
                    try:
                        date_elem = post_elem.find_element(By.CSS_SELECTOR, "span.feed-shared-actor__sub-description")
                        post_data["posted_at"] = date_elem.text.strip()
                    except:
                        post_data["posted_at"] = None
                    
                    try:
                        reactions = post_elem.find_element(By.CSS_SELECTOR, "span.social-details-social-counts__reactions-count").text.strip()
                        post_data["likes_count"] = int(''.join(filter(str.isdigit, reactions))) if reactions else 0
                    except:
                        post_data["likes_count"] = 0
                    
                    try:
                        comments = post_elem.find_element(By.CSS_SELECTOR, "button[aria-label*='comment']").text.strip()
                        post_data["comments_count"] = int(''.join(filter(str.isdigit, comments))) if comments else 0
                    except:
                        post_data["comments_count"] = 0
                    
                    post_data["page_id"] = company_id
                    posts.append(post_data)
                    
                except Exception as e:
                    print(f"Error scraping post {idx}: {str(e)}")
                    continue
            
            print(f"Successfully scraped {len(posts)} posts")
            return posts
            
        except Exception as e:
            print(f"Error scraping posts: {str(e)}")
            return posts
    
    def scrape_company_employees(self, company_id: str, max_employees: int = 50) -> List[Dict]:
        """Scrape employees from company page"""
        url = f"https://www.linkedin.com/company/{company_id}/people/"
        print(f"Scraping employees: {url}")
        
        self.driver.get(url)
        time.sleep(3)
        
        employees = []
        
        try:
            for _ in range(3):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
            
            employee_elements = self.driver.find_elements(By.CSS_SELECTOR, "li.org-people-profile-card__profile-card-spacing")
            
            for idx, emp_elem in enumerate(employee_elements[:max_employees]):
                try:
                    employee_data = {"type": "EMPLOYEE", "page_id": company_id}
                    
                    try:
                        name = emp_elem.find_element(By.CSS_SELECTOR, "div.org-people-profile-card__profile-title").text.strip()
                        employee_data["full_name"] = name
                    except:
                        employee_data["full_name"] = f"Employee {idx + 1}"
                    
                    try:
                        profile_link = emp_elem.find_element(By.CSS_SELECTOR, "a[data-control-name='people_profile_card_name_link']")
                        profile_url = profile_link.get_attribute("href")
                        employee_data["profile_url"] = profile_url
                    except:
                        employee_data["profile_url"] = None
                    
                    try:
                        headline = emp_elem.find_element(By.CSS_SELECTOR, "div.artdeco-entity-lockup__subtitle").text.strip()
                        employee_data["headline"] = headline
                    except:
                        employee_data["headline"] = None
                    
                    try:
                        location = emp_elem.find_element(By.CSS_SELECTOR, "div.artdeco-entity-lockup__caption").text.strip()
                        employee_data["location"] = location
                    except:
                        employee_data["location"] = None
                    
                    employees.append(employee_data)
                    
                except Exception as e:
                    print(f"Error scraping employee {idx}: {str(e)}")
                    continue
            
            print(f"Successfully scraped {len(employees)} employees")
            return employees
            
        except Exception as e:
            print(f"Error scraping employees: {str(e)}")
            return employees
    
    def scrape_post_comments(self, post_url: str, max_comments: int = 50) -> List[Dict]:
        """Scrape comments from a specific post"""
        print(f"Scraping comments from: {post_url}")
        
        self.driver.get(post_url)
        time.sleep(3)
        
        comments = []
        
        try:
            try:
                load_comments_btn = self.driver.find_element(By.CSS_SELECTOR, "button[aria-label*='comment']")
                load_comments_btn.click()
                time.sleep(2)
            except:
                pass
            
            for _ in range(2):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
            
            comment_elements = self.driver.find_elements(By.CSS_SELECTOR, "article.comments-comment-item")
            
            for idx, comment_elem in enumerate(comment_elements[:max_comments]):
                try:
                    comment_data = {}
                    
                    try:
                        author_name = comment_elem.find_element(By.CSS_SELECTOR, "span.comments-post-meta__name-text").text.strip()
                        comment_data["author_name"] = author_name
                    except:
                        comment_data["author_name"] = "Unknown"
                    
                    try:
                        text = comment_elem.find_element(By.CSS_SELECTOR, "span.comments-comment-item__main-content").text.strip()
                        comment_data["text"] = text
                    except:
                        comment_data["text"] = ""
                    
                    try:
                        date = comment_elem.find_element(By.CSS_SELECTOR, "span.comments-comment-item__timestamp").text.strip()
                        comment_data["created_at"] = date
                    except:
                        comment_data["created_at"] = None
                    
                    comments.append(comment_data)
                    
                except Exception as e:
                    print(f"Error scraping comment {idx}: {str(e)}")
                    continue
            
            print(f"Successfully scraped {len(comments)} comments")
            return comments
            
        except Exception as e:
            print(f"Error scraping comments: {str(e)}")
            return comments
    
    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
            self.is_logged_in = False
            print("Browser closed")