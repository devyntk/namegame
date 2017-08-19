import discord
from discord.ext import commands
import json
import tbapy
import random
import asyncio
import logging
from fuzzywuzzy import fuzz

with open("config.json", "r+") as f:
	config = json.loads(f.read())

tba = tbapy.TBA(config["tba_token"])

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

class namebot(commands.Bot):

	def __init__(self,*args, **kwargs):
		super().__init__(*args,**kwargs)

		self.picked = []
		self.strikes = {}
		self.order = []
		self.channel = 347585645536870400
		self.time = None
		self.current_turn = None
		self.lastdigit = 0

		self.timer_loop = self.loop.create_task(self.timercheck())

	async def timercheck(self):
		await self.wait_until_ready()
		while not self.is_closed():
			if self.time is not None:
				self.time -= 1
				print("Time Increment {0}".format(self.time))
			if self.time == 15:
				timer_embed = discord.Embed()
				timer_embed.title = "Time is running out!"
				player_string = ""
				for player in bot.order:
					if len(player_string) > 1:
						player_string += ", "
					player_string += player.display_name
				timer_embed.add_field(name="Players", value=player_string)
				timer_embed.add_field(name="Current Player", value = bot.current_turn.mention)
				timer_embed.add_field(name="Current Number", value = bot.lastdigit)
				timer_embed.add_field(name="Time Left", value=bot.time)
				send_channel = bot.get_channel(bot.channel)
				await send_channel.send(embed=timer_embed)
			if self.time == 0:
				await SkipPlayer(bot.current_turn)
			await asyncio.sleep(1)


bot = namebot(command_prefix='*')

@bot.event
async def on_ready():
	print("Logged in as {0}".format(bot.user))

@bot.command()
async def addplayer(ctx):
	for player in ctx.message.mentions:
		if player in bot.players:
			await ctx.send("Player {} is already in the game!".format(player.mention))
			continue
		elif player.bot:
			await ctx.send("You can't invite bot users!")
			continue
		bot.strikes[player] = 0
		bot.order.append(player)
	if bot.time is None:
		await ctx.send("There's not a game going on! Start one with `*startround`")
		return
	add_embed = discord.Embed()
	add_embed.description = "Players have been added to the game. See below for an updated player list."
	player_string = ""
	for player in bot.order:
		if len(player_string) > 1:
			player_string += ", "
		player_string += player.display_name
	add_embed.add_field(name="Players", value=player_string)
	add_embed.add_field(name="Current Player", value = bot.current_turn.mention)
	add_embed.add_field(name="Current Number", value = bot.lastdigit)
	add_embed.add_field(name="Time Left", value=bot.time)
	await ctx.send(embed=add_embed)


@bot.command()
async def startround(ctx: commands.Context):
	if bot.time is not None:
		await ctx.send("A game is currently going on! Wait till the players finish up to start again.")
		return
	bot.picked = []
	bot.players = []
	bot.strikes[ctx.author] = 0
	bot.current_turn = ctx.author
	bot.order = []
	bot.order.append(ctx.author)
	bot.channel = ctx.channel.id
	bot.time = 60
	for player in ctx.message.mentions:
		if player.bot:
			await ctx.send("You can't invite bot users!")
			continue
		bot.strikes[player] = 0
		bot.order.append(player)
	num = 1
	bot.lastdigit = num
	start_embed = discord.Embed(title="FRC Name Game")
	start_embed.description = "A game has been started! The info about the game is as follows:"
	player_string = ""
	for player in bot.order:
		if len(player_string) > 1:
			player_string += ", "
		player_string += player.display_name
	start_embed.add_field(name="Players", value = player_string)
	start_embed.add_field(name="Starting Number", value = num)
	start_embed.add_field(name = "Starting Player", value = bot.current_turn.display_name)
	await ctx.send(embed=start_embed)


