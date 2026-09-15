from VILLAIN_MUSIC.core.bot import Aviax
from VILLAIN_MUSIC.core.dir import dirr
from VILLAIN_MUSIC.core.userbot import Userbot
from VILLAIN_MUSIC.misc import dbb, heroku

from .logging import LOGGER

dirr()
dbb()
heroku()

app = Aviax()
userbot = Userbot()


from .platforms import *

Apple = AppleAPI()
Carbon = CarbonAPI()
SoundCloud = SoundAPI()
Spotify = SpotifyAPI()
Resso = RessoAPI()
Telegram = TeleAPI()
YouTube = YouTubeAPI()



