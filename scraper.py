import os
import json
import asyncio
import aiohttp
import pandas as pd

# গিটহাব সিক্রেট থেকে লিংকটি রিড করছে
SHEET_URL = os.environ.get("SHEET_URL")

GITHUB_FILE = "index.html"
M3U_OUTPUT_FILE = "live.m3u"

async def test_link(session, semaphore, name, url, logo):
    async with semaphore:
        try:
            async with session.get(url, timeout=15, allow_redirects=True) as response:
                if response.status in [200, 206]:
                    return {"name": name, "category": "Sports" if "sport" in name.lower() else "Live", "logo": logo, "url": url}
        except:
            pass
        return None

async def main():
    if not SHEET_URL:
        print("SHEET_URL পাওয়া যায়নি!")
        return

    df = pd.read_csv(SHEET_URL)
    tasks = []
    semaphore = asyncio.Semaphore(5)
    
    async with aiohttp.ClientSession() as session:
        for index, row in df.iterrows():
            tasks.append(test_link(session, semaphore, str(row['Name']), str(row['URL']), str(row['Logo'])))
        
        results = await asyncio.gather(*tasks)
        valid_channels = [r for r in results if r is not None]

    # ফাইল আপডেট
    with open(M3U_OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for ch in valid_channels:
            f.write(f'#EXTINF:-1 tvg-logo="{ch["logo"]}",{ch["name"]}\n{ch["url"]}\n')
            
    print(f"✅ সফল! {len(valid_channels)} টি চ্যানেল পাওয়া গেছে।")

if __name__ == "__main__":
    asyncio.run(main())
