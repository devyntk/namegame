import asyncio
import json
import logging
import traceback
import os
import sys

import discord
import tbapy
from discord.ext import commands
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
		print("init")
		self.channels = {}
		#self.picked = []
		#self.players = []
		#self.strikes = {}
		#self.order = []
		#self.channel = 347585645536870400
		#self.time = None
		#self.current_turn = None
		#self.lastdigit = 0

		self.timer_loop = self.loop.create_task(self.timercheck())

	async def timercheck(self):
		await self.wait_until_ready()
		while not self.is_closed():
			if self.channels != {}:
				for channel in self.channels.keys():
					try:
						if self.channels[channel].time is not None:
							self.channels[channel].time -= 1
							print("Time Increment {0} in {1}".format(self.channels[channel].time, channel))

						if self.channels[channel].time == 15:
							timer_embed = discord.Embed()
							timer_embed.title = "Time is running out!"
							player_string = ""
							for player in bot.channels[channel].order:
								if len(player_string) > 1:
									player_string += ", "
								player_string += player.display_name
							timer_embed.add_field(name="Players", value=player_string)
							timer_embed.add_field(name="Current Player", value = bot.channels[channel].current_turn.mention)
							timer_embed.add_field(name="Current Number", value = bot.channels[channel].lastdigit)
							timer_embed.add_field(name="Time Left", value=bot.channels[channel].time)
							send_channel = bot.get_channel(channel)
							await send_channel.send(embed=timer_embed)

						if self.channels[channel].time == 0:
							send_channel = bot.get_channel(channel)
							await SkipPlayer(send_channel, bot.channels[channel].current_turn)
					except Exception as e:
						print(e)

				await asyncio.sleep(1)
			else:
				await asyncio.sleep(1)

class GameStatus(object):
	def __init__(self):
		self.picked = []
		self.strikes = {}
		self.order = []
		self.channel = 0
		self.time = None
		self.current_turn = None
		self.lastdigit = 0

bot = namebot(command_prefix='*')

@bot.listen()
async def on_ready():
	print("Logged in as {0}".format(bot.user))

#disabled temporarily, will add better ways of doing this without physically remove reactions because of input lag
#@bot.listen()
#async def on_reaction_add(reaction: discord.Reaction,user: discord.Member):
#	if user == bot.user:
#		return
#	if reaction.message.author == bot.user:
#		if user not in bot.channels[reaction.message.channel.id].order:
#			await reaction.message.remove_reaction(reaction.emoji, user)

#@bot.listen()
async def on_command_error(ctx,error: commands.CommandError):
	err_embed = discord.Embed()
	err_embed.title = "ERROR"
	err_embed.description = "The bot has encountered a unhandled error."
	err_embed.add_field(name="Error",value=error)
	traceback.print_tb(error.__traceback__)
	err_embed.add_field(name="Traceback",value=repr(traceback.extract_stack()))
	await ctx.send(embed=err_embed)

@bot.command()
async def addplayer(ctx):
	print(bot.channels[ctx.channel.id].players)
	for player in ctx.message.mentions:
		if player in bot.channels[ctx.channel.id].order:
			await ctx.send("Player {} is already in the game!".format(player.mention))
			continue
		elif player.bot:
			await ctx.send("You can't invite bot users!")
			continue
		bot.channels[ctx.channel.id].strikes[player] = 0
		bot.channels[ctx.channel.id].order.append(player)
	if bot.channels[ctx.channel.id].time is None:
		await ctx.send("There's not a game going on! Start one with `*startround`")
		return
	add_embed = discord.Embed()
	add_embed.description = "Players have been added to the game. See below for an updated player list."
	player_string = ""
	for player in bot.channels[ctx.channel.id].order:
		if len(player_string) > 1:
			player_string += ", "
		player_string += player.display_name
	add_embed.add_field(name="Players", value=player_string)
	add_embed.add_field(name="Current Player", value = bot.channels[ctx.channel.id].current_turn.mention)
	startdigit = bot.channels[ctx.channel.id].last_digit
	if startdigit == "0":
		startdigit = "Wildcard"
	add_embed.add_field(name="Current Number", value = startdigit)
	add_embed.add_field(name="Time Left", value=bot.channels[ctx.channel.id].time)
	await ctx.send(embed=add_embed)


