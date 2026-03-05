"""
Team Coordination Cog
Handles events, roster management, and support coordination
"""
import discord
from discord.ext import commands
from datetime import datetime
from config import Config
from utils.database import db
from utils.helpers import check_permissions

class TeamCoordination(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==================== EVENT MANAGEMENT ====================

    @commands.group(name='event')
    async def event_group(self, ctx):
        """Event management commands"""
        if ctx.invoked_subcommand is None:
            await ctx.send("Use `!event create`, `!event join`, `!event list`, or `!event roster`")

    @event_group.command(name='create')
    async def create_event(self, ctx, name, event_time, event_type="Guild Event"):
        """[OFF] Create a new guild event"""
        if not check_permissions(ctx.author, 'OFF'):
            await ctx.send("❌ You need [OFF] or [O] role to create events!")
            return

        event_id = await db.create_event(name, event_type, event_time, ctx.author.id)

        embed = discord.Embed(
            title="📅 Event Created!",
            description=f"**{name}**\nType: {event_type}\nTime: {event_time}",
            color=Config.COLORS['success']
        )
        embed.add_field(name="Event ID", value=event_id, inline=True)
        embed.add_field(name="Created by", value=ctx.author.display_name, inline=True)
        embed.set_footer(text=f"Join with: !event join {event_id} <role>")

        await ctx.send(embed=embed)

    @event_group.command(name='join')
    async def join_event(self, ctx, event_id: int, role, *, character):
        """Join an event with a specific role and character"""
        event = await db.get_event(event_id)
        if not event:
            await ctx.send("❌ Event not found!")
            return

        await db.join_event(event_id, ctx.author.id, role, character)

        await ctx.send(f"✅ {ctx.author.display_name} joined **{event[1]}** as **{role}** with **{character}**!")

    @event_group.command(name='leave')
    async def leave_event(self, ctx, event_id: int):
        """Leave an event"""
        # Implementation would remove from database
        await ctx.send(f"✅ {ctx.author.display_name} left the event!")

    @event_group.command(name='roster')
    async def event_roster(self, ctx, event_id: int):
        """View event participants"""
        event = await db.get_event(event_id)
        if not event:
            await ctx.send("❌ Event not found!")
            return

        participants = await db.get_event_participants(event_id)

        embed = discord.Embed(
            title=f"📋 {event[1]} - Participants",
            description=f"Type: {event[2]} | Time: {event[3]}",
            color=Config.COLORS['default']
        )

        if participants:
            for username, role, character, confirmed in participants:
                status = "✅" if confirmed else "⏳"
                embed.add_field(
                    name=f"{status} {username}",
                    value=f"Role: {role}\nCharacter: {character}",
                    inline=True
                )
        else:
            embed.description += "\n\nNo participants yet!"

        await ctx.send(embed=embed)

    @event_group.command(name='list')
    async def list_events(self, ctx):
        """List all active events"""
        # Would query active events from DB
        embed = discord.Embed(
            title="📅 Active Events",
            color=Config.COLORS['default']
        )
        embed.description = "Use `!event roster <id>` to view details"
        await ctx.send(embed=embed)

    # ==================== ROSTER MANAGEMENT ====================

    @commands.command(name='roster')
    async def view_roster(self, ctx, member: discord.Member = None):
        """View your or another member's character roster"""
        target = member or ctx.author

        roster = await db.get_roster(target.id)

        if not roster:
            await ctx.send(f"📭 {target.display_name} has no characters in their roster! Use `!setroster` to add.")
            return

        embed = discord.Embed(
            title=f"🎭 {target.display_name}'s Character Roster",
            color=Config.COLORS['default']
        )

        for char_id, boundary in roster:
            embed.add_field(
                name=char_id.replace('_', ' ').title(),
                value=f"Boundary: {boundary}",
                inline=True
            )

        await ctx.send(embed=embed)

    @commands.command(name='setroster')
    async def set_roster(self, ctx, character_id, boundary):
        """Add or update a character in your roster"""
        await db.get_or_create_member(ctx.author.id, ctx.author.name, ctx.author.display_name)
        await db.add_to_roster(ctx.author.id, character_id, boundary)

        await ctx.send(f"✅ Added **{character_id}** at **{boundary}** to your roster!")

    @commands.command(name='delroster')
    async def remove_from_roster(self, ctx, character_id):
        """Remove a character from your roster"""
        # Would implement delete in database
        await ctx.send(f"✅ Removed **{character_id}** from your roster!")

    # ==================== SUPPORT COORDINATION ====================

    @commands.command(name='support')
    async def offer_support(self, ctx, *, character):
        """Offer a support character for guild use"""
        # Would add to support pool in database
        await ctx.send(f"✅ {ctx.author.display_name} is offering **{character}** as support!")

    @commands.command(name='need')
    async def request_support(self, ctx, *, character):
        """Request a support character"""
        # Would query who has the character
        await ctx.send(f"📢 {ctx.author.display_name} is looking for **{character}** support!")

    @commands.command(name='supports')
    async def list_supports(self, ctx):
        """List all available support characters"""
        embed = discord.Embed(
            title="🤝 Available Supports",
            description="Guild members offering support characters",
            color=Config.COLORS['default']
        )
        # Would query from database
        await ctx.send(embed=embed)

    # ==================== TEAM BUILDER ====================

    @commands.command(name='team')
    async def suggest_team(self, ctx, *, content_type):
        """Get team composition suggestions"""
        teams = {
            'slash': ['Ichigo (Bankai)', 'Kisuke', 'Byakuya'],
            'thrust': ['Ikkaku', 'Tosen', 'Nelliel'],
            'strike': ['Yoruichi', 'Kenpachi', 'Sajin'],
            'spirit': ['Toshiro', 'Aizen', 'Rukia'],
            'freeze': ['Toshiro', 'Rukia', 'Kisuke'],
            'wound': ['Ikkaku', 'Tosen', 'Gin']
        }

        content_type = content_type.lower()
        if content_type not in teams:
            available = ', '.join(teams.keys())
            await ctx.send(f"❌ Unknown team type! Available: {available}")
            return

        embed = discord.Embed(
            title=f"⚔️ {content_type.upper()} Team Composition",
            description=' > '.join(teams[content_type]),
            color=Config.COLORS['default']
        )
        embed.set_footer(text="Use `!char <name>` for build details")

        await ctx.send(embed=embed)

    @commands.command(name='findmember')
    async def find_member_with_char(self, ctx, *, character):
        """Find guild members who have a specific character"""
        # Would search all rosters in database
        await ctx.send(f"🔍 Searching for members with **{character}**...")

async def setup(bot):
    await bot.add_cog(TeamCoordination(bot))
