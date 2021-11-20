import os
import re
import shutil

import requests
from bs4 import *
from sanitize_filename import sanitize


def download_img(src, img_path):
    ir = requests.get(src, stream=True)
    if ir.status_code == 200:
        with open(img_path, "wb") as f:
            ir.raw.decode_content = True
            shutil.copyfileobj(ir.raw, f)

def save_images(root_path, soup):
    images = soup.find_all("img", attrs={"data-original": re.compile("pic2.52tgfc.com")})
    if len(images) > 0:
        img_folder = f"{root_path}/imgs"
        if os.path.exists(img_folder) == False:
            os.mkdir(img_folder)
        for img in images:
            src = img["data-original"]
            file_name = sanitize(src[src.rindex("/")+1:])
            img_path = f"{img_folder}/{file_name}"
            if os.path.exists(img_path) == False:
                download_img(src, img_path)

            img["src"] = f"imgs/{file_name}"

def save_page(ttype, tid, page_index):
    url = ""
    if (ttype == "s"):
        url = f"https://s.tgfcer.com/wap/index.php?action=thread&tid={tid}&pic=1&page={page_index}"
    else:
        url = f"https://wap.tgfcer.com/index.php?action=thread&tid={tid}&pic=1&page={page_index}"
    
    r = requests.get(url)
    soup = BeautifulSoup(r.text, "html.parser")
    for s in soup.find_all("script"):
        s.decompose()

    folder_name = f"downloads/w{tid}"
    if os.path.exists(folder_name) == False:
        os.makedirs(folder_name)
    save_images(folder_name, soup)


    with open(f"{folder_name}/{sanitize(soup.title.text)}_{page_index}.html", 'w') as saved:
        print(str(soup), file=saved)

save_page("w", 8344473, 1)