@bot.command()
async def startround(ctx: commands.Context):
	try:
		if bot.channels[ctx.channel.id].time is not None:
			await ctx.send("A game is currently going on! Wait till the players finish up to start again.")
			return
	except:
		bot.channels[ctx.channel.id] = GameStatus()
		bot.channels[ctx.channel.id].picked = []
		bot.channels[ctx.channel.id].players = []
		bot.channels[ctx.channel.id].strikes[ctx.author] = 0
		bot.channels[ctx.channel.id].current_turn = ctx.author
		bot.channels[ctx.channel.id].order = []
		bot.channels[ctx.channel.id].order.append(ctx.author)
		bot.channels[ctx.channel.id].channel = ctx.channel.id
		bot.channels[ctx.channel.id].time = 60
		for player in ctx.message.mentions:
			if player.bot:
				await ctx.send("You can't invite bot users!")
				continue
			if player == ctx.author:
				await ctx.send("You can't invite yourself!")
				continue
			bot.channels[ctx.channel.id].strikes[player] = 0
			bot.channels[ctx.channel.id].order.append(player)
		bot.channels[ctx.channel.id].last_digit = 0
		start_embed = discord.Embed(title="FRC Name Game")
		start_embed.description = "A game has been started! The info about the game is as follows:"
		player_string = ""
		for player in bot.channels[ctx.channel.id].order:
			if len(player_string) > 1:
				player_string += ", "
			player_string += player.display_name
		start_embed.add_field(name="Players", value = player_string)
		start_embed.add_field(name="Time", value= bot.channels[ctx.channel.id].time)
		start_embed.add_field(name="Starting Number", value = "Wildcard")
		start_embed.add_field(name = "Starting Player", value = bot.channels[ctx.channel.id].current_turn.display_name)
		await ctx.send(embed=start_embed)


