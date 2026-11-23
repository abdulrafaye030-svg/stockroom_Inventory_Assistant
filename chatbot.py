"""Run with py chatbot.py. Add --mongo to use your MERN database."""
import difflib
from database import clean, get_answer, open_shop

phrases = {
    "available": ["available products", "which products are available", "what is in stock", "konsa saman available hai"],
    "empty": ["out of stock products", "which products are not available", "unavailable products",
              "which products are unavailable", "which products are out of stock", "out of stock", "konsa saman khatam hai"],
    "low": ["low stock products", "low stock", "what should i reorder", "which items are short",
            "which products are low in stock", "konsa saman kam hai"],
    "dues": ["customer dues", "which customers owe money", "show pending balances",
             "which customers have remaining amounts", "kis customer ka udhaar baqi hai"],
}
# {name} is the part the user can change, e.g. Sugar or Cooking Oil.
name_questions = {
    "product": ["stock of {name}", "stock for {name}", "how much {name} is left", "{name} ka stock kitna hai"],
    "balance": ["balance of {name}", "balance for {name}", "how much does {name} owe",
                "{name} ka udhaar kitna hai", "{name} ka balance kitna hai"],
}
help_text = """Try: available products | out of stock products | low stock products
     stock of Sugar | customer dues | how much does Ali owe?
     konsa saman kam hai? | Ali ka udhaar kitna hai?
Or type check product / check balance and enter a name when asked.
Type help for examples or bye to exit."""


# Each phrase points to the kind of answer the user wants.
questions = {"check product": "product", "check balance": "balance"}
for intent, examples in phrases.items():
    for example in examples:
        questions[example] = intent

vocabulary = sorted(set(" ".join(questions).split()))


def match_question(message):
    if message in questions:
        return questions[message], None

    # For "stock of cooking oil", remove "stock of " to get "cooking oil".
    for intent, templates in name_questions.items():
        for template in templates:
            before, after = template.split("{name}")
            if message.startswith(before) and message.endswith(after):
                name = message.removeprefix(before).removesuffix(after).strip()
                if name:
                    return intent, name

    # Keep every word, especially "not", when correcting small spelling errors.
    words = message.split()
    for index, word in enumerate(words):
        if len(word) >= 4 and word not in vocabulary:
            matches = difflib.get_close_matches(word, vocabulary, n=1, cutoff=0.84)
            if matches:
                words[index] = matches[0]
    return questions.get(" ".join(words)), None


if __name__ == "__main__":
    with open_shop() as shop:
        print(help_text)
        while (msg := clean(input("\nYou: "))) not in ("bye", "quit", "exit"):
            if msg in ("hi", "hello", "salam", "help", "assalamualaikum", "aslamualikum"):
                if msg != "help":
                    print("Bot: Wa alaikum assalam!")
                print(help_text)
                continue
            intent, name = match_question(msg)
            if intent is None:
                print("Bot: I didn't understand. Type help for examples.")
                continue
            if name is None and intent in ("product", "balance"):
                prompt = "Product name? " if intent == "product" else "Customer name? "
                name = clean(input(prompt))
                if not name:
                    print("Bot: Please enter a name.")
                    continue
            print("Bot:", get_answer(shop, intent, name))
        print("Bot: Goodbye!")
