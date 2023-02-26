Contributing and Development
============================
This is a quick guide on how to develop and contribute to this project

## Dependencies
Make sure you can run these commands and install them if not present.
* Python 3.10 or higher
* pip3 (packaged as python3-pip)


## Get a Discord bot token and enable intents
* Go to https://discordapp.com/developers/applications (log in if needed)
* Create an application (name doesn't matter)
* Click "Bot" it the left sidebar
* Create a bot
  * The bot's name will be what users see in servers
  * Changing the bot's name changes the BotToken
* Make note of the token on this page (later refered to as BotToken)
* Enable Discord member intents ![Intents](https://i.postimg.cc/hhWy9N7W/Screen-Shot-2020-11-06-at-10-30-25-AM.png)


## Join the test server
[Click here to join the server](https://discord.gg/FACu8k4)
ping @Jayy#6249 for permissions to add bots


## Prepare bot for connecting to discord server
* Click "OAuth2" in the left sidebar and click "URL Generator"
* In the "scopes" section, check `bot` and `applications.commands`
* In the "bot permissions" section, check the following boxes ![perms](https://i.imgur.com/7zTDDkN.png)
* Copy the link from the "scopes" section and open in a new tab/window
* Select the test server to add the bot to

## Prepare the Repo
* Fork this repo
* `git clone` your fork to wherever you want to work on this bot
* Copy `BotSecrets.json.template` and rename that copy to `BotSecrets.json`
* Copy/paste the token from the Discord page into the `BotToken` empty string
* Set a custom bot prefix that will invoke your commands 

## Prepare your ClemBot.Bot config variables
* Copy `BotSecrets.json.template` and rename that copy to `BotSecrets.json`
* Copy/paste the token from the Discord page into the `BotToken` empty string
* Copy and paste the channel Ids of the channels in the test server that you want to use for Connection Status updates and Error Logging into the `ErrorLogChannelIds` and `StartupLogChannelIds`. If you dont want this. Leave the field as an empty brackets, []
* Set a custom bot prefix in the `BotPrefix` field that will invoke your commands 

### All Config Variables

* `BotToken`:(Required) Your discord bots api access token
* `BotPrefix`:(Required) Your discord bots prefix that it will default to responding too
* `StartupLogChannelIds`:(Optional) The ID of the channel for the bot to send startup events too
* `ErrorLogChannelIds`:(Optional) The ID of the channel for the bot to send error events too (recommended if you are doing work with services)
* `GifMeToken`:(Optional) GifMe api token
* `MerriamKey`:(Optional) Merriam api token
* `WeatherKey`:(Optional) Weather forecast api token
* `GeocodeKey`:(Optional) Geocode weather service api token
* `AzureTranslateKey`:(Optional) Azure translation api token
* `ClassArchiveCategoryIds`:(Optional) Discord category IDs for class archival. Required for `/class` command.
* `ClassNotifsChannelId`:(Optional) Discord channel ID for class notifications. Required for `/class` command.

## Setting up the ClemBot.Bot build environment
Installing Poetry:  
`pip3 install poetry` windows: `py -m pip install poetry`

Tell Poetry to put the venv in the project folder
`poetry config virtualenvs.in-project true`

Installing dependencies with Poetry:
`poetry install`

You can then test-run the bot with the command:  
`poetry run python3 -m bot`  windows: `poetry run py -m bot`
when you are in the directory `SockBot/`

The bot should show up in the test server and respond to commands (test with `<your_prefix>hello`)
