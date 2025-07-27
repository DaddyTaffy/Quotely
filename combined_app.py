# app_combined.py
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import random
import requests

app = Flask(__name__)
CORS(app)

# Simulated buyer behavior multipliers and URLs
BUYER_DATA = {
    "CarMax": {
        "multiplier": 0.93,
        "url": "https://www.carmax.com/sell-my-car"
    },
    "Carvana": {
        "multiplier": 0.92,
        "url": "https://www.carvana.com/sell-my-car"
    },
    "CarStory": {
        "multiplier": 0.90,
        "url": "https://www.carstory.com/sell"
    },
    "KBB ICO": {
        "multiplier": 0.91,
        "url": "https://www.kbb.com/instant-cash-offer"
    }
}

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
        phone = data.get("phone", "")
        email = data.get("email", "")

        vin_details = decode_vin_nhtsa(vin)

        base_retail_value = random.randint(18000, 22000)
        adjusted_value = mileage_adjustment(base_retail_value, miles)

        offers = []
        for idx, (buyer, info) in enumerate(BUYER_DATA.items(), start=1):
            offer = round(adjusted_value * info["multiplier"])
            redirect_url = f"{info['url']}?name={name}&phone={phone}&email={email}&vin={vin}&miles={miles}"
            offers.append({
                "id": idx,
                "buyer": buyer,
                "offer": offer,
                "url": redirect_url
            })

        return jsonify({
            "vin": vin,
            "mileage": miles,
            "base_value": round(adjusted_value, 2),
            "offers": offers,
            "details": vin_details
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

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

        <label for="phone">Phone:</label>
        <input type="text" id="phone" name="phone" required><br><br>

        <label for="email">Email:</label>
        <input type="email" id="email" name="email" required><br><br>

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
            const name = document.getElementById('name').value;
            const phone = document.getElementById('phone').value;
            const email = document.getElementById('email').value;
            const vin = document.getElementById('vin').value;
            const miles = parseInt(document.getElementById('miles').value);

            const response = await fetch('/api/estimate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, phone, email, vin, miles })
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
            for (const offerObj of data.offers) {
                resultsDiv.innerHTML += `<li><strong>${offerObj.buyer}</strong>: $${offerObj.offer} — <a href="${offerObj.url}" target="_blank">Text ${offerObj.id}</a></li>`;
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
        "name": "John Doe",
        "phone": "5551234567",
        "email": "john@example.com"
    }
    with app.test_client() as client:
        response = client.post("/api/estimate", json=sample_data)
        assert response.status_code == 200, "Expected 200 OK"
        json_data = response.get_json()
        assert "offers" in json_data, "Offers key missing in response"
        assert isinstance(json_data["offers"], list), "Offers should be a list"
        assert "details" in json_data, "VIN details missing in response"
        print("Test passed.")

if __name__ == "__main__":
    test_estimate()
    app.run(host="0.0.0.0", port=10000)
