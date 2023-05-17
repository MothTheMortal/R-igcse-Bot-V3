import nextcord as discord
import pymongo
import os
import functions

class ReputationDB:
    def __init__(self, link: str):
        self.client = pymongo.MongoClient(link, server_api=pymongo.server_api.ServerApi('1'))
        self.db = self.client.IGCSEBot
        self.reputation = self.db.reputation

    def bulk_insert_rep(self, rep_dict: dict, guild_id: int):
        # rep_dict = eval("{DICT}".replace("\n","")) to restore reputation from #rep-backup
        insertion = [{"user_id": user_id, "rep": rep, "guild_id": guild_id} for user_id, rep in rep_dict.items()]
        result = self.reputation.insert_many(insertion)
        return result

    def get_rep(self, user_id: int, guild_id: int):
        result = self.reputation.find_one({"user_id": user_id, "guild_id": guild_id})
        if result is None:
            return None
        else:
            return result

    def change_rep(self, user_id: int, new_rep: int, guild_id: int):
        result = self.reputation.update_one({"user_id": user_id, "guild_id": guild_id}, {"$set": {"rep": new_rep}})
        return new_rep

    def delete_user(self, user_id: int, guild_id: int):
        result = self.reputation.delete_one({"user_id": user_id, "guild_id": guild_id})
        return result

    def add_rep(self, user_id: int, guild_id: int):
        result = self.get_rep(user_id, guild_id)
        rep = result["rep"]
        if rep is None:
            rep = 1
            self.reputation.insert_one({"user_id": user_id, "guild_id": guild_id, "rep": rep})
        else:
            rep += 1
            self.change_rep(user_id, rep, guild_id)
        return rep

    def rep_leaderboard(self, guild_id):
        leaderboard = self.reputation.find({"guild_id": guild_id}, {"_id": 0, "guild_id": 0}).sort("rep", -1)
        return list(leaderboard)

repDB = ReputationDB(functions.preferences.LINK)

async def isThanks(text):
    alternatives = ['thanks', 'thank you', 'thx', 'tysm', 'thank u', 'thnks', 'tanks', "thanku", "tyvm", "thankyou"]
    if "ty" in text.lower().split():
        return True
    else:
        for alternative in alternatives:
            if alternative in text.lower():
                return True


async def isWelcome(text):
    alternatives = ["you're welcome", "your welcome", "ur welcome", "your welcome", 'no problem']
    alternatives_2 = ["np", "np!", "yw", "yw!"]
    if "welcome" == text.lower():
        return True
    else:
        for alternative in alternatives:
            if alternative in text.lower():
                return True
        for alternative in alternatives_2:
            if alternative in text.lower().split() or alternative == text.lower():
                return True
    return False


async def repMessages(message):
    repped = []
    if message.reference:
        msg = await message.channel.fetch_message(message.reference.message_id)

    if message.reference and msg.author != message.author and not msg.author.bot and not message.author.mentioned_in(
            msg) and (
            await isWelcome(message.content)):
        repped = [message.author]
    elif await isThanks(message.content):
        for mention in message.mentions:
            if mention == message.author:
                await message.channel.send(f"Uh-oh, {message.author.mention}, you can't rep yourself!")
            elif mention.bot:
                await message.channel.send(f"Uh-oh, {message.author.mention}, you can't rep a bot!")
            else:
                repped.append(mention)

    if repped:
        for user in repped:
            rep = repDB.add_rep(user.id, message.guild.id)
            if rep == 100 or rep == 500:
                role = discord.utils.get(user.guild.roles, name=f"{rep}+ Rep Club")
                await user.add_roles(role)
                await message.channel.send(f"Gave +1 Rep to {user.mention} ({rep})\nWelcome to the {rep}+ Rep Club!")
            else:
                await message.channel.send(f"Gave +1 Rep to {user} ({rep})")
        leaderboard = repDB.rep_leaderboard(message.guild.id)
        members = [list(item.values())[0] for item in leaderboard[:3]]  # Creating list of Reputed member ids
        role = discord.utils.get(message.guild.roles, name="Reputed")
        if [member.id for member in role.members] != members:  # If Reputed has changed
            for m in role.members:
                await m.remove_roles(role)
            for member in members:
                member = message.guild.get_member(member)
                await member.add_roles(role)