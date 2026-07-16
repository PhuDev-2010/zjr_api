Bạn nói đúng! Tôi sẽ tạo một file README.md đầy đủ với TẤT CẢ các hàm từ file _client.py của bạn. Dưới đây là bản hoàn chỉnh:

---

🟦 ZaloAPI - Python Client for Zalo Chat (zjr_api)

https://img.shields.io/badge/Python-3.8+-blue.svg
https://img.shields.io/badge/License-MIT-green.svg
https://img.shields.io/badge/PRs-welcome-brightgreen.svg
https://img.shields.io/badge/GitHub-PhuDev--2010/zjr_api-blue?logo=github

Unofficial Python client for interacting with Zalo Chat Platform. Supports messaging, group management, file sending, and real-time event listening.

---

📌 Table of Contents

· ✨ Features
· 🚀 Installation
· 📖 How to get IMEI and Cookies
· ⚡ Quick Start
· 🔐 Authentication
· 📚 API Documentation
  · Account & Session
  · Fetch Information
  · Account Actions
  · User Actions
  · Group Management
  · Send Messages
  · Send Media
  · Message Actions
  · Event Listening
  · Event Callbacks
· 🔧 Advanced Usage
· ⚠️ Disclaimer
· 📄 License
· 🤝 Contributing

---

✨ Features

· ✅ Full authentication with phone/password or session cookies
· ✅ Send & receive text, images, videos, files, stickers, GIFs
· ✅ Group management - create, rename, add/kick members, set admins, disperse
· ✅ Message reactions (emoji reactions, multi-reactions)
· ✅ Real-time listening via WebSocket & HTTP polling
· ✅ Rich event system with customizable callbacks
· ✅ Message formatting - bold, italic, underline, strikethrough, mentions
· ✅ Thread-safe with ThreadPoolExecutor support
· ✅ Session persistence - save and load cookies
· ✅ Todo & Poll creation in groups
· ✅ QR Code generation and sending
· ✅ Business card sharing
· ✅ Voice & Video calls

---

🚀 Installation

```bash
pip install zjr_api
```

Or install directly from source:

```bash
pip install git+https://github.com/PhuDev-2010/zjr_api.git
```

---

📖 How to get IMEI and Cookies

Download Extension

· Click Here to download the extension.

Extension Usage Tutorial

1. Enable the extension downloaded above.
2. Go to https://chat.zalo.me, Sign in to your account.
3. After successfully logging in, go back to extension and get IMEI, Cookies.

[!TIP]
If you have opened the website chat.zalo.me but the extension does not have IMEI & Cookies, please click Refresh Page.

---

⚡ Quick Start

Custom Class (Recommended)

```python
from zjr_api import ZaloAPI, ThreadType, Message

class PhudDev(ZaloAPI):
    def __init__(self, phone, password, imei, session_cookies=None):
        super().__init__(
            phone=phone,
            password=password,
            imei=imei,
            session_cookies=session_cookies
        )

    def onMessage(self, mid, author_id, message, message_object, thread_id, thread_type):
        if message == ".hi":
            self.send(
                Message(text="Hello there! 👋"),
                thread_id=thread_id,
                thread_type=thread_type
            )

imei = "your_imei"
session_cookies = {}

client = PhudDev(
    phone="0912345678",
    password="your_password",
    imei=imei,
    session_cookies=session_cookies
)

client.listen(delay=0, thread=True, run_forever=True, type="websocket")
```

---

🔐 Authentication

Login with Phone & Password

```python
from zjr_api import ZaloAPI

client = ZaloAPI(
    phone="0912345678",
    password="your_password",
    imei="your_imei"
)
```

Login with Session Cookies

```python
from zjr_api import ZaloAPI

session_cookies = {
    'zpsid': 'your_zpsid_value',
    'zpext': 'your_zpext_value'
}

client = ZaloAPI(
    phone="0912345678",
    password="your_password",
    imei="your_imei",
    session_cookies=session_cookies
)
```

Get & Set Session

```python
# Save session
cookies = self.getSession()
import json
with open('session.json', 'w') as f:
    json.dump(cookies, f)

# Load session
with open('session.json', 'r') as f:
    cookies = json.load(f)
self.setSession(cookies)
```

