import time
import discord
from timeit import default_timer as timer
from discord.ui import View
import bot.cogs.geo_cog.geo_cog as geo
from discord.ui import Button
from bot.data.geo_repository import GeoGuessrRepository


class geo_view:
    def __init__(self, bot):
        self.bot = bot
        self.repo = GeoGuessrRepository()

    # Enable panning and zooming functionality for the 4 utility buttons
    @staticmethod
    async def navigate(interaction, view: View, args: dict, pan_and_zoom: list, users_clicked: list, user_id: int,
                       Pan_left: bool, Pan_right: bool, Zoom_in: bool, Zoom_out: bool) -> None:
        if user_id in users_clicked:
            return
        b1 = pan_and_zoom[0]
        b2 = pan_and_zoom[1]
        b3 = pan_and_zoom[2]
        b4 = pan_and_zoom[3]

        if Pan_left:
            args['headings'] = ((args['headings'] - 90) % 360)
        elif Pan_right:
            args['headings'] = ((args['headings'] + 90) % 360)
        elif Zoom_in:
            args['fovs'] = ((args['fovs'] - 40) % 360)
        elif Zoom_out:
            args['fovs'] = ((args['fovs'] + 40) % 360)

        passThis = {'heading': args['headings'],
                    'pitch': args['pitches'],
                    'fov': args['fovs'],
                    'key': args['api_key'],
                    'location': args['location'],
                    'size': args['size']}

        start = timer()
        container = geo.GeoGuessCOG.pull_street_view(passThis, geo.pic_base, geo.filename)
        end = timer()
        api_rest_time = (end - start) * 1000

        FN = container[0]
        quota_per_game = container[1]
        NE = geo.GeoGuessCOG.create_embed(FN, b3, b4, args, quota_per_game, api_rest_time)
        file1 = discord.File(fp=f'bot/cogs/geo_cog/tempAssets/{FN}', filename=FN)

        if quota_per_game <= 0:
            b1.disabled, b2.disabled, b3.disabled, b4.disabled = True, True, True, True

        await interaction.response.edit_message(embed=NE[0],
                                                attachments=[file1, NE[1]],
                                                view=view)

    # For the wrong answer
    async def incorrect(button: Button, view: View, users_clicked: list, user_id: int,
                        interaction: discord.Interaction):
        user_id = user_id
        if user_id in users_clicked:
            return
        users_clicked.append(user_id)
        button.style = discord.ButtonStyle.red
        await interaction.response.edit_message(view=view)

    # For the correct answer
    @staticmethod
    async def correct(interaction, initial_score: int, scoreDecay: int, users_clicked: list, pan_and_zoom: list,
                      OptionsList: list, view: View, country: str, cityname: str, userID: int, o1: Button) -> None:
        endScore = timer()
        final_Score = geo.GeoGuessCOG.decay_score(initial_score, scoreDecay, endScore)
        user_id = userID
        if user_id in users_clicked:
            return

        # Disable all zoom and pan functionality
        for button in pan_and_zoom:
            button.disabled = True

        # Display the correct and incorrect answers
        for button in OptionsList[0::]:
            if button != o1:
                button.style = discord.ButtonStyle.red
        o1.style = discord.ButtonStyle.green

        # Update user's score
        geo.GeoGuessCOG.update_user_score(user_id, final_Score)

        await interaction.response.edit_message(view=view)
        msg = await interaction.original_response()
        time.sleep(5)
        await msg.edit(view=None)

        await interaction.followup.send(content=f"{interaction.user.mention} got the right answer of "
                                                f"**{cityname}"
                                                f"{country}"
                                                f"** and won **{final_Score} points.** ")
