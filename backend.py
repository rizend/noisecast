from secrets import slack_token
if len(slack_token) < 1:
  raise ValueError('Slack token must be set')

from flask import Flask
from flask import request
app = Flask(__name__)

import pychromecast
import pychromecast.controllers.youtube as youtube
import threading

chromecasts = pychromecast.get_chromecasts()
controllers = {}

def list_chromecasts():
  return '\tChromecasts:\n' + '\n'.join([x.device.friendly_name + " - " + x.status.status_text + " (" + (str(x.status.volume_level) if not x.status.volume_muted else "muted") + ")" for x in chromecasts])

def get_chromecast(name):
  name = name.lower()
  for c in chromecasts:
    if c.device.friendly_name.lower().startswith(name):
      return c
  return None

def get_specified_chromecasts(descriptor):
  if descriptor == 'all':
    return chromecasts
  if descriptor == '':
    descriptor = 'hackitorium'
  return [get_chromecast(descriptor)]

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

def play_something(url):
  if url.startswith('https://www.youtube.com/watch?v='):
    targets = get_specified_chromecasts('all')
    id = url.split("=")[1]
    _ = [play_yt_vid(target, id) for target in targets]
    return str(len(_)) + " chromecasts are now playing video id " + id
  return 'invalid url!'

@app.route("/", methods=['GET', 'POST'])
def hello():
  if request.method == 'POST':
    if request.form['token'] != slack_token:
      return "Look what you made me do :)!"
    txt = request.form['text']
    if len(txt) == 0 or txt == "list":
      return list_chromecasts()
    if txt.startswith('http'):
      return play_something(txt)
    if txt.startswith('mute'):
      targets = get_specified_chromecasts(txt[4:].strip())
      if len(targets) < 1 or (len(targets) == 1 and targets[0] == None):
        return 'No matching chromecasts found'
      _ = [x.set_volume_muted(True) for x in targets]
      return 'Muted ' + str(len(_)) + ' chromecasts'
    if txt.startswith('unmute'):
      targets = get_specified_chromecasts(txt[6:].strip())
      if len(targets) < 1 or (len(targets) == 1 and targets[0] == None):
        return 'No matching chromecasts found'
      _ = [x.set_volume_muted(False) for x in targets]
      return 'Unmuted ' + str(len(_)) + ' chromecasts'
    return "unknown command"
  else:
    return "Hello World!"
