import pandas as pd
import re
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from tokenizers.decoders import WordPiece
import Levenshtein

model_name = "avichr/heBERT_NER"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForTokenClassification.from_pretrained(model_name)
ner_pipeline = pipeline("ner", model=model, tokenizer=tokenizer, aggregation_strategy="simple")

oracle = pipeline('ner', model='dicta-il/dictabert-ner', aggregation_strategy='simple')
oracle.tokenizer.backend_tokenizer.decoder = WordPiece()

time = {"אחד", "אחת", "שניים", "שתיים", "שלוש", "ארבע", "חמש", "שש", "שבע", "שמונה", "תשע", "עשר", "אחד עשרה", "שתיים עשרה", "אחת עשרה", "שניים עשרה", "רבע", "חצי"}
opt_period = {"בוקר", "צהריים", "ערב", "אחר", "אחרי"}
questions = {"מה", "מי", "איך", "למה", "מתי", "איפה", "האם", "מהי"}
months = {
    'ראשון' : 'לינואר',
    'שני' : 'לפברואר',
    'שלישי' : 'למרץ',
    'רביעי' : 'לאפריל',
    'חמישי' : 'למאי',
    'שישי' : 'ליוני',
    'שביעי' : 'ליולי',
    'שמיני' : 'לאוגוסט',
    'תשיעי' : 'לספטמבר',
    'עשירי' : 'לאוקטובר',
    'אחת עשרה' : 'לנובמבר',
    'שתיים עשרה' : 'לדצמבר',
}

close_times = {"היום", "מחר", "מחרתיים"}
days = {"ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"}

def create_command(template):
    """
    Builds a clean, well-formatted command string from a list of template components.

    This function joins all items in the `template` list into a single string, removes
    unwanted character combinations (e.g., '- '), collapses multiple spaces into a single
    one, and trims leading or trailing whitespace.

    Parameters
    ----------
    template : list[str]
        A list of command components (strings) to be concatenated into a final command.

    Returns
    -------
    str
        A cleaned command string suitable for final use (e.g., sending to a voice assistant).
    """
    new_command = ' '.join(template)
    new_command = new_command.replace("- ", "")
    new_command = re.sub(r'\s+', ' ', new_command).strip()
    return new_command

def find_person(utter):
    """
    Identifies and extracts a person’s name mentioned in a given utterance using two NER pipelines.

    The function first runs a named entity recognition (NER) pipeline (`ner_pipeline`) to locate
    any entity tagged as a person ("B_PERS"). If none is found, it falls back to a secondary
    recognition model (`oracle`) and searches for entities labeled as "PER".

    Once a person’s name is detected, it applies normalization rules to remove the Hebrew
    preposition prefix "ל" (meaning "to") when appropriate:
      - If the name starts with "לל", only the first 'ל' is removed (e.g., "לליאור" → "ליאור").
      - If the name starts with a single 'ל', it is removed completely (e.g., "לישראל" → "ישראל").

    The function also records the character index of where the detected name ends (`end_point`)
    to allow downstream components to process the remaining part of the utterance.

    Parameters
    ----------
    utter : str
        The input utterance containing a potential person name.

    Returns
    -------
    tuple[str | None, int]
        A tuple containing:
        - `person`: the extracted and normalized person name, or `None` if no name was found.
        - `end_point`: the character index (int) where the detected name ends in the utterance.
          Defaults to 0 if no name was detected.
    """

    person = None
    end_point = None

    ents1 = ner_pipeline(utter)
    ents2 = oracle(utter)

    for x in ents1:
      if person == None:
        if x['entity_group'] == "B_PERS":
          person = x['word']
          end_point = x['end']

    for x in ents2:
      if person == None:
        if x['entity_group'] == "PER":
          person = x['word']
          end_point = x['end']


    if person != None:
      # אם מתחיל ב"לל" → מורידים רק ל אחת
      if person.startswith("לל"):
          person = person[1:].strip()   # 'לליאור כהן' → 'ליאור כהן', 'ללאנה' → 'לאנה'

      # אם מתחיל ב"ל" ולא ב"לל" → מורידים את הל' היחס
      elif person.startswith("ל") and len(person) > 1:
          person = person[1:].strip()

    if end_point == None:
      end_point = 0

    return (person, end_point)

def call_command(utter):
    """
    Generates a standardized 'call' command based on the user's utterance.

    The function attempts to detect a person’s name within the given utterance using
    the `find_person()` helper (which relies on NER). If a name is found, it formats
    a canonical command template to initiate a phone call to that person. If no person
    name is detected, it falls back to a default command that opens the contacts list.

    Parameters
    ----------
    utter : str
        The input utterance from the user (e.g., "תתקשרי לליאור כהן").

    Returns
    -------
    str
        A clean, standardized command string, such as:
        - "תתקשרי לליאור כהן" if a person was detected.
        - "תפתחי את רשימת אנשי הקשר" if no person was found.
    """

    template = ["תתקשרי", "{person}"]
    person = None
    ents = oracle(utter)


    person, _ = find_person(utter)


    if person == None:
      return "תתקשרי"

    else:
      template[1] = person

      return create_command(template)


