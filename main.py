import discord
from discord.ext import commands
import json
import tbapy
import random

with open("config.json", "r+") as f:
	config = json.loads(f.read)

tba = tbapy.TBA(config["tba_token"])

class namebot(commands.Bot):

	def __init__(self,*args, **kwargs):
		super().__init__(*args,**kwargs)

		self.picked = []
		self.players = []
		self.channel = '347587893952512000'
		self.is_playing = False
		self.time = 0
		self.current_turn = 0
		self.lastdigit = 0



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
	bot.players.append(player)
	add_embed = discord.Embed()
	add_embed.description = "Players have been added to the game. See below for an updated player list."
	player_string = ""
	for player in bot.players:
		if len(player_string) > 1:
			player_string += ", "
		player_string += player.display_name
	add_embed.add_field(name="Players", value=player_string)
	add_embed.add_field(name="Current Player", value = bot.players[bot.current_turn].mention)
	add_embed.add_field(name="Current Number", value = bot.lastdigit)
	await ctx.send(embed=add_embed)


@bot.command()
async def startround(ctx):
	if bot.is_playing == True:
		await ctx.send("A game is currently going on! Wait till the players finish up to start again.")
		return
	bot.picked = []
	bot.players = []
	bot.players.append(ctx.author)
	bot.current_turn = 0
	for player in ctx.message.mentions:
		if player.bot:
			await ctx.send("You can't invite bot users!")
			continue
		bot.players.append(player)
	bot.is_playing = True
	num = random.randrange(0, 10)
	bot.lastdigit = num
	start_embed = discord.Embed(title="FRC Name Game")
	start_embed.description = "A game has been started! The info about the game is as follows:"
	start_embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
	player_string = ""
	for player in bot.players:
		if len(player_string) > 1:
			player_string += ", "
		player_string += player.display_name
	start_embed.add_field(name="Players", value = player_string)
	start_embed.add_field(name="Starting Number", value = num)
	start_embed.add_field(name = "Starting Player", value = bot.players[0].display_name)
	await ctx.send(embed=start_embed)


bot.run(config["discord_token"])