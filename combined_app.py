# app_combined.py
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import random
import requests
import csv
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Simulated buyer behavior multipliers
BUYER_MULTIPLIERS = {
    "CarMax": 0.93,
    "Carvana": 0.92,
    "CarStory": 0.90,
    "KBB ICO": 0.91
}

BUYER_LINKS = {
    "CarMax": "https://www.carmax.com/sell-my-car",
    "Carvana": "https://www.carvana.com/sell-my-car",
    "CarStory": "https://www.carstory.com/sell",
    "KBB ICO": "https://www.kbb.com/instant-cash-offer"
}

LEAD_FILE = "leads.csv"

# Ensure leads file exists
if not os.path.exists(LEAD_FILE):
    with open(LEAD_FILE, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["timestamp", "name", "email", "phone", "vin", "miles", "offers"])

def mileage_adjustment(base_value, miles):
    average_miles = 12000
    depreciation_per_mile = 0.15
    delta = (miles - average_miles) * depreciation_per_mile
    return max(base_value - delta, 1000)

def decode_vin_nhtsa(vin):
    url = f"https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/{vin}?format=json"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            result = response.json()['Results'][0]
            return {
                "make": result.get("Make"),
                "model": result.get("Model"),
                "year": result.get("ModelYear"),
                "body_class": result.get("BodyClass"),
                "trim": result.get("Trim"),
                "vehicle_type": result.get("VehicleType")
            }
    except Exception as e:
        print(f"VIN decode error: {e}")
    return {}

def mock_send_sms(phone, message):
    print(f"[MOCK SMS to {phone}]: {message}")

@app.route("/api/estimate", methods=["POST"])
def estimate():
    try:
        data = request.get_json(force=True)
        if not data:
            raise ValueError("No JSON data provided.")

        vin = data.get("vin", "").strip()
        if not vin:
            raise ValueError("VIN is required.")

        miles = int(data.get("miles", 0))
        name = data.get("name", "")
        email = data.get("email", "")
        phone = data.get("phone", "")

        vin_details = decode_vin_nhtsa(vin)
        base_retail_value = random.randint(18000, 22000)
        adjusted_value = mileage_adjustment(base_retail_value, miles)

        shuffled_buyers = list(BUYER_MULTIPLIERS.items())
        random.shuffle(shuffled_buyers)

        offers = {
            buyer: round(adjusted_value * multiplier)
            for buyer, multiplier in shuffled_buyers
        }

        if phone:
            message = f"Hey {name or 'there'}, here are your offers:\n" + "\n".join([
                f"Text {i+1} for {buyer}: ${offers[buyer]}"
                for i, buyer in enumerate(offers)
            ])
            mock_send_sms(phone, message)

        with open(LEAD_FILE, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([datetime.utcnow(), name, email, phone, vin, miles, offers])

        return jsonify({
            "vin": vin,
            "mileage": miles,
            "base_value": adjusted_value,
            "offers": offers,
            "details": vin_details,
            "links": BUYER_LINKS
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/leads", methods=["GET"])
def get_leads():
    try:
        with open(LEAD_FILE, mode='r') as file:
            reader = csv.DictReader(file)
            return jsonify(list(reader))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/")
def index():
    return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quotely</title>
</head>
<body>
    <h1>Quotely</h1>
    <form id="valuationForm">
        <label for="name">Name:</label>
        <input type="text" id="name" name="name" required><br><br>

        <label for="email">Email:</label>
        <input type="email" id="email" name="email" required><br><br>

        <label for="phone">Phone:</label>
        <input type="tel" id="phone" name="phone" required><br><br>

        <label for="vin">VIN:</label>
        <input type="text" id="vin" name="vin" required><br><br>

        <label for="miles">Mileage:</label>
        <input type="number" id="miles" name="miles" required><br><br>

        <button type="submit">Get Offers</button>
    </form>

    <div id="results"></div>

    <script>
        document.getElementById('valuationForm').addEventListener('submit', async function(event) {
            event.preventDefault();
            const vin = document.getElementById('vin').value;
            const miles = parseInt(document.getElementById('miles').value);
            const name = document.getElementById('name').value;
            const email = document.getElementById('email').value;
            const phone = document.getElementById('phone').value;

            const response = await fetch('/api/estimate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ vin, miles, name, email, phone })
            });

            const data = await response.json();
            const resultsDiv = document.getElementById('results');

            if (data.error) {
                resultsDiv.innerHTML = `<p style='color:red;'>Error: ${data.error}</p>`;
                return;
            }

            resultsDiv.innerHTML = `<h3>Offers for VIN: ${data.vin}</h3>`;
            resultsDiv.innerHTML += `<p>Mileage: ${data.mileage}</p>`;
            resultsDiv.innerHTML += `<p>Base Value: $${data.base_value}</p>`;

            if (data.details) {
                resultsDiv.innerHTML += `<h4>Vehicle Details</h4>`;
                resultsDiv.innerHTML += `<p>${data.details.year} ${data.details.make} ${data.details.model} ${data.details.trim}</p>`;
            }

            resultsDiv.innerHTML += '<ul>';
            let i = 1;
            for (const [buyer, offer] of Object.entries(data.offers)) {
                const link = data.links[buyer];
                resultsDiv.innerHTML += `<li><strong>${buyer}</strong>: $${offer} — <a href="${link}" target="_blank">Go to site</a> (Text ${i})</li>`;
                i++;
            }
            resultsDiv.innerHTML += '</ul>';
        });
    </script>
</body>
</html>
''')

# Basic test case
def test_estimate():
    sample_data = {
        "vin": "1HGCM82633A004352",
        "miles": 45000,
        "name": "Test User",
        "email": "test@example.com",
        "phone": "1234567890"
    }
    with app.test_client() as client:
        response = client.post("/api/estimate", json=sample_data)
        assert response.status_code == 200, "Expected 200 OK"
        json_data = response.get_json()
        assert "offers" in json_data, "Offers key missing in response"
        assert isinstance(json_data["offers"], dict), "Offers should be a dictionary"
        assert "details" in json_data, "VIN details missing in response"
        print("Test passed.")

if __name__ == "__main__":
    test_estimate()
    app.run(host="0.0.0.0", port=10000)
