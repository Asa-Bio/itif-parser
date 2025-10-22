
# ITIF publications parser 🚀

A Python script that parses publication data from [itif.org](https://itif.org/publications) 

The script collects titles, publication dates, authors, full text, and PDF download links, saving everything into a structured CSV file.

---

### Requirements
Before running the script, install the dependencies:
```
pip install selenium requests lxml tqdm
```
### Usage
```
python itif_parser.py
```
### Results will be saved as
```
itif_results.csv
```
### Notes
Set MAX_PAGES in the script to control how many listing pages are scraped

### Example Output

| Title | Pubdate | Authors | Article body | Pdf link | Url |
|:------:|:--------:|:--------:|:-------------:|:--------:|:----:|
| AR/VR’s Potential in Health Care | 2025-06-02 | Alex Ambrose | AR/VR innovation needs to accelerate in order to meet the critical demands of health care... | [PDF Link](https://www2.itif.org/2025-ar-vr-health-care.pdf) | [Article](https://itif.org/publications/2025/06/02/arvrs-potential-in-health-care/) |
