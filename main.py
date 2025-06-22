import discord
from discord.ext import commands, tasks
import os
import datetime
import asyncio
from dotenv import load_dotenv
from keep_alive import keep_alive # For Render's internal web server pinging

load_dotenv() # Load environment variables from .env file

# Get token from environment variable
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
# Set bot prefix
bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

# --- Bot Events ---
@bot.event
async def on_ready():
    print(f'{bot.user.name} is online!')
    print(f'Bot ID: {bot.user.id}')
    await bot.change_presence(activity=discord.Game(name="!help | All-in-One"))
    print("Bot is ready!")

@bot.event
async def on_member_join(member):
    # Example Welcome message (customize channel ID and message)
    # Replace YOUR_WELCOME_CHANNEL_ID with the actual ID of your welcome channel
    welcome_channel_id = 123456789012345678 # <<< Apne welcome channel ki ID yahan daalein
    welcome_channel = bot.get_channel(welcome_channel_id)
    if welcome_channel:
        await welcome_channel.send(f"Welcome {member.mention} to the server! Please read the rules.")
    print(f"{member.name} joined the server.")

# --- Moderation Commands ---
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    await member.kick(reason=reason)
    await ctx.send(f'{member.mention} has been kicked for: {reason}' if reason else f'{member.mention} has been kicked.')

@kick.error
async def kick_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to kick members.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Please specify a member to kick. Usage: `!kick @user [reason]`")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f'{member.mention} has been banned for: {reason}' if reason else f'{member.mention} has been banned.')

@ban.error
async def ban_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to ban members.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Please specify a member to ban. Usage: `!ban @user [reason]`")

@bot.command()
@commands.has_permissions(moderate_members=True) # or manage_roles, kick_members etc.
async def timeout(ctx, member: discord.Member, minutes: int, *, reason=None):
    duration = datetime.timedelta(minutes=minutes)
    await member.timeout(duration, reason=reason)
    await ctx.send(f'{member.mention} has been timed out for {minutes} minutes for: {reason}' if reason else f'{member.mention} has been timed out for {minutes} minutes.')

@timeout.error
async def timeout_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to timeout members.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Please specify a member and duration (in minutes). Usage: `!timeout @user <minutes> [reason]`")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Invalid duration. Please provide minutes as a whole number.")

# --- Ticket System ---
# Ticket command (from previous example)
@bot.command()
async def ticket(ctx):
    if ctx.guild is None:
        await ctx.author.send("Tickets can only be created in a server.")
        return

    for channel in ctx.guild.channels:
        if isinstance(channel, discord.TextChannel) and channel.name == f"ticket-{ctx.author.id}":
            await ctx.send(f"You already have an open ticket channel: {channel.mention}")
            return

    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        ctx.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    try:
        channel = await ctx.guild.create_text_channel(
            f"ticket-{ctx.author.name.lower().replace(' ', '-')}-{ctx.author.discriminator}",
            overwrites=overwrites
        )
        await ctx.send(f"Your ticket has been created: {channel.mention}")
        await channel.send(f"Hello {ctx.author.mention}! Please describe your issue here. A staff member will be with you shortly.")
    except discord.Forbidden:
        await ctx.send("I don't have permission to create channels. Please check my role permissions.")
    except Exception as e:
        await ctx.send(f"An error occurred while creating your ticket: {e}")

# Ticket close command
@bot.command()
@commands.has_permissions(manage_channels=True)
async def close(ctx):
    if ctx.channel.name.startswith("ticket-"):
        await ctx.send("Closing this ticket in 5 seconds...")
        await ctx.channel.delete(delay=5)
    else:
        await ctx.send("This is not a ticket channel.")

# --- Giveaway Command (Simple) ---
@bot.command()
@commands.has_permissions(manage_channels=True)
async def gstart(ctx, time, winners: int, *, prize):
    try:
        # Convert time string (e.g., 10s, 5m, 1h) to seconds
        seconds = 0
        if time.endswith('s'):
            seconds = int(time[:-1])
        elif time.endswith('m'):
            seconds = int(time[:-1]) * 60
        elif time.endswith('h'):
            seconds = int(time[:-1]) * 3600
        else:
            await ctx.send("Invalid time format. Use s, m, or h (e.g., `10s`, `5m`, `1h`).")
            return

        embed = discord.Embed(
            title="🎉 Giveaway! 🎉",
            description=f"Prize: **{prize}**\nReact with 🎉 to enter!",
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"Ends in {time} | Winners: {winners}")
        
        msg = await ctx.send(embed=embed)
        await msg.add_reaction("🎉")

        await asyncio.sleep(seconds)

        new_msg = await ctx.channel.fetch_message(msg.id)
        users = [user for user in await new_msg.reactions[0].users().flatten() if user != bot.user]

        if not users:
            await ctx.send("No one reacted to the giveaway. No winner.")
            return

        # Randomly select winners
        selected_winners = []
        if len(users) <= winners:
            selected_winners = users
        else:
            selected_winners = random.sample(users, winners)

        winner_mentions = ", ".join([winner.mention for winner in selected_winners])

        winner_embed = discord.Embed(
            title="🎉 Giveaway Ended! 🎉",
            description=f"The winner(s) of **{prize}** is/are: {winner_mentions}!",
            color=discord.Color.green()
        )
        await ctx.send(embed=winner_embed)

    except ValueError:
        await ctx.send("Invalid input. Usage: `!gstart <time> <winners> <prize>` (e.g., `!gstart 10s 1 My Awesome Prize`)")
    except Exception as e:
        await ctx.send(f"An error occurred during the giveaway: {e}")

