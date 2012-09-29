from twython import Twython
from app import db
from app import Tweet
import math, sched, time, collections, re
from threading import Timer
from datetime import datetime, timedelta 
from app import tavorite, tweet_age_in_hours, tweets_age_for_view, following



def filter_for_double_links_from_same_person(all_links):
    filtered_links = []

    tweet_links = []

    for lnk in all_links:
        link = lnk.link
        user_id = lnk.user_id

        if (link, user_id) not in filtered_links:

            x = (link, user_id)

            filtered_links.append(x)

            tweet_links.append(link)

    return tweet_links


def links_number_of_times():
    five_days_ago = datetime.utcnow() - timedelta(days=5) 
    Tweets = Tweet.query.filter(Tweet.date > five_days_ago).all()
    tweets = [x for x in Tweets if x.url_exists] 
    links = filter_for_double_links_from_same_person(tweets)
    cnt = collections.Counter(links).most_common(100)
    return cnt


def get_tweets_update_db():
    get_tweets =  tavorite.getHomeTimeline(count=200, include_entities=1, include_retweets=1)
    for x in get_tweets:
        tweet = Tweet(x)
        tweet_in_db = Tweet.query.filter_by(tweet_id=tweet.tweet_id).first()
        if tweet_in_db:
            if tweet_age_in_hours(tweet_in_db) < 14:
                if tweet_in_db.retweet_count < tweet.retweet_count:
                    tweet_in_db.retweet_count = tweet.retweet_count
                    db.session.commit()
        else:
            if tweet.url_exists:
                try:
                    db.session.add(tweet)
                    db.session.commit()
                except:
                    db.session.rollback()
    print "update successful"

link_counter = links_number_of_times()

#FASTER FASTER FASTER

def update_averages_and_std_deviation():

    for z in following:
        user = Tweet.query.filter_by(user_id=z).all()
        retweet_counts = [y.retweet_count for y in user]
            # average retweet count of user_id

        if len(retweet_counts) != 0:
            average = sum(retweet_counts)/len(retweet_counts)
            calculate = sum([pow((g-average), 2) for g in retweet_counts])
            standard_deviation = math.sqrt(calculate/len(retweet_counts))
        else:
            average = 0
            calculate = 0
            standard_deviation = 0
        
        Tweet.query.filter_by(user_id=z).update(dict(average_rt_count=average, std_deviation=standard_deviation))
        try: 
            db.session.commit()
        except:
            db.session.rollback()

        for x in user:
            if tweet_age_in_hours(x) < 168:
                if standard_deviation != 0:
                    x.std_dev_sigma    = (x.retweet_count - average)/standard_deviation
                if len(retweet_counts) < 30 and x.std_dev_sigma > 3:
                    x.std_dev_sigma = 3.0

                if len(retweet_counts) < 5:
                    x.std_dev_sigma = .125
            
                tweet_hour_age = tweet_age_in_hours(x)

                number_of_times_retweeted = times_appears_in_stream(x.link, link_counter)

                points = (10*(x.std_dev_sigma))*number_of_times_retweeted
                score_with_time = hacker_news(points, tweet_hour_age)

                x.score = round(points)
                x.score_with_time = score_with_time
                try:
                    db.session.commit()
                except:
                    db.session.rollback()





#Automate get new tweets every X minues and update the DB    
def update_every_fifteen_minutes():
    """Automates - every X minutes gets new tweets and update those tweets with there raking score"""
    s = sched.scheduler(time.time, time.sleep)
    print "updating feed beginning"
    s.enter(900, 1, get_tweets_update_db, ())
    s.run()
    update_averages_and_std_deviation()
    update_every_fifteen_minutes()
    """To continously loop recursive call update_every_minute()"""





def times_appears_in_stream(link, counter):
    links_only = []
    for x in counter:
        links_only.append(x[0])
    if link not in links_only:
        return 1
    else:
        for x in counter:
            if link in x[0]:
                if x[1] == 1:
                    return 1
                if x[1] > 1:
                    if x[1] < 5:
                        return pow(1.75, x[1])
                    else: 
                        return pow(1.75, 4) + (x[1]-4)



def hacker_news(votes, item_hour_age, gravity=1.8):
    return votes/pow((item_hour_age+2), gravity)



 
if __name__ == '__main__':
    update_every_fifteen_minutes()
