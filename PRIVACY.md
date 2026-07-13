# Privacy

Feelz processes short pieces of text about how you're feeling, so it's worth
being explicit about where that text goes. Short version: as little as
possible leaves your machine, and nothing is ever sent to Feelz's developers
or any analytics/telemetry service - there isn't one.

## Processed entirely on your device

- **Polarity/sentiment scoring** - NLTK's VADER lexicon runs locally.
- **Depression-language scoring** - the shipped TF-IDF + Logistic Regression
  pipeline (`Extensions/Models/depression_pipeline.pickle`) runs locally.
- **Theme preference** - stored in `Data/Data.db` (SQLite, on disk, never
  transmitted).
- **Mood history** (if you use the History tab) - stored in
  `Data/history.db`, a local-only SQLite file that is `.gitignore`d and never
  uploaded anywhere. Delete it (or use the in-app "Clear history" button) to
  remove it at any time.

## Sent to a third party, only when you use that specific feature

| Feature | What leaves your device | Sent to |
|---|---|---|
| Image OCR (upload a photo) | The image file's bytes | Google Cloud Vision API |
| Voice input | Your recorded audio clip | Google Web Speech API (the free, keyless endpoint used by `SpeechRecognition`) |
| Social post lookup | The post URL you paste | X/Twitter's public `oembed` endpoint (`publish.twitter.com/oembed`) |

None of these calls include your name, device identifiers, or any other
personal metadata beyond what's inherent to the request (the image, the
audio, or the URL itself). None of them are proxied through, logged by, or
visible to Feelz's developers - your device talks directly to Google/X's
servers over HTTPS.

If you'd rather nothing ever leaves your device, stick to the Text and File
(.txt) input modes and skip image/voice/link input - everything else in the
app is 100% local.

## What's never collected

Feelz has no analytics, crash reporting, or telemetry of any kind. There is
no account, no login, and no server component - it's a local desktop app
that occasionally makes the three outbound calls listed above.
