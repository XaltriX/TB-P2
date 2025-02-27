import asyncio
from sys import version as pyver

import pyrogram, uvloop
from pyrogram import __version__ as pyrover
from pyrogram import filters, idle
from pyrogram.errors import FloodWait
from pyrogram.types import Message
from datetime import datetime, timedelta
import pyrogram, asyncio, os, uvloop, time
from pyrogram import Client, filters, idle, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo 
from sys import version as pyver
from pyrogram import __version__ as pyrover
import config
from tools import get_data, fetch_download_link_async, extract_links, check_url_patterns_async, download_file, download_thumb, get_duration, update_progress, extract_code, shorten_url, extract_video_id
from pyrogram.errors import FloodWait, UserNotParticipant, WebpageCurlFailed, MediaEmpty
uvloop.install()
import motor.motor_asyncio
loop = asyncio.get_event_loop()

client = motor.motor_asyncio.AsyncIOMotorClient("mongodb+srv://video:video@cluster0.suiny.mongodb.net/")
db = client.nest  # Replace "your_database" with the name of your MongoDB database
file_collection = db.file
usersdb = db.users
urldb = db.urls
tokendb = db.token
rokendb = db.roken

API_ID = "24955235"
API_HASH = "f317b3f7bbe390346d8b46868cff0de8"
BOT_TOKEN = "6883841510:AAHyWn0qv3Mj-r0UIbOsmdJ_tzEAAY6OVvQ"

queue_url = {}

def get_readable_time(seconds: int) -> str:
    count = 0
    readable_time = ""
    time_list = []
    time_suffix_list = ["s", "m", "h", " days"]
    while count < 4:
        count += 1
        if count < 3:
            remainder, result = divmod(seconds, 60)
        else:
            remainder, result = divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)
    for x in range(len(time_list)):
        time_list[x] = str(time_list[x]) + time_suffix_list[x]
    if len(time_list) == 4:
        readable_time += time_list.pop() + ", "
    time_list.reverse()
    readable_time += ": ".join(time_list)
    return readable_time 


app = pyrogram.Client(
    "acha",
    API_ID,
    API_HASH,
    bot_token=BOT_TOKEN,
)

START_TIME = time.time()
SUDO_USERS = config.SUDO_USER
ADMIN_USERS = config.ADMIN_USER
save = {}

async def get_token():
  chat_id = 12345
  document = {"chat_id": chat_id}
  hek = await rokendb.find_one(document)
  return hek['token']

async def save_link():
    chat_id = 12345
    token = await shorten_url()
    timer_after = datetime.now() + timedelta(minutes=720)
    await rokendb.update_one(
        {"chat_id": chat_id}, 
        {"$set": {"token": token, "timer_after": timer_after}}
    )
  
async def save_token(chat_id):
    if not await tokendb.find_one({"chat_id": chat_id}):
        timer_after = datetime.now() + timedelta(minutes=720)
        document = {"chat_id": chat_id, "timer_after": timer_after}
        await tokendb.insert_one(document)
        

async def delete_token(chat_id):
      await tokendb.delete_one({"chat_id": chat_id})         


async def remove_file(unique_id):
    await file_collection.delete_one({'unique_id': unique_id})

async def get_file(unique_id):
    file = await file_collection.find_one({'unique_id': unique_id})
    if file:
        return file.get('file_id')
    else:
        return None

async def store_file(unique_id, file_id):
    file = await file_collection.find_one({'unique_id': unique_id})
    if file:
      return
    await file_collection.insert_one({'unique_id': unique_id, 'file_id': file_id})
  
async def add_served_user(user_id: int):
        is_served = await usersdb.find_one({"user_id": user_id})
        if is_served:
            return
        return await usersdb.insert_one({"user_id": user_id})

async def get_served_users() -> list:
        users_list = []
        async for user in usersdb.find({"user_id": {"$gt": 0}}):
            users_list.append(user)
        return users_list

async def store_url(url, file_id, unique_id, direct_link):
    try:
        url = await extract_code(url)
        document = await urldb.find_one({"url": url})
        if document and unique_id not in document.get("unique_ids", []):
            await urldb.update_one(
                {"url": url},
                {"$addToSet": {"file_ids": file_id, "unique_ids": unique_id, "direct_links": direct_link}},
                upsert=True
            )
        elif not document:
            await urldb.insert_one({"url": url, "file_ids": [file_id], "unique_ids": [unique_id], "direct_links": [direct_link]})
    except Exception as e:
        print(f"Error storing URL, file ID, unique ID, and direct link: {e}")