@bot.command()
async def pick(ctx: commands.Context, team, *name):
	name = " ".join(name)
	if ctx.author != bot.channels[ctx.channel.id].current_turn:
		if ctx.author in bot.channels[ctx.channel.id].order:
			await ctx.send("It's not your turn! You've been given a strike for this behaviour! Don't let it happen again...")
			bot.channels[ctx.channel.id].strikes[ctx.author] += 1
			if bot.channels[ctx.channel.id].strikes[ctx.author] >= 3:
				bot.channels[ctx.channel.id].order.remove(ctx.author)
				bot.channels[ctx.channel.id].strikes.pop(ctx.author)
				await ctx.send("Player {} is ELIMINATED!".format(ctx.author.mention))
		else:
			await ctx.send("Let the people playing play! If you want to join, ask one of the people currently playing to excute `{0}addplayer @{1}`".format(bot.command_prefix, ctx.author.display_name))
		return
	if team == None:
		await ctx.send("You have to actually say a team! The full command is `*pick <number> <name>`. You haven't been given a strike for this, and it's still your turn.")
		return
	if name == None:
		await ctx.send("You have to say a name too! The full command is `*pick <number> <name>`. You haven't been given a strike for this, and it's still your turn.")
		return
	if int(bot.channels[ctx.channel.id].last_digit) != 0:
		if str(team[0]) != str(bot.channels[ctx.channel.id].last_digit):
			print(team)
			print(bot.channels[ctx.channel.id].last_digit)
			await ctx.send("Your team doesn't start with the correct digit! Strike given, moving onto the next player!")
			await SkipPlayer(ctx.channel, ctx.author)
			return
	if team in bot.channels[ctx.channel.id].picked:
		await ctx.send("That team has already been picked! You have been skipped and given a strike.")
		await SkipPlayer(ctx.channel, ctx.author)
		return
	search_team = tba.team("frc"+team)
	try:
		search_team['key']
	except KeyError:
		await ctx.send("Team {0} doesn't exist! Strike given to the responsible player and player is skipped.".format(team))
		await SkipPlayer(ctx.channel, ctx.author)
		return
	ratio = fuzz.partial_ratio(search_team['nickname'].lower(), name.lower())
	print("Ratio: " + str(ratio))
	if ratio > 60:
		bot.channels[ctx.channel.id].picked.append(team)
		correct_embed = discord.Embed()
		correct_embed.title = "Team correct!"
		correct_embed.description = "Team {0} was {1}% correct! Moving onto the next player as follows. Click the red X to override this decision.".format(team, ratio)
		player_string = ""
		for player in bot.channels[ctx.channel.id].order:
			if len(player_string) > 1:
				player_string += ", "
			player_string += player.display_name
		correct_embed.add_field(name="Players", value=player_string)
		current_position = bot.channels[ctx.channel.id].order.index(bot.channels[ctx.channel.id].current_turn)
		try:
			bot.channels[ctx.channel.id].current_turn = bot.channels[ctx.channel.id].order[current_position + 1]
		except IndexError:
			bot.channels[ctx.channel.id].current_turn = bot.channels[ctx.channel.id].order[0]
		correct_embed.add_field(name="Current Player",value=bot.channels[ctx.channel.id].current_turn.mention)
		bot.channels[ctx.channel.id].last_digit = team[-1]
		bot.channels[ctx.channel.id].time = 60
		startdigit = bot.channels[ctx.channel.id].last_digit
		if startdigit == "0":
			startdigit = "Wildcard"
		correct_embed.add_field(name="Current Number", value=startdigit)
		correct_embed.add_field(name="Time Left",value=bot.channels[ctx.channel.id].time)
		correct_embed.add_field(name="Voting Time",value=20)
		msg = await ctx.send(embed=correct_embed)
		await msg.add_reaction('❌')
		await asyncio.sleep(1)
		votetime = 20
		while votetime > 0:
			if bot.channels[ctx.channel.id].time > 50:
				break
			msg = await ctx.get_message(msg.id)
			deny = 0
			for reaction in msg.reactions:
				if reaction.emoji == '❌':
					deny = reaction.count - 1
			if deny > .5 * len(bot.channels[ctx.channel.id].order):
				await ctx.send("The decision was overruled! Player {0} is given a strike!".format(ctx.author.mention))
				bot.channels[ctx.channel.id].strikes[ctx.author] += 1
				if bot.channels[ctx.channel.id].strikes[ctx.author] >= 3:
					bot.channels[ctx.channel.id].order.remove(ctx.author)
					bot.channels[ctx.channel.id].strikes.pop(ctx.author)
					await ctx.send("Player {} is ELIMINATED!".format(ctx.author.mention))
				return
			votetime -= 1
			correct_embed.set_field_at(4,name="Voting Time",value=votetime)
			await msg.edit(embed=correct_embed)
			await asyncio.sleep(1)

	else:
		bot.channels[ctx.channel.id].time = -1
		vote_embed = discord.Embed()
		vote_embed.title = "A vote is needed!"
		vote_embed.description = "A player has made a choice with less than 50% similarity. The details of the pick are below. Click on the two emoji to vote if this is correct or not. A 50% majority of players is required to accept it, otherwise the player will get a strike."
		vote_embed.add_field(name="Player",value=bot.channels[ctx.channel.id].current_turn.mention)
		vote_embed.add_field(name="Team",value=team)
		vote_embed.add_field(name="Said Name",value=name)
		vote_embed.add_field(name="Actual Name",value=search_team['nickname'])
		vote_embed.add_field(name="Similarity",value=str(ratio) + "%")
		vote_time = 60
		vote_embed.add_field(name="Voting Time",value=vote_time)
		msg = await ctx.send(embed=vote_embed)
		await msg.add_reaction('✅')
		await msg.add_reaction('❌')
		msg = await ctx.get_message(msg.id)
		await asyncio.sleep(1)
		while vote_time > 0:
			accept = 0
			deny = 0
			msg = await ctx.get_message(msg.id)
			for reaction in msg.reactions:
				if reaction.emoji == '✅':
					accept = reaction.count - 1
				if reaction.emoji == '❌':
					deny = reaction.count - 1
			if accept >= .5 * len(bot.channels[ctx.channel.id].order):
				bot.channels[ctx.channel.id].picked.append(team)
				correct_embed = discord.Embed()
				correct_embed.title = "Team correct!"
				correct_embed.description = "Team {0} was correct! Moving onto the next player as follows:".format(team)
				player_string = ""
				for player in bot.channels[ctx.channel.id].order:
					if len(player_string) > 1:
						player_string += ", "
					player_string += player.display_name
				correct_embed.add_field(name="Players", value=player_string)
				current_position = bot.channels[ctx.channel.id].order.index(bot.channels[ctx.channel.id].current_turn)
				try:
					bot.channels[ctx.channel.id].current_turn = bot.channels[ctx.channel.id].order[current_position + 1]
				except IndexError:
					bot.channels[ctx.channel.id].current_turn = bot.channels[ctx.channel.id].order[0]
				correct_embed.add_field(name="Current Player", value=bot.channels[ctx.channel.id].current_turn.mention)
				bot.channels[ctx.channel.id].last_digit = team[-1]
				bot.channels[ctx.channel.id].time = 60
				startdigit = bot.channels[ctx.channel.id].last_digit
				if startdigit == "0":
					startdigit = "Wildcard"
				correct_embed.add_field(name="Current Number", value=startdigit)
				correct_embed.add_field(name="Time Left", value=bot.channels[ctx.channel.id].time)
				await ctx.send(embed=correct_embed)
				return
			if deny >= .5 * len(bot.channels[ctx.channel.id].order):
				await ctx.send(
					"Team {0} was guessed wrong! Strike given to the responsible player and player is skipped.".format(
						team))
				await SkipPlayer(ctx.channel, ctx.author)
				return
			vote_time -= 1
			vote_embed.set_field_at(5, value = vote_time, name = "Voting Time")
			await msg.edit(embed=vote_embed)
			await asyncio.sleep(1)
		await ctx.send("The vote did not reach 50% fail or completion, so the responsible player is given a strike and skipped.")
		await SkipPlayer(ctx.channel, ctx.author)




