# chat-translator

Turns a Chatbase export of WhatsApp chats between flexwerkers and the bot into a
spreadsheet staff can read in Dutch.

## Language

**Export**:
One Chatbase JSON file covering a date range, holding many conversations.
_Avoid_: Dump, log, input file

**Conversation**:
One WhatsApp chat between a single flexwerker and the bot, made of messages in order.
_Avoid_: Chat, thread, session

**Message**:
A single turn in a conversation, written either by the flexwerker or by the bot. Every message, including an empty one, becomes exactly one row of output.
_Avoid_: Turn, line, entry

**Role**:
Who wrote a message: `user` (the flexwerker) or `assistant` (the bot).
_Avoid_: Sender, author, speaker

**Flexwerker**:
A temporary worker who asks the bot questions; the `user` role.
_Avoid_: Customer, employee, end user

**Staff**:
The Dutch-reading colleagues who read the translated conversations.
_Avoid_: Reader, admin, operator

**Original language**:
The language a message is written in, judged from that message's own text alone, as an ISO 639-1 code. Not the conversation's `country`, and not inherited from neighbouring messages.
_Avoid_: Source language, locale, country

**Translation**:
A message's content rendered in Dutch. A message already in Dutch is its own translation; an empty message has none.
_Avoid_: Translated text, output
