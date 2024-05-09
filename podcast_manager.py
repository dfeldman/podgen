import os
import json
import boto3
from datetime import datetime, timezone
from feedgen.feed import FeedGenerator

class PodcastManager:
    def __init__(self, bucket_name, index_file='index.json', num_episodes=5):
        self.s3 = boto3.client('s3')
        self.bucket_name = bucket_name
        self.index_file = index_file
        self.num_episodes = num_episodes
        self.podcast_data = self._load_podcast_data()

    def _load_podcast_data(self):
        try:
            response = self.s3.get_object(Bucket=self.bucket_name, Key=self.index_file)
            return json.loads(response['Body'].read().decode('utf-8'))
        except self.s3.exceptions.NoSuchKey:
            return {'episodes': []}

    def _save_podcast_data(self):
        self.s3.put_object(
            Bucket=self.bucket_name,
            Key=self.index_file,
            Body=json.dumps(self.podcast_data, indent=2)
        )

    def add_episode(self, title, summary, mp3_file, is_test=False, duration=''):
        episode_id = len(self.podcast_data['episodes']) + 1
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d')
        mp3_key = f"{timestamp}_{episode_id}.mp3"

        self.s3.upload_file(mp3_file, self.bucket_name, mp3_key)

        episode_data = {
            'id': episode_id,
            'title': title,
            'summary': summary,
            'mp3_key': mp3_key,
            'pub_date': datetime.now(timezone.utc).isoformat(), # use utc time
            'is_test': is_test,
            'duration': duration
        }

        self.podcast_data['episodes'].append(episode_data)
        self._save_podcast_data()

    def generate_rss_feed(self, feed_type='main'):
        fg = FeedGenerator()
        fg.load_extension('podcast')

        fg.id(PODCAST_URL)
        fg.title(PODCAST_TITLE)
        fg.author({'name': PODCAST_AUTHOR, 'email': PODCAST_EMAIL})
        fg.link(href=PODCAST_URL, rel='alternate')
        fg.logo(PODCAST_LOGO)
        fg.subtitle(PODCAST_SUBTITLE)
        fg.language(PODCAST_LANGUAGE)

        fg.podcast.itunes_author(PODCAST_AUTHOR)
        fg.podcast.itunes_category(ITUNES_CATEGORY, ITUNES_SUBCATEGORY)
        fg.podcast.itunes_explicit(ITUNES_EXPLICIT)
        fg.podcast.itunes_owner(name=PODCAST_AUTHOR, email=PODCAST_EMAIL)
        fg.podcast.itunes_image(PODCAST_LOGO)
        print("COMPUTE EPISODES")
        for episode in self.podcast_data['episodes']:
            if (feed_type == 'main' and not episode['is_test']) or (feed_type == 'test' and episode['is_test']):
                print("EPISODE", episode['title'])
                fe = fg.add_entry()
                fe.id(f"{PODCAST_URL}/{episode['mp3_key']}")
                fe.title(episode['title'])
                fe.description(episode['summary'])
                fe.enclosure(f"{PODCAST_URL}/{episode['mp3_key']}", 0, 'audio/mpeg')
                print("ADD DATE")
                # This is a little weird. We parse a DateTime from a string, and then switch it back to a DateTime.
                pub_date = datetime.fromisoformat(episode['pub_date'])
                pub_date = pub_date.replace(tzinfo=timezone.utc)
                fe.pubDate(pub_date)
                print("DONE ADDING DATE")
                fe.podcast.itunes_author(PODCAST_AUTHOR)
                fe.podcast.itunes_explicit(ITUNES_EXPLICIT)
                fe.podcast.itunes_duration(episode['duration'])
        print("ABOUT TO UPLOAD")
        if feed_type == 'main':
            fg.rss_str(pretty=True)
            self.s3.put_object(Bucket=self.bucket_name, Key='podcast.rss', Body=fg.rss_str())
        else:
            fg.rss_str(pretty=True)
            self.s3.put_object(Bucket=self.bucket_name, Key='test.rss', Body=fg.rss_str())

    def generate_web_page(self):
        sorted_episodes = sorted(self.podcast_data['episodes'], key=lambda x: x['pub_date'], reverse=True)
        recent_episodes = sorted_episodes[:self.num_episodes]
        print("Got recent episodes", recent_episodes)
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{PODCAST_TITLE}</title>
            <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700&display=swap" rel="stylesheet">
            <style>
                body {{
                    font-family: 'Montserrat', sans-serif;
                    background-color: #F5F5DC;
                    color: #4B0082;
                    margin: 0;
                    padding: 0;
                }}
                header {{
                    background-color: #4B0082;
                    color: #FFFFFF;
                    padding: 20px;
                    text-align: center;
                }}
                h1 {{
                    font-size: 36px;
                    margin: 0;
                }}
                main {{
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .episode {{
                    background-color: #FFFFFF;
                    border-radius: 5px;
                    padding: 20px;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
                }}
                .episode-title {{
                    font-size: 24px;
                    font-weight: bold;
                    margin-bottom: 10px;
                }}
                .episode-description {{
                    font-size: 16px;
                    color: #333333;
                    margin-bottom: 10px;
                }}
                audio {{
                    width: 100%;
                }}
                .subscribe-section {{
                    text-align: center;
                    margin-top: 40px;
                }}
                .subscribe-link {{
                    display: inline-block;
                    background-color: #4B0082;
                    color: #FFFFFF;
                    font-size: 20px;
                    padding: 10px 20px;
                    text-decoration: none;
                    border-radius: 5px;
                }}
                .subscribe-link:hover {{
                    background-color: #6A5ACD;
                }}
            </style>
        </head>
        <body>
            <header>
                <h1>{PODCAST_TITLE}</h1>
            </header>
            <main>
                {''.join(self._generate_episode_html(episode) for episode in recent_episodes)}
                <div class="subscribe-section">
                    <a class="subscribe-link" href="{PODCAST_URL}/podcast.rss">Subscribe to {PODCAST_TITLE}</a>
                </div>
            </main>
        </body>
        </html>
        """

        self.s3.put_object(
            Bucket=self.bucket_name,
            Key='index.html',
            Body=html,
            ContentType='text/html',
            CacheControl='no-cache'
        )

    def _generate_episode_html(self, episode):
        return f"""
        <div class="episode">
            <div class="episode-title">{episode['title']}</div>
            <div class="episode-description">{episode['summary']}</div>
            <audio controls>
                <source src="{PODCAST_URL}/{episode['mp3_key']}" type="audio/mpeg">
                Your browser does not support the audio element.
            </audio>
        </div>
        """

# Constants for podcast information
PODCAST_TITLE = 'Quacker News'
PODCAST_SUBTITLE = 'daily superautomated techbro mockery'
PODCAST_AUTHOR = 'Daniel Feldman'
PODCAST_EMAIL = 'dfeldman.mn@gmail.com'
PODCAST_LANGUAGE = 'en'
PODCAST_URL = 'https://s3.amazonaws.com/quackernewspodcast'
PODCAST_LOGO = f'{PODCAST_URL}/logo.jpg'
ITUNES_CATEGORY = 'Technology'
ITUNES_SUBCATEGORY = 'Software How-To'
ITUNES_EXPLICIT = 'no'
