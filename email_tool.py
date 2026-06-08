import argparse
import json
import os
import smtplib
from pathlib import Path
from email.message import EmailMessage
import tempfile
from email.mime.image import MIMEImage
import matplotlib.pyplot as plt

import requests
from dotenv import load_dotenv

load_dotenv()

CONFIG_PATH = Path.home() / ".email_tool_config.json"


def load_config():
    if not CONFIG_PATH.exists():
        return {"content": []}

    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def get_current_location():
    url = "https://ipapi.co/json/"
    response = requests.get(url)
    response.raise_for_status()

    data = response.json()

    return {
        "latitude": data["latitude"],
        "longitude": data["longitude"],
        "location_name": f"{data.get('city', 'Current Location')}, {data.get('region', '')}".strip(
            ", "
        ),
    }


def add_weather(latitude=None, longitude=None, location_name=None):
    config = load_config()

    if latitude is None or longitude is None:
        location = get_current_location()
        latitude = location["latitude"]
        longitude = location["longitude"]

        if location_name is None:
            location_name = location["location_name"]

    if location_name is None:
        location_name = "Custom Location"

    config["content"].append(
        {
            "type": "weather",
            "latitude": latitude,
            "longitude": longitude,
            "location_name": location_name,
        }
    )

    save_config(config)
    print(f"Added weather for {location_name}")


def list_content():
    config = load_config()
    content = config.get("content", [])

    if not content:
        print("No email content has been added yet.")
        return

    print("Email content:")

    for index, item in enumerate(content, start=1):
        if item["type"] == "weather":
            print(
                f"{index}. Weather ({item['location_name']})"
            )

        elif item["type"] == "duedate":
            print(
                f"{index}. {item['title']}"
            )

        elif item["type"] == "news":
            print(
                f"{index}. {item['title']} "
                f"({item.get('category', 'general')})"
            )

        else:
            print(f"{index}. Unknown content type: {item}")


def delete_content(index):
    config = load_config()
    content = config.get("content", [])

    if index < 1 or index > len(content):
        print(f"Invalid content number: {index}")
        return

    removed = content.pop(index - 1)
    config["content"] = content
    save_config(config)

    if removed["type"] == "weather":
        print(f"Deleted weather content for {removed['location_name']}")
    else:
        print("Deleted content")


def get_weather_html(item):
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": item["latitude"],
        "longitude": item["longitude"],
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m",
        "daily": "temperature_2m_max,temperature_2m_min",
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "forecast_days": 1,
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json()

    current = data["current"]
    daily = data["daily"]

    current_temp = current["temperature_2m"]
    humidity = current["relative_humidity_2m"]
    wind_speed = current["wind_speed_10m"]
    high_temp = daily["temperature_2m_max"][0]
    low_temp = daily["temperature_2m_min"][0]

    return f"""
    <div style="border:1px solid #ddd; border-radius:12px; padding:18px; margin-bottom:20px; font-family:Arial, sans-serif;">
        <h2 style="margin-top:0; margin-bottom:12px; font-size:22px;">
            Weather for {item["location_name"]}
        </h2>

        <div style="font-size:42px; font-weight:bold; margin-bottom:10px;">
            {current_temp}°F
        </div>

        <div style="font-size:16px; margin-bottom:14px;">
            High: {high_temp}°F &nbsp; | &nbsp; Low: {low_temp}°F
        </div>

        <table style="font-size:15px;">
            <tr>
                <td style="padding-right:20px;"><strong>Humidity</strong></td>
                <td>{humidity}%</td>
            </tr>
            <tr>
                <td style="padding-right:20px;"><strong>Wind Speed</strong></td>
                <td>{wind_speed} mph</td>
            </tr>
        </table>
    </div>
    """


def build_email_html():
    config = load_config()
    sections = []

    for item in config.get("content", []):
        if item["type"] == "weather":
            sections.append(get_weather_html(item))

    content_html = "\n".join(sections)

    return f"""
    <html>
        <body style="font-family:Arial, sans-serif; padding:20px; color:#222;">
            {content_html}
        </body>
    </html>
    """


def build_email_images():
    config = load_config()

    image_files = []

    for item in config.get("content", []):
        if item["type"] == "weather":
            image_files.append(create_weather_snapshot(item))

    return image_files


def create_weather_snapshot(item):
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": item["latitude"],
        "longitude": item["longitude"],
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m",
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json()
    current = data["current"]

    temp = current["temperature_2m"]
    humidity = current["relative_humidity_2m"]
    wind = current["wind_speed_10m"]

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.axis("off")

    ax.text(
        0.05,
        0.80,
        item["location_name"],
        fontsize=22,
        weight="bold",
    )

    ax.text(
        0.05,
        0.50,
        f"{temp}°F",
        fontsize=42,
    )

    ax.text(
        0.05,
        0.25,
        f"Humidity: {humidity}%\nWind: {wind} mph",
        fontsize=16,
    )

    temp_file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".png",
    )

    plt.savefig(temp_file.name, bbox_inches="tight")
    plt.close()

    return temp_file.name


def send_email():
    sender = os.getenv("EMAIL_ADDRESS")
    password = os.getenv("EMAIL_APP_PASSWORD")
    recipient = os.getenv("RECIPIENT_EMAIL")

    html_body = build_email_html()

    msg = EmailMessage()
    msg["Subject"] = "Your Email Tool Update"
    msg["From"] = sender
    msg["To"] = recipient

    msg.set_content(
        "This email contains HTML content. Please view it in an HTML-compatible email client."
    )
    msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender, password)
        smtp.send_message(msg)

    print("Email sent")


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("send")
    subparsers.add_parser("content")

    delete_parser = subparsers.add_parser("delete-content")
    delete_parser.add_argument("index", type=int)

    weather_parser = subparsers.add_parser("add-weather")
    weather_parser.add_argument("--lat", type=float)
    weather_parser.add_argument("--lon", type=float)
    weather_parser.add_argument("--name")

    args = parser.parse_args()

    if args.command == "send":
        send_email()
    elif args.command == "content":
        list_content()
    elif args.command == "delete-content":
        delete_content(args.index)
    elif args.command == "add-weather":
        add_weather(args.lat, args.lon, args.name)


if __name__ == "__main__":
    main()
