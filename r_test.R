library(rvest)
library(httr)
library(magrittr)
tmp_url <- paste0("https://www.flightradar24.com/data/flights/lo135")
page <- httr::GET(tmp_url)
page
page$url

xpath = '//*[@id="btn-playback-3adec76e"]'
content(page) %>%
  html_element('//*[@id="tbl-datatable"]') %>%
  html_attr("href")

library(rvest)

# Example: Reading from a URL
url <- "https://www.flightradar24.com/data/flights/lo135"
page <- read_html(url)
page

rows <- page %>%
  html_elements("tr.live.data-row")

# Extract playback hrefs from each row
playback_hrefs <- rows %>%
  html_element("a.btn-playback") %>%
  html_attr("href")

# Print the result
print(playback_hrefs)

install.packages("RSelenium")
library(RSelenium)

# Launch Chrome via rsDriver (automatically downloads ChromeDriver)
driver <- rsDriver(browser = "chrome", chromever = "latest", verbose = FALSE)
remote_driver <- driver$client

