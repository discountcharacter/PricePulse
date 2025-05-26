# mail_sender.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
# from dotenv import load_dotenv # Not strictly needed here if app.py loads it and os.getenv works

# load_dotenv() # Call this only if you intend to run this script standalone for testing
                # and your .env file is in the same directory.
                # For use with the Flask app, app.py should handle loading .env.

GMAIL_USER = os.getenv('GMAIL_USER')
GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD')

def send_price_alert_email(recipient_email, product_name, product_url, current_price, target_price, product_image_url=None):
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        print("ERROR (mail_sender.py): Gmail credentials (GMAIL_USER, GMAIL_APP_PASSWORD) not found in environment variables. Cannot send email alert.")
        return False

    subject = f"Price Alert! {product_name} is now ₹{current_price:.2f}!"
    
    body_html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 0; background-color: #f4f4f4; color: #333; }}
            .container {{ max-width: 600px; margin: 20px auto; padding: 20px; background-color: #ffffff; border: 1px solid #dddddd; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.05); }}
            .header {{ background-color: #007bff; color: white; padding: 15px; text-align: center; border-top-left-radius: 8px; border-top-right-radius: 8px;}}
            .header h2 {{ margin: 0; font-size: 24px; }}
            .content {{ padding: 20px; text-align: left; }}
            .content p {{ margin-bottom: 15px; font-size: 16px; }}
            .product-image {{ max-width: 180px; height: auto; border-radius: 6px; margin: 15px auto; display: block; border: 1px solid #eee; }}
            .button-container {{ text-align: center; margin-top: 25px; margin-bottom: 15px; }}
            .button {{ display: inline-block; background-color: #28a745; color: white !important; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-size: 16px; font-weight: bold; }}
            .footer {{ font-size: 0.85em; text-align: center; color: #777777; margin-top: 25px; padding-top: 15px; border-top: 1px solid #eeeeee; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>PricePulse Alert!</h2>
            </div>
            <div class="content">
                <p>Hi there,</p>
                <p>Good news! The price for the product you're tracking, <strong>{product_name}</strong>, has dropped to <strong>₹{current_price:.2f}</strong>.</p>
                <p>This is at or below your target price of ₹{target_price:.2f}.</p>
                """
    if product_image_url and product_image_url not in ["N/A", "Image not found", ""] and product_image_url.startswith('http'):
        body_html += f'<p><img src="{product_image_url}" alt="{product_name}" class="product-image"></p>'
    
    body_html += f"""
                <div class="button-container">
                    <a href="{product_url}" class="button">View Product on Amazon</a>
                </div>
                <p>Happy Shopping!</p>
                <p><em>- The PricePulse Bot</em></p>
            </div>
            <div class="footer">
                <p>You are receiving this email because you set a price alert on PricePulse for this product.</p>
            </div>
        </div>
    </body>
    </html>
    """

    msg = MIMEMultipart('alternative')
    msg['From'] = f"PricePulse Alerts <{GMAIL_USER}>" # You can customize the sender name
    msg['To'] = recipient_email
    msg['Subject'] = subject
    
    # Attach HTML part
    msg.attach(MIMEText(body_html, 'html'))

    try:
        print(f"MAIL_SENDER: Attempting to send email to {recipient_email} from {GMAIL_USER} via smtp.gmail.com:465...")
        # Use SMTP_SSL for port 465
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            # server.set_debuglevel(1) # Uncomment for detailed SMTP logs
            print(f"MAIL_SENDER: Successfully connected to Gmail SMTP server.")
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            print(f"MAIL_SENDER: Logged into Gmail SMTP successfully.")
            server.sendmail(GMAIL_USER, recipient_email, msg.as_string())
            print(f"MAIL_SENDER: Price alert email successfully sent to {recipient_email} for product '{product_name}'.")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"MAIL_SENDER ERROR: SMTP Authentication Error: {e}. Please verify GMAIL_USER and GMAIL_APP_PASSWORD in your .env file. If using Gmail, ensure 'App Passwords' are correctly set up if 2-Step Verification is enabled.")
        return False
    except smtplib.SMTPServerDisconnected:
        print(f"MAIL_SENDER ERROR: SMTP Server Disconnected. This might be a temporary issue or a problem with network configuration.")
        return False
    except smtplib.SMTPException as e:
        print(f"MAIL_SENDER ERROR: An SMTP-related error occurred: {e}")
        return False
    except Exception as e:
        print(f"MAIL_SENDER ERROR: A general error occurred while trying to send email: {e}")
        return False

if __name__ == '__main__':
    # This block allows you to test this file directly.
    # 1. Make sure you have a .env file in this directory (or project root) with:
    #    GMAIL_USER="your_email@gmail.com"
    #    GMAIL_APP_PASSWORD="your_gmail_app_password"
    # 2. Ensure python-dotenv is installed: pip install python-dotenv
    # 3. Run this script from your terminal: python mail_sender.py

    print("MAIL_SENDER: Running direct test mode (__main__)...")
    from dotenv import load_dotenv
    # Assuming .env is in the project root, one level up if mail_sender.py is in a subfolder.
    # For simplicity, let's assume .env is in the same directory for direct testing,
    # or that app.py has already loaded it if called from there.
    # If running mail_sender.py directly from project root where .env is:
    dotenv_path = os.path.join(os.path.dirname(__file__), '.env') # Correctly finds .env if it's in the same dir
    if not os.path.exists(dotenv_path):
        dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env') # If .env is one level up

    # For this direct test, let's assume PricePulse is the root and .env is there
    project_root = os.path.dirname(os.path.abspath(__file__)) # This gives current file's dir
    # If your .env is in project_root, this should work
    load_dotenv(os.path.join(project_root, '.env')) 
                                             
    print(f"MAIL_SENDER_TEST: GMAIL_USER from env: {os.getenv('GMAIL_USER')}")
    
    if os.getenv('GMAIL_USER') and os.getenv('GMAIL_APP_PASSWORD'):
        print("MAIL_SENDER_TEST: Credentials found, attempting to send test email...")
        # IMPORTANT: Change the recipient_email to your actual email address for testing!
        test_recipient = "YOUR_OWN_TEST_EMAIL@example.com"
        print(f"MAIL_SENDER_TEST: Sending test email to {test_recipient}")
        
        success = send_price_alert_email(
            recipient_email=test_recipient, 
            product_name="Awesome Test Product (Direct Test)",
            product_url="https://www.amazon.in/dp/B0TESTTEST/", # Dummy URL
            current_price=99.99,
            target_price=100.00,
            product_image_url="https://upload.wikimedia.org/wikipedia/commons/thumb/3/3f/Placeholder_view_vector.svg/681px-Placeholder_view_vector.svg.png" # Generic placeholder
        )
        if success:
            print("MAIL_SENDER_TEST: Test email sent successfully (check your inbox and spam folder).")
        else:
            print("MAIL_SENDER_TEST: Test email failed to send. Check logs above for errors.")
    else:
        print("MAIL_SENDER_TEST: GMAIL_USER and/or GMAIL_APP_PASSWORD not found in .env file or environment. Cannot send test email.")
        print(f"MAIL_SENDER_TEST: Looked for .env at {os.path.join(project_root, '.env')}")