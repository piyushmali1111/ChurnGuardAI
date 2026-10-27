import os
import sys

# Ensure backend root is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.ml.sentiment_model import analyze_sentiment


def test_sentiment_outputs():
    test_cases = [
        ("Item arrived crushed. Box had zero padding. Want immediate store credit or refund.", "Angry"),
        ("My order arrived completely damaged and missing items! This is unacceptable and I want a refund!", "Angry"),
        ("Hi, can I change the delivery address for my order?", "Neutral"),
        ("Thanks so much, the package arrived early and everything looks great!", "Happy"),
    ]

    print("\n--- Sentiment Model Test Evaluation ---")
    print(f"{'Text':<75} {'Expected':<8} {'Actual':<8} {'Compound':<9} {'Urgency':<8}")
    print("-" * 110)

    for text, expected in test_cases:
        res = analyze_sentiment(text)
        label = res["sentiment_label"]
        compound = res["compound"]
        urgency = res["urgency_score"]

        print(f"{text[:72] + '...':<75} {expected:<8} {label:<8} {compound:<9.4f} {urgency:<8}")

        if expected == "Angry":
            assert compound <= -0.35, f"Expected Angry (S <= -0.35), got compound={compound}"
            assert label == "Angry"
        elif expected == "Happy":
            assert compound >= 0.35, f"Expected Happy (S >= 0.35), got compound={compound}"
            assert label == "Happy"
        elif expected == "Neutral":
            assert -0.35 < compound < 0.35, f"Expected Neutral, got compound={compound}"
            assert label == "Neutral"

    print("\n[+] All sentiment tests passed successfully!")


if __name__ == "__main__":
    test_sentiment_outputs()