Check Login Status

```python
if self.isLoggedIn():
    print("✅ Logged in!")
```

---

📚 API Documentation

Account & Session

isLoggedIn() -> bool

Check if client is logged in.

```python
if self.isLoggedIn():
    print("✅ Logged in!")
```

getSession() -> dict

Get session cookies.

```python
cookies = self.getSession()
```

setSession(session_cookies) -> bool

Load session cookies.

```python
self.setSession({'zpsid': 'value'})
```

getSecretKey() -> str

Get secret key for encoding/decoding.

```python
secret = self.getSecretKey()
```

setSecretKey(secret_key) -> bool

Set secret key manually.

```python
self.setSecretKey("your_base64_secret_key")
```

login(phone, password, imei, user_agent=None)

Manually login.

```python
self.login("0912345678", "password123", "imei_example")
```

---

Fetch Information

fetchAccountInfo() -> User

Get current user profile.

```python
user = self.fetchAccountInfo()
print(f"👤 {user.name}")
print(f"🆔 {user.userId}")
print(f"📱 {user.phone}")
```

fetchUserInfo(userId) -> User

Get user info by ID.

```python
user = self.fetchUserInfo("123456789")
print(user.name, user.avatar)
```

fetchPhoneNumber(phoneNumber, language="vi") -> User

Fetch user by phone number.

[!NOTE]
Can't get information of hidden phone number or locked account

```python
user = self.fetchPhoneNumber("0912345678")
print(user.name)
```

fetchAllFriends() -> List[User]

Get all friends.

```python
friends = self.fetchAllFriends()
for friend in friends:
    print(f"👥 {friend.name} - {friend.userId}")
```

fetchGroupInfo(groupId) -> Group

Get group information.

```python
group = self.fetchGroupInfo("987654321")
print(f"📁 {group.name}")
print(f"👤 Members: {len(group.members)}")
```

fetchAllGroups() -> List[Group]

Get all joined groups.

```python
groups = self.fetchAllGroups()
for group in groups:
    print(f"📁 {group.name} - {group.groupId}")
```

fetchUserLink(userId) -> dict

Get QR code link of a user.

```python
link = self.fetchUserLink("123456789")
print(f"🔗 QR URL: {link['qrUrl']}")
```

getLastMsgs() -> dict

Get last messages from all conversations.

```python
messages = self.getLastMsgs()
for msg in messages.msgs:
    print(f"💬 {msg.content}")
```

getRecentGroup(groupId) -> Group

Get recent messages in a group.

```python
messages = self.getRecentGroup("987654321")
for msg in messages.groupMsgs:
    print(f"💬 {msg.content}")
```

getGroupBoardList(groupId, page=1, count=20) -> Group

Get group board list (pinmsg, note, poll).

```python
board = self.getGroupBoardList("987654321")
```

getGroupPinMsg(groupId, page=1, count=20) -> Group

Get pinned messages in group.

```python
pins = self.getGroupPinMsg("987654321")
```

getGroupNote(groupId, page=1, count=20) -> Group

Get notes in group.

```python
notes = self.getGroupNote("987654321")
```

getGroupPoll(groupId, page=1, count=20) -> Group

Get polls in group.

```python
polls = self.getGroupPoll("987654321")
```

---

Account Actions

changeAccountSetting(name, dob, gender, biz={}, language="vi") -> User

Change account information.

```python
self.changeAccountSetting(
    name="New Name",
    dob="2000-01-01",
    gender=0  # 0 = Male, 1 = Female
)
```

changeAccountAvatar(filePath, width=500, height=500, language="vn", size=None) -> User

Change account avatar.

```python
self.changeAccountAvatar("avatar.jpg")
```

---

User Actions

sendFriendRequest(userId, msg, language="vi") -> User

Send friend request.

```python
self.sendFriendRequest(
    userId="123456789",
    msg="Hi, let's connect!"
)
```

acceptFriendRequest(userId, language="vi") -> User

Accept friend request.

```python
self.acceptFriendRequest("123456789")
```

unfriendUser(userId, language="vi") -> dict

Unfriend a user.

```python
self.unfriendUser("123456789")
```

blockUser(userId) -> User

Block a user.

```python
self.blockUser("123456789")
```

unblockUser(userId) -> User

