import os
import json
import requests
from datetime import datetime
from openai import OpenAI
from string import Template

class HackerNewsPodcastGenerator:
    default_prompt_template = """
Based on the following top stories from Hacker News, generate a creative and engaging conversation about the topics:

$stories
Conversation:
"""

    def __init__(self, url, num_stories=3, prompt_template=None):
        self.url = url
        self.num_stories = num_stories
        self.prompt_template = prompt_template or self.default_prompt_template
    
    def fetch_top_stories(self):
        response = requests.get(self.url)
        data = response.json()
        stories = data  # Assuming the JSON data is already a list of stories
        stories.sort(key=lambda x: x["points"], reverse=True)
        return stories[:self.num_stories]
    
    def generate_conversation(self, stories):
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        story_text = ""
        for story in stories:
            story_text += f"Title: {story['title']}\nFirst Paragraph: {story['first_paragraph']}\n\nComments:\n"
            for comment in story["comments"][:3]:
                story_text += f"- {comment}\n"
            story_text += "\n"
        
        prompt_template = Template(self.prompt_template)
        prompt_text = prompt_template.substitute(stories=story_text)
        
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are a creative assistant."},
                {"role": "user", "content": prompt_text}
            ]
        )
        
        if response and response.choices and len(response.choices) > 0:
            content = response.choices[0].message.content.strip()
            return content
        else:
            raise Exception("Failed to generate conversation.")
    
    def generate_script_json(self):
        top_stories = self.fetch_top_stories()
        conversation = self.generate_conversation(top_stories)
        
        today = datetime.now().strftime("%Y-%m-%d")
        output_data = {
            "date": today,
            "input_data": top_stories,
            "conversation": conversation
        }
        with open("script.txt", "w") as file:
            file.write(conversation)
        return json.dumps(output_data, indent=2)
    
    def save_script(self):
        script_json = self.generate_script_json()
        today = datetime.now().strftime("%Y-%m-%d")
        output_filename = f"script-{today}.json"
        with open(output_filename, "w") as file:
            file.write(script_json) 
        print(f"Generated script saved as {output_filename}")
        return output_filename

def main():
    url = "https://quackernews.com/output/output2.json"
    num_stories = 5  # Change this to the desired number of top stories
    
    # Custom prompt template
    custom_prompt_template = """

Write a script for a very funny podcast called Quacker News, where the hosts talk daily about and poke fun at today's Hacker News stories.. The hosts are Dave and Julie. The script will be automatically turned into an audio podcast. 
The script should be in this format exactly:
Dave: <Dave's words>
Julie: <Julie's words> 
etc.
Dave is funny and tells jokes and is open and enthusiastic and a bit of a comedian.
Julie is icy, overly serious, and is the "straight man" to Dave's jokes.
DO NOT use laughs, groans, or other nonverbal sounds. But it's fine to use unfinished sentences, uh, huh, etc to make it sound realistic. Make them sound as natural as possible, like a real podcast or youtube video, by not always using complete sentences and using informal phrases like "I mean" and "well" and "On the other hand." 
It's ok to not be too technical. For example, if a story mentions the Apple M4 chip, you can just mention that and move on to talking about Apple or chips. If it mentions a cyberattack, just mention it and talk about cybersecurity in general. 
Make it fun and interesting to listen to! 
The podcast should be about 5 minutes long (2000 words). 

$stories
Conversation:
"""
    
    generator = HackerNewsPodcastGenerator(url, num_stories, prompt_template=custom_prompt_template)
    generator.save_script()

if __name__ == "__main__":
    main()
