from selenium.common import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import undetected_chromedriver as uc
from selenium.webdriver.chrome.service import Service as ChromeService
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
import urllib.request
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as cond
import wisecreator.wisecreate

import wisecreator.wisecreate

domain = os.environ['HIDE_DOMAIN']
timeout = os.environ['TIMEOUT']


def get_meta_data(driver):
    driver.get(domain)
    WebDriverWait(driver, timeout).until(
        cond.visibility_of_element_located((By.CLASS_NAME, "cookie-disclaimer__cta"))).click()
    start_button = WebDriverWait(driver, timeout).until(
        cond.visibility_of_element_located((By.CSS_SELECTOR, "[data-test-id='view-daily-blink-button']")))
    article = driver.find_element(By.XPATH, "//article")
    title = article.find_element(By.TAG_NAME, "h2").get_attribute('innerHTML').strip()
    author = article.find_element(By.XPATH, "//div[3]/div/p").get_attribute('innerHTML').strip()
    subtitle = article.find_element(By.XPATH, "//div[3]/div/div[1]").get_attribute('innerHTML').strip()
    img_url = article.find_element(By.TAG_NAME, "img").get_attribute('src')
    description = driver.find_element(By.CSS_SELECTOR, "[data-test-id='about-section']") \
        .find_element(By.XPATH, "//p/p").get_attribute('innerHTML').strip()

    return title, author, subtitle, description, img_url, start_button


def get_article(driver, start_button):
    next_button = start_button
    html_article = ""
    chapter_headline_locator = (By.CLASS_NAME, "reader-content__headline")
    chapter_headline = "XXXX"
    audio_link_locator = (By.CSS_SELECTOR, "[data-test-id='readerAudio']")
    audio_link_attribute = "audio-url"
    audio_link = "XXXX"
    audio_links = {}
    chapter_counter = 0
    while next_button:
        next_button.click()
        wait_for_element_text_change(driver, chapter_headline_locator, chapter_headline)
        wait_for_element_attribute_change(driver, audio_link_locator, audio_link_attribute, audio_link)
        next_button = get_next_button(driver)
        audio_link = driver.find_element(*audio_link_locator).get_attribute(audio_link_attribute)
        chapter_headline = driver.find_element(*chapter_headline_locator).get_attribute('innerHTML')
        chapter = driver.find_element(By.CLASS_NAME, "reader-content__text").get_attribute('innerHTML')
        html_article += f'<h1>{chapter_headline}</h1>'
        html_article += chapter
        audio_links[chapter_counter] = audio_link
        chapter_counter += 1
    return html_article, audio_links


def wait_for_element_attribute_change(driver, locator, attribute, current_state):
    return WebDriverWait(driver, timeout).until(
        cond.all_of(
            cond.presence_of_element_located(locator),
            cond.none_of(cond.text_to_be_present_in_element_attribute(locator, attribute, current_state))))


def wait_for_element_text_change(driver, locator, current_state):
    return WebDriverWait(driver, timeout).until(
        cond.all_of(
            cond.presence_of_element_located(locator),
            cond.none_of(cond.text_to_be_present_in_element(locator, current_state))))


def wait_for_reader_page(driver):
    WebDriverWait(driver, timeout).until(cond.visibility_of_element_located((By.CLASS_NAME, "reader-content__text")))


def get_next_button(driver):
    button_locator = (By.CSS_SELECTOR, "[data-test-id='nextChapter']")
    try:
        WebDriverWait(driver, timeout).until(cond.element_to_be_clickable(button_locator))
        return driver.find_element(*button_locator)
    except TimeoutException:
        return None


def write_audio_file(opener, audio_links, directory, title):
    for chapterNo, audio_link in audio_links.items():
        opener.retrieve(audio_link, os.path.join(directory, f'{title}-{chapterNo}.m4a'))


def create_webdriver():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    driver = uc.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)

    return driver


def run():
    print('Fetching content...', end='')
    driver = create_webdriver()
    title, author, subtitle, description, img_url, start_button = get_meta_data(driver)
    html_article, audio_links = get_article(driver, start_button)
    date = datetime.now().strftime('%Y%m%d')
    legal_author = re.sub('[^A-Za-z0-9]+', '_', author.replace('by ', ''))
    legal_title = re.sub('[^A-Za-z0-9]+', '_', title)
    directory = 'blinks/' + f'{date[:4]}' + '/' + legal_title
    if not os.path.exists(directory):
        os.makedirs(directory)
    opener = urllib.request.URLopener()
    opener.addheader('User-Agent', driver.execute_script("return navigator.userAgent;"))
    image_name = os.path.join(directory, str(img_url).split('/')[-1])
    opener.retrieve(img_url, image_name)
    output_html = f'<h1>{title}</h1><h2>{author}</h2><h3>{subtitle}</h3><p>{description}</p>{html_article}'

    commit_message = f'{title} by {author}\n'
    html_file_name = os.path.join(directory, f'{date}-{legal_title}-{legal_author}.html')

    print('Building output...', end='')
    write_to_file(html_file_name, output_html, 'w')
    language_file_name = wisecreator.wisecreate.main(f'{html_file_name}', image_name)

    os.remove(html_file_name)
    os.remove(image_name)
    write_audio_file(opener, audio_links, directory, legal_title)
    write_to_file("commit_message", commit_message, 'w')


def write_to_file(file_name, output, option):
    file = open(file_name, option)
    file.write(output)
    file.close()


if __name__ == '__main__':
    run()