async def SkipPlayer(channel, player: discord.Member):
	bot.channels[channel.id].strikes[player] += 1
	current_position = bot.channels[channel.id].order.index(bot.channels[channel.id].current_turn)
	try:
		bot.channels[channel.id].current_turn = bot.channels[channel.id].order[current_position + 1]
	except IndexError:
		bot.channels[channel.id].current_turn = bot.channels[channel.id].order[0]
	bot.channels[channel.id].time = 60
	player_string = ""
	for player in bot.channels[channel.id].order:
		if len(player_string) > 1:
			player_string += ", "
		player_string += player.display_name
	skip_embed = discord.Embed()
	skip_embed.title = "Player {0} was skipped and now has {1} strike(s)!".format(bot.channels[channel.id].order[current_position].display_name, bot.channels[channel.id].strikes[player])
	skip_embed.add_field(name="Players", value=player_string)
	try:
		skip_embed.add_field(name="Current Player", value=bot.channels[channel.id].current_turn.mention)
	except Exception as e:
		print(e)
	skip_embed.add_field(name="Current Number", value=bot.channels[channel.id].last_digit)
	skip_embed.add_field(name="Time Left", value=bot.channels[channel.id].time)
	send_channel = bot.get_channel(bot.channels[channel.id].channel)
	await send_channel.send(embed=skip_embed)
	if bot.channels[channel.id].strikes[player] > 2:
		bot.channels[channel.id].order.remove(player)
		bot.channels[channel.id].strikes.pop(player)
		await send_channel.send("Player {} is ELIMINATED!".format(player.mention))
	await check_win(channel.id)
	return

