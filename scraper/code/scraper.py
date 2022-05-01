import pprint
import sys

import praw
import data_sender as comm
from datetime import datetime
from apscheduler.schedulers.background import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

INTERVAL = 1


def init_reddit_instance():
    reddit_instance = praw.Reddit(
        client_id='6MkzuKozOa5zec13CM6H7A',
        client_secret='WDwKAUoQuRRYS_LRgUt2KF5rf5zgQA',
        user_agent='Micro Scrapper',
        redirect_url='http://localhost:8080'
    )
    return reddit_instance


# Post methods that need a little work
def get_author(post):
    try:
        return post.author.name
    except AttributeError:
        return '[Deleted]'


def get_subreddit(post):
    return post.subreddit.display_name


def get_date(post):
    post_timestamp = post.created_utc
    post_datetime = datetime.utcfromtimestamp(post_timestamp)\
                            .strftime('%Y-%m-%d %H:%M:%S')
    return post_datetime


def get_permalink(post):
    return 'reddit.com' + post.permalink


interesting_post_parameters = (
    'author', 'title', 'downs', 'ups', 'subreddit', 'permalink', 'created', 'selftext_html'
)


def get_post_param(post, parameter):
    if interesting_post_parameters.count(parameter) == 0:
        raise NotImplementedError("Parsing of parameter: " + parameter +
                                  " is not implemented!")
    if parameter == 'author':
        return get_author(post)
    if parameter == 'subreddit':
        return get_subreddit(post)
    if parameter == 'created':
        return get_date(post)
    if parameter == 'permalink':
        return get_permalink(post)

    return getattr(post, parameter)


def get_single_image(post):
    try:
        return post.preview['images'][0]['source']['url']
    except AttributeError:
        return None


def get_multi_image(post):
    if post.secure_media is None:
        return None
    media_metadata = post.media_metadata
    images = []
    for media in media_metadata.values():
        resolutions = media['p']
        result = resolutions[0]
        for img in resolutions:
            if result['x'] < img['x']:
                result = img
        images.append(result)
    return images


def get_new_posts():
    top_posts = reddit.subreddit('MachineLearning').new(limit=200)
    print("Posts fetched")
    data_dict = dict()
    counter = 0

    for post in top_posts:
        # Determine what are possible post fields. Debug only.
        # pprint.pprint(vars(post))

        # if post.selftext_html is None:
        #    continue

        post_dict = dict()

        for param in interesting_post_parameters:
            post_dict[param] = get_post_param(post, param)

        post_dict['single_image'] = get_single_image(post)
        if post.selftext_html is None and post_dict['single_image'] is None:
            sys.stderr.write("Unknown post format!\n")
            continue
            # Experimental code below
            # try:
            #    post_dict['multi_image'] = get_multi_image(post)
            # except:
            #    pprint.pprint(vars(post))
            #    raise

        #except AttributeError:
        #    sys.stderr.write("Unable to fetch media\n")

        data_dict[counter] = post_dict
        counter += 1

    # print(data_dict)
    return data_dict


scheduler = BlockingScheduler()


@scheduler.scheduled_job(IntervalTrigger(hours=INTERVAL))
def scrap_data():
    data_dict = get_new_posts()
    comm.send_data(data_dict)


if __name__ == '__main__':
    reddit = init_reddit_instance()
    print("Instance created")
    scrap_data()
    scheduler.start()