Unblock a user.

```python
self.unblockUser("123456789")
```

blockViewFeed(userId, isBlockFeed) -> User

Block/unblock user from viewing feed.

```python
self.blockViewFeed("123456789", isBlockFeed=1)  # Block
self.blockViewFeed("123456789", isBlockFeed=0)  # Unblock
```

sendReport(user_id, reason=0, content=None) -> User

Report a user.

```python
# Report with reason
self.sendReport(
    user_id="123456789",
    reason=1  # 1=Sensitive, 2=Spam, 3=Scam
)

# Custom report
self.sendReport(
    user_id="123456789",
    content="Spamming inappropriate messages"
)
```

---

Group Management

createGroup(name=None, description=None, members=[], nameChanged=1, createLink=1) -> Group

Create a new group.

```python
group = self.createGroup(
    name="Python Dev Group",
    description="ZaloAPI developers",
    members=["123456789", "987654321"],
    createLink=1
)
print(f"✅ Group created: {group['grid']}")
```

changeGroupName(groupName, groupId) -> Group

Change group name.

[!NOTE]
Client must be the Owner of the group

```python
self.changeGroupName("New Group Name", "987654321")
```

changeGroupAvatar(filePath, groupId) -> Group

Change group avatar.

[!NOTE]
Client must be the Owner of the group

```python
self.changeGroupAvatar("new_avatar.jpg", "987654321")
```

addUsersToGroup(user_ids, groupId) -> Group

Add members to group.

```python
self.addUsersToGroup(
    user_ids=["123456789", "987654321"],
    groupId="987654321"
)
```

kickUsersInGroup(members, groupId) -> Group

Remove members from group.

[!NOTE]
Client must be the Owner of the group

```python
self.kickUsersInGroup(
    members=["123456789"],
    groupId="987654321"
)
```

blockUsersInGroup(members, groupId) -> Group

Block members in group.

[!NOTE]
Client must be the Owner of the group

```python
self.blockUsersInGroup(
    members=["123456789"],
    groupId="987654321"
)
```

unblockUsersInGroup(members, groupId) -> Group

Unblock members in group.

[!NOTE]
Client must be the Owner of the group

```python
self.unblockUsersInGroup(
    members=["123456789"],
    groupId="987654321"
)
```

addGroupAdmins(members, groupId) -> Group

Add group admins (white key).

[!NOTE]
Client must be the Owner of the group

```python
self.addGroupAdmins(
    members=["123456789"],
    groupId="987654321"
)
```

removeGroupAdmins(members, groupId) -> Group

Remove group admins.

[!NOTE]
Client must be the Owner of the group

```python
self.removeGroupAdmins(
    members=["123456789"],
    groupId="987654321"
)
```

changeGroupOwner(newAdminId, groupId) -> Group

Transfer group ownership.

[!NOTE]
Client must be the Owner of the group

```python
self.changeGroupOwner(
    newAdminId="123456789",
    groupId="987654321"
)
```

changeGroupSetting(groupId, defaultMode="default", **kwargs) -> Group

Update group settings.

[!NOTE]
Client must be the Owner/Admin of the group

```python
# Anti-raid mode
self.changeGroupSetting(
    groupId="987654321",
    defaultMode="anti-raid"
)

# Custom settings
self.changeGroupSetting(
    groupId="987654321",
    blockName=1,           # Prevent name/avatar changes
    lockSendMsg=1,         # Lock sending messages
    joinAppr=1,           # Approval required
    setTopicOnly=1        # Only admins can pin
)
```

pinGroupMsg(pinMsg, groupId) -> Group

Pin a message.

```python
message = self.getRecentGroup("987654321").groupMsgs[0]
self.pinGroupMsg(
    pinMsg=message,
    groupId="987654321"
)
```

unpinGroupMsg(pinId, pinTime, groupId) -> Group

Unpin a message.

```python
self.unpinGroupMsg(
    pinId="12345",
    pinTime=1700000000,
    groupId="987654321"
)
```

deleteGroupMsg(msgId, ownerId, clientMsgId, groupId) -> Group

Delete a message in group.

```python
self.deleteGroupMsg(
    msgId="12345",
    ownerId="123456789",
    clientMsgId="67890",
    groupId="987654321"
)
```

