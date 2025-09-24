import nltk
from .dfa import AnaphoraDFA

nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)

def resolve_pronouns(text):
    dfa = AnaphoraDFA(text)
    return dfa.run()

