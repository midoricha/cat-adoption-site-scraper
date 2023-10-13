import time
import requests
from lxml import html
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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
]


def scrape_all_pages(driver):
    next_page_button = driver.find_element_by_xpath(
        '//*[@id="main"]/div/div[2]/ul/li[6]/a'
    )

    while next_page_button:
        cats = driver.find_elements_by_xpath('//*[@id="post-2038"]/div[2]')
        for cat in cats:
            name = cat.xpath('//*[@id="post-2038"]/div[2]/div[1]/a/div[2]/div/text()')
            breed = cat.xpath(
                '//*[@id="post-2038"]/div[2]/div[1]/a/div[2]/ul/li[1]/text()'
            )
            age = cat.xpath('//*[@id="post-2038"]/div[2]/div[1]/a/div[2]/ul/li[2]')
            sex = cat.xpath(
                '//*[@id="post-2038"]/div[2]/div[1]/a/div[2]/ul/li[3]/text()'
            )
            color = cat.xpath(
                '//*[@id="post-2038"]/div[2]/div[1]/a/div[2]/ul/li[4]/text()'
            )
            id = cat.xpath(
                '//*[@id="post-2038"]/div[2]/div[1]/a/div[2]/ul/li[5]/text()'
            )
            link = cat.xpath('//*[@id="post-2038"]/div[2]/div[1]/a/@href')

        # check age and sex
        age_months = parse_age(age)
        if (
            age_months is not None
            and age_months <= max_age_months_total
            and sex == "female"
        ):
            send_notification(name, breed, age, sex, color, id, link)

        # check color
        matching_keywords = [
            keyword for keyword in keywords if keyword.lower() in color.lower()
        ]
        if matching_keywords:
            send_notification(name, breed, age, sex, color, id, link)

        next_page_button.click()
        WebDriverWait(driver, 10).until(EC.staleness_of(next_page_button))
        scrape_all_pages(driver)


def send_notification(name, breed, age, sex, color, id, link):
    gmail_user = "***REMOVED***"
    gmail_password = "***REMOVED***"

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
        print("Email sent!")
    except Exception as e:
        print("Something went wrong...")
        print(e)


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


driver = webdriver.Chrome()
driver.get(base_url)

while True:
    try:
        scrape_all_pages(driver)
    except Exception as e:
        print("Something went wrong...")
        print(e)
        continue
    finally:
        time.sleep(3600)  # Check every hour
