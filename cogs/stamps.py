"""
Stamps and Weapons Guide Cog
"""
import discord
from discord.ext import commands
import json
from config import Config
from utils.helpers import get_type_color

class Stamps(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open('data/stamps.json', 'r') as f:
            self.stamps = json.load(f)
        with open('data/characters.json', 'r') as f:
            self.characters = json.load(f)
    
    @commands.command(name='stamp')
    async def stamp_info(self, ctx, *, name):
        """Get information about a specific stamp"""
        # Search in weapon stamps
        for stamp_id, stamp_data in self.stamps['weapon_stamps'].items():
            if name.lower() in stamp_id or name.lower() in stamp_data['name'].lower():
                embed = discord.Embed(
                    title=f"🗡️ {stamp_data['name']}",
                    description=f"**Type:** {stamp_data['type']}\n**Character:** {stamp_data['character']}",
                    color=Config.COLORS['default']
                )
                embed.add_field(name="📊 Main Stat", value=stamp_data['mainstat'], inline=True)
                embed.add_field(name="⭐ Bonus Stat", value=stamp_data['bonus_stat'], inline=True)
                embed.add_field(name="✨ Effect", value=stamp_data['effect'], inline=False)
                embed.add_field(name="🎯 Priority", value=stamp_data['priority'], inline=True)
                embed.add_field(name="💡 Recommendation", value=stamp_data['recommendation'], inline=False)
                await ctx.send(embed=embed)
                return
        
        await ctx.send(f"❌ Stamp '{name}' not found!")
    
    @commands.command(name='weapon')
    async def weapon_recommendation(self, ctx, *, character_name):
        """Get weapon stamp recommendations for a character"""
        # Find character
        char_data = None
        char_id = None
        search_lower = character_name.lower().replace(' ', '_')
        
        for cid, cdata in self.characters.items():
            if search_lower in cid or search_lower in cdata['name'].lower():
                char_data = cdata
                char_id = cid
                break
        
        if not char_data:
            await ctx.send(f"❌ Character '{character_name}' not found!")
            return
        
        weapon = char_data['weapon_stamps']
        
        embed = discord.Embed(
            title=f"🗡️ {char_data['name']} - Weapon Stamps",
            color=get_type_color(char_data['type'])
        )
        
        embed.add_field(name="Slot 1 (Exclusive)", value=weapon['slot_1'], inline=False)
        embed.add_field(name="Slot 2 (Alternative)", value=weapon['slot_2'], inline=False)
        embed.add_field(name="Pull Recommendation", value=weapon['pull_recommendation'], inline=False)
        embed.add_field(name="Priority", value=weapon['priority'], inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.command(name='core')
    async def core_stamps(self, ctx, stamp_type):
        """Get core stamp set information (slash/thrust/strike/spirit)"""
        stamp_type = stamp_type.lower()
        set_key = f"{stamp_type}_set"
        
        if set_key not in self.stamps['core_stamps']:
            await ctx.send("❌ Invalid type! Use: slash, thrust, strike, or spirit")
            return
        
        core = self.stamps['core_stamps'][set_key]
        
        embed = discord.Embed(
            title=f"🛡️ {core['name']}",
            description=f"**Type:** {core['bonus_type']}",
            color=get_type_color(core['bonus_type'])
        )
        
        embed.add_field(name="2-Piece Bonus", value=core['set_bonus_2'], inline=False)
        embed.add_field(name="4-Piece Bonus", value=core['set_bonus_4'], inline=False)
        
        slots_text = f"""
**Slot 1:** {core['slots']['1']}
**Slot 2:** {core['slots']['2']}
**Slot 3:** {core['slots']['3']}
        """
        embed.add_field(name="Recommended Main Stats", value=slots_text, inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name='substats')
    async def substats_priority(self, ctx, *, character_name):
        """Get substats priority for a character"""
        char_data = None
        search_lower = character_name.lower().replace(' ', '_')
        
        for cid, cdata in self.characters.items():
            if search_lower in cid or search_lower in cdata['name'].lower():
                char_data = cdata
                break
        
        if not char_data:
            await ctx.send(f"❌ Character '{character_name}' not found!")
            return
        
        substats = char_data['substats_priority']
        
        embed = discord.Embed(
            title=f"📊 {char_data['name']} - Substats Priority",
            color=get_type_color(char_data['type'])
        )
        
        priority_text = "\n".join([f"{i+1}. {sub}" for i, sub in enumerate(substats)])
        embed.description = f"```{priority_text}```"
        
        # Add explanations
        explanations = self.stamps['substats']['explanations']
        expl_text = ""
        for sub in substats[:3]:
            if sub in explanations:
                expl_text += f"**{sub}:** {explanations[sub]}\n"
        
        if expl_text:
            embed.add_field(name="💡 Why These?", value=expl_text, inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name='stamplist')
    async def list_stamps(self, ctx, stamp_type=None):
        """List all stamps (optionally filter by type: weapon/core)"""
        if stamp_type == 'weapon' or stamp_type is None:
            weapons = [f"{s['name']} ({s['character']})" for s in self.stamps['weapon_stamps'].values()]
            
            # Split into chunks if too long
            chunk_size = 20
            for i in range(0, len(weapons), chunk_size):
                chunk = weapons[i:i+chunk_size]
                embed = discord.Embed(
                    title=f"🗡️ Weapon Stamps {f'({i+1}-{min(i+chunk_size, len(weapons))})' if len(weapons) > chunk_size else ''}",
                    description="\n".join(chunk),
                    color=Config.COLORS['default']
                )
                await ctx.send(embed=embed)
        
        if stamp_type == 'core' or stamp_type is None:
            cores = [f"{s['name']} ({s['bonus_type']})" for s in self.stamps['core_stamps'].values()]
            embed = discord.Embed(
                title="🛡️ Core Stamp Sets",
                description="\n".join(cores),
                color=Config.COLORS['default']
            )
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Stamps(bot))