def parse_alarm_time_and_period(utter):
    """
    Extracts time expressions and an optional period (e.g., morning/evening)
    from a user utterance intended to set an alarm.

    The function scans each token in the utterance and compares it against two
    predefined lexical sets:
      - `time`: a collection of Hebrew time-related keywords (e.g., {"שבע", "שמונה", "וחצי"}).
      - `opt_period`: a collection of Hebrew period indicators (e.g., {"בוקר", "ערב", "לילה"}).

    Behavior:
    ----------
    1. Iterates through every word in the utterance.
    2. If a token contains any period keyword, it assigns it to `period`.
    3. If a token contains any time keyword, it appends it to `full_time`.
       - The first detected match is appended as the canonical time token.
       - Subsequent matches append the full token (to capture multi-word times like
         "שש וחצי" or "ארבע עשרה ושלושים").
    4. At the end, returns both the list of time-related tokens and the detected period.

    Parameters
    ----------
    utter : str
        The user utterance, e.g., "תעירי אותי בשבע בבוקר".

    Returns
    -------
    tuple[list[str], str]
        - `full_time`: a list of strings representing the detected time expression(s).
        - `period`: a string representing the detected period (e.g., "בוקר"), or an empty
          string if no period was found.
    """
    full_time = []
    period = ""

    for x in utter.split():

      for p in opt_period:
        if p in x:
          period = p
          continue

      if period == "":
        if "מחר" in x:
          period = "בוקר"

      for t in time:
        if t in x:
          if len(full_time) == 0:
            full_time.append(t)
          else:
            full_time.append(x)
          break
    if len(full_time) > 1:
      if full_time[-1][0] != "ו" and full_time[-1][0] != "ל":
        full_time[-1] = "ו" + full_time[-1]
    return full_time, period


def alarm_command(utter):
    """
    Constructs a canonical 'set alarm' command from a user utterance.

    The function analyzes the user's spoken input to detect a time expression
    and an optional period (e.g., "morning", "evening"), and reformulates it
    into a clean, standardized command suitable for a voice assistant.

    It relies on two predefined lexical resources:
      - `time`: a collection of Hebrew time-related keywords
        (e.g., {"שבע", "שמונה", "וחצי"}).
      - `opt_period`: a collection of Hebrew period keywords
        (e.g., {"בוקר", "ערב", "לילה"}).

    Behavior
    --------
    1. Tokenizes the utterance by whitespace.
    2. Scans each token:
       - If a token contains a period word from `opt_period`, assigns it to `period`.
       - If a token contains a time-related word from `time`, appends it to `full_time`.
         This allows for multi-word time expressions such as "שש וחצי" or
         "ארבע עשרה ושלושים".
    3. If no time expression is found, the function returns the fallback command:
       `"שעון מעורר"`.
    4. Otherwise, it fills the template:
         - "שעון מעורר ל-{time}"  (if no period found)
         - "שעון מעורר ל-{time} ב-{opt_period}"  (if period found)
    5. The final text is normalized using `create_command()` to remove redundant spaces
       and ensure consistent formatting.

    Parameters
    ----------
    utter : str
        The user utterance, e.g., "תעירי אותי בשבע בבוקר" or "תכווני שעון לשש וחצי בערב".

    Returns
    -------
    str
        A clean, formatted alarm command, for example:
        - "שעון מעורר לשבע בבוקר"
        - "שעון מעורר לשש וחצי"
        - "שעון מעורר"  (if no valid time was detected)

    Notes
    -----
    - The function assumes `opt_period` and `time` are globally accessible collections.
    - Substring matching (`if t in x`) is intentional to capture prefixes and suffixes
      such as "בשמונה" or "לשבע".
    - The cleaning of the final command is handled by the `create_command()` helper.
    """
    template = ["שעון מעורר ל-", "{opt_period}", "{time}"]

    full_time, period = parse_alarm_time_and_period(utter)


    if len(full_time) == 0:
      return "שעון מעורר"

    template[2] = ' '.join(full_time)

    if period == "":
      template[1] = template[2]
      template = template[:2]

    else:
      template[1] = period


    return create_command(template)