viewGroupPending(groupId) -> Group

View pending members.

```python
pending = self.viewGroupPending("987654321")
```

handleGroupPending(members, groupId, isApprove=True) -> Group

Approve/Deny pending members.

[!NOTE]
Client must be the Owner of the group

```python
self.handleGroupPending(
    members=["123456789"],
    groupId="987654321",
    isApprove=True
)
```

createPoll(question, options, groupId, expiredTime=0, **kwargs) -> Group

Create a poll.

[!NOTE]
Client must be the Owner of the group

```python
self.createPoll(
    question="What's your favorite Python library?",
    options=["Requests", "BeautifulSoup", "Django", "Flask"],
    groupId="987654321",
    expiredTime=3600,  # 1 hour
    multiChoices=True,
    isAnonymous=False
)
```

lockPoll(pollId) -> Group

Lock/end a poll.

```python
self.lockPoll(pollId="12345")
```

viewPollDetail(pollId) -> Group

View poll details.

```python
poll = self.viewPollDetail("12345")
print(poll)
```

joinGroup(url) -> dict

Join a group via invite link.

```python
result = self.joinGroup("https://zalo.me/g/abc123")
print(result)
```

newLink(groupId) -> dict

Create a new invite link.

```python
link = self.newLink("987654321")
print(f"🔗 New link: {link['new_link']}")
```

disableLink(groupId) -> dict

Disable group invite link.

```python
self.disableLink("987654321")
```

leaveGroup(groupId, silent=1, language='vi') -> dict

Leave a group.

```python
self.leaveGroup(
    groupId="987654321",
    silent=1  # 1 = silent, 0 = notify members
)
```

disperseGroup(groupId) -> Group

Disperse/delete group.

[!NOTE]
Client must be the Owner of the group

```python
self.disperseGroup("987654321")
```

---

Send Messages

send(message, thread_id, thread_type=ThreadType.USER, mark_message=None, ttl=0) -> User/Group

Send a message with formatting and mentions.

```python
from zjr_api import Message, Mention, ThreadType

# Plain text
msg = Message(text="Hello world!")
self.send(msg, "123456789", ThreadType.USER)

# With formatting
msg = Message(
    text="**Bold** *Italic* __Underline__ ~~Strikethrough~~",
    style=MessageStyle(
        bold=True,
        italic=True,
        underline=True,
        strikethrough=True
    )
)
self.send(msg, "123456789", ThreadType.USER)

# With mentions
mention = Mention(
    uid="123456789",
    displayName="John Doe",
    start=0,
    length=8
)
msg = Message(
    text="@John Hello!",
    mention=[mention.toDict()]
)
self.send(msg, "123456789", ThreadType.USER)
```

sendMessage(message, thread_id, thread_type, mark_message=None, ttl=0) -> User/Group

Send plain text message with urgency marking.

```python
self.sendMessage(
    message=Message(text="Urgent news!"),
    thread_id="123456789",
    thread_type=ThreadType.GROUP,
    mark_message="urgent"  # or "important"
)
```

replyMessage(message, replyMsg, thread_id, thread_type, ttl=0) -> User/Group

Reply to a specific message.

```python
original_msg = self.getLastMsgs().msgs[0]
reply = Message(text="I agree with you!")
self.replyMessage(
    message=reply,
    replyMsg=original_msg,
    thread_id="123456789",
    thread_type=ThreadType.USER
)
```

sendMentionMessage(message, groupId, ttl=0) -> Group

Send mention message in group.

```python
mention = Mention(uid="123456789", length=5, offset=10)
msg = Message(
    text="@John Hello!",
    mention=[mention.toDict()]
)
self.sendMentionMessage(msg, "987654321")
```

undoMessage(msgId, cliMsgId, thread_id, thread_type) -> User/Group

Unsend/recall a message.

```python
self.undoMessage(
    msgId="12345",
    cliMsgId="67890",
    thread_id="123456789",
    thread_type=ThreadType.USER
)
```

sendReaction(messageObject, reactionIcon, thread_id, thread_type, reactionType=75) -> User/Group

React to a message.

```python
message = self.getLastMsgs().msgs[0]
self.sendReaction(
    messageObject=message,
    reactionIcon="❤️",
    thread_id="123456789",
    thread_type=ThreadType.USER
)
```

