import asyncio
import discord
import discord.ui
import math
import nest_asyncio
import random
from bot.cogs.geo_cog.streetviewrandomizer.street_view_static_api import StreetViewStaticApi
from bot.data.georepository import GeoRepository
from timeit import default_timer as timer
from PIL import Image

nest_asyncio.apply()

FILE_NAME = 'StreetView.jpg'
PIC_BASE = 'https://maps.googleapis.com/maps/api/streetview?'


class GeoView(discord.ui.View):
    def __init__(self, args: dict, labels: dict, city_name: str):
        super().__init__()
        self.repo = GeoRepository()
        self.quota = 10
        self.location_params = {
            'heading':  args['headings'],
            'pitch':    args['pitches'],
            'fov':      args['fovs'],
            'key':      args['api_key'],
            'location': args['location'],
            'size':     args['size'],
            'city':     city_name
        }
        self.users_clicked: list = []
        # Add country options upon initialization
        self.options: list = [CountryBTN(self, labels['labels'][x], labels['emojis'][x], "correct") if x == 0 else
                              CountryBTN(self, labels['labels'][x], labels['emojis'][x], f"incorrect{x}")
                              for x in range(5)]
        random.shuffle(self.options)
        for i in range(5):
            self.add_item(self.options[i])

    # Functions #
    @staticmethod
    def crop_image(image_path: str, crop_height: int = 10) -> None:
        """
        Crop out the lower 10 pixels of the image.
        :param image_path: String path of the image on the computer.
        :param crop_height: Amount to be cropped.
        """
        img = Image.open(image_path)
        width, height = img.size
        box = (10, 10, width, height - crop_height)
        cropped_img = img.crop(box)
        cropped_img.save("bot/cogs/geo_cog/temp_assets/StreetView.jpg", 'JPEG')

    def has_user_answered(self, user_id: int) -> bool:
        """
        Search through list to see if a user has already answered.
        :param user_id: User's id.
        :return: True if so, false if not.
        """
        if user_id in self.users_clicked:
            return True
        return False

    async def create_embed(self, api_rest_time: float, interacted: str) -> tuple[discord.Embed, discord.File]:
        """
        Create the embed which displays the game.
        :param api_rest_time: API response time.
        :param interacted: Last user that interacted with nav controls.
        :return: A tuple of the embed, and the asset file used in it.
        """
        temp_file = ""
        self.crop_image(f'bot/cogs/geo_cog/temp_assets/{FILE_NAME}')
        new_embed = discord.Embed(title="Geoguessr challenge time!",
                                  description="Can you guess where this is? 1 guess per user.",
                                  color=0xF56600)
        new_embed.set_image(url=f"attachment://{FILE_NAME}")
        new_embed.add_field(name="", value=f'Moves Left: **{self.quota}**', inline=True)
        new_embed.set_author(name="Geoguessr by yeet.us",
                             icon_url="https://i.imgur.com/ZyGOyTg.png")
        new_embed.set_footer(text=f"{round(api_rest_time)} ms. Use \"?geoguess lb\" for the GeoguessrLeaderboard.",
                             icon_url="https://i.imgur.com/Y4gnqiV.png")
        if len(interacted) > 1:
            new_embed.set_footer(text=f"{round(api_rest_time)} ms. {interacted}",
                                 icon_url="https://i.imgur.com/Y4gnqiV.png")

        # Adjust thumbnail to account for compass direction
        match self.location_params['heading']:
            case 0:
                temp_file = 'northward.png'
            case 90:
                temp_file = 'eastward.png'
            case 180:
                temp_file = 'southward.png'
            case _:
                temp_file = 'westward.png'

        asset_file = discord.File(f'bot/cogs/geo_cog/assets/{temp_file}', filename=temp_file)
        new_embed.set_thumbnail(url=f'attachment://{temp_file}')
        return new_embed, asset_file

    def disable_btns(self, disable: bool):
        """
        Disables all navigation buttons, can enable them if "disable" is set to false.
        :return: void
        """
        [x for x in self.children if x.custom_id == "left"][0].disabled = disable
        [x for x in self.children if x.custom_id == "right"][0].disabled = disable
        [x for x in self.children if x.custom_id == "zoom_in"][0].disabled = disable
        [x for x in self.children if x.custom_id == "zoom_out"][0].disabled = disable

    def verify_quota(self) -> bool:
        """
        :return: Check to see if api quota is exceeded, disable buttons if so.
        """
        if self.quota <= 0:
            self.disable_btns(True)
            return False
        return True

    def verify_zoom(self, current: int) -> bool:
        """
        Verify and disable buttons in the event that zoom limit is violated.
        :param current: Integer representing the zoom level.
        :return: True if limits are not exceeded, false otherwise.
        """
        if current >= 145:
            [x for x in self.children if x.custom_id == "zoom_out"][0].disabled = True
            [x for x in self.children if x.custom_id == "zoom_in"][0].disabled = False
            return False
        elif current <= 35:
            [x for x in self.children if x.custom_id == "zoom_out"][0].disabled = False
            [x for x in self.children if x.custom_id == "zoom_in"][0].disabled = True
            return False
        else:
            [x for x in self.children if x.custom_id == "zoom_out"][0].disabled = False
            [x for x in self.children if x.custom_id == "zoom_in"][0].disabled = False
            return True

    """
    Navigation and Answer Buttons
    Create the row of image navigation options and answer options.
    """
    @discord.ui.button(label="Turn LEFT", style=discord.ButtonStyle.secondary, emoji="👈", row=1, custom_id="left")
    async def turn_left(self, interaction: discord.Interaction, button: discord.ui.button):
        await interaction.response.defer()
        if not button.disabled and not self.has_user_answered(interaction.user.id):
            await self.utility_btn_callback(interaction, 'heading', -90)

    @discord.ui.button(label="Turn RIGHT", style=discord.ButtonStyle.secondary, emoji="👉", row=1, custom_id="right")
    async def turn_right(self, interaction: discord.Interaction, button: discord.ui.button):
        await interaction.response.defer()
        if not button.disabled and not self.has_user_answered(interaction.user.id):
            await self.utility_btn_callback(interaction, 'heading', 90)

    @discord.ui.button(label="Zoom IN", style=discord.ButtonStyle.secondary, emoji="🔍", row=1, custom_id="zoom_in")
    async def zoom_in(self, interaction: discord.Interaction, button: discord.ui.button):
        await interaction.response.defer()
        # Keep zoom within maximum
        if not button.disabled and not self.has_user_answered(interaction.user.id):
            await self.utility_btn_callback(interaction, 'fov', -20)

    @discord.ui.button(label="Zoom OUT", style=discord.ButtonStyle.secondary, emoji="🔭", row=1, custom_id="zoom_out")
    async def zoom_out(self, interaction: discord.Interaction, button: discord.ui.button):
        await interaction.response.defer()
        # Keep zoom within maximum
        if not button.disabled and not self.has_user_answered(interaction.user.id):
            await self.utility_btn_callback(interaction, 'fov', 20)

    async def utility_btn_callback(self, interaction: discord.Interaction, parameter: str, amount: int) -> None:
        # Prevent FOV buttons from exceeding limits.
        fov_check: bool = True
        if parameter == "fov":
            if not self.verify_zoom((self.location_params['fov'] + amount) % 360):
                fov_check = False

        if fov_check:
            self.location_params[parameter] = ((self.location_params[parameter] + amount) % 360)
            if self.verify_quota() and interaction.user.id not in self.users_clicked:
                raw_image, api_response = await StreetViewStaticApi.geolocate(self.quota, PIC_BASE,
                                                                              FILE_NAME, self.location_params)
                embed, other_image_assets = await self.create_embed(api_response, f"{interaction.user.display_name} "
                                                                                  f"adjusted {parameter}")
                country_sv = discord.File(fp=f'bot/cogs/geo_cog/temp_assets/{FILE_NAME}', filename=FILE_NAME)
                self.quota -= 1
                await interaction.edit_original_response(embed=embed,
                                                         attachments=[country_sv, other_image_assets],
                                                         view=self)
            else:
                await interaction.edit_original_response(view=self)
        else:
            await interaction.edit_original_response(view=self)


