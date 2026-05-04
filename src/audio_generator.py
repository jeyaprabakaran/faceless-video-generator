import os
from gtts import gTTS


def generate_audio(text, output_file, voice_name):
    # voice_name is a gTTS top-level domain (tld) that selects the accent,
    # e.g. "com" (US), "co.uk" (British), "com.au" (Australian).
    tld = voice_name if voice_name else "com"

    try:
        tts = gTTS(text=text, lang="en", tld=tld, slow=False)
        tts.save(output_file)

        print(f"Speech synthesized for text [{text}], and the audio was saved to [{output_file}]")
        return True

    except Exception as e:
        print(f"Error generating audio: {str(e)}")
        return False