def sms_command(utter):
    """
    Constructs a canonical 'send SMS' command from a user utterance.

    The function attempts to:
      1. Detect the recipient (person) using `find_person()`.
      2. Infer the message content from the remaining part of the utterance,
         while skipping meta-words such as "הודעה", "אס אם אס", "סמס", etc.
      3. Reformulate everything into a clean template suitable for a voice assistant.

    Processing steps
    ----------------
    1. Person extraction:
       - Calls `find_person(utter)` to obtain:
         - `person`: the normalized recipient name (or None if not found).
         - `end_point`: the character index where the person name ends.
       - If `end_point` is None, it is set to 0.

    2. Message content extraction:
       - Takes the substring from `end_point` to the end of the utterance
         and splits it into tokens: `content = utter[end_point:].split()`.
       - Iterates over these tokens and skips initial words that are "meta"
         about messaging rather than the actual content, using a fuzzy match
         (Levenshtein distance < 3) against an `exclude` list that contains
         variants of:
           "הודעה", "הבאה", "אס אם אס", "טקסט", "אסאמאס", "סמס",
           "אסמס", "ההודעה", "אס", "אם", "לרשום", "לכתוב", "תכתבי", "SMS".
       - The first token that is *not* similar to any excluded word is taken
         as the start of the message (`start_message_at`), and all subsequent
         tokens are treated as the SMS body.
       - If no such token is found, `message` is set to an empty list.

    3. Command formulation:
       - If both `person` is None and `message` is empty:
           → returns the generic command: "תשלחי הודעה".
       - If `person` is None but `message` is not empty:
           → returns: "תשלחי את ההודעה {message}".
       - Otherwise (a person was found):
           - Fills the base template: ["תשלחי הודעה ל-", "{person}", "{message}"].
           - If the message is empty, the template is truncated to:
             ["תשלחי הודעה ל-", "{person}"].
           - If the message is not empty, it is joined into a single string and
             set in the "{message}" slot.
           - Finally, the command is normalized via `create_command(template)`
             (which handles joining and whitespace cleanup).

    Parameters
    ----------
    utter : str
        The original user utterance, e.g.
        "תשלחי הודעה לישראל זילברמן שאני מאחרת לעשר"
        or
        "תכתבי סמס שאני מגיעה עוד מעט".

    Returns
    -------
    str
        A standardized SMS command, for example:
        - "תשלחי הודעה לישראל זילברמן שאני מאחרת לעשר"
        - "תשלחי את ההודעה אני מגיעה עוד מעט"
        - "תשלחי הודעה" (if neither recipient nor content were detected).

    Notes
    -----
    - The function relies on `find_person()` and `create_command()` as helpers.
    - Fuzzy matching with Levenshtein distance is used to robustly skip various
      noisy forms of the word "message" and related meta-phrases, especially
      in noisy or non-standard speech by older adults.
    """

    template = ["תשלחי הודעה ל-", "{person}", "{message}"]

    person, end_point = find_person(utter)
    if end_point == None:
      end_point = 0

    exclude = ["הודעה", "הבאה", "אס אם אס", "טקסט", "אסאמאס", "סמס", "אסמס", "ההודעה", "אס", "אם", "אס", "לרשום", "לכתוב", "תכתבי", "SMS", "תודה", "בבקשה"]
    content = utter[end_point:].split()

    start_message_at = None

    for i, word in enumerate(content):
      bad = False

      for e in exclude:

        if bad:
          break

        dist_calc = Levenshtein.distance(e, word)
        if dist_calc < 3:
          bad = True

      if bad != True:
        start_message_at = i
        break

    if start_message_at != None:
      message = content[start_message_at:]
    else:
      message = []

    if person == None and message == []:
      return "תשלחי הודעה"

    elif person == None:
      return f"תשלחי את ההודעה {' '.join(message)}"

    template[1] = person

    if message == []:
      template = template[:2]
    else:
      message = ' '.join(message)
      template[2] = message

    return create_command(template)

def search_command(utter):
    """
    Builds a canonical 'web search' command from a user utterance.

    The function processes a spoken user query (often informal or verbose)
    and reformulates it into a clean, standardized "search the web" command.
    It removes irrelevant filler words, polite expressions, and meta-instructions
    that are not part of the actual search intent.

    Behavior
    --------
    1. Initializes a base template: ["לחפש באינטרנט", "{query}"].
    2. Defines an `exclude` set containing common Hebrew words and polite phrases
       that are typically unrelated to the search content (e.g., "בבקשה", "תודה",
       "סירי", "אני", "רוצה", "תבדקי", etc.).
    3. Iterates through each token in the utterance:
       - For each word, computes the Levenshtein distance to every excluded term.
       - If the distance is < 2 (i.e., the word is a close match to an excluded one),
         the word is skipped.
       - Otherwise, the word is added to the query list.
    4. Joins all valid tokens into a single query string.
    5. Returns the final formatted command: `"לחפש באינטרנט {query}"`.

    Parameters
    ----------
    utter : str
        The user utterance (e.g., "תבדקי לי בבקשה מה מזג האוויר מחר בתל אביב").

    Returns
    -------
    str
        A cleaned, canonical web search command, for example:
        - "לחפש באינטרנט מה מזג האוויר מחר בתל אביב"
        - "לחפש באינטרנט מתכון לעוגת גבינה"
        - "לחפש באינטרנט"  (if no meaningful query terms remain).

    Notes
    -----
    - Fuzzy filtering (Levenshtein distance < 2) is used to tolerate small spelling
      or speech-to-text variations in polite or meta words (e.g., "תבדקי" vs "תבדוקי").
    - The output command is not postprocessed with `create_command()` but could be,
      if you want to standardize formatting across all command types.
    - This design is robust for older-adult speech, where utterances often contain
      conversational padding before the actual search topic.
    """
    template = ["לחפש באינטרנט", "{query}"]

    exclude = {"תעדכן" ,"סירי", "לבדוק", "אני", "בדיקה", "חיפוש", "לדעת", "אני", "בבקשה", "תודה", "מעוניין", "מבקש", "רוצה", "יכול", "תבדקי", "תבדוק",
               "שאלה", "סליחה", "צריך", "לחפש", "חיפוש", "אותי", "אני", "עזרה", "תעזרי", "טוב", "ערב", "לילה", "בוקר", "שלום", "צהריים", "על", "של",
               "תעדכני", "לגבי", "נושא", "מעוניינת", "מראש","לשאול","לי","ממך","הייתי","את","תחפשי", "תגידי", "להיות", "מוכן", "מוכנה", "תמצאי", "באינטרנט"}

    start_from = ["תחפשי","תבדקי","לבדוק","לחפש"]

    query = []
    for word in utter.split():
      if word in start_from:
        query = []
        continue
      bad = False
      for e in exclude:
        dist_calc = Levenshtein.distance(e, word)
        if dist_calc < 2:
          bad = True
          break
      if not bad:
        query.append(word)

    template[1] = ' '.join(query)
    return ' '.join(template)