class CountryBTN(discord.ui.Button):
    def __init__(self, parent_self, label: str, emoji, status: str):
        super().__init__(label=label, style=discord.ButtonStyle.blurple, emoji=emoji, row=2, custom_id=status)
        self.repo = GeoRepository()
        self.status = status
        self.parent_self = parent_self
        self.start = timer()

    async def callback(self, interaction: discord.Interaction) -> None:
        # Allow for response
        await interaction.response.defer()
        end = timer()

        # Allow only one response per user
        if interaction.user.id not in self.parent_self.users_clicked:
            # Add user to "already answered" list
            self.parent_self.users_clicked.append(interaction.user.id)

            # If the correct option is selected do as such.
            if self.status == "correct":
                # Calculate score and update database with new score.
                final_score: int = int(5000 * math.exp((-1 / 28) * (end - self.start)))
                if await self.repo.get_by_userid_scores_descending(interaction.user.id) is None:
                    await self.repo.add_into(interaction.user.id, final_score)
                else:
                    existingScore = (await self.repo.get_existing_score(interaction.user.id)) + final_score
                    await self.repo.update_score(existingScore, interaction.user.id)

                # Generate a message displaying the location of the image.
                city: str = self.parent_self.location_params['city']
                return_string: str = city if len(city) != 0 else self.label

                # Color the correct answer green, and the wrong answers red.
                self.style = discord.ButtonStyle.green
                for i in range(4):
                    [x for x in self.parent_self.children if "inco" in x.custom_id][i].style = discord.ButtonStyle.red
                    [x for x in self.parent_self.children if "corr" not in x.custom_id][i].disabled = True

                # Send off these changes to be displayed
                await interaction.edit_original_response(view=self.view)
                msg = await interaction.original_response()
                await asyncio.sleep(0.1)
                await msg.edit(view=None)
                await interaction.followup.send(content=f"{interaction.user.mention} got the right answer of "
                                                        f"**{return_string}**"
                                                        f" and won **{final_score} points.** ")
                # Indicate the view is finished.
                self.parent_self.is_finished()
                self.parent_self.stop()
            else:
                # Add user to list to stop them from answering again.
                self.parent_self.users_clicked.append(interaction.user.id)

                # Color the wrong answer red and disable it.
                self.style = discord.ButtonStyle.red
                self.disabled = True

                # Send off these changes to be displayed
                await interaction.edit_original_response(view=self.view)
