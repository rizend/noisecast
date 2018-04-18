from secrets import slack_token
from secrets import slack_token_mary
from secrets import slack_token_cowsay
if len(slack_token) < 1:
  raise ValueError('Slack token must be set')

from subprocess import call
from flask import Flask
from flask import request
app = Flask(__name__)

from cowpy import cow

import pychromecast
import pychromecast.controllers.youtube as youtube
import threading
import urllib

chromecasts = pychromecast.get_chromecasts()
controllers = {}

def get_url_query(url):
    """
    Returns the query params of a url as a dict
    """
    return urllib.parse.parse_qs(urllib.parse.urlparse(url).query)

def list_chromecasts(args):
  if len(args) > 0:
    return 'The list command takes no arguments'
  return '\tChromecasts:\n' + '\n'.join([x.device.friendly_name + " - " + x.status.status_text + " (" + (str(x.status.volume_level * 100) if not x.status.volume_muted else "muted") + ")" for x in chromecasts])

def get_specified_chromecasts(descriptor):
  descriptor = descriptor.lower()
  if descriptor == 'all':
    return chromecasts
  if descriptor == '':
    descriptor = 'hackitorium'
  return list(filter(lambda x: x.device.friendly_name.lower().startswith(descriptor), chromecasts))

def play_yt_vid(cast, id):
  def task():
    if not cast.uuid in controllers:
      yt = youtube.YouTubeController()
      cast.register_handler(yt)
      controllers[cast.uuid] = yt

    yt = controllers[cast.uuid]
    if yt.in_session:
      yt.add_to_queue(id)
    else:
      yt.play_video(id)
  t = threading.Thread(target=task)
  t.start()

def play(targets, args):
  url = args[0]
  if url.startswith('https://www.youtube.com/watch?v='):
    id = get_url_query(url)["v"][0]
    _ = [play_yt_vid(target, id) for target in targets]
    return str(len(_)) + " chromecasts are now playing video id " + id
  return 'invalid url!'

def say(txt):
  def task():
    call(['say', txt])
  t = threading.Thread(target=task)
  t.start()
  return 'Mary is now saying ' + txt

@app.route("/mary", methods=['POST'])
def mary():
  if request.form['token'] != slack_token_mary:
    return 'Token not set'
  return say(request.form['text'])

def mute(targets):
  _ = [x.set_volume_muted(True) for x in targets]
  return 'Muted ' + str(len(_)) + ' chromecasts'
def unmute(targets):
  _ = [x.set_volume_muted(False) for x in targets]
  return 'Unmuted ' + str(len(_)) + ' chromecasts'

def volume(targets, args):
  vol_str = args[0]
  vol = 0
  try:
    vol = float(vol_str)
  except ValueError:
    return "I couldn't parse the volume you entered."
  if vol < 0 or vol > 100:
    return "Specified volume is not between 0 and 100 inclusive."
  vol = vol / 100
  _ = [x.set_volume(vol) for x in targets]
  return "Set volume to " + vol_str + " on " + str(len(_)) + " chromecasts"

def wrap_cmd(cmd, num_args):
  def ret(args):
    print("in ret")
    print('args: "' + '", "'.join(args) + '"')
    if len(args) < num_args:
      return 'This command requires ' + str(num_args) + ' arguments in additional to the optional cast specifier suffix, you entered too few.'
    call_with = args[:num_args]
    specifier = args[num_args:]
    if len(specifier) > 1 and specifier[0] == 'on':
      specifier = specifier[1:]
    targets = get_specified_chromecasts(' '.join(specifier))
    if len(targets) < 1:
      return 'No matching chromecasts found (maybe you entered too many arguments?)'
    if num_args == 0:
      return cmd(targets)
    return cmd(targets, call_with)
  return ret

cast_cmds = {}
cast_cmds['mute'] = wrap_cmd(mute, 0)
cast_cmds['unmute'] = cast_cmds['umute'] = wrap_cmd(unmute, 0)
cast_cmds['play'] = wrap_cmd(play, 1)
cast_cmds['list'] = list_chromecasts
cast_cmds['vol'] = cast_cmds['volume'] = cast_cmds['set_volume'] = wrap_cmd(volume, 1)

def run_cmd(cmd, args):
  return cast_cmds[cmd](args)

@app.route("/", methods=['GET', 'POST'])
def hello():
  if request.method == 'POST':
    if request.form['token'] != slack_token:
      return "Look what you made me do :)!"
    txt = request.form['text']
    if len(txt) == 0:
      txt = 'list'
    if txt in cast_cmds:
      run_cmd(txt, [])
    if txt.split(" ")[0] in cast_cmds:
      return run_cmd(txt.split(" ")[0], txt.split(" ")[1:])
    return "unknown command"
  else:
    return "Hello World!"

cowsay = cow.Cowacter().milk
@app.route("/cowsay", methods=['POST'])
def _cowsay():
  if request.form['token'] != slack_token_cowsay:
    return ':('
  txt = request.form['text']
  if len(txt) == 0:
    return 'Usage: /cowsay [some text]'
  return cowsay(txt)
