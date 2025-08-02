![Logo](https://i.imgur.com/CMnA5Sh.jpeg "Logo")

## ``zjr_api`` - Zalo API (Unofficial) for Python

### What is ``zjr_api``?

A powerful and efficient library to interact with Zalo Website. 
This is *not* an official API, Zalo has that [over here](https://developers.zalo.me/docs) for chat bots. This library differs by using a normal Zalo account instead (More flexible).

``zjr_api`` currently support:

- Custom style for message.
- Sending many types of messages, with files, stickers, mentions, etc.
- Fetching messages, threads and users info.
- Creating groups, setting the group, creating polls, etc.
- Listening for, an reacting to messages and other events in real-time.
- Assign tasks to multiple users.
- etc.

Essentially, everything you need to make an amazing Zalo Bot!


### Caveats

``zjr_api`` works by imitating what the browser does, and thereby tricking Zalo into thinking it's accessing the website normally.

However, there's a catch! **Using this library may not comply with Zalo's Terms Of Service**, so be! We are not responsible if your account gets banned or disabled!


### What's New?

This is an updated version for ``zjr_api`` to improve features and fix bugs (v1.0)

**Improvements**

- Eliminate asynchrony and simple code style
- Set fixed listen delay to 0s
- The code is easier to understand, the structure is separate from one line as before.
- Send jobs to users[GET](#send-to-do)
- Send voice call to person[GET](#send-call)
- Create new group link[GET](#new-link)
- Disable the current group link[GET](#disable-link)
- Unfriend user[GET](#unfriend-user)
- Get your own QR code[GET](#fetch-user-link)
- Send image by direct url[GET](#send-image-by-url)

</br>

## Installation

```bash
pip install git+https://github.com/PhuDev-2010/zjr_api
```

</br>

## How to get IMEI and Cookies?

### Download Extension

- [Click Here](https://drive.google.com/file/d/18_-8ruYOVa89JkHdr3muGj3kGWxwt6mc/view?usp=drive_link) to download the extension support getting IMEI & Cookies more conveniently.

### Extension Usage Tutorial

1. Enable the extension downloaded above.
2. Go to [https://chat.zalo.me](https://chat.zalo.me), Sign in to your account.
3. After successfully logging in, go back to extension and get IMEI, Cookies.

> [!TIP]
If you have opened the website ``chat.zalo.me`` but the extension does not have IMEI & Cookies, please click ``Refresh Page``.

#### Windows

[![](https://previews.jumpshare.com/thumb/815bc01b796dd6f1733c957c5af19493968eb06ccf48b6a5036cf7916c0a83965899fb056fe88c29f2bcb2f9f0f5ed5832801eede43aa22e94d5c7bc545ef9448bfbfd14044e807555841b406fdf069aa3acda441ff8675390fa0ff601ff0bcd)](https://jumpshare.com/embed/8SjFyd3EQlCMx1V7N1UQ)

</br>

#### Android

> - Use ``kiwibrowser`` instead of ``chrome`` to be able to use the extension.
> - If you are redirect when accessing ``https://chat.zalo.me``. [Watch this video](https://jumpshare.com/embed/l3LLjAWSAR8KQxvh9dzz)

[![](https://previews.jumpshare.com/thumb/815bc01b796dd6f1733c957c5af194938966297dbb29c75d038ac93e0691be4c741e5e2cbb689c41b8dfebde4ded3316844e23ec82425f377c248f1a57861470e76e9fe268bdf0803c7c14a61c9dc50769f92efb3803e5ae68c46d260d3407db)](https://jumpshare.com/embed/n56jtVQ7pwZDfR5ZtPft)

</br>

## Basic Usage

### Login Account Using Cookies

```py
from zjr_api import ZaloAPI
from zjr_api.models import *

imei = ""
session_cookie = {}

class Bot(ZaloAPI):
	def __init__(self, api_key, secret_key, imei, session_cookies):
		super().__init__(api_key, secret_key, imei=imei, session_cookies=session_cookies)

	def onMessage(self, mid, author_id, message, message_object, thread_id, thread_type):

bot = Bot(
	"api_key", 
	"secret_key", 
	imei=imei, 
	session_cookies=session_cookie
).listen(
	delay=0, 
	thread=True, 
	run_forever=True, 
	type="websocket"
)
```

</br>

### Listen Message, Event, ...

* You can enable thread mode for [On Message](#on-message) function (work with ``requests`` type) with ``thread=True``.

```py
bot.listen(thread=True)
```

* You can change the listen mode with ``type="<listen type>"``. Current module support ``websocket``, ``requests`` type (default type is **websocket**)

```py
bot.listen(type="<listen type>")
```

* If you don't want to have to rerun the bot script when something goes wrong in the **listen** function you can use ``run_forever=True``.

```py
bot.listen(run_forever=True)
```

</br>

### Custom On Message Function

``onMessage`` function will be called when receiving a message from ``listen`` function. **So we can handle that message here.**

```py
from zjr_api import ZaloAPI
from zjr_api.models import *

imei = ""
session_cookie = {}

class Bot(ZaloAPI):
	def __init__(self, api_key, secret_key, imei, session_cookies):
		super().__init__(api_key, secret_key, imei=imei, session_cookies=session_cookies)

	def onMessage(self, mid, author_id, message, message_object, thread_id, thread_type):
		pass

bot = Bot(
	"api_key", 
	"secret_key", 
	imei=imei, 
	session_cookies=session_cookie
).listen(
	delay=0, 
	thread=True, 
	run_forever=True, 
	type="websocket"
)
```

</br>

### Example Handle Message

```py
from zjr_api import ZaloAPI
from zjr_api.models import *

imei = ""
session_cookie = {}

class Bot(ZaloAPI):
	def __init__(self, api_key, secret_key, imei, session_cookies):
		super().__init__(api_key, secret_key, imei=imei, session_cookies=session_cookies)

	def onMessage(self, mid, author_id, message, message_object, thread_id, thread_type):
		if ".hi" in message:
			print(author_id, "Đã gửi tin nhắn '.hi'")

bot = Bot(
	"api_key", 
	"secret_key", 
	imei=imei, 
	session_cookies=session_cookie
).listen(
	delay=0, 
	thread=True, 
	run_forever=True, 
	type="websocket"
)
```
</br>

<!-- fetchAccountInfo -->

### Fetch Account Information

This function will get the account information you are using in ``zjr_api``.

```py
self.fetchAccountInfo()
```
</br>

<!-- END FetchAccountInfo -->

<!-- fetchPhoneNumber -->

### Fetch Phone Number

This function will get user information using that user phone number.

> [!NOTE]
Can't get information of **hidden phone number** or **locked account**

```py
self.fetchPhoneNumber(<phone number>)
```
</br>

<!-- END FetchPhoneNumber -->

<!-- fetchUserInfo -->

### Fetch User Info

This function will get user information using that user ID.

```py
self.fetchUserInfo(<user id>)
```
</br>

<!-- END FetchUserInfo -->

<!-- fetchUserLink -->

### Fetch User Link

This function will get the user's QR code by ID

```py
self.fetchUserLink(<user id>)
```
<!-- fetchGroupInfo -->

### Fetch Group Info

This function will get group information using that group ID.

```py
self.fetchGroupInfo("<group id>")
```
</br>

<!-- END FetchGroupInfo -->

<!-- fetchAllFriends -->

### Fetch All Friends

This function will get all the friends information of the account currently using the ``zjr_api``.

```py
self.fetchAllFriends()
```
</br>

<!-- END FetchAllFriends -->

<!-- fetchAllGroups -->

### Fetch All Groups

This function will get all the groups id of the account currently using the ``zjr_api``.

```py
self.fetchAllGroups()
```
</br>

<!-- END FetchAllGroups -->

<!-- changeAccountSetting -->

### Change Account Setting

This function will change setting of the account currently using the ``zjr_api``.

> - Args:
>	- name (str): The new account name
>	- dob (str): Date of birth wants to change (format: year-month-day)
>	- gender (int | str): Gender wants to change (0 = Male, 1 = Female)

```py
self.changeAccountSetting(
	<name>, 
	<dob>, 
	<gender>
)
```
</br>
<!-- END changeAccountSetting -->

<!-- changeAccountAvatar -->

### Change Account Avatar

This function will upload/change avatar of the account currently using the ``zjr_api``.

> - Args:
>	- filePath (str): A path to the image to upload/change avatar
>	- size (int): Avatar image size (default = auto)
>	- width (int): Width of avatar image
>	- height (int): height of avatar image
>	- language (int | str): Zalo Website language ? (idk)

```py
self.changeAccountAvatar(
	<filePath>, 
	<size>, 
	<width>, 
	<height>, 
)
```
</br>
<!-- END changeAccountAvatar -->

<!-- sendFriendRequest -->

### Send Friend Request

This function will send friend request to a user by ID.

> - Args:
>	- userId (int | str): User ID to send friend request
>	- msg (str): Friend request message
>	- language (str): Response language or Zalo interface language

```py
self.sendFriendRequest(<userId>, <msg>)
```
</br>

<!-- END sendFriendRequest -->

<!-- unfriendUser -->

### unfriend User

This function will delete user friend by ID

> - Args:
>	- userId (int | str): User ID to delete the triple

```py
self.unfriendUser(<userId>)
```
</br>

<!-- END unfriendUser -->

<!-- acceptFriendRequest -->

### Accept Friend Request

This function will accept friend request from user by ID.

> - Args:
>	- userId (int | str): User ID to accept friend request
>	- language (str): Response language or Zalo interface language

```py
self.acceptFriendRequest(<userId>)
```
</br>

<!-- END acceptFriendRequest -->

<!-- blockViewFeed -->

### Block View Feed

This function will Block/Unblock friend view feed by ID.

> - Args:
>	- userId (int | str): User ID to block/unblock view feed
>	- isBlockFeed (int): Block/Unblock friend view feed (1 = True | 0 = False)

```py
self.blockViewFeed(<userId>, <isBlockFeed>)
```
</br>

<!-- END blockViewFeed -->

<!-- blockUser -->

### Block User

This function will block user by ID.

> - Args:
>	- userId (int | str): User ID to block

```py
self.blockUser(<userId>)
```
</br>

<!-- END blockUser -->

<!-- unblockUser -->

### Unblock User

This function will unblock user by ID.

> - Args:
>	- userId (int | str): User ID to unblock

```py
self.unblockUser(<userId>)
```
</br>

<!-- END unblockUser -->

<!-- newLink -->

### New Link

This function will create a new link for the group.

> - Args:
>	- groupId (int | str): Group ID to create dream link

```py
self.newLink(<groupId>)
```
</br>

<!-- END newLink -->

<!-- disableLink -->

### Disable Link 
This function will disable the current group link.

> - Args:
>	- groupId (int | str): Group ID to be disabled

```py
self.disableLink(<groupId>)
```
</br>

<!-- END disableLink -->

<!-- joinGroup -->

### Join Group
This function will join the group by url

> - Args:
>	- url (str): Group url to join

```py
self.joinGroup(<url>)
```
</br>

<!-- END joinGroup -->

<!-- leaveGroup -->

### Leave Group
This function will leave the group by ID

> - Args:
>	- groupId (int | str): Group ID to leave

```py
self.leaveGroup(<groupId>)
```
</br>

<!-- createGroup -->

### Create Group

This function will Create a new group.

> - Args:
>	- name (str): The new group name
>	- description (str): Description of the new group
>	- members (str | list): List/String member IDs add to new group
>	- nameChanged (int - auto): Will use default name if disabled (0), else (1)
>	- createLink (int - default): Create a group link? Default = 1 (True)

```py
self.createGroup(
	<name>, 
	<description>, 
	<members>
)
```
</br>

<!-- END createGroup -->

<!-- changeGroupAvatar -->

### Change Group Avatar

This function will Upload/Change group avatar by ID.

> - Args:
>	- filePath (str): A path to the image to upload/change avatar
>	- groupId (int | str): Group ID to upload/change avatar

```py
self.changeGroupAvatar(<filePath>, <groupId>)
```

> [!NOTE]
Client must be the Owner of the group
(If the group does not allow members to upload/change)
</br>

<!-- END changeGroupAvatar -->

<!-- changeGroupName -->

### Change Group Name

This function will Set/Change group name by ID.

> - Args:
>	- groupName (str): Group name to change
>	- groupId (int | str): Group ID to change name

```py
self.changeGroupName(<groupName>, <groupId>)
```

> [!NOTE]
Client must be the Owner of the group
(If the group does not allow members to upload/change)
</br>

<!-- END changeGroupName -->

<!-- changeGroupSetting -->

### Change Group Setting

This function will Update group settings by ID.

> - Args:
>	- groupId (int | str): Group ID to update settings
>	- defaultMode (str): Default mode of settings
>			
>		- default: Group default settings
>		- anti-raid: Group default settings for anti-raid
>			
>	- **kwargs: Group settings kwargs, Value: (1 = True, 0 = False)
>			
>		- blockName: Không cho phép user đổi tên & ảnh đại diện nhóm
>		- signAdminMsg: Đánh dấu tin nhắn từ chủ/phó nhóm
>		- addMemberOnly: Chỉ thêm members (Khi tắt link tham gia nhóm)
>		- setTopicOnly: Cho phép members ghim (tin nhắn, ghi chú, bình chọn)
>		- enableMsgHistory: Cho phép new members đọc tin nhắn gần nhất
>		- lockCreatePost: Không cho phép members tạo ghi chú, nhắc hẹn
>		- lockCreatePoll: Không cho phép members tạo bình chọn
>		- joinAppr: Chế độ phê duyệt thành viên
>		- bannFeature: Default (No description)
>		- dirtyMedia: Default (No description)
>		- banDuration: Default (No description)
>		- lockSendMsg: Không cho phép members gửi tin nhắn
>		- lockViewMember: Không cho phép members xem thành viên nhóm
>		- blocked_members: Danh sách members bị chặn

```py
self.changeGroupSetting(<groupId>, **kwargs)
```

> [!WARNING]
Other settings will default value if not set. See `defaultMode`
</br>

<!-- END changeGroupSetting -->

<!-- changeGroupOwner -->

### Change Group Owner

This function will Change group owner by ID.

> - Args:
>	- newAdminId (int | str): members ID to changer owner
>	- groupId (int | str): ID of the group to changer owner

```py
self.changeGroupOwner(<newAdminId>, <groupId>)
```

> [!NOTE]
Client must be the Owner of the group.
</br>

<!-- END changeGroupOwner -->

<!-- addUsersToGroup -->

### Add Users To Group

This function will Add friends/users to a group.

> - Args:
>	- user_ids (str | list): One or more friend/user IDs to add
>	- groupId (int | str): Group ID to add friend/user to

```py
self.addUsersToGroup(<user_ids>, <groupId>)
```
</br>

<!-- END addUsersToGroup -->

<!-- kickUsersInGroup -->

### Kick Users In Group

This function will Kickout members in group by ID.

> - Args:
>	- members (str | list): One or More member IDs to kickout
>	- groupId (int | str): Group ID to kick member from

```py
self.kickUsersInGroup(<members>, <groupId>)
```

> [!NOTE]
Client must be the Owner of the group.
</br>

<!-- END kickUsersInGroup -->

<!-- blockUsersInGroup -->

### Block Users In Group

This function will Blocked members in group by ID.

> - Args:
>	- members (str | list): One or More member IDs to block
>	- groupId (int | str): Group ID to block member from

```py
self.blockUsersInGroup(<members>, <groupId>)
```

> [!NOTE]
Client must be the Owner of the group.
</br>

<!-- END blockUsersInGroup -->

<!-- unblockUsersInGroup -->

### Unblock Users In Group

This function will Unblock members in group by ID.

> - Args:
>	- members (str | list): One or More member IDs to unblock
>	- groupId (int | str): Group ID to unblock member from

```py
self.unblockUsersInGroup(<members>, <groupId>)
```

> [!NOTE]
Client must be the Owner of the group.
</br>

<!-- END unblockUsersInGroup -->

<!-- addGroupAdmins -->

### Add Group Admins

This function will Add admins to the group by ID.

> - Args:
>	- members (str | list): One or More member IDs to add
>	- groupId (int | str): Group ID to add admins

```py
self.addGroupAdmins(<members>, <groupId>)
```

> [!NOTE]
Client must be the Owner of the group.
</br>

<!-- END addGroupAdmins -->

<!-- removeGroupAdmins -->

### Remove Group Admins

This function will Remove admins in the group by ID.

> - Args:
>	- members (str | list): One or More admin IDs to remove
>	- groupId (int | str): Group ID to remove admins

```py
self.removeGroupAdmins(<members>, <groupId>)
```

> [!NOTE]
Client must be the Owner of the group.
</br>

<!-- END removeGroupAdmins -->

<!-- pinGroupMsg -->

### Pin Group Message

This function will Pin message in group by ID.

> - Args:
>	- pinMsg (Message): Message Object to pin
>	- groupId (int | str): Group ID to pin message

```py
self.pinGroupMsg(<pinMsg>, <groupId>)
```
</br>
<!-- END pinGroupMsg -->

<!-- unpinGroupMsg -->

### Unpin Group Message

This function will Unpin message in group by ID.

> - Args:
>	- pinId (int | str): Pin ID to unpin
>	- pinTime (int): Pin start time
>	- groupId (int | str): Group ID to unpin message

```py
self.unpinGroupMsg(
	<pinId>, 
	<pinTime>, 
	<groupId>
)
```
</br>

<!-- END unpinGroupMsg -->

<!-- deleteGroupMsg -->

### Delete Group Message

This function will Delete message in group by ID.

> - Args:
>	- msgId (int | str): Message ID to delete
>	- ownerId (int | str): Owner ID of the message to delete
>	- clientMsgId (int | str): Client message ID to delete message
>	- groupId (int | str): Group ID to delete message

```py
self.deleteGroupMsg(
	<msgId>, 
	<onwerId>, 
	<clientMsgId>, 
	<groupId>
)
```
</br>

<!-- END deleteGroupMsg -->

<!-- viewGroupPending -->

### View Group Pending

This function will Give list of people pending approval in group by ID.

> - Args:
>	- groupId (int | str): Group ID to view pending members

```py
self.viewGroupPending(<groupId>)
```
</br>

<!-- END viewGroupPending -->

<!-- handleGroupPending -->

### Handle Group Pending

This function will Approve/Deny pending users to the group from the group's approval.

> - Args:
>	- members (str | list): One or More member IDs to handle
>	- groupId (int | str): ID of the group to handle pending members
>	- isApprove (bool): Approve/Reject pending members (True | False)

```py
self.handleGroupPending(<members>, <groupId>)
```
</br>

<!-- END handleGroupPending -->

<!-- viewPollDetail -->

### View Poll Detail

This function will Give poll data by ID.

> - Args:
>	- pollId (int | str): Poll ID to view detail

```py
self.viewPollDetail(<pollId>)
```
</br>

<!-- END viewPollDetail -->

<!-- createPoll -->

### Create Poll

This function will Create poll in group by ID.

> - Args:
>	- question (str): Question for poll
>	- options (str | list): List options for poll
>	- groupId (int | str): Group ID to create poll from
>	- expiredTime (int): Poll expiration time (0 = no expiration)
>	- pinAct (bool): Pin action (pin poll)
>	- multiChoices (bool): Allows multiple poll choices
>	- allowAddNewOption (bool): Allow members to add new options
>	- hideVotePreview (bool): Hide voting results when haven't voted
>	- isAnonymous (bool): Hide poll voters
			

```py
self.createPoll(
	<question>, 
	<options>, 
	<groupId>
)
```
</br>

<!-- END createPoll -->

<!-- lockPoll -->

### Lock Poll

This function will Lock/end poll by ID.

> - Args:
>	- pollId (int | str): Poll ID to lock

```py
self.lockPoll(<pollId>)
```
</br>

<!-- END lockPoll -->

<!-- disperseGroup -->

### Disperse Group

This function will Disperse group by ID.

> - Args:
>	- groupId (int | str): Group ID to disperse

```py
self.disperseGroup(<groupId>)
```
</br>

<!-- END disperseGroup -->

<!-- send/sendMessage -->

### Send Message

This function will Send message to a thread (user/group).

> - Args:
>	- message (str): Message send to
>	- thread_id (int | str): User/Group ID to send to
>	- thread_type (ThreadType): ``ThreadType.USER``, ``ThreadType.GROUP``
>	- mark_message (str): Send messages as `Urgent` or `Important` mark

```py
self.send(
	Message(
		text=<message>, 
		style=None, 
		memtions=None
	), 
	<thread_id>, 
	<thread_type>
)
```
</br>

<!-- END send/sendMessage -->

<!-- replyMessage -->

### Reply Message

This function will Reply message in thread (user/group).

> - Args:
>	- message (str): Message send to
>	- message_object (Message): ``Message Object`` to reply
>	- thread_id (int | str): User/Group ID to send to.
>	- thread_type (ThreadType): ``ThreadType.USER``, ``ThreadType.GROUP``

```py
self.replyMessage(
	Message(
		text=<message>, 
		style=None, 
		mentions=None
	), 
	<message_object>, 
	<thread_id>, 
	<thread_type>
)
```
</br>

<!-- END replyMessage -->

<!-- sendToDo -->

### Send To Do

This function will send the job to the users in the group.

> - Args:
>	- message_object (Mess