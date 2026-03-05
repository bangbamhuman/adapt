"""
Tier List Management Cog
Handles meta rankings with Officer/Owner management
"""
import discord
from discord.ext import commands
import json
from config import Config
from utils.helpers import get_tier_color, check_permissions, get_member_role

class TierList(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.load_data()
    
    def load_data(self):
        with open('data/tierlist.json', 'r') as f:
            self.tierlist = json.load(f)
        with open('data/characters.json', 'r') as f:
            self.characters = json.load(f)
    
    def save_data(self):
        with open('data/tierlist.json', 'w') as f:
            json.dump(self.tierlist, f, indent=2)
    
    def get_character_name(self, char_id):
        """Get character name from ID"""
        if char_id in self.characters:
            return self.characters[char_id]['name']
        return char_id
    
    @commands.command(name='tierlist')
    async def show_tierlist(self, ctx, category):
        """Display tier list for category (dps/tactic/support)"""
        category = category.lower()
        if category not in ['dps', 'tactic', 'support']:
            await ctx.send("❌ Invalid category! Use: dps, tactic, or support")
            return
        
        tiers = self.tierlist[category]
        
        embed = discord.Embed(
            title=f"📊 {category.upper()} Tier List",
            description=f"Last updated: {self.tierlist['last_updated']} by {self.tierlist['updated_by']}",
            color=Config.COLORS['default']
        )
        
        for tier_name in ['SS', 'S', 'A', 'B', 'C']:
            if tier_name in tiers and tiers[tier_name]:
                tier_chars = tiers[tier_name]
                char_list = []
                for char in tier_chars:
                    char_name = self.get_character_name(char['character_id'])
                    char_list.append(f"**{char_name}**\n*{char['explanation']}*")
                
                embed.add_field(
                    name=f"{tier_name} Tier",
                    value="\n\n".join(char_list),
                    inline=False
                )
        
        await ctx.send(embed=embed)
    
    @commands.command(name='tieradd')
    async def add_to_tier(self, ctx, category, tier, character_id, *, explanation):
        """[OFF] Add character to tier list"""
        if not check_permissions(ctx.author, 'OFF'):
            await ctx.send("❌ You need [OFF] or [O] role to use this command!")
            return
        
        category = category.lower()
        tier = tier.upper()
        
        if category not in ['dps', 'tactic', 'support']:
            await ctx.send("❌ Invalid category! Use: dps, tactic, or support")
            return
        
        if tier not in ['SS', 'S', 'A', 'B', 'C']:
            await ctx.send("❌ Invalid tier! Use: SS, S, A, B, or C")
            return
        
        # Check if character exists
        if character_id not in self.characters:
            await ctx.send(f"❌ Character '{character_id}' not found in database!")
            return
        
        # Add to tier
        new_entry = {
            'character_id': character_id,
            'explanation': explanation
        }
        
        if tier not in self.tierlist[category]:
            self.tierlist[category][tier] = []
        
        self.tierlist[category][tier].append(new_entry)
        self.tierlist['last_updated'] = discord.utils.format_dt(discord.utils.utcnow(), 'D')
        self.tierlist['updated_by'] = ctx.author.name
        self.save_data()
        
        await ctx.send(f"✅ Added {self.get_character_name(character_id)} to {tier} tier in {category}!")
    
    @commands.command(name='tierdel')
    async def remove_from_tier(self, ctx, category, tier, character_id):
        """[OFF] Remove character from tier list"""
        if not check_permissions(ctx.author, 'OFF'):
            await ctx.send("❌ You need [OFF] or [O] role to use this command!")
            return
        
        category = category.lower()
        tier = tier.upper()
        
        if category not in self.tierlist or tier not in self.tierlist[category]:
            await ctx.send("❌ Category or tier not found!")
            return
        
        tier_list = self.tierlist[category][tier]
        original_len = len(tier_list)
        
        self.tierlist[category][tier] = [
            char for char in tier_list 
            if char['character_id'] != character_id
        ]
        
        if len(self.tierlist[category][tier]) < original_len:
            self.tierlist['last_updated'] = discord.utils.format_dt(discord.utils.utcnow(), 'D')
            self.tierlist['updated_by'] = ctx.author.name
            self.save_data()
            await ctx.send(f"✅ Removed {self.get_character_name(character_id)} from {tier} tier!")
        else:
            await ctx.send("❌ Character not found in that tier!")
    
    @commands.command(name='tiermove')
    async def move_in_tier(self, ctx, category, character_id, from_tier, to_tier):
        """[OFF] Move character between tiers"""
        if not check_permissions(ctx.author, 'OFF'):
            await ctx.send("❌ You need [OFF] or [O] role to use this command!")
            return
        
        category = category.lower()
        from_tier = from_tier.upper()
        to_tier = to_tier.upper()
        
        # Find and remove from old tier
        char_data = None
        if from_tier in self.tierlist[category]:
            for char in self.tierlist[category][from_tier]:
                if char['character_id'] == character_id:
                    char_data = char
                    break
        
        if not char_data:
            await ctx.send(f"❌ Character not found in {from_tier} tier!")
            return
        
        # Remove from old
        self.tierlist[category][from_tier] = [
            char for char in self.tierlist[category][from_tier]
            if char['character_id'] != character_id
        ]
        
        # Add to new
        if to_tier not in self.tierlist[category]:
            self.tierlist[category][to_tier] = []
        
        self.tierlist[category][to_tier].append(char_data)
        self.tierlist['last_updated'] = discord.utils.format_dt(discord.utils.utcnow(), 'D')
        self.tierlist['updated_by'] = ctx.author.name
        self.save_data()
        
        await ctx.send(f"✅ Moved {self.get_character_name(character_id)} from {from_tier} to {to_tier}!")
    
    @commands.command(name='tieredit')
    async def edit_explanation(self, ctx, category, tier, character_id, *, new_explanation):
        """[OFF] Edit tier list explanation"""
        if not check_permissions(ctx.author, 'OFF'):
            await ctx.send("❌ You need [OFF] or [O] role to use this command!")
            return
        
        category = category.lower()
        tier = tier.upper()
        
        found = False
        if tier in self.tierlist[category]:
            for char in self.tierlist[category][tier]:
                if char['character_id'] == character_id:
                    char['explanation'] = new_explanation
                    found = True
                    break
        
        if found:
            self.tierlist['last_updated'] = discord.utils.format_dt(discord.utils.utcnow(), 'D')
            self.tierlist['updated_by'] = ctx.author.name
            self.save_data()
            await ctx.send(f"✅ Updated explanation for {self.get_character_name(character_id)}!")
        else:
            await ctx.send("❌ Character not found!")
    
    @commands.command(name='meta')
    async def show_meta(self, ctx):
        """Show current meta summary"""
        embed = discord.Embed(
            title="⚔️ Current Meta Summary",
            description="Top picks for each category",
            color=Config.COLORS['default']
        )
        
        for category in ['dps', 'tactic', 'support']:
            if 'SS' in self.tierlist[category] and self.tierlist[category]['SS']:
                chars = [self.get_character_name(c['character_id']) for c in self.tierlist[category]['SS']]
                embed.add_field(
                    name=f"{category.upper()} - SS Tier",
                    value="\n".join(chars),
                    inline=True
                )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(TierList(bot))
