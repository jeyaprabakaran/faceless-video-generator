import os
import re
import json
from dotenv import load_dotenv
import google.generativeai as genai
from utils import pick_voice_name
from story_generator import (
    generate_story_and_title,
    generate_general_storyboard,
    generate_life_pro_tips_storyboard,
    generate_characters,
    generate_philosophy_storyboard,
    generate_fun_facts_storyboard,
)
from image_generator import generate_and_download_images
from video_creator import create_video
from utils import (
    create_resource_dir,
    pick_story_type,
    pick_image_style,
    load_config,
)
from api import replicate_flux_api, fal_flux_api, huggingface_hf_api
from video_creator import add_subtitles

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))
# Construct the path to the .env file
dotenv_path = os.path.join(os.path.dirname(script_dir), ".env")
# Load the .env file
load_dotenv(dotenv_path)

config = load_config()
# Initialize the Gemini client
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
client = genai.GenerativeModel(config["gemini"]["model"])


def pick_image_provider():
    providers = [
        ("Hugging Face (free — FLUX.1-schnell)", huggingface_hf_api),
        ("Replicate (paid — Flux Schnell)", replicate_flux_api),
        ("FAL AI (paid — Flux Schnell)", fal_flux_api),
    ]
    print("\nChoose an image generation provider:")
    for i, (label, _) in enumerate(providers, 1):
        print(f"{i}. {label}")

    while True:
        try:
            choice = int(input("Enter the number of your choice: "))
            if 1 <= choice <= len(providers):
                return providers[choice - 1][1]
            else:
                print("Invalid choice. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")


def main():
    # 1. pick story type, image style, voice name, and image provider
    story_type = pick_story_type()
    image_style = pick_image_style()
    voice_name = pick_voice_name()
    image_generator = pick_image_provider()

    # 2. generate story and title
    title, description, story = generate_story_and_title(client, story_type)
    if story is None or title is None:
        print("Failed to generate a story and title. Please try again later.")
        return

    story_dir = create_resource_dir(script_dir, story_type, title)

    # 3. generate characters
    characters = []
    if story_type.lower() != "life pro tips" and story_type.lower() != "fun facts":
        print("\nGenerating character descriptions...")
        characters = generate_characters(client, story)
        if characters is None:
            print("Failed to generate characters. Please try again later.")
            return
        print("characters: ", characters)

    character_names = (
        [character["name"] for character in characters] if characters else []
    )

    # 4. generate storyboard
    print("\nGenerating storyboard...")
    if story_type.lower() == "life pro tips":
        storyboard_project = generate_life_pro_tips_storyboard(
            client, title, story)
    elif story_type.lower() == "philosophy":
        storyboard_project = generate_philosophy_storyboard(
            client, title, story, character_names
        )
    elif story_type.lower() == "fun facts":
        storyboard_project = generate_fun_facts_storyboard(
            client, title, story)
    else:
        storyboard_project = generate_general_storyboard(
            client, title, story, character_names
        )

    if len(storyboard_project.get("storyboards")) == 0:
        print("Failed to generate storyboard. Please try again later.")
        return

    # Remove scenes with empty subtitles
    storyboard_project["storyboards"] = [
        scene
        for scene in storyboard_project["storyboards"]
        if scene["subtitles"].strip()
    ]

    storyboard_project["characters"] = characters

    # 5. save the story and storyboard to files
    with open(
        os.path.join(script_dir, story_dir, "story_english.txt"), "w", encoding="utf-8"
    ) as f:
        f.write(f"{title}\n\n{description}\n\n{story}")

    # 6. generate images
    print("\nGenerating images for each scene...")
    image_files = generate_and_download_images(
        storyboard_project,
        story_dir,
        image_style,
        image_generator,
    )

    # Update storyboard_project with image and audio paths
    for i, storyboard in enumerate(storyboard_project['storyboards']):
        storyboard['image'] = image_files[i] if i < len(image_files) else None
        storyboard['audio'] = os.path.join(story_dir, "audio", f"scene_{storyboard['scene_number']}.mp3")

    # Save the storyboard_project to a json file
    print("\nSaving storyboard project...")
    with open(
        os.path.join(script_dir, story_dir, "storyboard_project.json"),
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(storyboard_project, f, ensure_ascii=False, indent=4)

    # 7. create video
    if image_files:
        print("\nCreating video from images...")
        audio_dir = os.path.join(story_dir, "audio")
        os.makedirs(audio_dir, exist_ok=True)
        video_path = os.path.join(story_dir, "story_video.mp4")
        create_video(client, storyboard_project, video_path, audio_dir, voice_name)
        print(f"Video created: {video_path}")
    else:
        print("No images were generated. Cannot create video.")

if __name__ == "__main__":
    main()