async def get_file_ids(url):
    try:
        url = await extract_code(url)
        document = await urldb.find_one({"url": url})
        if document:
            file_ids = document.get("file_ids", [])
            direct_links = document.get("direct_links", [])
            file_id_direct_link_pairs = [(file_id, direct_link) for file_id, direct_link in zip(file_ids, direct_links)]
            return file_id_direct_link_pairs
        else:
            return None
    except Exception as e:
        print(f"Error retrieving file IDs and direct links for URL: {e}")
        return None

joined = set()

async def is_join(user_id):
    if user_id in joined:
      return True
    try:
        await app.get_chat_member(-1002097822007, user_id)  
   #     await app.get_chat_member(-1001922006659, user_id)
        joined.add(user_id)
        return True
    except UserNotParticipant:
        return False  
    except FloodWait as e:
        await asyncio.sleep(e.value)



@app.on_message(filters.command("start") & filters.private)
async def start_fun(client, message: Message):
    asyncio.create_task(start_func(client, message))


async def start_func(client, message):
    if len(message.command) > 1 and "unqid" in message.command[1]:              
             unq_id = message.command[1].replace("unqid", "")
             file_id = await get_file(unq_id)
             if file_id:
                 hel = await client.send_cached_media(message.chat.id, file_id)
                 return await add_served_user(message.chat.id)
    elif len(message.command) > 1 and "token" in message.command[1]:
            # token = message.command[1].replace("token", "")
             await message.reply_text("🎉 Token Activated 🎉")
             return await save_token(message.from_user.id)
    await message.reply_text("Send Only Terabox Urls")
    return await add_served_user(message.chat.id)


async def token_fun(client, message):
        token = await get_token()
        keyboard = InlineKeyboardMarkup([
                 [InlineKeyboardButton("Refresh Token", url=token)],
                 [InlineKeyboardButton("Video Tutorial", url="https://t.me/HTDTeraBox/8")]
        ])
        return await message.reply_text("Your Ads Token is expired and needs to be refreshed.\n\nToken Timeout: 12 hours\n\nToken Usage: Pass 1 ad to use the bot for the next 12 hours.\n\nFor Apple users: Copy the token and paste it into your browser.\n\nWatch a video tutorial if you encounter any issues.", reply_markup=keyboard)


@app.on_message(filters.command("stats") & filters.private & filters.user(SUDO_USERS))
async def stats_func(_, message: Message):
        if db is None:
            return await message.reply_text(
               "MONGO_DB_URI var not defined. Please define it first"
            )
        served_users = await db.users.count_documents({})
        text = f""" **TeraBox Bot Stats:**
        
**Python Version :** {pyver.split()[0]}
**Pyrogram Version :** {pyrover}
**Served Users:** {served_users}
**Uptime:** {get_readable_time(time.time() - START_TIME)}"""
        await message.reply_text(text)

@app.on_message(filters.command("broadcast") & filters.private & filters.user(SUDO_USERS))
async def broadcast_func(_, message: Message):
    if db is None:
            return await message.reply_text(
               "MONGO_DB_URI var not defined. Please define it first"
            )
    if message.reply_to_message:
        x = message.reply_to_message.id
        y = message.chat.id
    elif len(message.command) < 2:
        return await message.reply_text(
            "**Usage**:\n/broadcast [MESSAGE] or [Reply to a Message]"
        )
    else:
        query = message.text.split(None, 1)[1]
    susr = 0
    susers = await get_served_users()
    served_users = [int(user["user_id"]) for user in susers]
    for i in served_users:
        try:
            await app.forward_messages(
                i, y, x
            ) if message.reply_to_message else await app.send_message(
                i, text=query
            )
            susr += 1
        except FloodWait as e:
            flood_time = int(e.value)
            await asyncio.sleep(flood_time)
        except Exception:
            pass
    try:
        await message.reply_text(
            f"**Broadcasted Message to {susr} Users.**"
        )
    except:
        pass
      


