import time
import scrapy

from scrapy.http import Response
from selenium import webdriver
from scrapy.http import HtmlResponse
from scraping_vacancies.items import VacancyItem
from selenium.common import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class DouSpider(scrapy.Spider):
    name = "dou"
    allowed_domains = ["jobs.dou.ua"]
    start_urls = ["https://jobs.dou.ua/vacancies/?category=Python"]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.experience = ["0-1", "1-3", "3-5", "5plus"]
        self.technologies = self.load_technologies("technologies.txt")

        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        self.driver = webdriver.Chrome(options=options)

    def load_technologies(self, filename: str) -> list[str]:
        with open(filename, "r") as file:
            return [line.strip() for line in file if line.strip()]

    def start_requests(self) -> scrapy.Request:
        base_url = self.start_urls[0] + "&exp={}"
        for exp in self.experience:
            url = base_url.format(exp)
            yield scrapy.Request(
                url=url,
                callback=self.parse_vacancies,
                meta={"experience": exp}
            )

    def parse_vacancies(self, response: Response) -> scrapy.Request:
        self.driver.get(response.url)

        while True:
            try:
                more_button = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, ".more-btn a")
                    )
                )
                if "display:none" in more_button.get_attribute("style"):
                    break
                else:
                    more_button.click()
                    time.sleep(1)
            except TimeoutException:
                self.logger.info("No more 'more' button or timeout occurred.")
                break
            except WebDriverException as e:
                self.logger.error(f"WebDriver error: {e}")
                break

        page_source = self.driver.page_source
        selenium_response = HtmlResponse(
            url=self.driver.current_url, body=page_source, encoding="utf-8"
        )
        vacancy_links = selenium_response.css("a.vt::attr(href)").getall()

        for link in vacancy_links:
            vacancy_url = response.urljoin(link)
            yield scrapy.Request(
                vacancy_url,
                callback=self.parse_vacancy_details,
                meta={"experience": response.meta["experience"]}
            )

    def parse_vacancy_details(self, response: Response) -> VacancyItem:
        item = VacancyItem()
        item["company"] = response.css(".l-n a::text").get()
        item["title"] = response.css(".l-vacancy > h1::text").get()
        item["date"] = response.css(".date::text").get().strip()
        item["experience"] = response.meta["experience"]
        item["location"] = response.css(".sh-info > span::text").get().strip()
        item["salary"] = self.get_salary(response)
        item["description"] = self.get_description(response)
        item["technologies"] = self.get_technologies(
            item["description"].lower()
        ) or "Unknown"

        yield item

    def get_salary(self, response: Response) -> str:
        salary = response.css("span.salary::text").get()
        if salary:
            return salary.replace("\xa0", " ")

        return "Unknown"

    def get_description(self, response: Response) -> str:
        description = response.css(
            ".b-typo.vacancy-section"
        ).xpath(".//text()").getall()
        return (
            "".join(description)
            .replace("\xa0", " ")
            .replace("\u200b", "")
            .replace("\u202f", "")
            .strip()
        )

    def get_technologies(self, description: str) -> list[str]:
        return [tech for tech in self.technologies if tech in description]

    def close(self, spider, reason: str) -> None:
        self.driver.quit()
