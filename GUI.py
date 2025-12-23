import FreeSimpleGUI as sg
import os
import random
from PIL import Image
import io
import google.genai as genai

# Configure Gemini (replace with your API key setup)
# In powershell: $env:GOOGLE_API_KEY =  'APIKEY'
client = genai.Client(api_key=os.getenv('GOOGLE_API_KEY'))  # Set your key in environment

class TarotDeck:
    def __init__(self, base_path='resources'):
        self.base_path = base_path
        self.major_path = os.path.join(base_path, 'MajorArcana')
        self.minor_path = os.path.join(base_path, 'MinorArcana')
        self.deck = self._load_deck()

    def _load_deck(self):
        """Scans folders and returns a list of dicts with card info."""
        full_deck = []
        # Scan Major Arcana
        if os.path.exists(self.major_path):
            for f in os.listdir(self.major_path):
                if f.lower().endswith(('.jpg', '.jpeg')):
                    full_deck.append({'name': self._clean_name(f), 'path': os.path.join(self.major_path, f), 'type': 'Major'})
        
        # Scan Minor Arcana
        if os.path.exists(self.minor_path):
            for f in os.listdir(self.minor_path):
                if f.lower().endswith(('.jpg', '.jpeg')):
                    full_deck.append({'name': self._clean_name(f), 'path': os.path.join(self.minor_path, f), 'type': 'Minor'})
        
        return full_deck

    def _clean_name(self, filename):
        """Turns '01_The_Magician.jpg' into 'The Magician'"""
        name_no_ext = os.path.splitext(filename)[0]
        # Remove leading numbers/underscores often found in tarot sets
        return name_no_ext.replace('_', ' ').strip()

    def draw(self, count):
        """Returns a random sample of unique cards, each with a reversed flag."""
        if count > len(self.deck):
            drawn = self.deck
        else:
            drawn = random.sample(self.deck, count)
        # Add reversed status to each card
        for card in drawn:
            card['reversed'] = random.choice([True, False])
        return drawn
    
SPREAD_CONFIG = {
    '1 Card': 1,
    '3 Card': 3,
    'Horseshoe': 7,
    '9 Card': 9,
    'Celtic Cross': 10
}

def get_card_image_bytes(card_path, reversed=False, size=(200, 300)):
    """Load and resize card image to bytes for display. Rotate if reversed."""
    try:
        img = Image.open(card_path)
        if reversed:
            img = img.rotate(180)
        img = img.resize(size)
        bio = io.BytesIO()
        img.save(bio, format='PNG')
        return bio.getvalue()
    except Exception as e:
        print(f"Error loading image {card_path}: {e}")
        return None

def generate_interpretation(cards):
    """Use Gemini to generate a simple tarot reading."""
    card_descriptions = []
    for card in cards:
        status = "reversed" if card['reversed'] else "upright"
        card_descriptions.append(f"{card['name']} ({status})")
    prompt = f"Provide a tarot reading for the following cards: {', '.join(card_descriptions)}. Provide keywords for each card, explaining first each card, taking into consideration if it is reversed or not, then providing an overall interpretation."
    try:
        response = client.models.generate_content(contents=prompt, model="gemini-2.5-flash")
        return response.text
    except Exception as e:
        return f"Error generating interpretation: {e}"

# GUI Layout
sg.theme('DarkBlue')

layout = [
    [sg.Text('Select Spread:'), sg.Combo(list(SPREAD_CONFIG.keys()), default_value='3 Card', key='-SPREAD-')],
    [sg.Button('Draw Cards'), sg.Button('Exit')],
    [sg.HorizontalSeparator()],
    [sg.Text('Drawn Cards:')],
    [sg.Column(
        [
            # Grid: 3 rows of 4 images each (total 12, but we use up to 10)
            *[ [sg.Image(key=f'-CARD{i + row*4}-', size=(200, 300)) for i in range(4)] for row in range(3) ],
        ],
        scrollable=True,
        vertical_scroll_only=True,
        size=(850, 650),  # Fixed size for the scrollable area; adjust as needed
        key='-CARD_COLUMN-'
    )],
    [sg.HorizontalSeparator()],
    [sg.Text('Interpretation:')],
    [sg.Multiline(size=(120, 16), key='-INTERP-', disabled=True)]
]

window = sg.Window('Tarot Reader', layout, resizable=True)

deck = TarotDeck()

while True:
    event, values = window.read()
    if event == sg.WINDOW_CLOSED or event == 'Exit':
        break
    if event == 'Draw Cards':
        spread = values['-SPREAD-']
        count = SPREAD_CONFIG[spread]
        drawn_cards = deck.draw(count)
        
        # Clear previous images
        for i in range(10):
            window[f'-CARD{i}-'].update(data=None)
        
        # Display images
        for i, card in enumerate(drawn_cards):
            img_bytes = get_card_image_bytes(card['path'], card['reversed'])
            if img_bytes:
                window[f'-CARD{i}-'].update(data=img_bytes)
        
        # Generate interpretation
        window['-INTERP-'].print(f'Generating interpretation for cards: {", ".join([card["name"] for card in drawn_cards])}...\n')
        interpretation = generate_interpretation(drawn_cards)
        window['-INTERP-'].print(interpretation)

window.close()