import discord
from discord.ext import commands
import yt_dlp
import asyncio
from discord import app_commands, Object

current_song = None

intents = discord.Intents.default()
intents.message_content = True  # 메시지 내용 접근 활성화
bot = commands.Bot(command_prefix="!", intents=intents, reconnect=True, shard_count=2)

music_queue = []

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)
    print(f'봇이 온라인 상태입니다: {bot.user}')
    print('We have logged in as {0.user}'.format(bot))
    await bot.change_presence(status=discord.Status.online, activity=discord.Game("탑툰"))

async def play_next(ctx):
    """대기열에서 다음 곡 재생"""
    if len(music_queue) > 0:
        url, title = music_queue.pop(0)
        await play_music(ctx, url, title)
    else:
        await ctx.send("🎶 음악이 끝났습니다. 대기열이 비었습니다.")

async def play_music(ctx, url, title):
    """YouTube URL 음악 재생"""
    global current_song
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'extract_flat': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info['url']
        art_url = info.get('thumbnail')  
        duration = info['duration']

    ffmpeg_options = {
        'options': '-vn -f wav', 
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    }

    if not ctx.guild.voice_client:
        channel = ctx.author.voice.channel
        await channel.connect()

    if ctx.guild.voice_client.is_playing():
        ctx.guild.voice_client.stop()

    audio_source = discord.FFmpegPCMAudio(audio_url, **ffmpeg_options)
    ctx.guild.voice_client.play(audio_source, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))

    if not current_song:
        list_add_embed = discord.Embed(title='노래 재생', description='어 유니키야~', color=0xE2A8F2)
        list_add_embed.set_image(url=art_url)
        list_add_embed.add_field(name='제목', value=title, inline=False)
        list_add_embed.add_field(name='링크', value=f'[노래 링크]({url})', inline=False)
        await ctx.followup.send(embed=list_add_embed)

    current_song = {
        'title': title,
        'url': url,
        'art_url': art_url,
        'duration': duration
    }

@bot.command()
async def p(ctx, *, title: str):
    """음악 제목으로 검색하여 재생"""
    if not ctx.author.voice:
        await ctx.send("음성 채널에 먼저 접속해주세요.")
        return

    ydl_opts = {
        'quiet': False,
        'extract_flat': True,
        'default_search': 'auto'
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_results = ydl.extract_info(f"ytsearch:{title}", download=False)
            art_url = search_results.get('thumbnail')
            if search_results and 'entries' in search_results:
                video = search_results['entries'][0]
                url = video['url']
                if ctx.voice_client and ctx.voice_client.is_playing():
                    music_queue.append((url, video['title']))
                    search_results = ydl.extract_info(url, download=False)
                    art_url = search_results.get('thumbnail')
                    list_add_embed = discord.Embed(title='대기열 추가', description='어 유니키야~', color=0xE2A8F2)
                    list_add_embed.set_image(url=art_url)
                    list_add_embed.add_field(name = '제목', value = video['title'], inline=False)
                    list_add_embed.add_field(name = '링크', value = f'[노래 링크]({url})', inline=False)
                    await ctx.send(embed=list_add_embed)
                else:
                    await play_music(ctx, url, video['title'])
            else:
                await ctx.send(f"검색된 결과가 없습니다: {title}")
    except Exception as e:
        await ctx.send(f"오류 발생: {str(e)}")
        print(f"오류 발생: {str(e)}")

@bot.command()
async def stop(ctx):
    """음악 정지 및 봇 퇴장"""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("음악을 멈추고 음성 채널에서 퇴장했습니다.")
    else:
        await ctx.send("봇이 음성 채널에 연결되어 있지 않습니다.")

@bot.command()
async def skip(ctx):
    """음악 건너뛰기"""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭ 음악을 건너뜁니다.")
    else:
        await ctx.send("현재 재생 중인 음악이 없습니다.")

@bot.command()
async def list(ctx):
    """대기 중인 음악 목록 보기"""
    if not music_queue:
        await ctx.send("🎵 현재 대기열에 음악이 없습니다.")
    else:

        embed = discord.Embed(title="대기열", description="현재 대기 중인 음악 목록이야", color=0xE2A8F2)
        
        for idx, (url, title) in enumerate(music_queue):
            embed.add_field(name=f"{idx + 1}. {title}", value=f"[노래 링크]({url})", inline=False)
        embed.set_image(url="https://i.pinimg.com/736x/dc/89/9b/dc899b8322e1e5cf16f00fa81e9d1921.jpg")

        await ctx.send(embed=embed)
            
@bot.command()
async def now(ctx):
    """현재 재생 중인 곡에 대한 정보를 임베드로 표시"""
    if current_song:
        song = current_song
        minutes, seconds = divmod(song['duration'], 60)
        time_str = f"{minutes}분 {seconds}초"
        embed = discord.Embed(title=f"**{song['title']}** 재생 중", description='유니, 탑툰보는 중이야. 그만 불러!', color=0xE2A8F2)
        embed.set_image(url=song['art_url'])
        embed.add_field(name="제목", value=song['title'], inline=False)
        embed.add_field(name="길이", value=time_str)
        embed.add_field(name="링크", value=f"[노래 링크]({song['url']})", inline=False)

        await ctx.send(embed=embed)
    else:
        await ctx.send("🎵 현재 재생 중인 곡이 없습니다.")

@bot.command()
async def 헤응(ctx):
    await ctx.send("헤응")
    await ctx.send("https://youtu.be/5gLeYFZjuFE?si=ZmnAxoseXhdvuj0G&t=64")

@bot.tree.command(name="재생", description="노래를 재생합니다.")
@app_commands.describe(song_name="노래 제목")
async def slash_play_music(interaction: discord.Interaction, song_name: str):

    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("음성 채널에 먼저 접속해주세요.")
        return

    voice_channel = interaction.user.voice.channel


    if not interaction.guild.voice_client:
        await voice_channel.connect()


    ydl_opts = {
        'quiet': False,
        'extract_flat': True,
        'default_search': 'auto'
    }

    try:
        await interaction.response.defer() 

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_results = ydl.extract_info(f"ytsearch:{song_name}", download=False)

            if search_results and 'entries' in search_results:
                video = search_results['entries'][0]
                url = video['url']
                title = video['title']
                thumbnail_url = video.get('thumbnail')

                voice_client = interaction.guild.voice_client
                if voice_client and voice_client.is_playing():

                    music_queue.append((url, title))
                    search_results = ydl.extract_info(url, download=False)
                    thumbnail_url = search_results.get('thumbnail')
                    embed = discord.Embed(
                        title="대기열 추가", 
                        description="아래 노래가 대기열에 추가되었습니다.", 
                        color=0xE2A8F2
                    )
                    embed.set_image(url=thumbnail_url)
                    embed.add_field(name="제목", value=title, inline=False)
                    embed.add_field(name="링크", value=f"[바로가기]({url})", inline=False)
                    await interaction.followup.send(embed=embed)
                else:

                    await play_music(interaction, url, title)
            else:
                await interaction.followup.send(f"검색된 결과가 없습니다: {song_name}")

    except Exception as e:
        await interaction.followup.send(f"오류 발생: {str(e)}")
        print(f"오류 발생: {str(e)}")


    

bot.run("MTMyMzczMTE1OTkyNjE3Nzg3Mw.GUS6kw.fbfnBEMEHhsaiI00gXTd395XRDtRMsfSW7vVhs")