sendMultiReaction(reactionObj, reactionIcon, thread_id, thread_type, reactionType=75) -> User/Group

React to multiple messages.

```python
messages = self.getLastMsgs().msgs[:3]
reaction_obj = [
    {"gMsgID": int(msg.msgId), "cMsgID": int(msg.cliMsgId), "msgType": 1}
    for msg in messages
]
self.sendMultiReaction(
    reactionObj=reaction_obj,
    reactionIcon="❤️",
    thread_id="123456789",
    thread_type=ThreadType.USER
)
```

sendToDo(message_object, content, assignees, thread_id, thread_type, due_date=-1, description="PhuDev") -> dict

Send a todo.

```python
message = self.getLastMsgs().msgs[0]
self.sendToDo(
    message_object=message,
    content="Buy groceries",
    assignees=["123456789"],
    thread_id="987654321",
    thread_type=ThreadType.GROUP,
    due_date=1700000000
)
```

sendCall(userId, callId=None) -> dict

Initiate a call to a user.

```python
self.sendCall(userId="123456789")
```

---

Send Media

_uploadImage(filePath, thread_id, thread_type) -> dict

Upload image to Zalo (internal use).

```python
upload_data = self._uploadImage("photo.jpg", "123456789", ThreadType.USER)
```

sendLocalImage(imagePath, thread_id, thread_type, width=2560, height=2560, message=None, custom_payload=None, ttl=0) -> User/Group

Send image from local file.

```python
self.sendLocalImage(
    imagePath="photo.jpg",
    thread_id="123456789",
    thread_type=ThreadType.USER,
    message=Message(text="Check this out!")
)
```

sendImageByUrl(image_url, thread_id, thread_type, width=2560, height=2560, message=None, ttl=0) -> list

Send image from URL (supports multiple).

```python
# Single image
self.sendImageByUrl(
    image_url="https://example.com/image.jpg",
    thread_id="123456789",
    thread_type=ThreadType.GROUP
)

# Multiple images
self.sendImageByUrl(
    image_url=["url1.jpg", "url2.jpg"],
    thread_id="123456789",
    thread_type=ThreadType.USER
)
```

sendMultiLocalImage(imagePathList, thread_id, thread_type, width=2560, height=2560, message=None, ttl=0) -> User/Group

Send multiple images from local files.

```python
self.sendMultiLocalImage(
    imagePathList=["photo1.jpg", "photo2.jpg", "photo3.jpg"],
    thread_id="123456789",
    thread_type=ThreadType.USER
)
```

sendLocalGif(gifPath, thumbnailUrl, thread_id, thread_type, gifName="phudev.gif", width=500, height=500, ttl=0) -> User/Group

Send GIF from local file.

```python
self.sendLocalGif(
    gifPath="animation.gif",
    thumbnailUrl="https://example.com/thumb.jpg",
    thread_id="123456789",
    thread_type=ThreadType.USER
)
```

sendRemoteFile(fileUrl, thread_id, thread_type, fileName="default", fileSize=None, extension="phudev", ttl=0) -> User/Group

Send file from URL.

```python
self.sendRemoteFile(
    fileUrl="https://example.com/document.pdf",
    fileName="report.pdf",
    extension="pdf",
    thread_id="123456789",
    thread_type=ThreadType.USER
)
```

sendRemoteVideo(videoUrl, thumbnailUrl, duration, thread_id, thread_type, width=1280, height=720, message=None, ttl=0) -> User/Group

Send video from URL.

[!WARNING]
This is a feature created through the forward function. Because Zalo Web does not allow viewing videos.

```python
self.sendRemoteVideo(
    videoUrl="https://example.com/video.mp4",
    thumbnailUrl="https://example.com/thumb.jpg",
    duration=30000,  # milliseconds
    thread_id="123456789",
    thread_type=ThreadType.USER
)
```

sendRemoteVoice(voiceUrl, thread_id, thread_type, fileSize=None, ttl=0) -> User/Group

Send voice message from URL.

```python
self.sendRemoteVoice(
    voiceUrl="https://example.com/voice.mp3",
    thread_id="123456789",
    thread_type=ThreadType.USER
)
```

