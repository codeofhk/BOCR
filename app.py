import os
from dotenv import load_dotenv
import json
import logging
from flask import Flask, request, jsonify
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
import hmac
import hashlib

app = Flask(__name__)
load_dotenv() #load the env variable

# 1. Setup Gemini (The Brain)
genai.configure(api_key=os.getenv("GEN_AI"))
model = genai.GenerativeModel('gemini-2.5-flash')

# 2. Setup Google Sheets (The Database)
# scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
# creds = ServiceAccountCredentials.from_json_keyfile_name('path/to/credentials.json', scope)
# client = gspread.authorize(creds)
# sheet = client.open("My Client Data").sheet1

# 3. WhatsApp Helper Functions
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")


APP_SECRET = os.getenv("APP_SECRET") # Get this from Meta App Dashboard -> Basic Settings

def verify_signature(request):
    signature = request.headers.get('X-Hub-Signature-256')
    if not signature:
        return False
    
    # Clean the signature (remove 'sha256=')
    signature = signature.replace("sha256=", "")
    
    # Calculate your own signature
    expected_signature = hmac.new(
        key=APP_SECRET.encode(), 
        msg=request.data, 
        digestmod=hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)

def send_whatsapp_message(to_number, text_body):
    url = f"https://graph.facebook.com/v22.0/1029286163594215/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": text_body}
    }
    response = requests.post(url, headers=headers, json=data)
    print(response.status_code)
    print(response.json()) # This will tell you EXACTLY what Meta is complaining about


def download_whatsapp_image(image_id):
    # Step A: Get the Media URL
    url = f"https://graph.facebook.com/v22.0/{image_id}"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Error fetching media URL: {response.text}")
        return None
        
    image_url = response.json().get('url')

    # Step B: Download the actual image bytes
    # You must send the Token again to the new URL
    image_response = requests.get(image_url, headers=headers)
    
    if image_response.status_code == 200:
        return {
            "mime_type": "image/jpeg", # WhatsApp usually sends JPEGs
            "data": image_response.content
        }
    return None

@app.route("/")
def home():
    return "hello"

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    # VERIFICATION STEP (Meta will ping this URL to check if you are alive)
    if request.method == 'GET':
        if request.args.get("hub.verify_token") == os.getenv("WEB_HOOK_TOKEN"):
            return request.args.get("hub.challenge")
        return "Verification failed", 403

    # HANDLING MESSAGES
    if request.method == 'POST':

        if not verify_signature(request):
            return "Signature Mismatch", 403
        

        data = request.json
        # Extract the message details safely
        try:
            entry = data['entry'][0]['changes'][0]['value']
            messages = entry.get('messages', [])
            
            if messages:
                msg = messages[0]
                sender_id = msg['from']
                
                # CHECK IF IMAGE IS PRESENT
                if msg['type'] == 'image':
                    image_id = msg['image']['id']
                    
                    # TODO: 1. Download image using image_id (Need a separate function for this)
                    # TODO: 2. Send image to Gemini Flash
                    # prompt = "Extract Date, GSTIN, Total Amount as JSON."
                    # response = model.generate_content([prompt, downloaded_image])
                    
                    # TODO: 3. Parse JSON and save to GSheet
                    # sheet.append_row([date, gstin, amount])

                    # 1. DOWNLOAD
                    downloaded_image = download_whatsapp_image(image_id)
                    
                    if downloaded_image:
                        # 2. GEMINI PROCESSING
                        prompt = """
                        Extract the following from this bill image as a JSON object:
                        {
                        "Date": "DD/MM/YYYY",
                        "GSTIN": "string",
                        "Total_Amount": number
                        }
                        Return ONLY the raw JSON. No markdown backticks.
                        """
                        
                        try:
                            # Pass the prompt and the image bytes directly
                            gen_response = model.generate_content([prompt, downloaded_image])
                            
                            # Clean text in case Gemini adds markdown ```json blocks
                            raw_text = gen_response.text.replace('```json', '').replace('```', '').strip()
                            bill_data = json.loads(raw_text)
                            
                            print(bill_data)
                            # 3. SAVE TO GOOGLE SHEETS
                            # sheet.append_row([Date, GSTIN, Amount])
                            # sheet.append_row([
                            #     bill_data.get("Date"), 
                            #     bill_data.get("GSTIN"), 
                            #     bill_data.get("Total_Amount")
                            # ])
                            
                            # 4. REPLY
                            success_msg = f"✅ Bill Processed!\nAmount: ₹{bill_data.get('Total_Amount')}\nSaved to Sheet."
                            send_whatsapp_message(sender_id, success_msg)

                        except Exception as e:
                            print(f"Gemini/GSheet Error: {e}")
                            send_whatsapp_message(sender_id, "❌ Error reading bill. Please try a clearer photo.")

                
                else:
                    send_whatsapp_message(sender_id, "Please send a photo of the bill.")
                    
        except Exception as e:
            logging.error(f"Error: {e}")
            
        return "OK", 200

if __name__ == '__main__':
    
   # print(send_whatsapp_message("916379190592", "what are even doing bro"))
    port = int(os.environ.get("PORT",5001))
    app.run(host="0.0.0.0",port=port)