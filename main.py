import discord
import discord.utils
import os
import json
from replit import db
from keep_alive import keep_alive
import pytz
from datetime import datetime

intents = discord.Intents(messages=True, guilds=True)
client = discord.Client(intents=intents)

#State Variables
client.token = os.getenv('TOKEN')

#load in the banned words from the .env file
client.t1_banned_words = json.loads(os.getenv('T1'))
client.t2_banned_words = json.loads(os.getenv('T2'))
client.t3_banned_words = json.loads(os.getenv('T3'))

#config parameters for this to run on the server
client.this_guild = 279668907101388810
client.admin_channel_id = 771103473701224480
client.moderator_roles = ['Moderation','Moderation Team Member']

#Utility Functions(To be taken into separate file)
async def add_role(message, role_name):
  print('Trying to add the role!')
  member = message.author
  role = discord.utils.get(message.guild.roles, name=role_name)
  await member.add_roles(role)

async def add_reaction(emoji, message):
  print('adding emoji')
  await message.add_reaction(emoji)

#get the datetime in EST time
async def get_time():
  tz_NY = pytz.timezone('America/New_York') 
  datetime_NY = datetime.now(tz_NY)
  current_time = datetime_NY.strftime("%c")
  return current_time

def create_log_key(user_id):
  return "log_{0}".format(user_id)

async def add_user_log(tier, message, b_Word):
  this_key = create_log_key(message.author.id)
  this_log = {}
  this_log['time'] = await get_time()
  this_log['tier'] = tier
  this_log['content'] = message.content
  json_log = json.dumps(this_log)

  if (this_key in db.keys()):
    current_log = db[this_key]
    current_log.append(json_log)
    db[this_key] = current_log
  else:
    db[this_key] = [json_log]

async def get_user_log(user_id):
  this_key = create_log_key(user_id)
  if (this_key in db.keys()):
    return db[this_key]
  else:
    return []

async def clear_user_log(user_id):
  this_key = create_log_key(user_id)
  del db[this_key]
  return True

async def find_bad_word(msg, b_words):
  for word in b_words:
    if(word in msg):
      return word

async def generate_discord_url(message):
  base_url = 'https://discord.com/channels'
  return '{0}/{1}/{2}/{3}'.format(base_url, client.this_guild, message.channel.id, message.id)

async def create_log_embed(logs, user):
  embedVar = discord.Embed(title="Banned Word Log For:", description=user, color=0xEF5148)

  for entry in logs:
    entry_json = json.loads(entry)
    embedVar.add_field(name=entry_json["content"], value='Tier: **{1}** \n **{0}**'.format(entry_json["time"], entry_json["tier"]), inline=True)
  
  return embedVar

async def banned_word_actions(message, msg, b_word, tier):
  admin_channel = message.guild.get_channel(client.admin_channel_id)
  await add_user_log(tier, message, b_word)

  if(tier < 3):
    #foreach defined moderator role send a ping
    for mod_role in client.moderator_roles:
      role = discord.utils.get(message.guild.roles, name=mod_role)
      await admin_channel.send(role.mention)

  embedVar = discord.Embed(title="A message was sent with a banned word:", description=b_word, color=0xEF5148)
  embedVar.add_field(name="Tier", value=tier, inline=False)
  embedVar.add_field(name="User", value=message.author.mention, inline=False)
  embedVar.add_field(name="Content", value=msg, inline=False)
  embedVar.add_field(name="Channel", value=message.channel.mention, inline=False)

  if(tier > 2):
    embedVar.add_field(name="Jump To", value=await generate_discord_url(message), inline=False)

  await admin_channel.send(embed=embedVar)

async def kick_user(message):
  guild = message.guild
  user = message.author
  await guild.kick(user)

async def ban_user(message):
  guild = message.guild
  user = message.author
  await guild.ban(user)

#Discord Events
@client.event
async def on_ready():
  print('We have logged in as {0.user}'.format(client))

#On Message, where all the commands are
@client.event
async def on_message(message):
  #if this message is from the bot ignore it
  if message.author == client.user:
    return

  #create a useful shorthand for the message content
  msg = message.content
  msg_lower = msg.lower()

  #If the bot recieves a DM we forward it to the admin channel.
  if isinstance(message.channel, discord.channel.DMChannel) and message.author != client.user:
    my_guild = client.get_guild(client.this_guild)
    admin_channel = my_guild.get_channel(client.admin_channel_id)
    await message.channel.send('I have forwarded this message to our Moderators.')
    embedVar = discord.Embed(title="I have forwarded this from my DMS:", description=msg, color=0x3598D4)
    embedVar.add_field(name="User", value=message.author.mention, inline=False)
    await admin_channel.send(embed=embedVar)

  #If a user posts a message with a T1 banned word, we delete the message
  #send a DM that is harsh, and tag the moderation team.
  if any(word in msg_lower for word in client.t1_banned_words):
    b_word = await find_bad_word(msg_lower, client.t1_banned_words)
    await message.author.send('I have detected the word "**{0}**" in your last message that we have deemed breaks our rules __in many contexts__. \n\n This message has been deleted and the moderators have been alerted; they will be reaching out to you for further action if necessary. Thanks for understanding!'.format(b_word))
    await banned_word_actions(message, msg, b_word, 1)
    await message.delete()

  #If a user posts a message with a T2 banned word, we delete the message
  #send a DM that is not as harsh, and tag the moderation team.
  if any(word in msg_lower for word in client.t2_banned_words):
    b_word = await find_bad_word(msg_lower, client.t2_banned_words)
    await message.author.send('I have detected the word "**{0}**" in your last message that does not belong in BG. \n\n This message has been deleted and the Moderators have been alerted incase any action needs to be taken. Thanks for Understanding!'.format(b_word))
    await banned_word_actions(message, msg, b_word, 2)
    await message.delete()

  #If a user posts a message with a T3 banned word, We dont delete the message
  if any(word in msg_lower for word in client.t3_banned_words):
    b_word = await find_bad_word(msg_lower, client.t3_banned_words)
    await banned_word_actions(message, msg, b_word, 3)

  #allows the user to request a log for a given user
  if(msg.startswith('=log')):
    message_parts = message.content.split("=log ", 1)
    if(len(message_parts) > 1 and len(message.mentions) > 0):
      user = message.mentions[0].id
      log = await get_user_log(user)
      mention = message.mentions[0].mention
      embed = await create_log_embed(log, mention)
      await message.channel.send(embed=embed)
    else:
      await message.channel.send('Sorry, You need to provide a user whose log I should look up.')

  #allows the user to clear a log for a given user
  if(msg.startswith('=clearlog')):
    message_parts = message.content.split("=clearlog ", 1)
    if(len(message_parts) > 1 and len(message.mentions) > 0):
      user = message.mentions[0].id
      await clear_user_log(user)
      await message.channel.send('I have cleared the log for {0}'.format(message.mentions[0].mention))
    else:
      await message.channel.send('Sorry, You need to provide a user whose log I should clear.')

#Run the threads
keep_alive()
client.run(client.token)
