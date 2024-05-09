from podcast_manager import PodcastManager
import argparse
import os

def main(args):
    # Create an instance of the PodcastManager
    podcast_manager = PodcastManager(args.bucket_name, args.index_file, args.num_episodes)

    try:
        # Add the new episode to the podcast manager
        podcast_manager.add_episode(args.title, args.summary, args.mp3_file, duration=args.duration)
        print('Episode added successfully.')

        # Generate the main and test RSS feeds
        podcast_manager.generate_rss_feed('main')
        podcast_manager.generate_rss_feed('test')
        print('RSS feeds generated successfully.')

        # Generate the index.html file
        podcast_manager.generate_web_page()
        print('index.html file generated successfully.')

    except Exception as e:
        print(f'An error occurred: {str(e)}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Upload a podcast episode and generate RSS feeds and index.html.')
    parser.add_argument('--bucket-name', type=str, default="quackernewspodcast", help='The name of the S3 bucket.')
    parser.add_argument('--index-file', type=str, default='index.json', help='The name of the index file.')
    parser.add_argument('--num-episodes', type=int, default=10, help='The number of episodes to display on the web page.')
    parser.add_argument('--title', type=str, default="Test Podcast", help='The title of the podcast episode.')
    parser.add_argument('--summary', type=str, default="Test Podcast Summary", help='The summary of the podcast episode.')
    parser.add_argument('--mp3-file', type=str, default="output.mp3", help='The path to the MP3 file of the podcast episode.')
    # TODO compute duration of the mp3
    parser.add_argument('--duration', type=str, default="00:05:00", help='The duration of the podcast episode (HH:MM:SS).')

    args = parser.parse_args()
    main(args)