def navigation_command(utter):
    """
    Constructs a canonical navigation command from a user utterance.

    This function uses a NER pipeline to detect location entities in the utterance,
    distinguishes between origin and destination, optionally infers a preferred
    mode of travel (e.g., walking, driving, public transport), and reformulates
    everything into a standardized navigation template.

    The base template is:
        ["מסלול", "מ-", "{loc_a}", "אל", "{loc_b}", "ב-", "{opt_how}"]

    Behavior
    --------
    1. Location extraction:
       - Runs `ner_pipeline(utter)` and collects all entities with
         `entity_group == "B_LOC"`.
       - For each detected location, stores:
         - The surface form (`ent['word']`) in `all_locations`.
         - Its character span (`(start, end)`) in `positions`.

    2. Handling number of locations:
       - If no locations are found:
           → returns the fallback command: "צריך מסלול".
       - If exactly one location is found:
           - Interprets it as the destination (`loc_b`).
           - Removes the "מ- {loc_a}" part of the template by blanking out
             `template[1]` and `template[2]`.
       - If two or more locations are found:
           - Iterates over `all_locations` and their positions to decide:
             * `loc_a` (origin): locations that start with the Hebrew prefix "מ"
               or are immediately preceded by 'מ' in the original utterance.
               The leading "מ" is stripped.
             * `loc_b` (destination): all other locations. If they start with "ל"
               or are immediately preceded by 'ל', that prefix is stripped.
           - For multiple destination segments, uses the character spans in
             `loc_b_pos` to reconstruct a possibly multi-token destination:
               - When there is a gap greater than 3 characters between consecutive
                 location spans, the text between them (`utter[cur_e:s]`) is also
                 inserted into `full_loc_b`.
           - Joins `full_loc_b` into a single destination string `loc_b`.

    3. Inferring mode of travel:
       - Uses a predefined mapping:
         {
             'הליכה': {'רגל', 'ללכת', 'רגלית', 'ברגל'},
             'תחבורה ציבורית': {'רכבת', 'אוטובוס'},
             'נסיעה': {'רכב', 'אוטו'}
         }
       - Iterates over the words in `utter.split()` and, for each word:
           * Computes the Levenshtein distance to each key (e.g., 'הליכה') and
             to each associated keyword set (e.g., 'רגל', 'רגלית', 'ברגל').
           * If the distance is < 2 for any of them, selects the corresponding
             mode (e.g., 'הליכה') as `opt_how`.
           * Stops as soon as a mode is found.
       - If no match is found, defaults to: `opt_how = 'נסיעה'`.

    4. Filling the template:
       - If no origin (`loc_a`) was detected:
           * Removes the "מ- {loc_a}" segment by blanking `template[1]` and
             `template[2]`.
           * Sets the destination in `template[-3]` and the travel mode in
             `template[-1]`.
       - If an origin was detected:
           * Sets `template[2]` to `loc_a` (the origin).
           * `loc_b` and `opt_how` remain in their original slots.

    5. Final formatting:
       - Calls `create_command(template)` to join and normalize the template
         into a clean command string (removing redundant hyphens and spaces).

    Parameters
    ----------
    utter : str
        The user utterance, for example:
        "תעשי לי מסלול מרחוב הרצל לפארק הלאומי ברגל"
        or
        "אני צריך מסלול מבאר שבע לתל אביב באוטובוס".

    Returns
    -------
    str
        A normalized navigation command, such as:
        - "מסלול מתל אביב לירושלים בנסיעה"
        - "מסלול מרחוב הרצל לפארק הלאומי בהליכה"
        - "צריך מסלול" (if no locations were detected).

    Notes
    -----
    - The function assumes:
        * `ner_pipeline` returns entities with 'entity_group', 'word',
          'start', and 'end' keys.
        * Location entities are tagged as "B_LOC".
    - Origin and destination detection is heuristic and based on Hebrew
      prefixes: "מ" (from) and "ל" (to), either attached to the location
      or as a preceding character in the utterance.
    - The use of Levenshtein distance allows robustness to ASR errors and
      non-standard pronunciations when detecting the travel mode.
    """

    template = ["מסלול", "מ-" ,"{loc_a}", "אל",  "{loc_b}", "ב-", "{opt_how}"]



    loc_a = None
    loc_b = None
    opt_how = None
    all_locations = []
    positions = []


    how = {
    'הליכה' : {'רגל' , 'ללכת', 'רגלית', 'ברגל'},
    'תחבורה ציבורית' : {'רכבת', 'אוטובוס'},
    'נסיעה' : {'רכב', 'אוטו'}
    }

    for word in utter.split():
      if opt_how != None:
        break
      for k, v in how.items():
        dist_calc = Levenshtein.distance(k, word)
        if dist_calc < 2:
          opt_how = k
          utter = utter.replace(opt_how,"")
          break
        for w in v:
          dist_calc = Levenshtein.distance(w, word)
          if dist_calc < 2:
            opt_how = k
            utter = utter.replace(w,"")
            break

    ents1 = ner_pipeline(utter)
    for ent in ents1:
      if ent['entity_group'] == "B_LOC" or ent['entity_group'] == "B_ORG":
        all_locations.append(ent['word'])
        positions.append((ent['start'], ent['end']))


    if len(all_locations) == 0:
      return "צריך מסלול"

    elif len(all_locations) == 1:
      loc =  all_locations[0]
      if loc.startswith("ל"):
        loc = loc[1:].strip()
      loc_b = loc
      template[1] = " "
      template[2] = " "

    else: # i have at least 2 locations

      full_loc_b = []
      loc_b_pos = []
      add_loc_a = False

      for i, loc in enumerate(all_locations):


        if i > 0:
          prev_s, prev_e = positions[i-1]

        s, e = positions[i]
        if loc.startswith("מ") or (s > 0 and utter[s-1] == "מ"):
          loc_a = loc[1:].strip()
          add_loc_a = True
        elif add_loc_a and prev_e + 1 == s:
          loc_a = loc_a + " " + loc

        else:
          add_loc_a = False
          loc_b_pos.append((s, e))
          if loc.startswith("ל") or (s > 0 and utter[s-1] == "ל"):
            full_loc_b.append(loc[1:].strip())
          else:
            full_loc_b.append(loc)

        if len(full_loc_b) > 1:
          cur_s, cur_e = loc_b_pos[0]

          for i, (s, e) in enumerate(loc_b_pos[1:]):
            if e - cur_e > 3: # something between
              between = utter[cur_e : s]
              for b_w in between.split():
                if b_w not in full_loc_b:
                  full_loc_b.insert(i+1, b_w)
              # full_loc_b.insert(i+1, between)


      loc_b = ' '.join(full_loc_b)

    if opt_how == None:
      opt_how = 'נסיעה'

    if loc_a == None:
      template[1] = ""
      template[2] = ""
      template[-3] = loc_b
      template[-1] = opt_how

    else:
      template[2] = loc_a
      template[-3] = loc_b
      template[-1] = opt_how

    if loc_b == None:
      return "צריך מסלול"

    return create_command(template)