@bot.command()
async def pick(ctx, team, *name):
	if ctx.author != bot.current_turn:
		if ctx.author in bot.order:
			await ctx.send("It's not your turn! You've been given a strike for this behaviour! Don't let it happen again...")
			bot.strikes[ctx.author] += 1
			if bot.strikes[ctx.author] == 3:
				bot.order.remove(ctx.author)
				bot.strikes.pop(ctx.author)
				await ctx.send("Player {} is ELIMINATED!".format(ctx.author.mention))
		else:
			await ctx.send("Let the people playing play! If you want to join, ask one of the people currently playing to excute `{0}addplayer @{1}`".format(bot.command_prefix, ctx.author.display_name))
		return

	if str(team[0]) != str(bot.lastdigit):
		print(team)
		print(bot.lastdigit)
		await ctx.send("Your team doesn't start with the correct digit! Strike given, moving onto the next player!")
		await SkipPlayer(ctx.author)
		return
	search_team = tba.team("frc"+team)
	try:
		search_team['key']
	except KeyError:
		await ctx.send("Team {0} doesn't exist! Strike given to the responsible player and player is skipped.".format(team))
		await SkipPlayer(ctx.author)
		return
	ratio = fuzz.partial_ratio(name, search_team['nickname'])
	print(ratio)
	if ratio > 50:
		bot.picked.append(team)
		correct_embed = discord.Embed()
		correct_embed.title = "Team correct!"
		correct_embed.description = "Team {0} was correct! Moving onto the next player as follows:"
		player_string = ""
		for player in bot.order:
			if len(player_string) > 1:
				player_string += ", "
			player_string += player.display_name
		correct_embed.add_field(title="Players", value=player_string)
		current_position = bot.order.index(bot.current_turn)
		try:
			bot.current_turn = bot.order[current_position + 1]
		except IndexError:
			bot.current_turn = bot.order[0]
		correct_embed.add_field(title="Current Player",value=bot.current_turn.mention)
		bot.lastdigit = team[-1]
		bot.time = 60
		correct_embed.add_field(title="Current Number",value=bot.lastdigit)
		correct_embed.add_field(title="Time Left",value=bot.time)
		await ctx.send(embed=correct_embed)



async def SkipPlayer(player: discord.Member):
	bot.strikes[player] += 1
	if bot.strikes[player] == 3:
		bot.order.remove(player)
		bot.strikes.pop(player)
		send_channel = bot.get_channel(bot.channel)
		await send_channel.send("Player {} is ELIMINATED!".format(player.mention))
	current_position = bot.order.index(bot.current_turn)
	try:
		bot.current_turn = bot.order[current_position + 1]
	except IndexError:
		bot.current_turn = bot.order[0]
	bot.time = 60
	player_string = ""
	for player in bot.order:
		if len(player_string) > 1:
			player_string += ", "
		player_string += player.display_name
	skip_embed = discord.Embed()
	skip_embed.title = "Player {0} was skipped!".format(bot.order[current_position].display_name)
	skip_embed.add_field(name="Players", value=player_string)
	try:
		skip_embed.add_field(name="Current Player", value=bot.current_turn.display_name)
	except Exception as e:
		print(e)
	skip_embed.add_field(name="Current Number", value=bot.lastdigit)
	skip_embed.add_field(name="Time Left", value=bot.time)
	send_channel = bot.get_channel(bot.channel)
	await send_channel.send(embed=skip_embed)
	return

async def check_win():
	if len(bot.order) == 1:
		win_embed = discord.Embed()
		win_embed.title = "We have a winner!"
		win_embed.add_field(name="Winning Player",value=bot.order[0])
		picked_string = ""
		for team in bot.picked:
			if len(picked_string) > 0:
				picked_string += ",  "
			picked_string += team
		win_embed.add_field(name="Teams Picked",value=picked_string)
		send_channel = bot.get_channel(bot.channel)
		await send_channel.send(embed=win_embed)


bot.run(config["discord_token"])