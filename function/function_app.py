import logging
import azure.functions as func
import requests
from lxml import html
from bs4 import BeautifulSoup
import re
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = func.FunctionApp()


# Function to extract information from the website
def extract_cat_info(soup, keywords, max_age_months_total):
    cats = soup.find_all("div", class_="info-card-grid__item")

    for cat in cats:
        name = (
            cat.find("div", class_="info-card__title")
            .get_text(strip=True)
            .split("|")[-1]
            .strip()
        )

        animal_link_element = cat.find("a", class_="info-card")
        if animal_link_element:
            animal_link = animal_link_element.get("href")

        info_list = cat.find("ul", class_="info-card__list")
        if info_list:
            breed = age = sex = color = id = None
            for li in info_list.find_all("li", class_="info-card__item"):
                span = li.find("span")

                if span:
                    span_text = span.get_text(strip=True)
                    label, value = map(str.strip, span_text.split(":", 1))

                    if label == "Breed":
                        breed = value
                    elif label == "Age":
                        age = value
                    elif label == "Sex":
                        sex = value
                    elif label == "Colour":
                        color = value
                    elif label == "Animal ID":
                        id = value
            logging.info(f"Name: {name}")
            logging.info(f"Breed: {breed}")
            logging.info(f"Age: {age}")
            logging.info(f"Sex: {sex}")
            logging.info(f"Color: {color}")
            logging.info(f"ID: {id}")
            logging.info(f"Link: {animal_link}")

            age_months = parse_age(age)
            if (
                age_months is not None
                and age_months <= max_age_months_total
                and "female" in sex.lower()
            ):
                send_notification(name, breed, age, sex, color, id, animal_link)

            matching_keywords = [
                keyword for keyword in keywords if keyword.lower() in color.lower()
            ]
            if matching_keywords and "female" in sex.lower():
                send_notification(name, breed, age, sex, color, id, animal_link)


# Azure timer trigger function
@app.function_name(name="myTimer")
@app.schedule(
    schedule="0 */15 * * * *",
    arg_name="myTimer",
    run_on_startup=True,
    use_monitor=False,
)
def timer_trigger(myTimer: func.TimerRequest) -> None:
    if myTimer.past_due:
        logging.info("The timer is past due!")

    base_url = "https://ottawahumane.ca/adopt/cats-for-adoption/"

    # Define the maximum age in months (1 year and 5 months)
    max_age_years = 1
    max_age_months = 5
    max_age_months_total = (max_age_years * 12) + max_age_months

    keywords = [
        "calico",
        "siamese",
        "lynx point",
        "tortie",
        "tortoiseshell",
        "ragdoll",
        "point",
        "black and white",
        "white and black",
        "orange",
    ]

    current_page = base_url

    while current_page:
        response = requests.get(current_page)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            extract_cat_info(soup, keywords, max_age_months_total)

            next_page_element = soup.find("a", class_="next pagination__link")
            if next_page_element:
                current_page = next_page_element.get("href")
            else:
                current_page = None
        else:
            logging.error(
                f"Failed to retrieve the web page. Status code: {response.status_code}"
            )

    logging.info("Python timer trigger function executed.")


def send_notification(name, breed, age, sex, color, id, link):
    # User email and password
    gmail_user = "enter user email here"
    gmail_password = "enter password here"

    from_email = gmail_user
    to_email = gmail_user
    subject = "New cat available for adoption!"
    body = f"Name: {name}\nBreed: {breed}\nAge: {age}\nSex: {sex}\nColor: {color}\nID: {id}\nLink: {link}"

    message = f"Subject: {subject}\nFrom: {from_email}\nTo: {to_email}\n\n{body}"

    try:
        smtp_server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        smtp_server.ehlo()
        smtp_server.login(gmail_user, gmail_password)
        smtp_server.sendmail(from_email, to_email, message)
        smtp_server.close()
        logging.info("Email sent!")
    except Exception as e:
        logging.info("Something went wrong...")
        logging.info(e)


def parse_age(age):
    age_parts = re.findall(r"\d+", age)
    if len(age_parts) == 2:
        years, months = map(int, age_parts)
    elif len(age_parts) == 1:
        years = int(age_parts[0])
        months = 0
    else:
        return None

    return (years * 12) + months
