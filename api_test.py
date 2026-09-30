import os
import requests


API_KEY = os.getenv("FORTNITE_API_KEY")

if not API_KEY:
    print("❌ FORTNITE_API_KEY non trovata!")
    exit(1)


url = "https://fortnite-api.com/v2/shop"

headers = {
    "Authorization": API_KEY
}


print("🔄 Connessione a Fortnite API...")


response = requests.get(
    url,
    headers=headers,
    timeout=20
)


print("Codice risposta:", response.status_code)


if response.status_code == 200:
    data = response.json()

    print("✅ Fortnite API funziona!")

    if "data" in data:
        print("✅ Dati dello Shop ricevuti!")

        shop_data = data["data"]

        if isinstance(shop_data, dict):
            print("Chiavi principali ricevute:", list(shop_data.keys())[:10])

    else:
        print("⚠️ Risposta ricevuta, ma non trovo 'data'.")

else:
    print("❌ Errore API")
    print(response.text[:500])
    exit(1)
