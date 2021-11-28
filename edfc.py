import os
import re
import shutil

import requests
from bs4 import *
from sanitize_filename import sanitize

NOT_EXISTS = "指定主题不存在"
NO_PERMISSION = "无权查看本主题"

def download_img(src, img_path):
    ir = requests.get(src, stream=True)
    if ir.status_code == 200:
        with open(img_path, "wb") as f:
            ir.raw.decode_content = True
            shutil.copyfileobj(ir.raw, f)

def save_images(root_path, soup):
    images = soup.find_all("img", attrs={"data-original": re.compile(r"tgfc\w*\.com")})
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

def get_last_page_index(soup):
    spans = soup.find_all("span", attrs={"class": "paging"})
    if len(spans) == 0:
        return 1
    
    return int(re.findall(r"page=(\d+)", spans[0].find_all("a")[-1]["href"])[0])

def change_navs(soup, html_name):
    spans = soup.find_all("span", attrs={"class": "paging"})
    if len(spans) == 0:
        return

    for span in spans:
        for a in span.find_all("a"):
            index = int(re.findall(r"page=(\d+)", a["href"])[0])
            a["href"] = f"{html_name}_{index}.html"

def save_page(ttype, tid, page_index, auth_key):
    url = ""
    cookies = {}
    if ttype == "s":
        url = f"https://s.tgfcer.com/wap/index.php?action=thread&tid={tid}&pic=1&page={page_index}"
        cookies = {"tgc_pika_verify": auth_key}
    else:
        url = f"https://wap.tgfcer.com/index.php?action=thread&tid={tid}&pic=1&page={page_index}"
    
    r = requests.get(url, cookies=cookies)
    soup = BeautifulSoup(r.text, "html.parser")
    if len(soup.find_all("div", attrs={"class": "message"})) == 0:
        p = soup.find("p", string=[NOT_EXISTS, NO_PERMISSION])
        if p is None:
            print("错误，原因不明。")
        else:
            print(p.text)
        return

    for s in soup.find_all("script"):
        s.decompose()

    folder_name = f"downloads/{ttype}{tid}"
    if os.path.exists(folder_name) == False:
        os.makedirs(folder_name)
    save_images(folder_name, soup)
    html_name = sanitize(soup.title.text)
    not_last_page = page_index < get_last_page_index(soup)
    change_navs(soup, html_name)
    with open(f"{folder_name}/{html_name}_{page_index}.html", 'w', encoding="utf-8") as saved:
        print(str(soup), file=saved)

    if not_last_page:
        save_page(ttype, tid, page_index + 1, auth_key)


ttype = input("输入板块类型，s为水区，t为其它区：")
tid = input("输入id，网页链接中tid=后面的数字：")
auth_key = ""
if ttype in ["s", "S"]:
    auth_key = input("水区需要输入身份验证信息，cookie中tgc_pika_verify的值：")
    ttype = "s"
else:
    ttype = "t"

save_page(ttype, tid, 1, auth_key)