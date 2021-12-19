import os
import re
import shutil
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from sanitize_filename import sanitize
import unicodedata
from modles import TThread, TPost, engine
from sqlalchemy import select
from sqlalchemy.orm import Session


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

            img["src"] = f"../imgs/{file_name}"

def get_last_page_index(soup):
    spans = soup.find_all("span", attrs={"class": "paging"})
    if len(spans) == 0:
        return 1
    
    return int(re.findall(r"page=(\d+)", spans[0].find_all("a")[-1]["href"])[0])

def get_forum(soup):
    return soup.find("div", attrs={"class": "navbar"}).find_next_sibling("p").find_all("a")[1].text

def get_author(soup):
    return soup.find("div", attrs={"class": "navbar"}).find_next_sibling("p").find("a", attrs={"href": re.compile(r"action=my")}).text
    
def get_posts(soup):
    def div2post(div):
        prev = div.find_previous_sibling("div", attrs={"class": "infobar"})
        if prev is None:
            return {"idx": 1, "msg": div.text}
        else:
            return {"idx": int(prev.find("a").text.replace("#", "")), "msg": div.text}
    return list(map(div2post, soup.find_all("div", attrs={"class": "message"})))

def change_navs(soup, html_name):
    spans = soup.find_all("span", attrs={"class": "paging"})
    if len(spans) == 0:
        return

    for span in spans:
        for a in span.find_all("a"):
            index = int(re.findall(r"page=(\d+)", a["href"])[0])
            a["href"] = f"{html_name}_{index}.html"

def save_page(ttype, tid, page_index, auth_key, session, thread, archived):
    tid = int(tid)
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

    for s in soup.find_all("script"): s.decompose()

    html_name = sanitize(unicodedata.normalize("NFKD", re.sub("-TGFC俱乐部$", "", soup.title.text)))
    #there is a bug of sanitize, so I have to call unicodedata.normalize at first to convert "\uff1f"(？) to "?"
    posts = get_posts(soup)
    first_time_touch = False
    if page_index == 1:
        thread = session.execute(select(TThread).where(TThread.id==tid)).one_or_none()
        if thread is None:
            first_time_touch = True
            thread = TThread(id = tid, forum_type = ttype, forum = get_forum(soup), title = html_name, author = get_author(soup))
            for p in posts:
                thread.posts.append(TPost(tid = tid, idx = p["idx"], str = p["msg"]))
            session.add(thread)
            session.commit()
        else:
            thread = thread[0]
            #make sure page indexes are consecutive
            for i in range(0, len(thread.posts)-1):
                if i != thread.posts[i].idx -1:
                    raise ValueError(f"posts indexes from db are not consecutive, tid:{tid}, post index: {i}")

    archive = False
    root_path = f"downloads/{ttype}{tid}"
    latest_dir = f"{root_path}/latest"

    if first_time_touch:
        new = True
    else:
        edited = False
        new = False
        for i in range(0, len(posts)):
            post = posts[i]
            if post["idx"] > thread.posts[-1].idx:#new post
                new = True
                thread.posts.append(TPost(tid = tid, idx = post["idx"], str = post["msg"]))
            else:
                post_in_db = thread.posts[post["idx"]-1]
                if post["msg"] != post_in_db.str:
                    edited = True
                    post_in_db.str = post["msg"]
                    
                    if archived == False:
                        archive = True
        
        if archive:
            p = Path(root_path)
            versions = [int(x.name.replace("v", "")) for x in p.iterdir() if x.is_dir() and re.match("^v\d{1,3}$", x.name)]
            ver = 1 if versions == [] else max(versions) + 1
            archive_dir = f"{root_path}/v{ver}"
            if os.path.exists(archive_dir):
                raise ValueError("archives exceed capacity.")

            os.makedirs(archive_dir)
            if os.path.exists(latest_dir):
                p = Path(latest_dir)
                for f in p.iterdir():
                    if f.is_file() and f.name.endswith(".html"):
                        shutil.copy(str(f), f"{archive_dir}/{f.name}")
            thread.ver = ver
            archived = True

        if new or edited or archive:
            session.commit()


    if not os.path.exists(latest_dir):
        os.makedirs(latest_dir)
    
    not_last_page = page_index < get_last_page_index(soup)
    html_file = f"{latest_dir}/{html_name}_{page_index}.html"
    if new or edited or not os.path.exists(html_file):
        save_images(root_path, soup)
        change_navs(soup, html_name)
        with open(html_file, 'w', encoding="utf-8") as saved:
            print(str(soup), file=saved)

    if not_last_page:
        save_page(ttype, tid, page_index + 1, auth_key, session, thread, archived)


ttype = input("输入板块类型，s为水区，t为其它区：")
tid = input("输入id，网页链接中tid=后面的数字：")
auth_key = ""
if ttype in ["s", "S"]:
    auth_key = input("水区需要输入身份验证信息，cookie中tgc_pika_verify的值：")
    ttype = "s"
else:
    ttype = "t"

with Session(engine) as session:
    save_page(ttype, tid, 1, auth_key, session, None, False)