def calander_command(utter):
    """
    Constructs a canonical 'create calendar event' command from a user utterance.

    The function attempts to extract:
      - A meeting name (title),
      - A date expression,
      - A time expression,
      - An optional period (e.g., morning/evening),
    and then reformulates them into a standardized command template for a
    calendar/agenda application.

    It relies on:
      - `months`: a mapping of month forms for fuzzy normalization.
      - `close_times`: lexical items like "היום", "מחר", etc.
      - `days`: names of weekdays.
      - `opt_period`: period-of-day terms (e.g., "בוקר", "ערב").
      - `ner_pipeline`: a NER model that tags DATE/TIME entities.
      - `oracle`: a secondary NER model for extracting person/title entities.
      - `create_command`: a helper that joins and cleans the final template.
      - `Levenshtein`: for fuzzy matching of month names and time-related words.

    Behavior
    --------
    1. Initialization:
       - Defines a base template:
         ["תצרי פגישה ביומן", "תקראי לה", "{meeting_name}", "{date}", "{hour}", "{opt_period}"].
       - Initializes empty slots: `meeting_name`, `date`, `hour`, `period`.
       - Splits the utterance into `utter_words`.

    2. Meeting name boundaries:
       - Iterates over `utter_words` with indices:
         * If the word is "בשם", sets `start_from = i + 1` to mark the beginning
           of the meeting name.
         * If the word exactly matches any string in `template` and `start_from`
           is already set, it may set `end_at = i` (end of the meeting name).
       - Normalizes month-like tokens:
         * If a word starts with "ל", it is compared (via Levenshtein distance)
           against keys in `months`. If close enough, it is replaced by the
           canonical month form.
       - If the word is in `close_times` or `days` and both `start_from` is set
         and `end_at` is still `None`, `end_at` is set to this index (assumed
         start of date/time information, and thus end of the name).
       - If none of the above conditions match, the function checks whether
         the word contains any period term from `opt_period`; if so, `period`
         is set and `end_at` may also be updated.

    3. Meeting name construction:
       - If `start_from` is set:
         * If `end_at` is `None` or `start_from > end_at`, the meeting name is
           taken as all words from `start_from` to the end.
         * Otherwise, the meeting name is taken as the slice
           `utter_words[start_from:end_at]`.
       - The name is rebuilt as a single string.

    4. Date and time extraction (NER-based):
       - Joins `utter_words` back into `new_utter`.
       - Runs `ner_pipeline(new_utter)` to get `ents1`.
       - For each entity in `ents1`:
         * If `entity_group` is "B_DATE" or "B_TIME":
             - Uses the `start` / `end` character offsets to slice from
               `new_utter`. If `new_utter[end]` is not a space, the function
               extends `end` forward until the next space (or end of string),
               to handle cases where the NER span cuts a token in the middle.
             - The substring `new_utter[start:end + 1]` is then taken as the
               full entity text.
             - If `entity_group == "B_DATE"`, this text is stored in `date`.
             - If `entity_group == "B_TIME"`, this text is stored in `hour`.

    5. Date fallback heuristics:
       - If `date` is still empty, the function scans `new_utter.split()`:
         * For each word, compares to entries in `close_times` using Levenshtein;
           if similar enough, assigns `date` to that word and clears the "date"
           label in the template by setting `template[3] = ""`.
         * Uses a flag `date_tem` when encountering the string "יום" to then
           look for a weekday in `days` (via fuzzy matching). If found,
           constructs a date of the form "יום{weekday}".
         * (Note: in the current implementation, `if word in "יום"` checks
           membership of characters rather than equality of the word.)

    6. Fallback meeting name via `oracle`:
       - If `meeting_name` is still empty, calls `oracle(new_utter)` to obtain
         additional entities (`ents2`).
       - Collects entities marked as "PER" (person) or "TTL" (title) and joins
         them into a potential meeting name.

    7. Fallback and template adjustment:
       - If both `meeting_name` and `date` remain empty:
           → returns the generic command: "תצרי פגישה ביומן".
       - If `meeting_name` is empty but `date` exists:
           * Removes the "תקראי לה" part by setting `template[1] = ""`.

    8. Filling the template:
       - `template[2]` is set to `meeting_name`.
       - `template[3]` is set to `date`.
       - `template[4]` is set to `hour`.
       - `template[5]` is set to `period`.

    9. Final formatting:
       - Returns `create_command(template)`, which joins the template items
         and normalizes spacing and stray characters.

    Parameters
    ----------
    utter : str
        The original user utterance in Hebrew, e.g.:
        "אני צריכה בבקשה שתתאמי לי תור לדוקטור רימון בתאריך הרביעי ליוני בשעה ארבע עשרה ושלושים"
        or
        "תזמיני לי פגישה בשם ועד בית ביום רביעי בערב".

    Returns
    -------
    str
        A standardized 'create meeting' command, such as:
        - "תצרי פגישה ביומן תקראי לה דוקטור רימון בתאריך הרביעי ליוני בשעה ארבע עשרה ושלושים"
        - "תצרי פגישה ביומן בתאריך מחר בשעה תשע בבוקר"
        - "תצרי פגישה ביומן" (if no meeting name and date could be reliably extracted).

    Notes
    -----
    - The function is tailored to noisy, conversational Hebrew (particularly
      from older adults), and combines NER with heuristic string processing.
    - The NER span extension logic (`if new_utter[end] != " "`) compensates
      for models that sometimes cut within a token, ensuring full words such
      as "שלושים" are captured.
    - The condition `if word in "יום":` checks for character membership rather
      than the whole word; if the intention is to detect the word "יום", consider
      replacing it with `if word == "יום"` or `if "יום" in word`.
    - Several global resources (`months`, `close_times`, `days`, `opt_period`)
      must be defined for the function to operate correctly.
    """
    template = ["תצרי פגישה ביומן", "תקראי לה", "{meeting_name}",  "{date}", "{hour}", "{opt_period}"]

    meeting_name = ""
    date = ""
    hour = ""
    period = ""

    utter_words = utter.split()

    start_from = None
    end_at = None

    # meeting name extraction

    for i, word in enumerate(utter_words):
      if word in {"בשם"}: # explicit mention
        start_from = i + 1

      elif word in ["בתאריך", "בשעה"]:
        if end_at == None and start_from != None:
          end_at = i

      if word[0] == "ל":
        for m in months:
          dist = Levenshtein.distance(m, word)
          # check if ther is month before \ after

          # if dist < 2 and ((utter_words[i+1] != None and utter_words[i+1][0] not in ["ל","ב"])):
          if dist < 2:
            utter_words[i] = months[m]

      elif end_at == None and start_from != None:
        for ct in close_times:
          if Levenshtein.distance(ct, word) < 2:
            end_at = i
            break
        for day in days:
          if Levenshtein.distance(day, word) < 2:
            end_at = i
            break
        for m_1, m_2 in months.items():
          if Levenshtein.distance(day, word) < 2 or Levenshtein.distance(m_1, word) < 2 or Levenshtein.distance(m_2, word) < 2:
            end_at = i
            break

      else:
        for p in opt_period:
          if p in word:
            period = "ב" + p
            if end_at == None and start_from != None:
              end_at = i


    if start_from != None:
      if end_at == None or start_from > end_at:
        meeting_name = ' '.join(utter_words[start_from:])
      elif start_from < end_at:
        meeting_name = ' '.join(utter_words[start_from:end_at])


    new_utter = ' '.join(utter_words)

    ents1 = ner_pipeline(new_utter)


    # date handling
    for e in ents1:

      if e['entity_group'] in ["B_DATE", "B_TIME"]:
        start, end = e['start'], e['end']
        if end < len(utter) - 1: # word is not at the end of the sentence
          if new_utter[end] != " ": # check if hour has been cut
            end = new_utter[end:].find(" ")
            if end == -1:
              end = len(new_utter) # move the end
            else:
              end += e['end']
             # check if the entity is full
        entity = new_utter[start:end + 1]
        rest_utter = new_utter[end + 1:].split()
        if "בשעה" not in rest_utter:
          for w_ru in rest_utter:
            if w_ru[0] == "ו":
              for t in time:
                if Levenshtein.distance(t, w_ru) < 2:
                  entity += " " + w_ru
                  break

        entity = entity.strip()

        if period != "":
          for ent_word in entity.split():
            if Levenshtein.distance(ent_word, period) < 2:
              entity = entity.replace(ent_word, "")
        if e['entity_group'] == "B_DATE":
          if date == "":
            date = entity
        else:
          if hour == "" and "שעה" in entity:
            hour = entity

    date_tem = False
    for word in new_utter.split():
      if date != "":
        break

      for t in close_times:
        if Levenshtein.distance(t, word) < 2:
          date = word
          template[3] = ""
          break

      if word in "יום":
        date_tem = True

      if date_tem:
        for d in days:
          if Levenshtein.distance(d, word) < 2:
            date = "יום" + d
            break

    if meeting_name == "":
      ents2 = oracle(new_utter)

      name = []
      start, end = None, None
      for e in ents2:
        entity_name = e['word']
        if e['entity_group'] == "PER" or e['entity_group'] == "TTL":
          if (start == None):
            start, end = e['start'], e['end']

          elif e['start'] == end + 1:
            start, end = e['start'], e['end']

          else:
            break

          name.append(entity_name)

      if len(name) > 0:
        meeting_name = ' '.join(name)

    if (meeting_name == "" and date == "") or (meeting_name != "" and date == "" and hour != ""):
      return "תצרי פגישה ביומן"

    if date != "" and hour != "":
      # look for partial match - check if hour is in date
      for h in hour.split():
        if h in date:
          date = date.replace(h, "")
    # remove duplicates in the command, if pharse is in i + 1 it cant be in i

    if meeting_name == "":
      template[1] = ""

    template[2] = meeting_name
    template[3] = date
    template[4] = hour
    template[5] = period

    print(template)
    return create_command(template)


