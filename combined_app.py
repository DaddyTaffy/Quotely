# app_combined.py
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import random
import requests

app = Flask(__name__)
CORS(app)

BUYER_MULTIPLIERS = {
    "CarMax": 0.78,
    "Carvana": 0.76,
    "CarStory": 0.75,
    "KBB ICO": 0.74
}

BUYER_LINKS = {
    "CarMax": "https://www.carmax.com/sell-my-car",
    "Carvana": "https://www.carvana.com/sell-my-car",
    "CarStory": "https://www.carstory.com/sell",
    "KBB ICO": "https://www.kbb.com/instant-cash-offer"
}

MARKETPLACE_TEMPLATE = """Selling my {{year}} {{make}} {{model}} {{trim}}! Runs great with only {{mileage}} miles. Clean title. VIN: {{vin}}. Asking price: ${{price}}. Reach out if interested!"""

ZIP_MODIFIERS = [0.96, 0.98, 1.00, 1.02, 1.04]  # slight regional pricing variations

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
        email = data.get("email", "")
        phone = data.get("phone", "")

        zip_modifier = random.choice(ZIP_MODIFIERS)

        vin_details = decode_vin_nhtsa(vin)

        base_retail_value = random.randint(18000, 22000)
        adjusted_value = mileage_adjustment(base_retail_value, miles)
        probable_value = round(adjusted_value * zip_modifier)

        offers = {
            buyer: round(probable_value * multiplier)
            for buyer, multiplier in BUYER_MULTIPLIERS.items()
        }

        marketplace_post = ""
        if vin_details:
            marketplace_post = MARKETPLACE_TEMPLATE.replace("{{year}}", vin_details.get("year", "")).replace("{{make}}", vin_details.get("make", "")).replace("{{model}}", vin_details.get("model", "")).replace("{{trim}}", vin_details.get("trim", "")).replace("{{mileage}}", str(miles)).replace("{{vin}}", vin).replace("{{price}}", str(probable_value))

        return jsonify({
            "vin": vin,
            "mileage": miles,
            "base_value": adjusted_value,
            "probable_value": probable_value,
            "offers": offers,
            "details": vin_details,
            "marketplace_post": marketplace_post
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
            resultsDiv.innerHTML += `<p><strong>Probable Market Value:</strong> $${data.probable_value}</p>`;

            if (data.details) {
                resultsDiv.innerHTML += `<h4>Vehicle Details</h4>`;
                resultsDiv.innerHTML += `<p>${data.details.year} ${data.details.make} ${data.details.model} ${data.details.trim}</p>`;
            }

            resultsDiv.innerHTML += '<h4>Select where to send your info:</h4><ul>';
            let counter = 1;
            for (const [buyer, offer] of Object.entries(data.offers)) {
                const buyerUrl = {
                    "CarMax": "https://www.carmax.com/sell-my-car",
                    "Carvana": "https://www.carvana.com/sell-my-car",
                    "CarStory": "https://www.carstory.com/sell",
                    "KBB ICO": "https://www.kbb.com/instant-cash-offer"
                }[buyer];
                const redirectLink = `${buyerUrl}?name=${encodeURIComponent(name)}&email=${encodeURIComponent(email)}&phone=${encodeURIComponent(phone)}&vin=${vin}&miles=${miles}`;
                resultsDiv.innerHTML += `<li><strong>${buyer}</strong>: $${offer} - <a href="${redirectLink}" target="_blank">Send Info</a></li>`;
                counter++;
            }
            resultsDiv.innerHTML += '</ul>';

            if (data.marketplace_post) {
                resultsDiv.innerHTML += `<h4>Want to sell it yourself?</h4><textarea rows="6" cols="60">${data.marketplace_post}</textarea>`;
            }
        });
    </script>
</body>
</html>
''')


# Basic test case
def test_estimate():
    sample_data = {
        "vin": "1HGCM82633A004352",
        "miles": 45000
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
