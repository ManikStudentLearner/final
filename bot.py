import os
import asyncio
import aiohttp
import discord
from discord.ext import commands
import time
from collections import defaultdict

# Hardcoded credentials (replace with your actual values)
TOKEN = os.getenv("DISCORD_TOKEN", "YOUR_DISCORD_BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))  # Replace with your channel ID

HYPIXEL_API = "https://api.hypixel.net/skyblock/auctions"

# ONLY these 7 sheep skins to track
TARGET_SKINS = {
    "Dark Green Sheep Skin",
    "Orange Sheep Skin", 
    "Red Sheep Skin",
    "Blue Sheep Skin",
    "Gray Sheep Skin",
    "Yellow Sheep Skin",
    "Monster Sheep Skin",
}

# Setup bot
intents = discord.Intents.default()
intents.message_content = True  # Required for !status command
bot = commands.Bot(command_prefix="!", intents=intents)

# Track seen auctions with TTL to prevent reposts and memory leaks
seen_auctions = {}  # {uuid: timestamp}
monitoring_active = False
TTL_HOURS = 6  # Clean auctions older than 6 hours

# Rate limiting tracking
api_call_times = []

async def fetch_auctions(session, page=0, timeout=10):
    """Fetch auctions with error handling and rate limiting"""
    global api_call_times
    
    # Clean old API call times (older than 1 minute)
    current_time = time.time()
    api_call_times = [t for t in api_call_times if current_time - t < 60]
    
    # Rate limit check (max 120 calls per minute)
    if len(api_call_times) >= 120:
        sleep_time = 60 - (current_time - api_call_times[0])
        if sleep_time > 0:
            print(f"⏳ Rate limit reached, sleeping for {sleep_time:.1f}s")
            await asyncio.sleep(sleep_time)
    
    try:
        timeout_obj = aiohttp.ClientTimeout(total=timeout)
        async with session.get(HYPIXEL_API, params={"page": page}, timeout=timeout_obj) as resp:
            api_call_times.append(current_time)
            
            if resp.status == 200:
                return await resp.json()
            elif resp.status == 429:
                # Rate limited, wait and retry
                retry_after = int(resp.headers.get('Retry-After', 60))
                print(f"🚫 Rate limited by API, waiting {retry_after}s")
                await asyncio.sleep(retry_after)
                return None
            else:
                print(f"API Error: Status {resp.status}")
                return None
    except asyncio.TimeoutError:
        print(f"⏰ Request timeout for page {page}")
        return None
    except Exception as e:
        print(f"Request failed: {e}")
        return None

class AuctionView(discord.ui.View):
    def __init__(self, auction_uuid):
        super().__init__(timeout=3600)  # 1 hour timeout
        self.auction_uuid = auction_uuid
        
        # Auction Link Button
        auction_url = f"https://sky.coflnet.com/auction/{auction_uuid}"
        self.add_item(discord.ui.Button(
            label="Auction Link",
            style=discord.ButtonStyle.link,
            url=auction_url
        ))
    
    @discord.ui.button(label="Copy Command", style=discord.ButtonStyle.secondary)
    async def copy_command(self, interaction: discord.Interaction, button: discord.ui.Button):
        command = f"/ah {self.auction_uuid}"
        await interaction.response.send_message(f"```{command}```", ephemeral=True)

async def poll_auctions():
    """Main polling loop - 2 requests per second"""
    global monitoring_active, seen_auctions
    monitoring_active = True
    
    print("🔄 Starting auction polling...")
    await bot.wait_until_ready()
    
    # Improved channel resolution with retry
    channel = None
    for attempt in range(3):
        try:
            channel = bot.get_channel(CHANNEL_ID)
            if channel:
                break
            # Try fetching if get fails
            channel = await bot.fetch_channel(CHANNEL_ID)
            if channel:
                break
        except Exception as e:
            print(f"Attempt {attempt + 1} to get channel failed: {e}")
            if attempt < 2:
                await asyncio.sleep(5)
    
    if not channel:
        print(f"❌ Error: Channel {CHANNEL_ID} not found after 3 attempts!")
        monitoring_active = False
        return
    
    print(f"✅ Connected to channel: {channel.name}")
    print("🔍 Beginning auction scan...")
    
    async with aiohttp.ClientSession() as session:
        page = 0
        
        while not bot.is_closed():
            try:
                # Fetch auction data
                print(f"📊 Fetching page {page}...")
                data = await fetch_auctions(session, page)
                
                if not data or not data.get("success"):
                    print(f"❌ API call failed for page {page}")
                    await asyncio.sleep(0.5)
                    continue
                
                auctions = data.get("auctions", [])
                print(f"📋 Processing {len(auctions)} auctions on page {page}")
                
                # Process each auction
                bin_count = 0
                for auc in auctions:
                    # Only BIN auctions
                    if not auc.get("bin"):
                        continue
                    
                    bin_count += 1
                    uuid = auc.get("uuid")
                    current_time = time.time()
                    
                    # Clean old seen auctions (TTL cleanup)
                    cutoff_time = current_time - (TTL_HOURS * 3600)
                    seen_auctions = {k: v for k, v in seen_auctions.items() if v > cutoff_time}
                    
                    if not uuid or uuid in seen_auctions:
                        continue
                    
                    item_name = auc.get("item_name", "")
                    price = auc.get("starting_bid", 0)
                    
                    # Check if it's one of our target skins (EXACT match)
                    if item_name in TARGET_SKINS:
                        print(f"🎯 FOUND TARGET SKIN: {item_name} - {price:,} coins")
                        # Determine price tier and @everyone count
                        everyone_count = 0
                        tier = ""
                        embed_color = 0x00ff00
                        
                        if price < 20_000_000:
                            everyone_count = 20
                            tier = "Under 20m"
                            embed_color = 0x00ff00  # Green
                        elif price < 50_000_000:
                            everyone_count = 10  
                            tier = "Under 50m"
                            embed_color = 0xffa500  # Orange
                        elif price < 100_000_000:
                            everyone_count = 5
                            tier = "Under 100m"
                            embed_color = 0xff0000  # Red
                        else:
                            everyone_count = 0
                            tier = "100m+"
                            embed_color = 0x800080  # Purple
                        
                        # Create embed for ALL matching skins regardless of price
                        embed = discord.Embed(
                            title="🐑 Skin Found!",
                            color=embed_color
                        )
                        embed.add_field(name="Skin", value=item_name, inline=False)
                        embed.add_field(name="Price", value=f"{tier} - {price:,} coins", inline=False)
                        
                        # Create view with buttons
                        view = AuctionView(uuid)
                        
                        try:
                            if hasattr(channel, 'send'):
                                # Send multiple separate @everyone messages for multiple pings
                                if everyone_count > 0:
                                    # Send separate @everyone messages for actual multiple pings
                                    for i in range(everyone_count):
                                        await channel.send("@everyone", delete_after=1)  # Auto-delete ping messages
                                        await asyncio.sleep(0.1)  # Small delay between pings
                                
                                # Send the main embed message
                                await channel.send(embed=embed, view=view)
                                print(f"Alert sent: {item_name} - {price:,} coins ({tier}) - {everyone_count} pings")
                        except Exception as e:
                            print(f"Failed to send message: {e}")
                        
                        # Mark as seen with timestamp
                        seen_auctions[uuid] = current_time
                
                print(f"📊 Page {page}: {bin_count} BIN auctions processed")
                
                # Move to next page
                page += 1
                total_pages = data.get("totalPages", 1)
                if page >= total_pages:
                    print(f"🔄 Completed full cycle of {total_pages} pages")
                    page = 0
                
            except Exception as e:
                print(f"Error in polling loop: {e}")
            
            # 2 requests per second = 0.5 second delay
            await asyncio.sleep(0.5)

@bot.event
async def on_ready():
    print(f"✅ Bot logged in as {bot.user}")
    print(f"📡 Channel ID: {CHANNEL_ID}")
    print(f"🎯 Tracking {len(TARGET_SKINS)} skins")
    # Start polling automatically
    bot.loop.create_task(poll_auctions())
    print("🚀 Started polling task")

@bot.command(name='status')
async def status_command(ctx):
    """Show bot status"""
    global monitoring_active
    
    embed = discord.Embed(title="🤖 Bot Status", color=0x0099ff)
    
    # Monitoring status
    if monitoring_active:
        embed.add_field(name="Monitoring", value="✅ Running", inline=True)
    else:
        embed.add_field(name="Monitoring", value="❌ Stopped", inline=True)
    
    # Auctions tracked in memory
    embed.add_field(name="Auctions Tracked", value=f"{len(seen_auctions):,}", inline=True)
    
    # Memory usage info
    current_time = time.time()
    cutoff_time = current_time - (TTL_HOURS * 3600)
    old_auctions = sum(1 for timestamp in seen_auctions.values() if timestamp <= cutoff_time)
    if old_auctions > 0:
        embed.add_field(name="Cleanup Needed", value=f"{old_auctions} old entries", inline=True)
    
    # Skins being tracked
    embed.add_field(name="Skins Tracked", value=f"{len(TARGET_SKINS)}", inline=True)
    
    await ctx.send(embed=embed)

# Run the bot
if __name__ == "__main__":
    if TOKEN == "YOUR_DISCORD_BOT_TOKEN" or CHANNEL_ID == 0:
        print("❌ Please replace TOKEN and CHANNEL_ID with your actual values!")
    else:
        bot.run(TOKEN)