import discord
from discord.ext import commands
import asyncio
import yt_dlp
import os



intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True # إضافة هذه النية للتعامل مع القنوات الصوتية

bot = commands.Bot(command_prefix='!', intents=intents)

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0', # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    print(f'Bot ID: {bot.user.id}')
    print('------')

@bot.command(name='servername')
async def servername(ctx):
    if ctx.guild:
        await ctx.send(f'اسم هذا السيرفر هو: {ctx.guild.name}')
    else:
        await ctx.send('هذا الأمر يمكن استخدامه فقط داخل سيرفر.')

@bot.command(name='join', help='يجعل البوت ينضم إلى القناة الصوتية التي تتواجد فيها.')
async def join(ctx):
    if not ctx.message.author.voice:
        await ctx.send(f'{ctx.message.author.name} ليس متصلاً بأي قناة صوتية.')
        return
    
    channel = ctx.message.author.voice.channel
    await channel.connect()
    await ctx.send(f'انضممت إلى القناة الصوتية: {channel.name}')

@bot.command(name='leave', help='يجعل البوت يغادر القناة الصوتية.')
async def leave(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_connected():
        await voice_client.disconnect()
        await ctx.send('غادرت القناة الصوتية.')
    else:
        await ctx.send('البوت ليس متصلاً بأي قناة صوتية.')

@bot.command(name='play', help='يشغل أغنية من رابط يوتيوب.')
async def play(ctx, url):
    try:
        server = ctx.message.guild
        voice_channel = server.voice_client

        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
            voice_channel.play(player, after=lambda e: print(f'Player error: {e}') if e else None)
        await ctx.send(f'**الآن أقوم بتشغيل:** {player.title}')
    except Exception as e:
        await ctx.send(f'حدث خطأ أثناء تشغيل الأغنية: {e}')

@bot.command(name='pause', help='يوقف الأغنية مؤقتاً.')
async def pause(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        voice_client.pause()
        await ctx.send('تم إيقاف الأغنية مؤقتاً.')
    else:
        await ctx.send('لا توجد أغنية قيد التشغيل حالياً.')

@bot.command(name='resume', help='يستأنف تشغيل الأغنية.')
async def resume(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_paused():
        voice_client.resume()
        await ctx.send('تم استئناف تشغيل الأغنية.')
    else:
        await ctx.send('لا توجد أغنية متوقفة مؤقتاً.')

@bot.command(name='stop', help='يوقف تشغيل الأغنية تماماً.')
async def stop(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing() or voice_client.is_paused():
        voice_client.stop()
        await ctx.send('تم إيقاف تشغيل الأغنية.')
    else:
        await ctx.send('لا توجد أغنية قيد التشغيل أو متوقفة مؤقتاً.')

# لا تقم بتشغيل البوت هنا، سيتم تشغيله بواسطة Flask
bot.run(os.getenv('DISCORD_TOKEN'))

