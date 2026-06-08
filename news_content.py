import os

import requests


def add_news_content(config, category="general"):
    for item in config.get("content", []):
        if item["type"] == "news":
            return "News content already exists."

    config["content"].append(
        {
            "type": "news",
            "title": "News",
            "category": category,
            "country": "us",
            "max_articles": 5,
        }
    )

    return f"Added news content: {category}"


def fetch_top_headlines(category="general", country="us", max_articles=5):
    api_key = os.getenv("NEWS_API_KEY")

    if not api_key:
        raise ValueError("Missing NEWS_API_KEY in .env")

    url = "https://newsapi.org/v2/top-headlines"

    params = {
        "apiKey": api_key,
        "country": country,
        "category": category,
        "pageSize": max_articles,
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json()

    return data.get("articles", [])


def get_news_html(item):
    articles = fetch_top_headlines(
        category=item.get("category", "technology"),
        country=item.get("country", "us"),
        max_articles=item.get("max_articles", 5),
    )

    html = f"""
    <div style="border:1px solid #ddd; border-radius:12px; padding:18px; margin-bottom:20px; font-family:Arial, sans-serif;">
        <h2 style="margin-top:0; margin-bottom:12px; font-size:18px;">
            📰 {item["title"]}
        </h2>

        <h3 style="font-size:15px; margin-bottom:8px;">
            Top {item.get("category", "technology").title()} Headlines
        </h3>
    """

    if not articles:
        html += "<p style='font-size:13px;'>No headlines found.</p>"
    else:
        html += "<ul style='font-size:13px;'>"

        for article in articles:
            title = article.get("title", "Untitled")
            source = article.get("source", {}).get("name", "Unknown Source")
            url = article.get("url", "")

            if url:
                html += f"""
                <li>
                    <a href="{url}" style="color:#1a73e8; text-decoration:none;">
                        {title}
                    </a>
                    <span style="color:#666;"> — {source}</span>
                </li>
                """
            else:
                html += f"""
                <li>
                    {title}
                    <span style="color:#666;"> — {source}</span>
                </li>
                """

        html += "</ul>"

    html += "</div>"

    return html