import os
import re
import json
import asyncio
import aiohttp

# --- 🚀 একাধিক সোর্স কনফিগারেশন (স্পেস ফিক্স করা হয়েছে) ---
SOURCE_URLS = [
    "https://raw.githubusercontent.com/Lane0118/IPTV/main/index.m3u", # গ্লোবাল সোর্স (ফিক্সড)
    "https://iptv-org.github.io/iptv/countries/bd.m3u",  # বাংলাদেশ
    "https://iptv-org.github.io/iptv/countries/in.m3u",  # ইন্ডিয়া
    "https://iptv-org.github.io/iptv/categories/movies.m3u" # মুভিজ
]

GITHUB_FILE = "index.html"
M3U_OUTPUT_FILE = "live.m3u"

def parse_category(meta):
    meta_lower = meta.lower()
    if "sport" in meta_lower: return "Sports"
    if "bangla" in meta_lower or "bd" in meta_lower: return "Bangladesh"
    if "india" in meta_lower: return "India"
    if "news" in meta_lower: return "News"
    if "movie" in meta_lower or "ent" in meta_lower or "general" in meta_lower: return "Entertainment"
    return "All"

async def test_link(session, name, category, logo, url):
    try:
        async with session.get(url, timeout=8, allow_redirects=True) as response:
            if response.status == 200:
                return {"name": name, "category": category, "logo": logo, "url": url}
    except:
        pass
    return None

async def fetch_m3u(session, url):
    try:
        async with session.get(url, timeout=15) as response:
            if response.status == 200:
                return await response.text()
    except Exception as e:
        print(f"⚠️ সোর্স ডাউনলোড ব্যর্থ: {url} | এরর: {e}")
    return ""

async def main():
    print("🔄 সবগুলো সোর্স থেকে M3U ফাইল ডাউনলোড করা হচ্ছে...")
    async with aiohttp.ClientSession() as session:
        m3u_tasks = [fetch_m3u(session, url) for url in SOURCE_URLS]
        m3u_contents = await asyncio.gather(*m3u_tasks)

    tasks = []
    seen_urls = set()
    
    print("📦 সব সোর্সের লিংক স্ক্র্যাপিং এবং ডুপ্লিকেট ফিল্টারিং শুরু হয়েছে...")
    for m3u_content in m3u_contents:
        if not m3u_content:
            continue
            
        lines = [line.strip() for line in m3u_content.split('\n') if line.strip()]
        for i in range(len(lines)):
            if lines[i].startswith("#EXTINF:"):
                stream_url = lines[i+1] if (i+1) < len(lines) else ""
                
                if stream_url and stream_url.startswith("http"):
                    if stream_url in seen_urls:
                        continue
                    seen_urls.add(stream_url)
                    
                    name_match = re.search(r',(.*)$', lines[i])
                    name = name_match.group(1).strip() if name_match else "Unknown Channel"
                    
                    logo_match = re.search(r'tvg-logo="([^"]+)"', lines[i])
                    logo = logo_match.group(1).strip() if logo_match else "https://images.unsplash.com/photo-1594909122845-11baa439b7bf?q=80&w=200"
                    
                    category = parse_category(lines[i])
                    tasks.append(test_link(session, name, category, logo, stream_url))
        
    print(f"⚡ ইউনিক মোট {len(tasks)} টি লিংক টেস্ট করা হচ্ছে... দয়া করে অপেক্ষা করুন।")
    if tasks:
        connector = aiohttp.TCPConnector(limit=50)
        async with aiohttp.ClientSession(connector=connector) as session:
            results = await asyncio.gather(*tasks)
    else:
        results = []
        
    valid_channels = [r for r in results if r is not None]
    print(f"✅ টেস্টিং শেষ! সচল চ্যানেল পাওয়া গেছে: {len(valid_channels)} টি।")

    # --- 📄 ইনডেক্স ফাইল আপডেট লজিক ---
    if os.path.exists(GITHUB_FILE):
        with open(GITHUB_FILE, "r", encoding="utf-8") as f:
            current_content = f.read()
    else:
        current_content = "const channels = [];"

    new_json_str = json.dumps(valid_channels, indent=2)
    start_marker = "const channels = ["
    end_marker = "];"
    
    if start_marker in current_content:
        start_idx = current_content.find(start_marker)
        end_idx = current_content.find(end_marker, start_idx)
        updated_content = (
            current_content[:start_idx + len(start_marker)] + 
            "\n" + new_json_str[1:-1] + "\n" + 
            current_content[end_idx:]
        )
    else:
        updated_content = f"const channels = {new_json_str};"

    with open(GITHUB_FILE, "w", encoding="utf-8") as f:
        f.write(updated_content)
    print("🚀 index.html ফাইলে লাইভ ডেটা আপডেট হয়েছে!")

    # --- 📺 লাইভ .M3U প্লেলিস্ট তৈরি করার লজিক ---
    print("📝 live.m3u প্লেলিস্ট ফাইল তৈরি করা হচ্ছে...")
    m3u_lines = ["#EXTM3U\n"]
    for ch in valid_channels:
        m3u_lines.append(f'#EXTINF:-1 tvg-name="{ch["name"]}" tvg-logo="{ch["logo"]}" group-title="{ch["category"]}",{ch["name"]}\n')
        m3u_lines.append(f'{ch["url"]}\n')
        
    with open(M3U_OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.writelines(m3u_lines)
    print("🎉 live.m3u প্লেলিস্ট ফাইল সফলভাবে তৈরি হয়েছে!")

if __name__ == "__main__":
    asyncio.run(main())
