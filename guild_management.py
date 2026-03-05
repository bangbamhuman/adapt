"""
Guild Management Cog
Handles check-ins, damage submissions (coop & guild challenge), leaderboards
"""
import discord
from discord.ext import commands
from datetime import datetime
from config import Config
from utils.database import db
from utils.helpers import (
    parse_damage, get_today_date, format_time_until_reset,
    check_permissions, get_member_role, get_role_emoji
)

class GuildManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==================== CHECK-IN SYSTEM ====================

    @commands.command(name='checkin')
    async def daily_checkin(self, ctx):
        """Daily check-in to maintain streak"""
        await db.get_or_create_member(ctx.author.id, ctx.author.name, ctx.author.display_name)
        
        result, error = await db.checkin(ctx.author.id)
        
        if error:
            await ctx.send(f"❌ {error}")
            return
        
        embed = discord.Embed(
            title="✅ Daily Check-in Successful!",
            description=f"**{ctx.author.display_name}** checked in today!",
            color=Config.COLORS['success']
        )
        embed.add_field(name="🔥 Current Streak", value=f"{result['streak']} days", inline=True)
        embed.add_field(name="🏆 Longest Streak", value=f"{result['longest']} days", inline=True)
        embed.add_field(name="📊 Total Check-ins", value=f"{result['total']}", inline=True)
        embed.set_footer(text=f"Next reset in: {format_time_until_reset()}")
        
        await ctx.send(embed=embed)

    @commands.command(name='streak')
    async def check_streak(self, ctx, member: discord.Member = None):
        """Check your or another member's check-in streak"""
        target = member or ctx.author
        
        member_data = await db.get_member(target.id)
        if not member_data:
            await ctx.send("❌ Member not found! They need to check in first.")
            return
        
        embed = discord.Embed(
            title=f"🔥 {target.display_name}'s Check-in Stats",
            color=Config.COLORS['default']
        )
        embed.add_field(name="Current Streak", value=f"{member_data[4]} days", inline=True)
        embed.add_field(name="Longest Streak", value=f"{member_data[5]} days", inline=True)
        embed.add_field(name="Total Check-ins", value=f"{member_data[7]}", inline=True)
        embed.add_field(name="Last Check-in", value=member_data[6] or "Never", inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name='leaderboard', aliases=['lb'])
    async def checkin_leaderboard(self, ctx):
        """Show check-in streak leaderboard"""
        leaderboard = await db.get_checkin_leaderboard(10)
        
        embed = discord.Embed(
            title="🏆 Check-in Leaderboard",
            description="Top 10 streaks",
            color=Config.COLORS['default']
        )
        
        for i, (username, streak, longest, total) in enumerate(leaderboard, 1):
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"#{i}")
            embed.add_field(
                name=f"{medal} {username}",
                value=f"🔥 {streak} days | 🏆 {longest} max | 📊 {total} total",
                inline=False
            )
        
        await ctx.send(embed=embed)

    # ==================== CO-OP DAMAGE SUBMISSION ====================

    @commands.command(name='coop')
    async def submit_coop(self, ctx, damage: str, boss_name: str):
        """Submit co-op damage (format: 20 = 20M, 200 = 200M) + attach screenshot"""
        if not ctx.message.attachments:
            await ctx.send("❌ You must attach a screenshot as proof!")
            return
        
        damage_raw, damage_display = parse_damage(damage)
        if damage_raw is None:
            await ctx.send("❌ Invalid damage format! Use numbers only (20 = 20M, 200 = 200M)")
            return
        
        proof_url = ctx.message.attachments[0].url
        role = get_member_role(ctx.author)
        
        if role == 'C':
            existing = await db.get_coop_submission(ctx.author.id)
            if existing:
                await ctx.send("❌ You already submitted co-op damage today! (Reset: 2:00 PM EST)")
                return
        
        await db.get_or_create_member(ctx.author.id, ctx.author.name, ctx.author.display_name)
        submission_id, error = await db.submit_coop(ctx.author.id, damage_raw, boss_name, proof_url)
        
        if error:
            await ctx.send(f"❌ {error}")
            return
        
        embed = discord.Embed(
            title="⚔️ Co-op Damage Submitted!",
            description=f"**{ctx.author.display_name}** dealt **{damage_display}** damage to **{boss_name}**!",
            color=Config.COLORS['success']
        )
        embed.set_image(url=proof_url)
        embed.set_footer(text=f"Submission ID: {submission_id} | Reset: 2:00 PM EST")
        
        await ctx.send(embed=embed)

    @commands.command(name='cooplb', aliases=['coopleaderboard'])
    async def coop_leaderboard(self, ctx):
        """Show today's co-op damage leaderboard"""
        submissions = await db.get_coop_leaderboard()
        
        if not submissions:
            await ctx.send("📭 No co-op submissions today yet!")
            return
        
        embed = discord.Embed(
            title="⚔️ Today's Co-op Damage Leaderboard",
            description=f"Reset in: {format_time_until_reset()}",
            color=Config.COLORS['default']
        )
        
        for i, (discord_id, username, damage, boss, proof, edited) in enumerate(submissions, 1):
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"#{i}")
            edited_mark = " ✏️" if edited else ""
            embed.add_field(
                name=f"{medal} {username}{edited_mark}",
                value=f"💥 {damage}M on {boss}",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @commands.command(name='coopdamage')
    async def view_coop_damage(self, ctx):
        """View all today's co-op submissions"""
        submissions = await db.get_coop_leaderboard()
        
        if not submissions:
            await ctx.send("📭 No co-op submissions today!")
            return
        
        embed = discord.Embed(
            title="📋 Today's Co-op Submissions",
            color=Config.COLORS['default']
        )
        
        for discord_id, username, damage, boss, proof, edited in submissions:
            edited_mark = " (edited)" if edited else ""
            embed.add_field(
                name=f"{username}{edited_mark}",
                value=f"{damage}M on {boss}\n[View Proof]({proof})",
                inline=True
            )
        
        await ctx.send(embed=embed)

    @commands.command(name='coopedit')
    async def edit_coop(self, ctx, member: discord.Member, new_damage: str):
        """[OFF] Edit a member's co-op submission"""
        if not check_permissions(ctx.author, 'OFF'):
            await ctx.send("❌ You need [OFF] or [O] role to use this command!")
            return
        
        damage_raw, damage_display = parse_damage(new_damage)
        if damage_raw is None:
            await ctx.send("❌ Invalid damage format!")
            return
        
        success = await db.edit_coop(member.id, damage_raw, ctx.author.name)
        
        if success:
            await ctx.send(f"✅ Updated {member.display_name}'s co-op damage to {damage_display}!")
        else:
            await ctx.send("❌ No submission found to edit!")

    @commands.command(name='coopdel')
    async def delete_coop(self, ctx, member: discord.Member):
        """[OFF] Delete a member's co-op submission"""
        if not check_permissions(ctx.author, 'OFF'):
            await ctx.send("❌ You need [OFF] or [O] role to use this command!")
            return
        
        success = await db.delete_coop(member.id)
        
        if success:
            await ctx.send(f"✅ Deleted {member.display_name}'s co-op submission!")
        else:
            await ctx.send("❌ No submission found to delete!")

    @commands.command(name='coopadd')
    async def add_coop(self, ctx, member: discord.Member, damage: str, *, boss_name):
        """[OFF] Add co-op submission for a member"""
        if not check_permissions(ctx.author, 'OFF'):
            await ctx.send("❌ You need [OFF] or [O] role to use this command!")
            return
        
        damage_raw, damage_display = parse_damage(damage)
        if damage_raw is None:
            await ctx.send("❌ Invalid damage format!")
            return
        
        existing = await db.get_coop_submission(member.id)
        if existing:
            await db.delete_coop(member.id)
        
        await db.get_or_create_member(member.id, member.name, member.display_name)
        submission_id, error = await db.submit_coop(member.id, damage_raw, boss_name, "Added by officer")
        
        if error:
            await db.delete_coop(member.id)
            submission_id, error = await db.submit_coop(member.id, damage_raw, boss_name, "Added by officer")
        
        await ctx.send(f"✅ Added co-op submission for {member.display_name}: {damage_display} on {boss_name}!")

    # ==================== GUILD CHALLENGE DAMAGE SUBMISSION ====================

    @commands.command(name='gc')
    async def submit_gc(self, ctx, damage: str, boss_name: str):
        """Submit guild challenge damage (format: 20 = 20M, 200 = 200M) + attach screenshot"""
        if not ctx.message.attachments:
            await ctx.send("❌ You must attach a screenshot as proof!")
            return
        
        damage_raw, damage_display = parse_damage(damage)
        if damage_raw is None:
            await ctx.send("❌ Invalid damage format! Use numbers only (20 = 20M, 200 = 200M)")
            return
        
        proof_url = ctx.message.attachments[0].url
        role = get_member_role(ctx.author)
        
        if role == 'C':
            existing = await db.get_gc_submission(ctx.author.id)
            if existing:
                await ctx.send("❌ You already submitted guild challenge damage today! (Reset: 2:00 PM EST)")
                return
        
        await db.get_or_create_member(ctx.author.id, ctx.author.name, ctx.author.display_name)
        submission_id, error = await db.submit_gc(ctx.author.id, damage_raw, boss_name, proof_url)
        
        if error:
            await ctx.send(f"❌ {error}")
            return
        
        embed = discord.Embed(
            title="🏰 Guild Challenge Damage Submitted!",
            description=f"**{ctx.author.display_name}** dealt **{damage_display}** damage to **{boss_name}**!",
            color=Config.COLORS['success']
        )
        embed.set_image(url=proof_url)
        embed.set_footer(text=f"Submission ID: {submission_id} | Reset: 2:00 PM EST")
        
        await ctx.send(embed=embed)

    @commands.command(name='gclb', aliases=['gcleaderboard'])
    async def gc_leaderboard(self, ctx):
        """Show today's guild challenge damage leaderboard"""
        submissions = await db.get_gc_leaderboard()
        
        if not submissions:
            await ctx.send("📭 No guild challenge submissions today yet!")
            return
        
        embed = discord.Embed(
            title="🏰 Today's Guild Challenge Leaderboard",
            description=f"Reset in: {format_time_until_reset()}",
            color=Config.COLORS['default']
        )
        
        for i, (discord_id, username, damage, boss, proof, edited) in enumerate(submissions, 1):
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"#{i}")
            edited_mark = " ✏️" if edited else ""
            embed.add_field(
                name=f"{medal} {username}{edited_mark}",
                value=f"💥 {damage}M on {boss}",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @commands.command(name='gcdamage')
    async def view_gc_damage(self, ctx):
        """View all today's guild challenge submissions"""
        submissions = await db.get_gc_leaderboard()
        
        if not submissions:
            await ctx.send("📭 No guild challenge submissions today!")
            return
        
        embed = discord.Embed(
            title="📋 Today's Guild Challenge Submissions",
            color=Config.COLORS['default']
        )
        
        for discord_id, username, damage, boss, proof, edited in submissions:
            edited_mark = " (edited)" if edited else ""
            embed.add_field(
                name=f"{username}{edited_mark}",
                value=f"{damage}M on {boss}\n[View Proof]({proof})",
                inline=True
            )
        
        await ctx.send(embed=embed)

    @commands.command(name='gcedit')
    async def edit_gc(self, ctx, member: discord.Member, new_damage: str):
        """[OFF] Edit a member's guild challenge submission"""
        if not check_permissions(ctx.author, 'OFF'):
            await ctx.send("❌ You need [OFF] or [O] role to use this command!")
            return
        
        damage_raw, damage_display = parse_damage(new_damage)
        if damage_raw is None:
            await ctx.send("❌ Invalid damage format!")
            return
        
        success = await db.edit_gc(member.id, damage_raw, ctx.author.name)
        
        if success:
            await ctx.send(f"✅ Updated {member.display_name}'s guild challenge damage to {damage_display}!")
        else:
            await ctx.send("❌ No submission found to edit!")

    @commands.command(name='gcdel')
    async def delete_gc(self, ctx, member: discord.Member):
        """[OFF] Delete a member's guild challenge submission"""
        if not check_permissions(ctx.author, 'OFF'):
            await ctx.send("❌ You need [OFF] or [O] role to use this command!")
            return
        
        success = await db.delete_gc(member.id)
        
        if success:
            await ctx.send(f"✅ Deleted {member.display_name}'s guild challenge submission!")
        else:
            await ctx.send("❌ No submission found to delete!")

    @commands.command(name='gcadd')
    async def add_gc(self, ctx, member: discord.Member, damage: str, *, boss_name):
        """[OFF] Add guild challenge submission for a member"""
        if not check_permissions(ctx.author, 'OFF'):
            await ctx.send("❌ You need [OFF] or [O] role to use this command!")
            return
        
        damage_raw, damage_display = parse_damage(damage)
        if damage_raw is None:
            await ctx.send("❌ Invalid damage format!")
            return
        
        existing = await db.get_gc_submission(member.id)
        if existing:
            await db.delete_gc(member.id)
        
        await db.get_or_create_member(member.id, member.name, member.display_name)
        submission_id, error = await db.submit_gc(member.id, damage_raw, boss_name, "Added by officer")
        
        if error:
            await db.delete_gc(member.id)
            submission_id, error = await db.submit_gc(member.id, damage_raw, boss_name, "Added by officer")
        
        await ctx.send(f"✅ Added guild challenge submission for {member.display_name}: {damage_display} on {boss_name}!")

    # ==================== MY DAMAGE ====================

    @commands.command(name='mydamage')
    async def my_damage(self, ctx):
        """View your today's submissions"""
        coop = await db.get_coop_submission(ctx.author.id)
        gc = await db.get_gc_submission(ctx.author.id)
        
        embed = discord.Embed(
            title=f"📊 {ctx.author.display_name}'s Today's Damage",
            color=Config.COLORS['default']
        )
        
        if coop:
            embed.add_field(
                name="⚔️ Co-op",
                value=f"{coop[3]}M on {coop[4]}",
                inline=False
            )
        else:
            embed.add_field(name="⚔️ Co-op", value="Not submitted", inline=False)
        
        if gc:
            embed.add_field(
                name="🏰 Guild Challenge",
                value=f"{gc[3]}M on {gc[4]}",
                inline=False
            )
        else:
            embed.add_field(name="🏰 Guild Challenge", value="Not submitted", inline=False)
        
        embed.set_footer(text=f"Reset in: {format_time_until_reset()}")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(GuildManagement(bot))