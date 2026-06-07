import os
import aiohttp
import asyncio
import pandas as pd

SHEET_URL = os.environ.get("SHEET_URL")

async def test_link(session, semaphore, name, url, logo):
    async with semaphore:
        try:
            async with session.get(url, timeout=8, allow_redirects=True) as response:
                if response.status in [200, 206]:
                    return {"name": name, "logo": logo, "url": url}
        except:
            pass
        return None

async def main():
    if not SHEET_URL: return
    df = pd.read_csv(SHEET_URL)
    tasks = []
    semaphore = asyncio.Semaphore(15) # ১০ থেকে বাড়িয়ে ১৫ করে দিলাম আরও দ্রুত টেস্টের জন্য
    
    async with aiohttp.ClientSession() as session:
        for _, row in df.iterrows():
            tasks.append(test_link(session, semaphore, str(row['Name']), str(row['URL']), str(row['Logo'])))
        
        results = await asyncio.gather(*tasks)
        valid = [r for r in results if r is not None]

    # M3U জেনারেট করা
    with open("live.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        # টি স্পোর্টস সবার উপরে রাখার লজিক
        for ch in valid:
            f.write(f'#EXTINF:-1 tvg-logo="{ch["logo"]}",{ch["name"]}\n{ch["url"]}\n')

if __name__ == "__main__":
    asyncio.run(main())