sendSticker(stickerType, stickerId, cateId, thread_id, thread_type, ttl=0) -> User/Group

Send sticker.

```python
self.sendSticker(
    stickerType=1,
    stickerId=12345,
    cateId=67890,
    thread_id="123456789",
    thread_type=ThreadType.USER
)
```

sendCustomSticker(staticImgUrl, animationImgUrl, thread_id, thread_type, reply=None, width=None, height=None, ttl=0) -> User/Group

Send custom sticker.

```python
self.sendCustomSticker(
    staticImgUrl="https://example.com/sticker.png",
    animationImgUrl="https://example.com/sticker.webp",
    thread_id="123456789",
    thread_type=ThreadType.USER
)
```

sendQrCode(content, thread_id, thread_type, background=None, width=2560, height=2560, message=None, ttl=0) -> User/Group

Generate and send QR code.

```python
self.sendQrCode(
    content="https://example.com",
    thread_id="123456789",
    thread_type=ThreadType.USER,
    background="https://example.com/bg.jpg"  # optional
)
```

sendBusinessCard(userId, qrCodeUrl, thread_id, thread_type, phone=None, ttl=0) -> User/Group

Send business card.

```python
self.sendBusinessCard(
    userId="123456789",
    qrCodeUrl="https://example.com/qr.jpg",
    thread_id="987654321",
    thread_type=ThreadType.USER,
    phone="0912345678"
)
```

sendLink(linkUrl, title, thread_id, thread_type, thumbnailUrl=None, domainUrl=None, description=None, message=None, ttl=0) -> User/Group

Send link with preview card.

```python
self.sendLink(
    linkUrl="https://github.com",
    title="GitHub",
    description="Build software better, together",
    thumbnailUrl="https://github.com/logo.png",
    thread_id="123456789",
    thread_type=ThreadType.USER
)
```

---

Message Actions

setTyping(thread_id, thread_type)

Set typing status.

```python
self.setTyping(
    thread_id="123456789",
    thread_type=ThreadType.USER
)
```

markAsDelivered(msgId, cliMsgId, senderId, thread_id, thread_type, seen=0, method="webchat") -> bool

Mark message as delivered.

```python
self.markAsDelivered(
    msgId="12345",
    cliMsgId="67890",
    senderId="123456789",
    thread_id="987654321",
    thread_type=ThreadType.GROUP
)
```

markAsRead(msgId, cliMsgId, senderId, thread_id, thread_type, method="webchat") -> bool

Mark message as read.

```python
self.markAsRead(
    msgId="12345",
    cliMsgId="67890",
    senderId="123456789",
    thread_id="987654321",
    thread_type=ThreadType.GROUP
)
```

---

Event Listening

listen(delay=0, thread=False, type="websocket", run_forever=False, reconnect=5)

Start listening for events.

```python
# WebSocket mode (recommended)
self.listen(
    delay=0,
    thread=True,
    type="websocket",
    run_forever=True,
    reconnect=5
)

# HTTP polling mode
self.listen(
    delay=1,
    thread=True,
    type="requests",
    run_forever=True
)
```

startListening(delay=0, thread=False, type="websocket", reconnect=5)

Start listening from an external event loop.

```python
self.startListening(delay=0, thread=True, type="websocket", reconnect=5)
```

stopListening()

Stop the listening loop.

```python
self.stopListening()
```

---

Event Callbacks

Override these methods in your custom class:

