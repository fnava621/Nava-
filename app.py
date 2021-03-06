import time, sched, requests, json, HTMLParser 
import urlparse, math, collections, re
from datetime import datetime, timedelta
from flask import *
from flask.ext.sqlalchemy import *
from BeautifulSoup import BeautifulSoup
from twython import Twython



app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')


db = SQLAlchemy(app)

tavorite = Twython(app_key=os.environ['CONSUMER_KEY'],
                  app_secret=os.environ['CONSUMER_SECRET'],
                   oauth_token=os.environ['ACCESS_TOKEN'],
                   oauth_token_secret=os.environ['ACCESS_TOKEN_SECRET'])

following = tavorite.getFriendsIDs()['ids']

filter_out_media = ['instagram.com', 'www.instagram.com', 'instagr.am', 'youtube.com', 'www.youtube.com', 'www.vimeo.com', 'vimeo.com', 'twitpic.com', 'www.twitpic.com', 'i.imgur.com', 'www.yfrog.com', 'twitter.yfrog.com','twitter.com', 'imgur.com', 't.co', 'join.app.net', 'd.pr', 'www.mobypicture.com', 'i.appimg.net', 'foursquare.com', 'www.foursquare.com', 'www.path.com', 'path.com', 'cl.ly', 'm.youtube.com', 'mobile.twitter.com', 'alpha.app.net', 'alpha-api.app.net', 'appnetizens.com', 'jer.srcd.mp', 'm.flickr.com']


def filter_double_links(tweet_obj):
  unique_links=[]
  top_links_filtered = []
  for x in tweet_obj:
    if x.link not in unique_links:
      unique_links.append(x.link)
      top_links_filtered.append(x)
  return top_links_filtered[0:50]


@app.route('/')
def home():
  return render_template('dyno_homepage.html')

@app.route('/blog')
def blog():
  return render_template('blog.html')

@app.route('/ogilvy')
def ogilvy():
  return render_template('ogilvy.html')

@app.route('/hackernews')
def hackernews():
  return render_template('HackerNews.html')

@app.route('/LearnableProgramming')
def learn():
  return render_template('LearnableProgramming.html')




@app.route('/news')
def news():
  links = Tweet.query.filter_by(url_exists=True).order_by(Tweet.score_with_time.desc()).filter(~Tweet.main_url.in_(filter_out_media)).limit(30).all()
  time = tweets_age_for_view(links)    
  return render_template('show_links.html', links=links, time=time)

@app.route('/best')
def best():
  five_days_ago = datetime.utcnow() - timedelta(days=5)                                    
  links = Tweet.query.filter_by(url_exists=True).order_by(Tweet.score.desc()).filter(Tweet.date > five_days_ago).filter(~Tweet.main_url.in_(filter_out_media)).limit(70).all()

  links = filter_double_links(links)
  time = tweets_age_for_view(links)

  return render_template('best_of_week.html', links=links, time=time)

@app.route('/photos')
def photos():
  photos = Tweet.query.filter(Tweet.picture != unicode("")).order_by(Tweet.date.desc()).limit(75).all()
  return render_template('photos.html', photos=photos)

@app.route('/videos')
def videos():
  three_days_ago = datetime.utcnow() - timedelta(days=3)
  media = ['www.youtube.com', 'youtube.com', 'vimeo.com', 'www.vimeo.com']
  videos = Tweet.query.filter_by(url_exists=True).filter(Tweet.date > three_days_ago).filter(Tweet.main_url.in_(media)).order_by(Tweet.score.desc()).limit(75).all()
  videos = filter_double_links(videos)
  time = tweets_age_for_view(videos)
  return render_template('videos.html', videos=videos, time=time)


@app.errorhandler(404)
def page_not_found(error):
  """Custom 404 page."""
  return render_template('404.html'), 404


