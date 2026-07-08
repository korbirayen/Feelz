# Feelz

Feelz is a small desktop mood checker that I refactored from the original Sentiment247 project. It still does the same core jobs, but the branding, launch flow, and a few of the internals have been cleaned up so it feels like a new app instead of a renamed copy.

It can check typed text, read text files, pull text from images, record and transcribe speech from your microphone, and read public X (Twitter) post URLs - all through the same sentiment/depression-language models.

## What You Need

Everything works out of the box except image OCR:

- Set `GOOGLE_APPLICATION_CREDENTIALS` to your Google Vision service account JSON path if you want OCR to use your own project credentials.
- Social post lookups use X/Twitter's public oEmbed endpoint, so no developer account or API keys are needed - just a public post URL.
- Voice input uses your default microphone and the free Google Web Speech API for transcription (no account needed, but it does need an internet connection).

If you want to make the app fully yours, replace the images in `images/` and swap out the legacy model files when you are ready.

## Start The App

Run `start_feelz.bat` from the project root. That script calls `start_feelz.py`, which checks the Python packages, downloads the NLTK data the app needs, and then launches the desktop app.

## A Small Note

The project still has some original structure inside it, because I kept the working pieces in place while modernizing the name and the startup path. That makes it easier to keep the app stable while you keep iterating on the design.