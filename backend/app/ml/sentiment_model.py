import math
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyzer = None

def get_analyzer():
    global _analyzer
    if _analyzer is None:
        _analyzer = SentimentIntensityAnalyzer()
    return _analyzer

def analyze_sentiment(text: str) -> dict:
    """
    Section 5 Sentiment rule:
    Use VADER compound score S:
    Angry if S <= -0.35, Happy if S >= 0.35, otherwise Neutral.
    Urgency U = clamp(floor((1 - S) / 2 * 100), 0, 100).
    """
    analyzer = get_analyzer()
    scores = analyzer.polarity_scores(text or "")
    compound = scores["compound"]

    if compound <= -0.35:
        label = "Angry"
    elif compound >= 0.35:
        label = "Happy"
    else:
        label = "Neutral"

    # Exact Section 5 formula:
    urgency = max(0, min(100, int(math.floor((1.0 - compound) / 2.0 * 100.0))))

    return {
        "sentiment_label": label,
        "sentiment_score": urgency,
        "urgency_score": urgency,
        "compound": compound,
    }