class Tweet(db.Model):

  id               = db.Column(db.Integer, primary_key=True)
  tweet            = db.Column(db.UnicodeText)
  screen_name      = db.Column(db.Unicode(256))
  name             = db.Column(db.Unicode(256))
  user_id_str      = db.Column(db.Unicode(256))
  user_id          = db.Column(db.BIGINT)
  user_created_at  = db.Column(db.Unicode(356))
  user_following   = db.Column(db.BIGINT)
  user_followers   = db.Column(db.BIGINT)
  user_url         = db.Column(db.Unicode(400))
  statuses_count   = db.Column(db.BIGINT)
  tweet_created_at = db.Column(db.Unicode(256))
  tweet_id         = db.Column(db.BIGINT)
  text             = db.Column(db.Unicode(400))
  retweeted        = db.Column(db.Boolean)
  url_exists       = db.Column(db.Boolean)
  link             = db.Column(db.Unicode(500))
  main_url         = db.Column(db.Unicode(500))
  profile_picture  = db.Column(db.Unicode(500))
  picture          = db.Column(db.Unicode(500))
  date             = db.Column(db.DateTime)
  page_text        = db.Column(db.UnicodeText)
  retweet_count    = db.Column(db.Integer)
  headline         = db.Column(db.Unicode(500))
  average_rt_count = db.Column(db.Float)
  std_deviation    = db.Column(db.Float)
  std_dev_sigma    = db.Column(db.Float)
  score            = db.Column(db.Integer)
  score_with_time  = db.Column(db.Float)  

  def __init__(self, feed):

    #pull twitter media and picture
    if unicode('media') in feed['entities'].keys():
      self.picture = feed['entities']['media'][0]['media_url']
        
    if self.bool_url_exists(feed):
      try:
        r = requests.get(feed['entities']['urls'][0]['expanded_url'])
        self.link = r.url
      except:
        self.link = feed['entities']['urls'][0]['expanded_url']

        #grab page text
      try:
        self.page_text = r.text
      except:
        self.page_text = "Error grabbing page"

      #get instagram
      if ('http://instagr' in self.link):
        try:
          soup = BeautifulSoup(self.page_text)
          a = soup.findAll(attrs={"property":"og:image"})[0]['content']
          #a = soup.find(id='media_photo').findAll('img')[0]['src']
          self.picture = a
        except:
          self.picture = unicode("")
            
      if [image_exists for image_exists in ['.gif', '.jpeg', 'jpg', '.png'] if image_exists in self.link]:
        self.picture = self.link
            

      #get twitpic
      if ('twitpic' in self.link):
        soup = BeautifulSoup(self.page_text)
        a = soup.findAll(attrs={"name":"twitter:image"})[0]['value']
        self.picture = a
            
      #get yfrog
      if ('yfrog' in self.link):
        soup = BeautifulSoup(self.page_text)
        a = soup.findAll(attrs={"property":"og:image"})[0]['content']
        self.picture = a

      #grab main url
      home = urlparse.urlsplit(self.link)
      self.main_url = home.netloc

      #defaults for link, page_text, main_url and main_url
      if not self.bool_url_exists(feed):
        self.link          = unicode("")
        self.page_text     = unicode("")
        self.main_url      = unicode("")
      if not self.picture:
        self.picture       = unicode("")


      self.tweet            = self.json_to_dict(feed)
      self.screen_name      = feed['user']['screen_name']
      self.name             = feed['user']['name']
      self.user_id_str      = feed['user']['id_str'] 
      self.user_id          = feed['user']['id']
      self.user_created_at  = feed['user']['created_at']
      self.user_following   = feed['user']['friends_count']
      self.user_followers   = feed['user']['followers_count']
      self.user_url         = feed['user']['url']
      self.statuses_count   = feed['user']['statuses_count']
      self.profile_picture  = feed['user']['profile_image_url_https']
      self.retweet_count    = feed['retweet_count']
      self.tweet_created_at = feed['created_at']
      self.tweet_id         = feed['id']
      self.text             = self.grab_text(feed)
      self.retweeted        = feed['retweeted'] 
      self.date             = datetime.utcnow()
      self.url_exists       = self.bool_url_exists(feed)
      self.headline         = self.pull_headline(self.page_text)
      self.average_rt_count = 1.0
      self.std_deviation    = .25
      self.std_dev_sigma    = .25
      self.score            = 0.5
      self.score_with_time  = 0.5
        
        

  def __repr__(self):
    return "<Tweet by %r>" % self.screen_name

  def json_to_dict(self, dct):
    tweet_str = json.dumps(dct)
    return tweet_str
    
  def grab_text(self, tfeed):
    text = tfeed['text']
    split_text = text.split(' ')
    text_no_tco = ' '.join([x for x in split_text if 'http://t.co' not in x])
    return text_no_tco
    

  def bool_url_exists(self, x):
    if len(x['entities']['urls']) == 0:
      return bool(0)
    else: return bool(1)

  def pull_headline(self, page_text):
    h = HTMLParser.HTMLParser()

    try:
      soup = BeautifulSoup(page_text)
    except:
      soup = BeautifulSoup('')

    if soup.findAll('title'):
      title = soup.find('title')
      content = title.renderContents()
      decode = content.decode("utf-8")
      unicode_text = h.unescape(decode)
      clean_up_0 = self.remove_separator_and_extra_content(unicode_text, " - ")
             
      clean_up_1 = self.remove_separator_and_extra_content(clean_up_0, " \| ") 
      clean_up_2 = self.remove_separator_and_extra_content(clean_up_1, " \// ")
      if clean_up_2 == unicode('403 Forbidden') or clean_up_2 == unicode('500 Internal Server Error'):
        a = self.text
        cleaned_up = a.lstrip("'").rstrip("'")
        return cleaned_up
      else:
        return clean_up_2
    else: 
      return self.text

  def remove_separator_and_extra_content(self, content, separator): 
    dash = re.findall(separator, content)
    split_content = re.split(separator, content)
    if len(dash) > 0 and len(split_content[0] + split_content[1]) > 30:
      a = split_content[0]
      b = a.lstrip()
      c = b.rstrip()
      return c
    elif len(dash) > 0 and len(split_content[0] + split_content[1]) < 30:
      if separator == " \| ":
        separator = " | "
      a = split_content[0] + unicode(separator) + split_content[1]
      b = a.lstrip()
      c = b.rstrip()
      return c
    else: 
      a = content.lstrip()
      b = a.rstrip()
      return b


def tweet_age_in_hours(Tweet):
  created_at = Tweet.date
  right_now = datetime.utcnow()
  tweet_age = right_now - created_at
  age_in_hours = (tweet_age.days)*24 + tweet_age.seconds/3600
  return age_in_hours

def tweets_age_for_view(Tweets):
  list_of_tweet_age = []
    
  for tweet in Tweets:
    age_in_hours = tweet_age_in_hours(tweet)
    if age_in_hours >= 24:
      days = age_in_hours/24
      if age_in_hours < 48:
        list_of_tweet_age.append((str(days) + " day ago"))
      else:
        list_of_tweet_age.append((str(days) + " days ago"))
    else:
      if age_in_hours == 1:
        list_of_tweet_age.append((str(age_in_hours) + " hour ago"))
      else:
        list_of_tweet_age.append((str(age_in_hours) + " hours ago"))
  return list_of_tweet_age



if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