def box_fil(_, __, message):
    if message.chat.type == enums.ChatType.PRIVATE and (message.text or message.caption):
        text = message.text or message.caption
        return "tera" in text or "box" in text


box_filter = filters.create(box_fil)

@app.on_message(box_filter)
async def tera_private(client, message):
        asyncio.create_task(terabox_dm(client, message))


"""
async def terabox_dm(client, message):
        urls = extract_links(message.text or message.caption)
        if not urls:
          return await message.reply_text("No Urls Found")
        if not await is_join(message.from_user.id):
              return await message.reply_text("First Join @CheemsBackup to Use me")
        if not await tokendb.find_one({"chat_id": message.from_user.id}):
              return await token_fun(client, message)
        try:
            for url in urls:
                if not await check_url_patterns_async(str(url)):
                    await message.reply_text("⚠️ Not a valid Terabox URL!", quote=True)
                    continue
                files = await get_file_ids(url)
                if files:
                   for file, link in files:
                       try:
                           await client.send_cached_media(message.chat.id, file, caption=f"**Direct File Link**: {link}")
                       except FloodWait as e:
                           await asyncio.sleep(e.value)
                       except Exception as e:
                           continue
                   continue
                user_id = int(message.from_user.id)
                if user_id in queue_url and str(url) in queue_url[user_id]:
                        await message.reply_text("This Url is Already In Process Wait")
                        continue 
                if user_id not in queue_url:
                     queue_url[user_id] = {}
                queue_url[user_id][url] = True
                nil = await message.reply_text("🔎 Processing URL...", quote=True)
                try:
                   link_data = await fetch_download_link_async(url)
                   if link_data is None:
                       await message.reply_text("No download link available for this URL", quote=True)
                       continue
                except Exception as e:
                   print(e)
                   await message.reply_text("Some Error Occurred", quote=True)
                   continue 
                for link in link_data:
                    name, size, size_bytes, dlink, thumb  = await get_data(link)
                    if dlink:
                      try:                        
                         ril = await client.send_video(-1002069870125, dlink, caption="Indian")
                         file_id = (ril.video.file_id if ril.video else (ril.document.file_id if ril.document else (ril.animation.file_id if ril.animation else (ril.sticker.file_id if ril.sticker else (ril.photo.file_id if ril.photo else ril.audio.file_id if ril.audio else None)))))
                         unique_id = (ril.video.file_unique_id if ril.video else (ril.document.file_unique_id if ril.document else (ril.animation.file_unique_id if ril.animation else (ril.sticker.file_unique_id if ril.sticker else (ril.photo.file_unique_id if ril.photo else ril.audio.file_unique_id if ril.audio else None)))))                         
                         direct_url = f"https://t.me/teradlrobot?start=unqid{unique_id}"
                         await ril.copy(message.chat.id, caption=f"**Title**: `{name}`\n**Size**: `{size}`\n\n**Direct File Link**: {direct_url}")
                         await nil.edit_text("Completed")
                         await store_file(unique_id, file_id)
                         await store_url(url, file_id, unique_id, direct_url)
                      except FloodWait as e:
                           await asyncio.sleep(e.value)
                      except Exception as e:
                         print(e)
                         await client.send_photo(message.chat.id, thumb, has_spoiler=True, caption=f"**Title**: `{name}`\n**Size**: `{size}`\n**Download Link**: {dlink}")
                         await nil.edit_text("Completed")
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception as e:
            print(e)
            await message.reply_text("Some Error Occurred", quote=True)
        finally:
            if user_id in queue_url:
                 del queue_url[user_id]



@app.on_message(filters.chat(-1001935231841) & filters.text)
async def message_handler(client, message):
  text = message.text
  if "tera" in text or "box" in text:
       asyncio.create_task(terabox_group(client, message))
  else:
    return await message.reply_text("Send Only Terabox Urls", quote=True)


async def terabox_group(client, message):
        urls = extract_links(message.text)
        if not urls:
          return await message.reply_text("No Urls Found")
        if not await is_join(message.from_user.id):
              return await message.reply_text("First Join @CheemsBackup to Use me")
    
        if not await tokendb.find_one({"chat_id": message.from_user.id}):
              return await token_fun(client, message)
        try:
           await client.send_message(message.from_user.id, ".")
        except:
           button = InlineKeyboardButton("Click Here", url="https://t.me/teradlrobot?start=True")
           keyboard = InlineKeyboardMarkup([[button]])
           return await message.reply_text("First start me in private", quote=True, reply_markup=keyboard)
        try:
            for url in urls:
                if not await check_url_patterns_async(str(url)):
                    await message.reply_text("⚠️ Not a valid Terabox URL!", quote=True)
                    continue         
                files = await get_file_ids(url)
                if files:
                   for file, link in files:
                       try:
                           await client.send_cached_media(message.from_user.id, file, caption=f"**Direct File Link**: {link}")
                       except FloodWait as e:
                           await asyncio.sleep(e.value)
                       except Exception as e:
                           continue
                   continue
                user_id = int(message.from_user.id)
                if user_id in queue_url and str(url) in queue_url[user_id]:
                        return await message.reply_text("This Url is Already In Process Wait")
                if user_id not in queue_url:
                     queue_url[user_id] = {}
                queue_url[user_id][url] = True
                nil = await message.reply_text("🔎 Processing URL...", quote=True)
                try:
                   link_data = await fetch_download_link_async(url)
                   if link_data is None:
                       await message.reply_text("No download link available for this URL", quote=True)
                       continue
                except Exception as e:
                   print(e)
                   await message.reply_text("Some Error Occurred", quote=True)
                   continue 
                for link in link_data:
                    name, size, size_bytes, dlink, thumb  = await get_data(link)
                    if dlink:
                      try:                        
                         ril = await client.send_video(-1002069870125, dlink, caption="Indian")
                         file_id = (ril.video.file_id if ril.video else (ril.document.file_id if ril.document else (ril.animation.file_id if ril.animation else (ril.sticker.file_id if ril.sticker else (ril.photo.file_id if ril.photo else ril.audio.file_id if ril.audio else None)))))
                         unique_id = (ril.video.file_unique_id if ril.video else (ril.document.file_unique_id if ril.document else (ril.animation.file_unique_id if ril.animation else (ril.sticker.file_unique_id if ril.sticker else (ril.photo.file_unique_id if ril.photo else ril.audio.file_unique_id if ril.audio else None)))))                         
                         direct_url = f"https://t.me/teradlrobot?start=unqid{unique_id}"
                         await ril.copy(message.from_user.id, caption=f"**Title**: `{name}`\n**Size**: `{size}`\n\n**Direct File Link**: {direct_url}")
                         await nil.edit_text(f"Completed\n\n**File Direct Link**: [Link]({direct_url})", disable_web_page_preview=True)
                         await store_file(unique_id, file_id)
                         await store_url(url, file_id, unique_id, direct_url)
                      except FloodWait as e:
                         await asyncio.sleep(e.value)
                      except Exception as e:
                         print(e)
                         if int(size_bytes) > 524288000 and not name.lower().endswith(('.mp4', '.mkv', '.webm')):
                                  await client.send_photo(message.from_user.id, thumb, has_spoiler=True, caption=f"**Title**: `{name}`\n**Size**: `{size}`\n**Download Link**: {dlink}")
                                  await nil.edit_text("Completed")
                         else:
                             try:                               
                                vid_path = await loop.run_in_executor(None, download_file, dlink, name)
                                thumb_path = await loop.run_in_executor(None, download_thumb, thumb)
                                ril = await client.send_video(-1002069870125, vid_path, thumb=thumb_path, caption="Indian")
                                file_id = (ril.video.file_id if ril.video else (ril.document.file_id if ril.document else (ril.animation.file_id if ril.animation else (ril.sticker.file_id if ril.sticker else (ril.photo.file_id if ril.photo else ril.audio.file_id if ril.audio else None)))))
                                unique_id = (ril.video.file_unique_id if ril.video else (ril.document.file_unique_id if ril.document else (ril.animation.file_unique_id if ril.animation else (ril.sticker.file_unique_id if ril.sticker else (ril.photo.file_unique_id if ril.photo else ril.audio.file_unique_id if ril.audio else None)))))                     
                                direct_url = f"https://t.me/teradlrobot?start=unqid{unique_id}"
                                await ril.copy(message.from_user.id, caption=f"**Title**: `{name}`\n**Size**: `{size}`\n\n**Direct File Link**: {direct_url}")
                                await nil.edit_text(f"Completed\n\n**File Direct Link**: [Link]({direct_url})", disable_web_page_preview=True)                                
                                await store_file(unique_id, file_id)
                                await store_url(url, file_id, unique_id, direct_url)
                             except FloodWait as e:
                                await asyncio.sleep(e.value)
                             except Exception as e:
                                 print(e)                                                         
                                 await client.send_photo(message.from_user.id, thumb, has_spoiler=True, caption=f"**Title**: `{name}`\n**Size**: `{size}`\n**Download Link**: {dlink}")
                                 await nil.edit_text("Completed")
                             finally:
                                    if vid_path and os.path.exists(vid_path):
                                         os.remove(vid_path)
                                    if thumb_path and os.path.exists(thumb_path):
                                         os.remove(thumb_path)
        except FloodWait as e:
            await asyncio.sleep(e.value)                              
        except Exception as e:
            print(e)
            await message.reply_text("Some Error Occurred", quote=True)
        finally:
            if user_id in queue_url:
                 del queue_url[user_id]

"""