# --- Basic Ping Command ---
@bot.command()
async def ping(ctx):
    await ctx.send(f'Pong! {round(bot.latency * 1000)}ms')

# --- Error Handling ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have the necessary permissions to use this command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing arguments. Please check command usage. Example: `{bot.command_prefix}{ctx.command.name} {ctx.command.usage if ctx.command.usage else ''}`")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Invalid argument provided. Please check your input.")
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("That command does not exist.")
    else:
        print(f"An unhandled error occurred: {error}")
        # await ctx.send(f"An unexpected error occurred: {error}") # Uncomment for user-facing errors

# --- Music Commands (Requires `youtube_dl` and `ffmpeg`) ---
# Note: Music commands can be complex and might require more resources.
# For simplicity, a basic play command is provided, but full features
# like queue, skip, pause, resume would require more advanced handling
# and potentially a dedicated music bot library like Wavelink.

# Setup FFMPEG and YTDL
# Render will automatically install these if you add them to requirements.txt
# and ensure ffmpeg is in your system PATH (usually handled by Render).

# Ensure you have opus installed for voice (pip install PyNaCl)
# `pip install youtube_dl` and `pip install PyNaCl` for basic voice
# For more robust music, consider `pip install yt-dlp` and `pip install ffmpeg-python`
# You might also need to install ffmpeg directly in your Render build command.

# Simple global variable to hold voice client for now
voice_clients = {}

@bot.command()
async def join(ctx):
    if not ctx.message.author.voice:
        await ctx.send("You are not connected to a voice channel.")
        return
    channel = ctx.message.author.voice.channel
    try:
        if ctx.voice_client:
            await ctx.voice_client.move_to(channel)
        else:
            voice_clients[ctx.guild.id] = await channel.connect()
        await ctx.send(f"Joined voice channel: {channel.name}")
    except discord.ClientException as e:
        await ctx.send(f"I am unable to join the voice channel: {e}")
    except Exception as e:
        await ctx.send(f"An error occurred while joining: {e}")

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        del voice_clients[ctx.guild.id]
        await ctx.send("Left the voice channel.")
    else:
        await ctx.send("I am not in a voice channel.")

# NOTE: For playing actual music, you'll need a library like `yt-dlp` or `youtube_dl`
# and `ffmpeg` installed on the server. Render usually has ffmpeg.
# Playing music is often resource-intensive and might hit free tier limits.
# This is a very basic example.
@bot.command()
async def play(ctx, *, url):
    if not ctx.voice_client:
        await ctx.send("I am not in a voice channel. Use `!join` first.")
        return

    try:
        # If already playing, stop current playback
        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()

        # You'll need to configure youtube_dl options.
        # This part assumes you have youtube_dl installed.
        # This is a simplified example, for production, handle errors and options.
        # import youtube_dl
        # ytdl_format_options = {
        #     'format': 'bestaudio/best',
        #     'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        #     'restrictfilenames': True,
        #     'noplaylist': True,
        #     'nocheckcertificate': True,
        #     'ignoreerrors': False,
        #     'logtostderr': False,
        #     'quiet': True,
        #     'no_warnings': True,
        #     'default_search': 'auto',
        #     'source_address': '0.0.0.0', # bind to ipv4 since ipv6 can cause issues
        # }

        # with youtube_dl.YoutubeDL(ytdl_format_options) as ydl:
        #     info = ydl.extract_info(url, download=False)
        #     url2 = info['formats'][0]['url']
        #     source = discord.FFmpegPCMAudio(url2)
        #     ctx.voice_client.play(source, after=lambda e: print(f'Player error: {e}') if e else None)

        # For this example, let's just confirm it would play something.
        await ctx.send(f"Attempting to play: {url}")
        # To actually play, you need the youtube_dl and ffmpeg setup above.
        # As a placeholder, assuming you want to play a local file (won't work on Render directly)
        # source = discord.FFmpegPCMAudio('path/to/your/audio.mp3')
        # ctx.voice_client.play(source, after=lambda e: print(f'Player error: {e}') if e else None)

    except Exception as e:
        await ctx.send(f"An error occurred while trying to play: {e}")


# Run the bot
keep_alive() # Starts the web server for Render's internal health checks
bot.run(TOKEN)
                       