def camera_command():
  return "תפתחי מצלמה"

def weather_command(utter):
    """
    Constructs a canonical 'weather query' command from a user utterance.

    The function attempts to:
      1. Detect a location (place) using a NER pipeline.
      2. Detect a time reference (when) such as "today", "tomorrow", or a
         weekday (e.g., "ביום רביעי").
      3. Reformulate everything into a standardized template for querying
         the weather.

    The base template is:
        ["מה מזג האוויר", "ב-", "{place}", "{when}"]

    Behavior
    --------
    1. Location extraction and normalization:
       - Runs `ner_pipeline(utter)` and iterates over the returned entities.
       - For the first entity with `entity_group == "B_LOC"`, assigns
         `place = ent['word']`.
       - Trims surrounding whitespace from `place`.
       - Applies Hebrew-specific normalization rules to remove the
         preposition prefix "ב" (meaning "in/at") when appropriate:
         * If `place` starts with "ב " (bet + space), removes both and strips:
             "ב תל אביב" → "תל אביב".
         * If `place` starts with "בב", assumes the name itself starts with bet
           and removes only the first "ב":
             "בבני ברק" → "בני ברק".
         * If `place` starts with "ב" and is longer than one character,
           removes the initial "ב" as a preposition:
             "בראשון לציון" → "ראשון לציון".

    2. Time reference detection:
       - Splits the utterance into tokens and iterates over them.
       - Defines two local sets:
           * `close_times = {"היום", "מחר", "מחרתיים"}`
           * `days = {"ראשון", "שני", "שלישי", "רביעי",
                      "חמישי", "שישי", "שבת"}`
       - If a word matches any item in `close_times`, assigns `when = word`
         and stops searching.
       - Otherwise, for each weekday name `d` in `days`, computes the
         Levenshtein distance between `d` and the current word:
         * If the distance is < 2, considers it a fuzzy match and sets:
             `when = f"ביום {d}"`,
           then stops searching.
       - This allows the function to handle slight ASR or spelling variations
         in weekday names (e.g., "רביעי" vs. "רביעיּ").

    3. Template adjustment:
       - If no `place` was detected (empty string), removes the "ב-" segment
         by clearing `template[1]` (so the output will not contain a dangling
         preposition).
       - If no `when` was detected, clears the last element in the template
         (so no empty time expression is appended).
       - Finally, sets:
           * `template[-2] = place`
           * `template[-1] = when`

    4. Final formatting:
       - Calls `create_command(template)` to join and normalize the template
         into a clean command string (handling spaces and hyphens).

    Parameters
    ----------
    utter : str
        The original user utterance in Hebrew, for example:
        - "מה מזג האוויר בבאר שבע מחר?"
        - "תבדקי לי מה מזג האוויר בתל אביב ביום רביעי"
        - "איך יהיה מזג האוויר בחיפה היום"

    Returns
    -------
    str
        A standardized weather query command, for example:
        - "מה מזג האוויר בבאר שבע מחר"
        - "מה מזג האוויר בתל אביב ביום רביעי"
        - "מה מזג האוויר מחר"    (if no place was detected)
        - "מה מזג האוויר בבאר שבע" (if no time reference was detected)

    Notes
    -----
    - The function assumes:
        * `ner_pipeline` returns entities with keys 'entity_group' and 'word'.
        * Location entities are tagged as "B_LOC".
        * `create_command` is responsible for final string cleanup.
    - The normalization of `place` is designed to handle Hebrew prepositions
      attached to location names, such as "בתל אביב", "בבני ברק", etc.
    - The sets `close_times` and `days` are currently defined inside the loop
      for each word; they could be moved outside the loop or to a shared
      configuration for efficiency and reuse.
    """

    template = ["מה מזג האוויר", "ב-", "{place}", "{when}"]
    place = ""
    when = ""
    ents = ner_pipeline(utter)

    for ent in ents:

      if ent['entity_group'] == "B_LOC":
        place = ent['word']


        place = place.strip()

        # מקרה מיוחד: "ב " עם רווח
        if place.startswith("ב "):
            place = place[2:].strip()

        # אם מתחיל ב"בב" → כנראה שם שמתחיל בב' (למשל 'בבני ברק')
        # מורידים רק ב אחת
        elif place.startswith("בב"):
            place = place[1:].strip()   # 'בבני ברק' → 'בני ברק'

        # אם מתחיל ב"ב" ולא בב' כפולה → כנראה ב' יחס
        elif place.startswith("ב") and len(place) > 1:
            place = place[1:].strip()   # 'ברחל כהן' → 'רחל כהן', 'באנה' → 'אנה'

    for word in utter.split():
      close_times = {"היום", "מחר", "מחרתיים"}
      days = {"ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"}
      if word in close_times:
        when = word
        break

      for d in days:
        if when != "":
          break
        dist_calc = Levenshtein.distance(d, word)

        if dist_calc < 2:
          when = f"ביום {d}"
          break

    if place == "":
      template[1] = ""

    if when == "":
      template[-1] = ""

    template[-2] = place
    template[-1] = when

    return create_command(template)