async def terabox_dm(client, message):
        urls = await extract_links(message.text or message.caption)
        if not urls:
          return await message.reply_text("No Urls Found")
        if not await is_join(message.from_user.id):
              return await message.reply_text("First Join @NeonGhost_Networks to Use me")
        if not await tokendb.find_one({"chat_id": message.from_user.id}):
              return await token_fun(client, message)
        try: 
            user_id = int(message.from_user.id)
            if user_id in queue_url:
                  return await message.reply_text("Your One Url is Already In Process pls Wait for it to Complete")                        
            queue_url[user_id] = True
            for url in urls:                
                if not await check_url_patterns_async(str(url)):
                    await message.reply_text("⚠️ Not a valid Terabox URL!", quote=True)
                    continue
                files = await get_file_ids(url)
                if files:
                   for file, link in files:
                       try:
                           await client.send_cached_media(message.chat.id, file, caption=f"**Direct File Link**: {link}")
                       except FloodWait as e:
                           await asyncio.sleep(e.value)
                       except Exception as e:
                           continue
                   continue
                nil = await message.reply_text("🔎 Processing URL...", quote=True)
                try:
                   link_data = await fetch_download_link_async(url)
                   if link_data is None:
                       await message.reply_text("No download link available for this URL", quote=True)
                       continue
                except Exception as e:
                   print(e)
                   await message.reply_text("Some Error Occurred", quote=True)
                   continue 
                for link in link_data:
                    name, size, size_bytes, dlink, dlink2, dlink3, thumb  = await get_data(link)
                    if dlink:
                      try:                        
                         ril = await client.send_video(-1002004278204, dlink, caption="Indian")
                         file_id = (ril.video.file_id if ril.video else (ril.document.file_id if ril.document else (ril.animation.file_id if ril.animation else (ril.sticker.file_id if ril.sticker else (ril.photo.file_id if ril.photo else ril.audio.file_id if ril.audio else None)))))
                         unique_id = (ril.video.file_unique_id if ril.video else (ril.document.file_unique_id if ril.document else (ril.animation.file_unique_id if ril.animation else (ril.sticker.file_unique_id if ril.sticker else (ril.photo.file_unique_id if ril.photo else ril.audio.file_unique_id if ril.audio else None)))))                         
                         direct_url = f"https://t.me/TeraBox_tEST_BoT?start=unqid{unique_id}"
                         await ril.copy(message.chat.id, caption=f"**Title**: `{name}`\n**Size**: `{size}`\n\n**Direct File Link**: {direct_url}")
                         await nil.edit_text("Completed")
                         await store_file(unique_id, file_id)
                         await store_url(url, file_id, unique_id, direct_url)
                      except FloodWait as e:
                         await asyncio.sleep(e.value)
                      except Exception as e:
                         print(e)                      
                         if (not name.endswith(".mp4") and not name.endswith(".mkv") and not name.endswith(".Mkv") and not name.endswith(".webm")) or int(size_bytes) > 314572800:
                                 play_url = await extract_video_id(url)
                                 play_url = f"https://apis.forn.fun/tera/m3u8.php?id={play_url}"
                                 keyboard = [[InlineKeyboardButton("Watch Online", web_app=WebAppInfo(url=play_url))]]
                                 await client.send_photo(message.chat.id, thumb, has_spoiler=True, caption=f"**Title**: `{name}`\n**Size**: `{size}`\n**Download Link V1**: [Link]({dlink})\n**Download Link V2**: [Link]({dlink2})\n**Download Link V3**: [Link]({dlink3})", reply_markup=InlineKeyboardMarkup(keyboard))
                                 await nil.edit_text("Completed")
                         else:
                             try:
                                vid_path = await download_file(dlink, name)
                                thumb_path = await download_thumb(thumb)                                                                                       
                                ril = await client.send_video(-1002004278204, vid_path, thumb=thumb_path, caption="Indian")
                                file_id = (ril.video.file_id if ril.video else (ril.document.file_id if ril.document else (ril.animation.file_id if ril.animation else (ril.sticker.file_id if ril.sticker else (ril.photo.file_id if ril.photo else ril.audio.file_id if ril.audio else None)))))
                                unique_id = (ril.video.file_unique_id if ril.video else (ril.document.file_unique_id if ril.document else (ril.animation.file_unique_id if ril.animation else (ril.sticker.file_unique_id if ril.sticker else (ril.photo.file_unique_id if ril.photo else ril.audio.file_unique_id if ril.audio else None)))))                     
                                direct_url = f"https://t.me/TeraBox_tEST_BoT?start=unqid{unique_id}"
                                await ril.copy(message.chat.id, caption=f"**Title**: `{name}`\n**Size**: `{size}`\n\n**Direct File Link**: {direct_url}")
                                await nil.edit_text("Completed")
                                try:
                                  os.remove(vid_path)
                                  os.remove(thumb_path)
                                except:
                                  pass
                                await store_file(unique_id, file_id)
                                await store_url(url, file_id, unique_id, direct_url)
                             except FloodWait as e:
                                await asyncio.sleep(e.value)
                             except Exception as e:
                                 print(e)
                                 play_url = await extract_video_id(url)
                                 play_url = f"https://apis.forn.fun/tera/m3u8.php?id={play_url}"
                                 keyboard = [[InlineKeyboardButton("Watch Online", web_app=WebAppInfo(url=play_url))]]
                                 await client.send_photo(message.chat.id, thumb, has_spoiler=True, caption=f"**Title**: `{name}`\n**Size**: `{size}`\n**Download Link V1**: [Link]({dlink})\n**Download Link V2**: [Link]({dlink2})\n**Download Link V3**: [Link]({dlink3})", reply_markup=InlineKeyboardMarkup(keyboard))
                                 await nil.edit_text("Completed")
                             finally:
                                    if vid_path and os.path.exists(vid_path):
                                         os.remove(vid_path)
                                    if thumb_path and os.path.exists(thumb_path):
                                         os.remove(thumb_path)
        except FloodWait as e:
            await asyncio.sleep(e.value)                             
        except Exception as e:
            print(e)
            await message.reply_text("Some Error Occurred", quote=True)
        finally:
            if user_id in queue_url:
                 del queue_url[user_id]
              

async def remove_tokens():
        while True:
          try:
            await asyncio.sleep(10)
            current_time = datetime.now()
            filter_query = {"timer_after": {"$lt": current_time}}
            deleted_documents = await tokendb.find(filter_query).to_list(None)
            for document in deleted_documents:
                chat_id = document.get("chat_id")           
                try:
                    await delete_token(chat_id)
                    await app.send_message(chat_id, "Your Token Has Been Expired please re-generate to continue Work.")
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                except Exception as e:
                    print(e)
          except Exception as e:
            print(f"Error in delete_videos loop: {e}")

async def remove_links():
    while True:
        try:
            await asyncio.sleep(10)
            current_time = datetime.now()
            filter_query = {"timer_after": {"$lt": current_time}}
            document = await rokendb.find(filter_query).to_list(None)
            if document:            
                try:
                    await save_link()
                except Exception as e:
                    print(f"Error updating token {e}")
        except Exception as e:
            print(f"Error in remove_links loop: {e}")
            
async def init():
    await app.start()
    asyncio.create_task(remove_tokens())
    asyncio.create_task(remove_links())    
    print("[LOG] - Yukki Chat Bot Started")
    await idle()
  
if __name__ == "__main__":
    loop.run_until_complete(init())