async def check_win(channel_id):
	if len(bot.channels[channel_id].order) == 1:
		win_embed = discord.Embed()
		win_embed.title = "We have a winner!"
		win_embed.add_field(name="Winning Player",value=bot.channels[channel_id].order[0])
		picked_string = ""
		for team in bot.channels[channel_id].picked:
			if len(picked_string) > 0:
				picked_string += ",  "
			picked_string += team
		if picked_string == "":
			picked_string = "No Picked Teams"
		win_embed.add_field(name="Teams Picked",value=picked_string)
		send_channel = bot.get_channel(bot.channels[channel_id].channel)
		await send_channel.send(embed=win_embed)
		bot.channels.pop(channel_id)


@bot.command()
async def gameinfo(ctx):
	try:
		time = bot.channels[ctx.channel.id].time
		info_embed = discord.Embed()
		info_embed.title = "Current Game Info"
		player_string = ""
		for player in bot.channels[ctx.channel.id].strikes.keys():
			if len(player_string) > 1:
				player_string += ", "
			player_string += "{0}:{1}".format(player.display_name, bot.channels[ctx.channel.id].strikes[player])
		info_embed.add_field(name="Strikes", value=player_string)
		startdigit = bot.channels[ctx.channel.id].last_digit
		if startdigit == "0":
			startdigit = "Wildcard"
		info_embed.add_field(name="Current Number", value=startdigit)
		info_embed.add_field(name="Current Player", value=bot.channels[ctx.channel.id].current_turn.display_name)
		info_embed.add_field(name="Time Left", value=bot.channels[ctx.channel.id].time)
		picked_string = ""
		for team in bot.channels[ctx.channel.id].picked:
			if len(picked_string) > 0:
				picked_string += ",  "
			picked_string += team
		if picked_string == "":
			picked_string = "No teams picked yet."
		info_embed.add_field(name="Teams Picked",value=picked_string)
		await ctx.send(embed=info_embed)
	except:
		await ctx.send("There's not a game going on right now. Go ahead and type `*startround` to start one.")

@bot.command()
async def info(ctx):
	game_embed = discord.Embed()
	game_embed.title="How to play"
	game_embed.description = "This is a very simple little game where players will name name a team number and name that starts with the last digit of the last named team. Some more specific rules are below:"
	game_embed.add_field(name="No Double Picking", value="Only pick teams once.")
	game_embed.add_field(name="Three Strikes, You're Out!",value="You are only allowed three strikes, which are given by picking out of turn, getting the team name wrong, picking a non existant team, being voted that your pick is incorrect, not picking in time, or picking a already picked team.")
	game_embed.add_field(name="No Cheatsy Doodles",value="No looking up teams on TBA or other methods, that's just unfair.")
	game_embed.add_field(name="Times up!", value="You have 60 seconds to make a pick, or you get skipped and get a strike.")
	game_embed.add_field(name="Shaking Things Up",value="Any team number that ends in a 0 mean that the next player has a wildcard, and can pick any legal team.")
	game_embed.add_field(name="Pesky Commands",value="To start a game, type *startround and mention the players you want to play with. You can add people with *addplayer. When it's your turn, type *pick <team> <teamname> to execute your pick. You can always do *gameinfo to get the current game status.")
	await ctx.send(embed=game_embed)

@bot.command()
async def restart(ctx):
	await ctx.send("Restarting Bot...")
	os.execl(sys.executable, sys.executable, *sys.argv)

bot.run(config["discord_token"])