def notes_command(utter):
    """
    Constructs a canonical 'create note' command from a user utterance.

    The function extracts the meaningful content of a note from a spoken
    utterance, filtering out polite or meta words (e.g., "תודה", "בבקשה"),
    action verbs (e.g., "תרשמי", "תצרי"), and filler expressions often used
    by older adults when speaking to a voice assistant. The cleaned text is
    then reformulated into a standardized "create note" command.

    The base template is:
        ["תצרי לי פתק", "{content}"]

    Behavior
    --------
    1. Defines a set of excluded words and expressions that are considered
       irrelevant for the actual note content. These include:
         - Politeness markers: {"תודה", "בבקשה", "מראש"}.
         - Assistant-related verbs: {"תעשי", "תצרי", "תכתבי", "תרשמי", "תפתחי"}.
         - Function words and pronouns: {"אני", "את", "אם", "של", "עם", "על", "לי", "בשבילי"}.
         - Generic terms for "note": {"פתק", "פתקית", "רישום"}.
         - Temporal fillers: {"בוקר", "צהריים", "ערב", "טוב", "טובים"}.
         - Miscellaneous: {"צריך", "צריכה", "מעוניין", "מעוניינת", "שיהיה", "להיות", "שם"}.

    2. Iterates through every token in the utterance (`utter.split()`):
       - For each token, compares it to every excluded term using the
         Levenshtein distance.
       - If the distance < 2 (fuzzy match), marks the token as "bad" and skips it.
         This allows the function to tolerate minor ASR or spelling variations.
       - Otherwise, appends the token to the `query` list.

    3. Joins the remaining tokens in `query` to form the note content.

    4. Fills the template:
         ["תצרי לי פתק", "{content}"]
       where `{content}` is replaced with the joined tokens.

    5. Returns the final command as a single string.

    Parameters
    ----------
    utter : str
        The user's utterance, for example:
        - "תכתבי לי פתק לקנות חלב ולחם"
        - "אני צריכה שתעשי פתק להזכיר לי לשלם חשבון"
        - "תוסיפי פתק שצריך לקנות תרופה"

    Returns
    -------
    str
        A standardized 'create note' command, for example:
        - "תצרי לי פתק לקנות חלב ולחם"
        - "תצרי לי פתק להזכיר לי לשלם חשבון"
        - "תצרי לי פתק לקנות תרופה"

    Notes
    -----
    - Fuzzy exclusion (`Levenshtein.distance < 2`) helps handle
      misrecognized or colloquial variants.
    - The output is not post-processed by `create_command()`, but can be,
      if consistency with other command types is desired.
    - The current `exclude` list is empirically tuned for speech patterns of
      older adults and can be extended with additional polite or helper phrases.
    """
    template = ["תצרי לי פתק", "{content}"]

    exclude = {"תעשי", "תצרי", "תכתבי", "תרשמי", "פתק", "בו", "בה", "תודה", "בבקשה", "של", "עם", "על", "בוקר", "צהריים", "ערב", "טוב", "טובים", "תודה", "מראש", "אני",
              "צריך", "צריכה", "פתקית", "רישום", "את", "אם", "יכול", "יכולה", "לרשום", "לי", "בשבילי", "עבורי", "מעוניין", "מעוניינת", "שיהיה", "להיות", "שם", "תפתחי", "כתוב",
               "להכין", "תכיני", "כלולה", "מבקש", "מבקשת", "תוסיפי", "פתקים", "רוצה", "לפתוח", "יש", "להוסיף", "ליצור", "בפנים", "בעצם", "לפחות","אפליקצייה", "באפליקצייה",
               "אבל", "סליחה", "לבדוק", "חייב", "מעדכן", "תעדכן", "שקוראים"}

    query = []
    for word in utter.split():
      bad = False
      for e in exclude:
        dist_calc = Levenshtein.distance(e, word)
        if dist_calc < 2:
          bad = True
          break
      if not bad:
        query.append(word)

    template[1] = ' '.join(query)
    return ' '.join(template)

def flashlight_command():
  return "להדליק פנס"

def reformulate(utter, intent):
  if intent == 0:
    return call_command(utter)
  elif intent == 1:
    return alarm_command(utter)
  elif intent == 2:
    return sms_command(utter)
  elif intent == 3:
    return search_command(utter)
  elif intent == 4:
    return navigation_command(utter)
  elif intent == 5:
    return calander_command(utter)
  elif intent == 6:
    return camera_command()
  elif intent == 7:
    return weather_command(utter)
  elif intent == 8:
    return notes_command(utter)
  else:
    return flashlight_command()


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python script.py <utterance> <intent>")
        sys.exit(1)
    utter = sys.argv[1]
    intent = int(sys.argv[2])
    print(reformulate(utter, intent))



    