```python
from zjr_api import ZaloAPI, ThreadType, Message, GroupEventType

class PhudDev(ZaloAPI):
    def onLoggingIn(self, phone=None):
        """Called when logging in."""
        print(f"🔐 Logging in as {phone}...")
    
    def onLoggedIn(self, phone=None):
        """Called when successfully logged in."""
        print(f"✅ Logged in as {phone}!")
    
    def onListening(self):
        """Called when client starts listening."""
        print("👂 Listening for messages...")
    
    def onMessage(self, mid, author_id, message, message_object, thread_id, thread_type):
        """Called when a new message is received."""
        print(f"💬 {author_id}: {message}")
        
        # Auto-reply
        if message.lower() == "hello":
            self.send(
                Message(text="Hi there! 👋"),
                thread_id=thread_id,
                thread_type=thread_type
            )
    
    def onEvent(self, event_data, event_type):
        """Called when a group event occurs."""
        print(f"⚡ Event: {event_type} from {event_data}")
        
        if event_type == GroupEventType.MEMBER_JOIN:
            print(f"👤 New member joined: {event_data.userId}")
    
    def onMessageDelivered(self, msg_ids=None, thread_id=None, thread_type=ThreadType.USER, ts=None):
        """Called when messages are marked as delivered."""
        print(f"✅ Message delivered: {msg_ids}")
    
    def onMarkedSeen(self, msg_ids=None, thread_id=None, thread_type=ThreadType.USER, ts=None):
        """Called when messages are marked as read/seen."""
        print(f"👁️ Message seen: {msg_ids}")
    
    def onErrorCallBack(self, error, ts=int(time.time())):
        """Called when an error occurs."""
        print(f"❌ Error at {ts}: {error}")
```

---

🔧 Advanced Usage

Custom Event Handlers

```python
from zjr_api import ZaloAPI, ThreadType, Message, GroupEventType

class Bot(ZaloAPI):
    def __init__(self, phone, password, imei, session_cookies=None):
        super().__init__(phone, password, imei, session_cookies)
        self.running = True
    
    def onMessage(self, mid, author_id, message, message_object, thread_id, thread_type):
        # Ignore own messages
        if author_id == self.uid:
            return
        
        # Command handler
        if message.startswith('/'):
            cmd = message[1:].lower()
            
            if cmd == 'ping':
                self.send(
                    Message(text="Pong! 🏓"),
                    thread_id, thread_type
                )
            
            elif cmd == 'info':
                user = self.fetchUserInfo(author_id)
                self.send(
                    Message(text=f"👤 {user.name}\n📱 {user.phone}"),
                    thread_id, thread_type
                )
            
            elif cmd == 'group':
                if thread_type == ThreadType.GROUP:
                    group = self.fetchGroupInfo(thread_id)
                    self.send(
                        Message(
                            text=f"📁 {group.name}\n"
                                 f"👥 {len(group.members)} members"
                        ),
                        thread_id, thread_type
                    )
            
            elif cmd == 'help':
                self.send(
                    Message(
                        text="/ping - Pong!\n"
                             "/info - Get user info\n"
                             "/group - Get group info"
                    ),
                    thread_id, thread_type
                )
```

Error Handling

```python
from zjr_api import ZaloAPI, ZaloAPIException, ZaloLoginError, ZaloUserError

try:
    client = ZaloAPI("0912345678", "password", "imei")
    client.send(Message(text="Hello"), "123456789", ThreadType.USER)
    
except ZaloLoginError:
    print("❌ Login failed! Check credentials.")
    
except ZaloAPIException as e:
    print(f"❌ API Error: {e}")
    
except ZaloUserError as e:
    print(f"❌ User Error: {e}")
    
except Exception as e:
    print(f"❌ Unexpected Error: {e}")
```

Thread Pool

```python
from concurrent.futures import ThreadPoolExecutor

# Custom thread pool
executor = ThreadPoolExecutor(max_workers=10)

# Submit tasks
future = executor.submit(self.fetchUserInfo, "123456789")
result = future.result()
```

---

⚠️ Disclaimer

· This is an unofficial client and is not affiliated with Zalo.
· Use at your own risk.
· Respect Zalo's Terms of Service.
· Do not use for spamming or malicious purposes.
· The author is not responsible for any misuse.

---

📄 License

MIT License - see LICENSE file for details.

---

🤝 Contributing

Contributions are welcome! Please submit a Pull Request.

1. Fork the repository
2. Create your feature branch (git checkout -b feature/AmazingFeature)
3. Commit your changes (git commit -m 'Add some AmazingFeature')
4. Push to the branch (git push origin feature/AmazingFeature)
5. Open a Pull Request

---

📞 Contact

· 💬 Zalo: PhuDev
· 📧 Email: phudev2010@gmail.com
· 🐛 Issues: GitHub Issues
· 📚 GitHub: PhuDev-2010/zjr_api

---

⭐ Acknowledgments

· This project was originally inspired by fbchat.
· listen websocket type taken from zca-js.

⭐ Star this repository if you find it useful!