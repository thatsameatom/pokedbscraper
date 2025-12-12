import json
import time
import requests
from bs4 import BeautifulSoup

# Configuración
LIMIT = None
OUTPUT_FILE = "database.json"
BASE_URL = "https://pokemondb.net"
ALL_URL = "https://pokemondb.net/pokedex/all"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0'
}

def get_moves(soup, keywords):
    target_href = None
    for link in soup.find_all("a"):
        if any(k in link.get_text() for k in keywords):
            href = link.get('href', '')
            if href.startswith("#tab-moves"):
                target_href = href
                break
    
    if not target_href:
        return []

    div_id = target_href.replace("#", "")
    move_div = soup.find("div", id=div_id)
    
    if not move_div:
        return []

    return list(set(
        link['href'].replace("/move/", "") 
        for link in move_div.find_all("a", class_="ent-name")
    ))

def get_abilities(soup):
    header = soup.find("th", string="Abilities")
    if header:
        cell = header.find_next_sibling("td")
        if cell:
            return [a.get_text(strip=True) for a in cell.find_all("a")]
    return []

def main():
    db = { 
        "data": {}, 
        "translations": { "pokemon": {}, "moves": {}, "abilities": {} }, 
        "items": [] 
    }

    print(f"Iniciando scraping -> {OUTPUT_FILE}")
    
    resp = requests.get(ALL_URL, headers=HEADERS)
    soup = BeautifulSoup(resp.content, "html.parser")
    rows = soup.find("table", id="pokedex").find("tbody").find_all("tr")

    count = 0
    
    for row in rows:
        if LIMIT and count >= LIMIT:
            break

        cols = row.find_all("td")
        
        raw_id = cols[0].find("span", class_="infocard-cell-data").text
        fmt_id = str(int(raw_id)).zfill(4)
        
        name_tag = cols[1].find("a")
        p_name = name_tag.text
        p_url = BASE_URL + name_tag['href']
        
        if p_name in db["data"]:
            continue

        print(f"[{fmt_id}] {p_name}...", end=" ", flush=True)

        try:
            p_page = requests.get(p_url, headers=HEADERS)
            p_soup = BeautifulSoup(p_page.content, "html.parser")

            moves_za = get_moves(p_soup, ["Z-A", "Legends"])
            moves_sv = get_moves(p_soup, ["Scarlet", "Violet"])
            abilities_list = get_abilities(p_soup)

            available_in = []
            final_moves = {}

            if moves_za:
                available_in.append("plza")
                final_moves["plza"] = moves_za
            
            if moves_sv:
                available_in.append("sv")
                final_moves["sv"] = moves_sv

            if not available_in:
                print("Skip (N/A)")
                continue

            print(f"OK {available_in} | Abs: {len(abilities_list)}")

            db["data"][p_name] = {
                "id": fmt_id,
                "available_in": available_in,
                "abilities": abilities_list,
                "moves": final_moves
            }
            
            db["translations"]["pokemon"][p_name] = p_name
            
            for m in set(moves_za + moves_sv):
                 if m not in db["translations"]["moves"]:
                    db["translations"]["moves"][m] = {
                        "n": m.replace("-", " ").title(), 
                        "t": "normal"
                    }

            for ab in abilities_list:
                if ab not in db["translations"]["abilities"]:
                     db["translations"]["abilities"][ab] = ab

            count += 1
            time.sleep(0.5)

        except Exception as e:
            print(f"\nError: {e}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4)
        
    print("Proceso finalizado.")

if __name__ == "__main__":
    main()