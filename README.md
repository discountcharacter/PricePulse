# PricePulse - E-Commerce Price Tracker & Smart Comparator

**Author:** Rahul Jaiswal
**Assignment:** Alfaleus Tech - Internship Assignment 1 (Full stack developer and web automation)
**Date:** May 27, 2025

## Description

PricePulse is a full-stack web application designed to help users track prices of products on Amazon.in. It allows users to submit an Amazon product URL, after which the application automatically scrapes and records the product's price at regular intervals. Users can then visualize the price trend on a graph over time. 

The project also includes bonus features: an email alert system for price drops and an AI-powered attempt to identify and compare the same product across other e-commerce platforms like Flipkart and Meesho.

## Features Implemented

### Core Functionality
* **Amazon Product URL Input:** Users can submit an Amazon.in product URL to start tracking. [cite: 1]
* **Automated Price Scraping:** The application backend scrapes the product's name, current price, and image from Amazon.
* **Scheduled Tracking:** A scheduler (APScheduler) automatically re-scrapes product prices every 30 minutes. [cite: 2]
* **Price History Database:** Scraped prices and timestamps are stored in a local SQLite database. [cite: 9]
* **Price Trend Visualization:** Product detail pages display a line graph showing the historical price trend over time using Chart.js. [cite: 3]
* **Product Preview:** Displays the current price, product name, and image for tracked items. [cite: 8]

### Bonus Features
* **Price Drop Email Alerts:**
    * Users can set a target price for a tracked product and provide their email address. [cite: 23]
    * If the product's price drops below this target, an email alert is designed to be automatically sent. [cite: 22]
    * The system uses Gmail SMTP for sending emails.
    * Alerts are deactivated after firing to prevent repeat notifications for the same drop. [cite: 4]
* **AI Multi-Platform Comparison (Attempted):**
    * A feature to use a Generative AI (Google Gemini) to extract product metadata from the Amazon URL. [cite: 12]
    * The AI is prompted to generate search queries for finding the same product on Flipkart and Meesho. [cite: 12]
    * Placeholder scraper functions attempt to use these queries to fetch data from other platforms. [cite: 13]
    * (Note: The actual scraping of Flipkart/Meesho is highly experimental due to their anti-scraping measures.)

## Technologies Used

* **Backend:** Python, Flask, SQLAlchemy (for ORM), APScheduler
* **Frontend:** HTML, CSS, JavaScript, Chart.js
* **Database:** SQLite
* **Web Scraping:** Python `requests` library, `BeautifulSoup4`
* **Generative AI (Bonus):** Google Gemini API (via `google-generativeai` Python library)
* **Email Service (Bonus):** Gmail SMTP (via Python `smtplib`)
* **Environment Management:** `python-dotenv`

## Setup Instructions

1.  **Clone the Repository:**
    ```bash
    git clone [https://github.com/](https://github.com/)discountcharacter/PricePulse.git
    cd PriePulse
    ```

2.  **Create and Activate a Virtual Environment (Recommended):**
    It's highly recommended to use Python 3.9 or newer for this project due to dependencies like `google-generativeai`.
    ```bash
    # Assuming you have Python 3.9+ available
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Ensure `requirements.txt` is up-to-date by running `pip freeze > requirements.txt` in your project's virtual environment after installing all packages).*

4.  **Set Up Environment Variables:**
    * Create a file named `.env` in the root of the project directory.
    * Add the following content, replacing the placeholder values with your actual credentials/keys:
        ```env
        # For Email Alerts (Gmail)
        GMAIL_USER="your_email@gmail.com"
        GMAIL_APP_PASSWORD="your_16_digit_gmail_app_password"

        # For AI Multi-Platform Comparison (Google Gemini)
        GEMINI_API_KEY="your_google_gemini_api_key"
        ```
    * **Note on `GMAIL_APP_PASSWORD`:** If you use 2-Step Verification with Gmail, you need to generate an "App Password" from your Google Account security settings. Do not use your regular Gmail password.
    * **Note on `GEMINI_API_KEY`:** Obtain this from Google AI Studio.

5.  **Run the Application:**
    ```bash
    python app.py
    ```

6.  **Access the Application:**
    Open your web browser and go to `http://127.0.0.1:5000/`.

## Challenges Faced & Known Issues

* **AI Model Initialization:** Encountered difficulties initializing the Google Gemini model (`gemini-1.5-flash-latest` or `gemini-pro`) due to issues with the `google-generativeai` library version in the initial development environment (stuck on an old `0.1.0rc1` version). While the environment was later updated to Python 3.9 to support newer library versions, further testing is needed to confirm consistent successful API calls. *(Rahul, adjust this based on your final success with the LLM call. If it worked after updating Python & the library, state that it was resolved).*
* **Multi-Platform Scraping:** The scrapers for Flipkart and Meesho are very basic placeholders. These platforms have strong anti-scraping measures (like CAPTCHAs, dynamic content loading, and request blocking e.g. 403 errors for Meesho, 429 for Flipkart), making reliable data extraction with simple `requests` and `BeautifulSoup` extremely challenging. Robust scraping would require more advanced tools like Selenium/Playwright and sophisticated anti-detection techniques.
* **Amazon Scraping Robustness:** While the current Amazon scraper works for some product pages, Amazon frequently changes its HTML structure. This can break the scraper, requiring updates to the selectors. Handling all variations of Amazon product pages and potential blocking is an ongoing challenge.
* **Email Alert Testing:** Thorough end-to-end testing of the email alert trigger via the scheduler requires waiting for actual price drops or careful manual simulation, which can be time-consuming. The individual components (email sending, alert database logic) have been set up.

## Future Improvements (Optional)

* Implement robust scraping for Flipkart, Meesho, etc., possibly using browser automation tools.
* Add user accounts and authentication to allow users to manage their tracked products and alerts.
* Store and display comparison data from other platforms more persistently.
* Improve UI/UX and error handling for a more polished user experience.
* Offer more notification options (e.g., SMS, browser notifications).

---