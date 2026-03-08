# -*- coding: UTF-8 -*-
from builtins import Exception, bool, int, isinstance, str
import random
from urllib import response
import websockets
import requests, json
import hashlib

from .models import *
from ._package import *
from . import _util, _state
from .logging import Logging
from websockets.sync.client import connect
from concurrent.futures import ThreadPoolExecutor

pool = ThreadPoolExecutor(max_workers=9999)

logger = Logging(theme="catppuccin-mocha", log_text_color="black")


class ZaloAPI(object):
	def __init__(
		self,
		phone,
		password,
		imei,
		session_cookies=None,
		user_agent=None,
		auto_login=True,
	):
		"""Initialize and log in the client.

		Args:
			imei (str): The device imei is logged into Zalo
			phone (str): Zalo account phone number
			password (str): Zalo account password
			auto_login (bool): Automatically log in when initializing ZaloAPI (Default: True)
			user_agent (str): Custom user agent to use when sending requests. If `None`, user agent will be chosen from a premade list
			session_cookies (dict): Cookies from a previous session (Required if logging in with cookies)

		Raises:
			ZaloLoginError: On failed login
			LoginMethodNotSupport: If method login not support
		"""
		self._state = _state.State()
		self._condition = threading.Event()
		self._listening = False
		self._start_fix = False

		if auto_login:
			if (
				not session_cookies
				or not self.setSession(session_cookies)
				or not self.isLoggedIn()
			):
				self.login(phone, password, imei, user_agent)

	def uid(self):
		"""The ID of the client."""
		return self.uid

	"""
	INTERNAL REQUEST METHODS
	"""

	def _get(self, *args, **kwargs):
		return self._state._get(*args, **kwargs)

	def _post(self, *args, **kwargs):
		return self._state._post(*args, **kwargs)

	"""
	END INTERNAL REQUEST METHODS
	"""

	"""
	EXTENSIONS METHODS
	"""

	def _encode(self, params):
		return _util.zalo_encode(params, self._state._config.get("secret_key"))

	def _decode(self, params):
		return _util.zalo_decode(params, self._state._config.get("secret_key"))

	"""
	END EXTENSIONS METHODS
	"""

	"""
	LOGIN METHODS
	"""

	def isLoggedIn(self):
		"""Get data from config to check the login status.

		Returns:
			bool: True if the client is still logged in
		"""
		return self._state.is_logged_in()

	def getSession(self):
		"""Retrieve session cookies.

		Returns:
			dict: A dictionary containing session cookies
		"""
		return self._state.get_cookies()

	def setSession(self, session_cookies):
		"""Load session cookies.

		Warning:
			Error sending requests if session cookie is wrong

		Args:
			session_cookies (dict): A dictionary containing session cookies

		Returns:
			Bool: False if ``session_cookies`` does not contain proper cookies
		"""
		try:
			if not isinstance(session_cookies, dict):
				return False
			# Load cookies into current session
			self._state.set_cookies(session_cookies)
			self.uid = self._state.user_id
		except Exception as e:
			print("Failed loading session")
			return False
		return True

	def getSecretKey(self):
		"""Retrieve secret key to encode/decode payload.

		Returns:
			str: A secret key string with base64 encode
		"""
		return self._state.get_secret_key()

	def setSecretKey(self, secret_key):
		"""Load secret key.

		Warning:
			Error (enc/de)code payload if secret key is wrong

		Args:
			secret_key (str): A secret key string with base64 encode

		Returns:
			bool: False if ``secret_key`` not correct to (en/de)code the payload
		"""
		try:
			self._state.set_secret_key(secret_key)

			return True
		except:
			return False

	def login(self, phone, password, imei, user_agent=None):
		"""Login the user, using ``phone`` and ``password``.

		If the user is already logged in, this will do a re-login.

		Args:
			imei (str): The device imei is logged into Zalo
			phone (str): Zalo account phone number
			password (str): Zalo account password
			user_agent (str): Custom user agent to use when sending requests. If `None`, user agent will be chosen from a premade list

		Raises:
			ZaloLoginError: On failed login
			LoginMethodNotSupport: If method login not support
		"""
		if not (phone and password):
			raise ZaloUserError("Phone and password not set")

		self.onLoggingIn()

		self._state.login(phone, password, imei, user_agent=user_agent)
		try:
			self._imei = self._state.user_imei
			self.uid = self.fetchAccountInfo().profile.get(
				"userId", self._state.user_id
			)
		except:
			self._imei = None
			self.uid = self._state.user_id

		self.onLoggedIn(self._state._config.get("phone_number"))

	"""
	END LOGIN METHODS
	"""

	"""
	ATTACHMENTS METHODS
	"""

	def _uploadImage(self, filePath, thread_id, thread_type):
		"""Upload images to Zalo.

		Args:
			filePath (str): Image path to upload
			thread_id (int | str): User/Group ID to upload to.
			thread_type (ThreadType): ThreadType.USER, ThreadType.GROUP

		Returns:
			dict: A dictionary containing the image info just uploaded
			dict: A dictionary containing error_code, response if failed

		Raises:
			ZaloAPIException: If request failed
		"""
		if not os.path.exists(filePath):
			raise ZaloUserError(f"{filePath} not found")

		files = [("chunkContent", open(filePath, "rb"))]
		fileSize = len(open(filePath, "rb").read())
		fileName = filePath if "/" not in filePath else filePath.rstrip("/")[1]

		params = {
			"params": {
				"totalChunk": 1,
				"fileName": fileName,
				"clientId": _util.now(),
				"totalSize": fileSize,
				"imei": self._imei,
				"isE2EE": 0,
				"jxl": 0,
				"chunkId": 1,
			},
			"zpw_ver": 645,
			"zpw_type": 30,
		}

		if thread_type == ThreadType.USER:
			url = "https://tt-files-wpa.chat.zalo.me/api/message/photo_original/upload"
			params["type"] = 2
			params["params"]["toid"] = str(thread_id)
		elif thread_type == ThreadType.GROUP:
			url = "https://tt-files-wpa.chat.zalo.me/api/group/photo_original/upload"
			params["type"] = 11
			params["params"]["grid"] = str(thread_id)
		else:
			raise ZaloUserError("Thread type is invalid")

		params["params"] = self._encode(params["params"])

		response = self._post(url, params=params, files=files)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(data["data"])
			results = results.get("data") if results.get("error_code") == 0 else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return results

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def _uploadAttachment(self, filePath, thread_id):
		"""Upload attachment (file, zip, pdf, etc.) to Zalo.

		Args:
			filePath (str): Đường dẫn file cần upload
			thread_id (int | str): ID người nhận (USER hoặc GROUP)

		Returns:
			dict: Thông tin file sau khi upload thành công
		Raises:
			ZaloAPIException nếu lỗi
		"""
		if not os.path.exists(filePath):
			raise ZaloUserError(f"{filePath} not found")

		# Chuẩn bị dữ liệu file
		with open(filePath, "rb") as f:
			file_content = f.read()

		fileSize = len(file_content)
		files = [("chunkContent", open(filePath, "rb"))]

		# Tách tên file
		fileName = os.path.basename(filePath)

		# Params upload
		params = {
			"params": {
				"totalChunk": 1,
				"fileName": fileName,
				"clientId": _util.now(),
				"totalSize": fileSize,
				"imei": self._imei,
				"chunkId": 1,
				"toid": str(thread_id)
			},
			"zpw_ver": 669,
			"zpw_type": 30,
			"type": 2
		}

		# Mã hóa params (E2EE encode)
		params["params"] = self._encode(params["params"])

		url = "https://tt-files-wpa.chat.zalo.me/api/message/asyncfile/upload"

		# Gửi request
		response = self._post(url, params=params, files=files)
		data = response.json()

		# Xử lý kết quả
		if data.get("error_code") == 0:
			decoded = self._decode(data["data"])
			results = decoded.get("data") if isinstance(decoded, dict) else decoded
			if not results:
				results = {"error_code": 1337, "error_message": "Data is None"}
			return results

		# Nếu lỗi
		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when uploading attachment: {error_message}"
		)
		
	"""
	END ATTACHMENTS METHODS
	"""

	"""
	FETCH METHODS
	"""

	def fetchUserLink(self, userId):
		"""Retrieve the QR code link for a user.

		Args:
			userId (int | str): ID of the user to retrieve the QR code for

		Returns:
			dict: Dictionary containing the QR code URL of the user
			dict: Dictionary containing error_code and response if failed

		Raises:
			ZaloAPIException: If the request fails
		"""
		params = {"zpw_ver": 641, "zpw_type": 30}

		payload = {"params": self._encode({"fids": [str(userId)]})}

		response = self._post(
			"https://tt-friend-wpa.chat.zalo.me/api/friend/mget-qr",
			params=params,
			data=payload,
		)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}
			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}
			return results
		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def fetchAccountInfo(self):
		"""fetch account information of the client

		Returns:
			object: `User` client info
			dict: A dictionary containing error_code, response if failed

		Raises:
			ZaloAPIException: If request failed
		"""
		params = {
			"params": self._encode({"avatar_size": 120, "imei": self._imei}),
			"zpw_ver": 645,
			"zpw_type": 30,
			"os": 8,
			"browser": 0,
		}

		response = self._get(
			"https://tt-profile-wpa.chat.zalo.me/api/social/profile/me-v2",
			params=params,
		)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("error_code") == 0 else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return User.fromDict(results, None)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def fetchPhoneNumber(self, phoneNumber, language="vi"):
		"""Fetch user info by Phone Number.

		Not available with hidden phone numbers

		Args:
			phoneNumber (int | str): Phone number to fetch information
			language (str): Language for response (not sure | Default: vi)

		Returns:
			object: `User` user(s) info
			dict: A dictionary containing error_code, response if failed

		Raises:
			ZaloAPIException: If request failed
		"""

		phone = (
			"84" + str(phoneNumber)
			if str(phoneNumber)[:1] != "0"
			else "84" + str(phoneNumber)[1:]
		)

		params = {
			"zpw_ver": 645,
			"zpw_type": 30,
			"params": self._encode(
				{
					"phone": phone,
					"avatar_size": 240,
					"language": language,
					"imei": self._imei,
					"reqSrc": 85,
				}
			),
		}

		response = self._get(
			"https://tt-friend-wpa.chat.zalo.me/api/friend/profile/get", params=params
		)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return User.fromDict(results, None)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def fetchUserInfo(self, userId):
		"""Fetch user info by ID.

		Args:
			userId (int | str | list): User(s) ID to get info

		Returns:
			object: `User` user(s) info
			dict: A dictionary containing error_code, response if failed

		Raises:
			ZaloAPIException: If request failed
		"""
		params = {"zpw_ver": 645, "zpw_type": 30}

		payload = {
			"params": {
				"phonebook_version": int(_util.now() / 1000),
				"friend_pversion_map": [],
				"avatar_size": 120,
				"language": "vi",
				"show_online_status": 1,
				"imei": self._imei,
			}
		}

		if isinstance(userId, list):
			for i in range(len(userId)):
				userId[i] = str(userId[i]) + "_0"
			payload["params"]["friend_pversion_map"] = userId

		else:
			payload["params"]["friend_pversion_map"].append(str(userId) + "_0")

		payload["params"] = self._encode(payload["params"])

		response = self._post(
			"https://tt-profile-wpa.chat.zalo.me/api/social/friend/getprofiles/v2",
			params=params,
			data=payload,
		)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("error_code") == 0 else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return User.fromDict(results, None)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def fetchGroupInfo(self, groupId):
		"""Fetch group info by ID.

		Args:
			groupId (int | str | dict): Group(s) ID to get info

		Returns:
			object: `Group` group info
			dict: A dictionary containing error_code, response if failed

		Raises:
			ZaloAPIException: If request failed
		"""

		params = {"zpw_ver": 645, "zpw_type": 30}

		payload = {"params": {"gridVerMap": {}}}

		if isinstance(groupId, dict):
			for i in groupId:
				payload["params"]["gridVerMap"][str(i)] = 0
		else:
			payload["params"]["gridVerMap"][str(groupId)] = 0

		payload["params"]["gridVerMap"] = json.dumps(payload["params"]["gridVerMap"])
		payload["params"] = self._encode(payload["params"])

		response = self._post(
			"https://tt-group-wpa.chat.zalo.me/api/group/getmg-v2",
			params=params,
			data=payload,
		)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("error_code") == 0 else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return Group.fromDict(results, None)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def fetchAllFriends(self):
		"""Fetch all users the client is currently chatting with (only friends).

		Returns:
			object: `User` all friend IDs
			any: If response is not list friends

		Raises:
			ZaloAPIException: If request failed
		"""

		params = {
			"params": self._encode(
				{
					"incInvalid": 0,
					"page": 1,
					"count": 20000,
					"avatar_size": 120,
					"actiontime": 0,
				}
			),
			"zpw_ver": 645,
			"zpw_type": 30,
			"nretry": 0,
		}

		response = self._get(
			"https://profile-wpa.chat.zalo.me/api/social/friend/getfriends",
			params=params,
		)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			datas = []
			if results.get("data"):
				for data in results.get("data"):
					datas.append(User(**data))

			return datas

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def fetchAllGroups(self):
		"""Fetch all group IDs are joining and chatting.

		Returns:
			object: `Group` all group IDs
			any: If response is not all group IDs

		Raises:
			ZaloAPIException: If request failed
		"""

		params = {"zpw_ver": 645, "zpw_type": 30}

		response = self._get(
			"https://tt-group-wpa.chat.zalo.me/api/group/getlg/v4", params=params
		)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("error_code") == 0 else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return Group.fromDict(results, None)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	"""
	END FETCH METHODS
	"""

	"""
	GET METHODS
	"""

	def getLastMsgs(self):
		"""Get last message the client's friends/group chat room.

		Returns:
			object: `User` last msg data
			dict: A dictionary containing error_code, response if failed

		Raises:
			ZaloAPIException: If request failed
		"""
		params = {
			"zpw_ver": "645",
			"zpw_type": "30",
			"params": self._encode(
				{"threadIdLocalMsgId": json.dumps({}), "imei": self._imei}
			),
		}

		response = self._get(
			"https://tt-convers-wpa.chat.zalo.me/api/preloadconvers/get-last-msgs",
			params=params,
		)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("error_code") == 0 else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return User.fromDict(results, None)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def getRecentGroup(self, groupId):
		"""Get recent messages in group by ID.

		Args:
			groupId (int | str): Group ID to get recent msgs

		Returns:
			object: `Group` List msg data in groupMsgs
			dict: A dictionary containing error_code, response if failed

		Raises:
			ZaloAPIException: If request failed
		"""
		params = {
			"params": self._encode(
				{
					"groupId": str(groupId),
					"globalMsgId": 10000000000000000,
					"count": 50,
					"msgIds": [],
					"imei": self._imei,
					"src": 1,
				}
			),
			"zpw_ver": 645,
			"zpw_type": 30,
			"nretry": 0,
		}

		response = self._get(
			"https://tt-group-cm.chat.zalo.me/api/cm/getrecentv2", params=params
		)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = (
				json.loads(results.get("data"))
				if results.get("error_code") == 0
				else results
			)
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return Group.fromDict(results, None)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def _getGroupBoardList(self, board_type, page, count, last_id, last_type, groupId):
		params = {
			"params": self._encode(
				{
					"group_id": str(groupId),
					"board_type": board_type,
					"page": page,
					"count": count,
					"last_id": last_id,
					"last_type": last_type,
					"imei": self._imei,
				}
			),
			"zpw_ver": 645,
			"zpw_type": 30,
		}

		response = self._get(
			"https://groupboard-wpa.chat.zalo.me/api/board/list", params=params
		)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = Group.fromDict(results.get("data"), None)

			return results

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def getGroupBoardList(self, groupId, page=1, count=20, last_id=0, last_type=0):
		"""Get group board list (pinmsg, note, poll) by ID.

		Args:
			groupId (int | str): Group ID to get board list
			page (int): Number of pages to retrieve data from
			count (int): Amount of data to retrieve per page (5 poll, ..)
			last_id (int): Default (no description)
			last_type (int): Default (no description)

		Returns:
			object: `Group` board data in group
			dict: A dictionary containing error_code, response if failed

		Raises:
			ZaloAPIException: If request failed
		"""
		response = self._getGroupBoardList(
			board_type=0,
			page=page,
			count=count,
			last_id=last_id,
			last_type=last_type,
			groupId=groupId,
		)

		return response

	def sendReminder(
		self,
		thread_id,
		thread_type,
		title,
		emoji="⏰",
		color=-16245706,
		start_time=None,
		duration=-1,
		pin_act=0,
		repeat=1,
		src=1,
	):
		"""
		Create a group board in a user or group chat.

		Args:
			thread_id (int | str): User or Group ID of the conversation.
			thread_type (ThreadType): ThreadType.USER or ThreadType.GROUP.
			title (str): Title of the board.
			emoji (str): Emoji (default: "⏰").
			color (int): Board color.
			start_time (int): Timestamp ms (default: now).
			duration (int): Duration ms, -1 indefinite.
			pin_act (int): Pin action (0 unpinned).
			repeat (int): Repeat count (default 1).
			src (int): Source identifier.

		Returns:
			dict: Decoded response data if successful.

		Raises:
			ZaloAPIException | ZaloUserError
		"""
		if thread_type not in (ThreadType.USER, ThreadType.GROUP):
			raise ZaloUserError("thread_type must be USER or GROUP")

		if not (thread_id and title):
			raise ZaloUserError("thread_id and title must be provided")

		if not getattr(self, "uid", None):
			raise ZaloUserError("creatorUid missing, ensure login success")

		if not self._imei:
			raise ZaloUserError("imei missing, ensure login success")

		# chọn endpoint
		endpoint = (
			"https://groupboard-wpa.chat.zalo.me/api/board/oneone/create"
			if thread_type == ThreadType.USER
			else "https://groupboard-wpa.chat.zalo.me/api/board/topic/createv2"
		)
		params = {"zpw_ver": 665, "zpw_type": 30}

		# thời gian mặc định
		start_time = int(time.time() * 1000) if start_time is None else start_time

		if thread_type == ThreadType.USER:
			# oneone/create: objectData (stringify)
			object_data = {
				"toUid": str(thread_id),
				"type": 0,
				"color": color,
				"emoji": emoji,
				"startTime": start_time,
				"duration": duration,
				"params": {"title": title},
				"needPin": False,
				"repeat": repeat,
				"creatorUid": str(self.uid),
				"src": src,
			}
			payload = {
				"params": {
					"objectData": json.dumps(object_data, ensure_ascii=False),
					"imei": self._imei,
				}
			}

		else:
			# topic/createv2: field rời, không objectData
			payload = {
				"params": {
					"grid": str(thread_id),
					"type": 0,
					"color": color,
					"emoji": emoji,
					"startTime": start_time,
					"duration": duration,
					"params": json.dumps({"title": title}, ensure_ascii=False),
					"repeat": repeat,
					"src": src,
					"imei": self._imei,
					"pinAct": pin_act,
				}
			}

		# encode params
		payload["params"] = self._encode(payload["params"])

		response = self._post(endpoint, params=params, data=payload)
		data = response.json()

		# lỗi param đặc biệt
		if data.get("error_code") == 114:
			raise ZaloAPIException(
				f"Error #114 invalid parameter. "
				f"Check thread_id {thread_id}, type, or payload={payload}"
			)

		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results is None:
				results = {"error_code": 1337, "error_message": "Data is None"}
			if isinstance(results, str):
				try:
					results = json.loads(results)
				except Exception:
					results = {"error_code": 1337, "error_message": results}
			return results

		raise ZaloAPIException(
			f"Error #{data.get('error_code')} creating group board: "
			f"{data.get('error_message') or data.get('data')}"
		)

	def sendNote(
		self,
		thread_id: str,
		title: str,
		color: int = -16777216,
		emoji: str = "",
		pin_act: int = 0,
		src: int = 1,
	) -> dict:
		"""
		Send a note (board topic) in a group.

		Args:
			thread_id (str): Group ID.
			title (str): Title of the note.
			color (int, optional): Note color (default: -16777216).
			emoji (str, optional): Emoji for the note (default: empty).
			pin_act (int, optional): Pin action flag (default: 0).
			src (int, optional): Source identifier (default: 1).

		Returns:
			dict: Response data if successful.

		Raises:
			ZaloAPIException: If the request fails.
		"""
		if not (thread_id and title):
			raise ZaloUserError("thread_id and title must be provided")

		url = "https://groupboard-wpa.chat.zalo.me/api/board/topic/createv2"
		params = {"zpw_ver": 665, "zpw_type": 30}

		payload = {
			"grid": str(thread_id),
			"type": 0,
			"color": color,
			"emoji": emoji,
			"startTime": -1,
			"duration": -1,
			"params": json.dumps({"title": title}, ensure_ascii=False),
			"repeat": 0,
			"src": src,
			"imei": self._imei,
			"pinAct": pin_act,
		}

		response = self._post(url, params=params, data=payload)

		try:
			data = response.json()
		except Exception:
			raise ZaloAPIException("Response is not valid JSON")

		if data.get("error_code") == 0:
			return data.get("data") or {"error_code": 0, "message": "Note sent successfully"}
		else:
			raise ZaloAPIException(
				f"Error #{data.get('error_code')} when sending group note: "
				f"{data.get('error_message') or data.get('data')}"
			)

	def setNotifications(self, group_id, mute: bool, thread_type):
		"""
		Enable or disable group notifications.

		Args:
			group_id (int | str): Group ID.
			mute (bool): True to mute, False to unmute.
			thread_type (ThreadType): GROUP or USER.

		Returns:
			dict: API response result.

		Raises:
			ZaloAPIException: If API returns error.
			ValueError: If mute is not True/False or thread_type invalid.
		"""
		if mute not in (True, False):
			raise ValueError("mute must be True or False")

		if thread_type == ThreadType.GROUP:
			mute_type = 2
		elif thread_type == ThreadType.USER:
			mute_type = 1
		else:
			raise ValueError("thread_type must be GROUP or USER")

		payload = {
			"toid": str(group_id),
			"duration": -1,
			"action": 1 if mute else 3,
			"startTime": int(time.time()),
			"muteType": mute_type,
			"imei": self._imei,
		}

		params = {"zpw_ver": 665, "zpw_type": 30, "params": self._encode(payload)}

		response = self._get(
			"https://tt-profile-wpa.chat.zalo.me/api/social/profile/setmute",
			params=params,
		)

		try:
			data = response.json()
		except Exception:
			raise ZaloAPIException("Invalid JSON response from API")

		if data.get("error_code") == 0:
			results = data.get("data")
			if results:
				results = self._decode(results)
				if isinstance(results, str):
					try:
						results = json.loads(results)
					except Exception:
						results = {"error_code": 1337, "error_message": results}
			else:
				results = {"error_code": 1337, "error_message": "Data is None"}
			return results
		else:
			error_code = data.get("error_code")
			error_message = data.get("error_message") or data.get("data")
			raise ZaloAPIException(
				f"Error #{error_code} when setting group notification: {error_message}"
			)

	"""
	END GET METHODS
	"""

	"""
	ACCOUNT ACTION METHODS
	"""

	def resetHiddenPin(self) -> dict:
		"""
		Reset hidden chat PIN (remove PIN protection).

		Returns:
			dict: Response data if successful.
		"""
		url = "https://tt-convers-wpa.chat.zalo.me/api/hiddenconvers/reset"
		params = {"zpw_ver": 665, "zpw_type": 30}

		response = self._post(url, params=params, data={})

		try:
			data = response.json()
		except Exception:
			raise ZaloAPIException("Response is not valid JSON")

		if data.get("error_code") == 0:
			return {"error_code": 0, "message": "Hidden PIN reset successfully"}
		else:
			raise ZaloAPIException(
				f"Error #{data.get('error_code')} when resetting hidden PIN: "
				f"{data.get('error_message') or data.get('data')}"
			)

	def updateHiddenPin(self, new_pin: int) -> dict:
		"""
		Update (set) hidden chat PIN.

		Args:
			new_pin (int): New PIN in plain text (will be MD5 hashed).

		Returns:
			dict: Response data if successful.
		"""
		if not isinstance(new_pin, int):
			raise ZaloUserError("PIN must be numeric")

		url = "https://tt-convers-wpa.chat.zalo.me/api/hiddenconvers/update-pin"
		params = {"zpw_ver": 665, "zpw_type": 30}

		# Hash MD5 PIN
		md5_pin = hashlib.md5(str(new_pin).encode()).hexdigest()

		payload = {
			"new_pin": md5_pin,
			"imei": self._imei,
		}

		payload["params"] = self._encode(payload)

		response = self._post(url, params=params, data=payload)

		try:
			data = response.json()
		except Exception:
			raise ZaloAPIException("Response is not valid JSON")

		if data.get("error_code") == 0:
			return {"error_code": 0, "message": "Hidden PIN updated successfully"}
		else:
			raise ZaloAPIException(
				f"Error #{data.get('error_code')} when updating hidden PIN: "
				f"{data.get('error_message') or data.get('data')}"
			)

	def hideConversation(self, thread_id, thread_type, hide=True):
		"""Hide or unhide a conversation (user or group).

		Args:
			thread_id (int | str): User or Group ID of the conversation to hide/unhide.
			thread_type (ThreadType): ThreadType.USER or ThreadType.GROUP.
			hide (bool): True to hide the conversation, False to unhide it. Defaults to True.

		Returns:
			dict: Decoded response data if successful.

		Raises:
			ZaloAPIException: If the request fails or response is invalid.
			ZaloUserError: If thread_type is invalid.
		"""
		if thread_type not in (ThreadType.USER, ThreadType.GROUP):
			raise ZaloUserError("Thread type is invalid")

		params = {"zpw_ver": 665, "zpw_type": 30}

		payload = {
			"params": {
				"del_threads": json.dumps([]),
				"add_threads": (
					json.dumps(
						[
							{
								"thread_id": str(thread_id),
								"is_group": 1 if thread_type == ThreadType.GROUP else 0,
							}
						]
					)
					if hide
					else json.dumps([])
				),
				"imei": self._imei,
			}
		}

		payload["params"] = self._encode(payload["params"])

		response = self._post(
			"https://tt-convers-wpa.chat.zalo.me/api/hiddenconvers/add-remove",
			params=params,
			data=payload,
		)

		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results is None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return results

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when hiding conversation: {error_message}"
		)

	def getHiddenConversations(self) -> dict:
		"""
		Get all hidden conversations.

		Returns:
			dict: List of hidden conversations if successful.

		Raises:
			ZaloAPIException: If the request fails.
		"""
		url = "https://tt-convers-wpa.chat.zalo.me/api/hiddenconvers/get-all"
		params = {"zpw_ver": 665, "zpw_type": 30}

		payload = {
			"imei": self._imei,
		}

		payload["params"] = self._encode(payload)

		response = self._post(url, params=params, data=payload)

		try:
			data = response.json()
		except Exception:
			raise ZaloAPIException("Response is not valid JSON")

		if data.get("error_code") == 0:
			results = data.get("data")
			if results:
				results = self._decode(results)
				if isinstance(results, str):
					try:
						results = json.loads(results)
					except Exception:
						results = {"error_code": 1337, "error_message": results}
				return results or {"hidden_list": []}
			return {"hidden_list": []}
		else:
			raise ZaloAPIException(
				f"Error #{data.get('error_code')} when fetching hidden conversations: "
				f"{data.get('error_message') or data.get('data')}"
			)

	def removeHiddenConversation(self, thread_id, thread_type):
		"""
		Remove a conversation from hidden list (unhide) for user or group.

		Args:
			thread_id (str): The thread ID to unhide.
			is_group (bool): True if it's a group, False if it's a user.

		Returns:
			dict: API response.
		"""
		url = "https://tt-convers-wpa.chat.zalo.me/api/hiddenconvers/add-remove"
		params = {"zpw_ver": 665, "zpw_type": 30}

		payload = {
			"del_threads": json.dumps([{"thread_id": thread_id, "is_group": thread_type}]),
			"add_threads": "[]",
			"imei": self._imei,
		}
		if thread_type == ThreadType.USER:
			payload["add_threads"] = json.dumps([{"thread_id": thread_id, "is_group": 0}])
		else:
			payload["add_threads"] = json.dumps([{"thread_id": thread_id, "is_group": 1}])

		result = self._post(url, params, payload)
		if result.get("error_code") == 0:
			return {"message": f"{'Group' if thread_type else 'User'} conversation removed from hidden successfully"}
		raise Exception(f"Remove hidden conversation failed: {result}")

	def deleteConversation(
		self, thread_id, client_id, msg_id, thread_type, only_me=True
	):
		"""Delete a conversation for the client.

		Args:
			thread_id (int | str): User or Group ID of the conversation to delete.
			client_id (int | str): Client message ID of the conversation.
			global_id (int | str): Global message ID of the conversation.
			thread_type (ThreadType): ThreadType.USER or ThreadType.GROUP.
			only_me (bool): If True, delete the conversation only for the client.

		Returns:
			dict: Decoded response data if successful.

		Raises:
			ZaloAPIException: If the request fails or response is invalid.
			ZaloUserError: If thread_type is invalid or required parameters are missing.
		"""
		if thread_type not in (ThreadType.USER, ThreadType.GROUP):
			raise ZaloUserError("Thread type is invalid")

		if not (thread_id and client_id):
			raise ZaloUserError("thread_id and client_id must be provided")

		params = {"zpw_ver": 665, "zpw_type": 30, "nretry": 0}

		payload = {
			"conver": {
				"ownerId": str(thread_id),
				"cliMsgId": str(client_id),
				"globalMsgId": str(msg_id),
			},
			"cliMsgId": str(client_id),
			"onlyMe": 1 if only_me else 0,
			"imei": self._imei,
		}

		if thread_type == ThreadType.GROUP:
			payload["grid"] = str(thread_id)
			api_url = "https://tt-group-wpa.chat.zalo.me/api/group/deleteconver"
		else:
			payload["toid"] = str(thread_id)
			api_url = "https://tt-chat4-wpa.chat.zalo.me/api/message/deleteconver"

		payload["params"] = self._encode(payload)

		response = self._post(api_url, params=params, data=payload)

		try:
			data = response.json()
		except Exception:
			raise ZaloAPIException("Response is not valid JSON")

		if data.get("error_code") == 0:
			results = data.get("data")
			if results:
				results = self._decode(results)
				if isinstance(results, str):
					try:
						results = json.loads(results)
					except Exception:
						results = {"error_code": 1337, "error_message": results}
				return results or {"error_code": 0, "message": "Deleted successfully"}
			return {"error_code": 0, "message": "Deleted successfully"}

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when deleting conversation: {error_message}"
		)

	def changeProfile(
		self,
		name: str,
		dob: str,
		gender: int | str,
		language: str = "vi",
	):
		"""Change account profile information only (name, dob, gender, language).
		
		Args:
			name (str): The new account name.
			dob (str): Date of birth in format YYYY-MM-DD.
			gender (int | str): Gender (0 = Male, 1 = Female).
			language (str, optional): Account language ("vi" or "en").
		
		Returns:
			dict: User info if update successful.
		
		Raises:
			ZaloAPIException: If request failed.
		"""
		params = {"zpw_ver": 665, "zpw_type": 30}
		payload = {
			"params": self.api_client._encode(
				{
					"profile": json.dumps(
						{"name": name, "dob": dob, "gender": int(gender)}
					),
					"biz": json.dumps({}),  # Empty biz to avoid changes
					"language": language,
				}
			)
		}
		
		response = self.api_client._post(
			"https://tt-profile-wpa.chat.zalo.me/api/social/profile/update",
			params=params,
			data=payload,
		)
		
		data = response.json()
		if data.get("error_code") == 0:
			results = self.api_client._decode(data.get("data"))
			if isinstance(results, str):
				try:
					results = json.loads(results)
				except Exception:
					results = {"error_code": 1337, "error_message": results}
			return results
		
		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when updating profile: {error_message}"
		)

	def updateBusiness(
		self,
		desc: str = "",
		cate: int = 0,
		addr: str = "",
		website: str = "",
		email: str = "",
		language: str = "vi",
	):
		"""Change business/game information only.
		
		Args:
			desc (str, optional): Business description. Default is empty string.
			cate (int, optional): Business category. Default is 0.
			addr (str, optional): Business address. Default is empty string.
			website (str, optional): Business website. Default is empty string.
			email (str, optional): Business email. Default is empty string.
			language (str, optional): Account language ("vi" or "en").
		
		Returns:
			dict: User info if update successful.
		
		Raises:
			ZaloAPIException: If request failed.
		"""
		params = {"zpw_ver": 665, "zpw_type": 30}
		
		biz_data = {
			"desc": desc,
			"cate": cate,
			"addr": addr,
			"website": website,
			"email": email
		}
		
		payload = {
			"params": self.api_client._encode(
				{
					"profile": json.dumps({}),  # Empty profile to avoid changes
					"biz": json.dumps(biz_data),
					"language": language,
				}
			)
		}
		
		response = self.api_client._post(
			"https://tt-profile-wpa.chat.zalo.me/api/social/profile/update",
			params=params,
			data=payload,
		)
		
		data = response.json()
		if data.get("error_code") == 0:
			results = self.api_client._decode(data.get("data"))
			if isinstance(results, str):
				try:
					results = json.loads(results)
				except Exception:
					results = {"error_code": 1337, "error_message": results}
			return results
		
		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when updating business info: {error_message}"
		)

	def updateLanguage(self, language: str = "VI") -> dict:
		"""
		Update profile language.
		Options: "VI" (Vietnamese), "EN" (English).
		"""
		if language not in ["VI", "EN"]:
			raise ValueError("Language must be either 'VI' or 'EN'.")

		url = "https://tt-profile-wpa.chat.zalo.me/api/social/profile/updatelang"
		params = {"zpw_ver": 665, "zpw_type": 30}
		payload = {"language": language}

		result = self._post(url, params, payload)
		if result.get("error_code") == 0:
			return result.get("data")
		raise Exception(f"Update language failed: {result}")

	def changeAccountAvatar(
		self, filePath, width=500, height=500, language="vn", size=None
	):
		"""Upload/Change account avatar.

		Args:
			filePath (str): A path to the image to upload/change avatar
			size (int): Avatar image size (default = auto)
			width (int): Width of avatar image
			height (int): height of avatar image
			language (int | str): Zalo Website language ? (idk)

		Returns:
			object: `User` Account avatar change status
			None: If requet success/failed depending on the case
			dict: A dictionary containing error responses

		Raises:
			ZaloAPIException: If request failed
		"""
		if not os.path.exists(filePath):
			raise ZaloUserError(f"{filePath} not found")

		size = os.stat(filePath).st_size if not size else size
		files = [("fileContent", open(filePath, "rb"))]

		params = {
			"zpw_ver": 645,
			"zpw_type": 30,
			"params": self._encode(
				{
					"avatarSize": 120,
					"clientId": str(self.uid) + _util.formatTime("%H:%M %d/%m/%Y"),
					"language": language,
					"metaData": json.dumps(
						{
							"origin": {"width": width, "height": height},
							"processed": {
								"width": width,
								"height": height,
								"size": size,
							},
						}
					),
				}
			),
		}

		response = self._post(
			"https://tt-files-wpa.chat.zalo.me/api/profile/upavatar",
			params=params,
			files=files,
		)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return User.fromDict(results, None)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def checkMutualGroups(self, profile_id: str) -> dict:
		"""
		Get extra profile info (e.g., mutual groups).

		Args:
			profile_id (str): The target user's profile ID.

		Returns:
			dict: API response with extra profile information.
		"""
		url = "https://tt-profile-wpa.chat.zalo.me/api/social/profile/extra"
		
		params = {
			"zpw_ver": 665, 
			"zpw_type": 30
		}

		payload = {
			"profile_id": profile_id,
			"imei": self._imei,
		}

		result = self._post(url, params, payload)
		if result.get("error_code") == 0:
			return result
		raise Exception(f"Get profile extra failed: {result}")

	def checkMutualGroups(self, profile_id: str) -> dict:
		"""
		Get extra profile info (e.g., mutual groups).

		Args:
			profile_id (str): The target user's profile ID.

		Returns:
			dict: API response with extra profile information.
		"""
		url = "https://tt-profile-wpa.chat.zalo.me/api/social/profile/extra"
		
		params = {
			"zpw_ver": 665, 
			"zpw_type": 30
		}

		payload = {
			"profile_id": profile_id,
			"imei": self._imei,
		}

		result = self._post(url, params, payload)
		if result.get("error_code") == 0:
			return result
		raise Exception(f"Get profile extra failed: {result}")


	def setQuickMessageStatus(self, status: int) -> dict:
		"""
		Enable or disable quick message feature.

		Args:
			status (int): 0 = disable, 1 = enable

		Returns:
			dict: API response.
		"""
		if status not in (0, 1):
			raise ValueError("status must be 0 (disable) or 1 (enable)")

		url = "https://tt-profile-wpa.chat.zalo.me/api/social/profile/updatelang"
		
		params = {
			"zpw_ver": 665, 
			"zpw_type": 30
		}

		payload = {"quickMessageStatus": status, "imei": self._imei}

		result = self._post(url, params, payload)
		if result.get("error_code") == 0:
			state = "enabled" if status == 1 else "disabled"
			return {"message": f"Quick message has been {state} successfully"}
		raise Exception(f"Set quick message status failed: {result}")

	def setOnlineStatus(self, status: int) -> dict:
		"""
		Set whether to show online status.

		Args:
			status (int): 0 = hide, 1 = show

		Returns:
			dict: API response
		"""
		if status not in (0, 1):
			raise ValueError("status must be 0 (hide) or 1 (show)")

		url = "https://tt-profile-wpa.chat.zalo.me/api/social/profile/update"
		
		params = {
			"zpw_ver": 665, 
			"zpw_type": 30
		}
		
		payload = {"show_online_status": status, "imei": self._imei}

		result = self._post(url, params, payload)
		if result.json().get("error_code") == 0:
			state = "shown" if status == 1 else "hidden"
			return {"message": f"Online status {state} successfully"}
		raise Exception(f"Set online status failed: {result}")

	def setConversationStatus(self, status: int) -> dict:
		"""
		Enable or disable archived chat feature.

		Args:
			status (int): 0 = disable, 1 = enable

		Returns:
			dict: API response
		"""
		if status not in (0, 1):
			raise ValueError("status must be 0 (disable) or 1 (enable)")

		url = "https://tt-profile-wpa.chat.zalo.me/api/social/profile/update"
		
		params = {
			"zpw_ver": 665, 
			"zpw_type": 30
		}
		
		payload = {"archivedChatStatus": status, "imei": self._imei}

		result = self._post(url, params, payload)
		if result.get("error_code") == 0:
			state = "enabled" if status == 1 else "disabled"
			return {"message": f"Archived chat {state} successfully"}
		raise Exception(f"Set archived chat status failed: {result}")


	"""
	END ACCOUNT ACTION METHODS
	"""

	"""
	USER ACTION METHODS
	"""

	def updateArchivedChat(self, thread_id, thread_type, action_type="other"):
		"""Update the archived status of a conversation (move to Other or Priority).

		Args:
			thread_id (int | str): User or Group ID of the conversation.
			thread_type (ThreadType): ThreadType.USER or ThreadType.GROUP.
			action_type (str): 'other' to move to Other (archive), 'priority' to prioritize (Default: 'other').

		Returns:
			dict: Decoded response data if successful.

		Raises:
			ZaloAPIException: If the request fails or response is invalid.
			ZaloUserError: If thread_type or action_type is invalid, or thread_id is missing.
		"""
		if thread_type not in (ThreadType.USER, ThreadType.GROUP):
			raise ZaloUserError("Thread type is invalid")

		if action_type.lower() not in ("other", "priority"):
			raise ZaloUserError("action_type must be 'other' or 'priority'")

		if not thread_id:
			raise ZaloUserError("thread_id must be provided")

		params = {"zpw_ver": 665, "zpw_type": 30}

		action_type_map = {"other": 0, "priority": 1}

		# Use current timestamp in milliseconds for version
		version = int(time.time() * 1000)

		payload = {
			"params": {
				"ids": [
					{
						"id": str(thread_id),
						"type": 1 if thread_type == ThreadType.GROUP else 0,
					}
				],
				"version": version,
				"actionType": action_type_map[action_type.lower()],
				"imei": self._imei,
			}
		}

		payload["params"] = self._encode(payload["params"])

		response = self._post(
			"https://label-wpa.chat.zalo.me/api/archivedchat/update",
			params=params,
			data=payload,
		)

		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results is None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return results

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when updating archived chat: {error_message}"
		)

	def sendFriendRequest(self, userId, msg, language="vi"):
		"""Send friend request to a user by ID.

		Args:
			userId (int | str): User ID to send friend request
			msg (str): Friend request message
			language (str): Response language or Zalo interface language

		Returns:
			object: `User` Friend requet response
			dict: A dictionary containing error responses

		Raises:
			ZaloAPIException: If request failed
		"""
		params = {"zpw_ver": 645, "zpw_type": 30}

		payload = {
			"params": self._encode(
				{
					"toid": str(userId),
					"msg": msg,
					"reqsrc": 30,
					"imei": self._imei,
					"language": language,
					"srcParams": json.dumps({"uidTo": str(userId)}),
				}
			)
		}

		response = self._post(
			"https://tt-friend-wpa.chat.zalo.me/api/friend/sendreq",
			params=params,
			data=payload,
		)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return User.fromDict(results, None)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def acceptFriendRequest(self, userId, language="vi"):
		"""Accept friend request from user by ID.

		Args:
			userId (int | str): User ID to accept friend request
			language (str): Response language or Zalo interface language

		Returns:
			object: `User` Friend accept requet response
			dict: A dictionary containing error responses

		Raises:
			ZaloAPIException: If request failed
		"""
		params = {"zpw_ver": 645, "zpw_type": 30}

		payload = {"params": self._encode({"fid": str(userId), "language": language})}

		response = self._post(
			"https://tt-friend-wpa.chat.zalo.me/api/friend/accept",
			params=params,
			data=payload,
		)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return User.fromDict(results, None)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def unfriendUser(self, userId, language="vi"):
		"""Unfriend a user by ID.

		Args:
			userId (int | str): User ID to unfriend.
			language (str): Response language or Zalo interface language.

		Returns:
			dict: A dictionary containing the unfriend status information.

		Raises:
			ZaloAPIException: If request failed.
		"""
		params = {"zpw_ver": 641, "zpw_type": 30}

		payload = {"params": self._encode({"fid": str(userId), "language": language})}

		response = self._post(
			"https://tt-friend-wpa.chat.zalo.me/api/friend/remove",
			params=params,
			data=payload,
		)
		data = response.json()

		if data.get("error_code") == 0:
			return {"status": "success", "message": "Unfriended successfully."}
		else:
			error_code = data.get("error_code")
			error_message = data.get("error_message") or data.get("data")
			raise ZaloAPIException(
				f"Error #{error_code} when unfriending: {error_message}"
			)

	def blockViewFeed(self, userId, isBlockFeed):
		"""Block/Unblock friend view feed by ID.

		Args:
			userId (int | str): User ID to block/unblock view feed
			isBlockFeed (int): Block/Unblock friend view feed (1 = True | 0 = False)

		Returns:
			object: `User` Friend requet response
			dict: A dictionary containing error responses

		Raises:
			ZaloAPIException: If request failed
		"""
		params = {"zpw_ver": 645, "zpw_type": 30}

		payload = {
			"params": self._encode(
				{"fid": str(userId), "isBlockFeed": isBlockFeed, "imei": self._imei}
			)
		}

		response = self._post(
			"https://tt-friend-wpa.chat.zalo.me/api/friend/feed/block",
			params=params,
			data=payload,
		)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return User.fromDict(results, None)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def updateAlias(self, friend_id: str, alias: str) -> dict:
		"""Update alias (gợi nhớ) for a friend.

		Args:
			friend_id (str): Friend ID.
			alias (str): Alias name to set.

		Returns:
			dict: Response data if successful.

		Raises:
			ZaloAPIException: If the request fails.
		"""
		if not (friend_id and alias):
			raise ZaloUserError("friend_id and alias must be provided")

		params = {"zpw_ver": 665, "zpw_type": 30}
		payload = {
			"friendId": str(friend_id),
			"alias": str(alias),
			"imei": self._imei,
		}

		payload["params"] = self._encode(payload)

		response = self._post(
			"https://tt-alias-wpa.chat.zalo.me/api/alias/update",
			params=params,
			data=payload,
		)

		try:
			data = response.json()
		except Exception:
			raise ZaloAPIException("Response is not valid JSON")

		if data.get("error_code") == 0:
			return self._decode(data.get("data")) or {"error_code": 0, "message": "Alias updated"}
		else:
			raise ZaloAPIException(
				f"Error #{data.get('error_code')}: {data.get('error_message') or data.get('data')}"
			)

	def removeAlias(self, friend_id: str) -> dict:
		"""Remove alias (gợi nhớ) for a friend.

		Args:
			friend_id (str): Friend ID.

		Returns:
			dict: Response data if successful.

		Raises:
			ZaloAPIException: If the request fails.
		"""
		if not friend_id:
			raise ZaloUserError("friend_id must be provided")

		params = {"zpw_ver": 665, "zpw_type": 30}
		payload = {"friendId": str(friend_id)}

		payload["params"] = self._encode(payload)

		response = self._post(
			"https://tt-alias-wpa.chat.zalo.me/api/alias/remove",
			params=params,
			data=payload,
		)

		try:
			data = response.json()
		except Exception:
			raise ZaloAPIException("Response is not valid JSON")

		if data.get("error_code") == 0:
			return self._decode(data.get("data")) or {"error_code": 0, "message": "Alias removed"}
		else:
			raise ZaloAPIException(
				f"Error #{data.get('error_code')}: {data.get('error_message') or data.get('data')}"
			)

	def blockUser(self, userId):
		"""Block user by ID.

		Args:
			userId (int | str): User ID to block

		Returns:
			object: `User` Block response
			dict: A dictionary containing error responses

		Raises:
			ZaloAPIException: If request failed
		"""
		params = {"zpw_ver": 645, "zpw_type": 30}

		payload = {"params": self._encode({"fid": str(userId), "imei": self._imei})}

		response = self._post(
			"https://tt-friend-wpa.chat.zalo.me/api/friend/block",
			params=params,
			data=payload,
		)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return User.fromDict(results, None)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def unblockUser(self, userId):
		"""Unblock user by ID.

		Args:
			userId (int | str): User ID to unblock

		Returns:
			object: `User` Unblock response
			dict: A dictionary containing error responses

		Raises:
			ZaloAPIException: If request failed
		"""
		params = {"zpw_ver": 645, "zpw_type": 30}

		payload = {"params": self._encode({"fid": str(userId), "imei": self._imei})}

		response = self._post(
			"https://tt-friend-wpa.chat.zalo.me/api/friend/unblock",
			params=params,
			data=payload,
		)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return User.fromDict(results, None)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	"""
	END USER ACTION METHODS
	"""

	"""
	GROUP ACTION METHODS
	"""

	def disableLink(self, groupId):
		"""Disable the invite link for a group.

		Args:
			groupId (int | str): ID of the group to disable the invite link for

		Returns:
			dict: Dictionary containing success status and message if successful

		Raises:
			ZaloAPIException: If the request fails or server returns invalid response
		"""
		params_data = {"grid": groupId}

		params = {"zpw_ver": 650, "zpw_type": 30, "params": self._encode(params_data)}

		response = self._post(
			"https://tt-group-wpa.chat.zalo.me/api/group/link/disable", data=params
		)

		try:
			data = response.json()
		except json.json_decode_error:
			raise ZaloAPIException("Invalid JSON response from server.")
		if data.get("error_code") == 0:
			return {"success": True, "message": "Group link disabled successfully."}
		else:
			error_code = data.get("error_code")
			error_message = data.get("error_message", "Unknown error from self.")
			raise ZaloAPIException(
				f"Error #{error_code} when disabling group link: {error_message}"
			)

	def newLink(self, groupId):
		"""Create a new invite link for a group.

		Args:
			group_id (int | str): ID of the group to create a new invite link for

		Returns:
			dict: Dictionary containing success status and new link if successful
			dict: Dictionary containing error_code and error_message if failed

		Raises:
			ZaloAPIException: If the request fails or server returns invalid response
		"""
		params_data = {"grid": groupId}

		params = {"zpw_ver": 650, "zpw_type": 30, "params": self._encode(params_data)}

		response = self._post(
			"https://tt-group-wpa.chat.zalo.me/api/group/link/new", data=params
		)
		try:
			data = response.json()
		except json.json_decode_error:
			raise ZaloAPIException("Invalid JSON response from server.")
		if data.get("error_code") == 0:
			new_link_info = self._decode(data.get("data"))
			if new_link_info and new_link_info.get("link"):
				return {"success": True, "new_link": new_link_info.get("link")}
			else:
				raise ZaloAPIException("Error #1337: Link not found in response.")
		else:
			error_code = data.get("error_code")
			error_message = data.get("error_message", "Unknown error")
			raise ZaloAPIException(
				f"Error #{error_code} when sending requests: {error_message}"
			)

	def joinGroup(self, url):
		"""Join a group using an invite link.

		Args:
			url (str): The group invite link URL

		Returns:
			dict: Decoded group information if successful

		Raises:
			ZaloAPIException: If the request fails, response is invalid, or decoding fails
		"""
		response = self._post(
			"https://tt-group-wpa.chat.zalo.me/api/group/link/join",
			params={"zpw_ver": 648, "zpw_type": 30},
			data={"params": self._encode({"link": str(url), "clientLang": "vi"})},
		)
		if isinstance(response, requests.models.response):
			try:
				response_data = response.json()
			except ValueError:
				raise ValueError("Response does not contain valid JSON")
			if response_data.get("error_code") == 0:
				data = response_data.get("data")
				if data:
					try:
						return self._decode(data)
					except Exception as e:
						raise ValueError(f"Decoding error: {str(e)}")
				else:
					raise ValueError("Data is None")
			else:
				error_message = response_data.get("error_message", "Unknown error")
				error_code = response_data.get("error_code", 0)
				raise Exception(f"Error #{error_code}: {error_message}")
		else:
			raise TypeError(
				f"Unexpected response type: expected requests.models.Response, got {type(response)}"
			)

	def leaveGroup(self, groupId, silent=1, language="vi"):
		"""Leave a specified group.

		Args:
			group_id (int | str): ID of the group to leave
			silent (int, optional): Whether to leave silently (1 for silent, 0 for notification). Defaults to 1
			language (str, optional): Language for the request. Defaults to "vi"

		Returns:
			dict: Decoded response data if successful

		Raises:
			ZaloAPIException: If the request fails, response is invalid, or decoding fails
		"""
		payload = {
			"grids": [groupId],
			"imei": self._imei,
			"silent": silent,
			"language": language,
		}

		params = {"params": self._encode(payload), "zpw_ver": 647, "zpw_type": 30}

		response = self._get(
			"https://tt-group-wpa.chat.zalo.me/api/group/leave", params=params
		)
		data = response.json()
		if data.get("error_code") == 0:
			decoded_data = self._decode(data.get("data"))
			return decoded_data
		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error {error_code} when sending requests: {error_message}"
		)

	def createGroup(
		self, name=None, description=None, members=[], nameChanged=1, createLink=1
	):
		"""Create a new group.

		Args:
			name (str): The new group name
			description (str): Description of the new group
			members (str | list): List/String member IDs add to new group
			nameChanged (int - auto): Will use default name if disabled (0), else (1)
			createLink (int - default): Create a group link? Default = 1 (True)

		Returns:
			object: `Group` new group response
			dict: A dictionary containing error_code, response if failed

		Raises:
			ZaloAPIException: If request failed
		"""
		memberTypes = []
		nameChanged = 1 if name else 0
		name = name or "Default Group Name"

		if members and isinstance(members, list):
			members = [str(member) for member in members]
		else:
			members = [str(members)]

		if members:
			for i in members:
				memberTypes.append(-1)

		params = {
			"params": self._encode(
				{
					"clientId": _util.now(),
					"gname": name,
					"gdesc": description,
					"members": members,
					"memberTypes": memberTypes,
					"nameChanged": nameChanged,
					"createLink": createLink,
					"clientLang": "vi",
					"imei": self._imei,
					"zsource": 601,
				}
			),
			"zpw_ver": 645,
			"zpw_type": 30,
		}

		response = self._get(
			"https://tt-group-wpa.chat.zalo.me/api/group/create/v2", params=params
		)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return results

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def changeGroupAvatar(self, filePath, groupId):
		"""Upload/Change group avatar by ID.

		Client must be the Owner of the group
		(If the group does not allow members to upload/change)

		Args:
			filePath (str): A path to the image to upload/change avatar
			groupId (int | str): Group ID to upload/change avatar

		Returns:
			object: `Group` Group avatar change status
			None: If requet success/failed depending on the case
			dict: A dictionary containing error responses

		Raises:
			ZaloAPIException: If request failed
		"""
		if not os.path.exists(filePath):
			raise ZaloUserError(f"{filePath} not found")

		files = [("fileContent", open(filePath, "rb"))]

		params = {
			"params": self._encode(
				{
					"grid": str(groupId),
					"avatarSize": 120,
					"clientId": "g" + str(groupId) + _util.formatTime("%H:%M %d/%m/%Y"),
					"originWidth": 640,
					"originHeight": 640,
					"imei": self._imei,
				}
			),
			"zpw_ver": 645,
			"zpw_type": 30,
		}

		response = self._post(
			"https://tt-files-wpa.chat.zalo.me/api/group/upavatar",
			params=params,
			files=files,
		)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return Group.fromDict(results, None)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def changeGroupName(self, groupName, groupId):
		"""Set/Change group name by ID.

		Client must be the Owner of the group
		(If the group does not allow members to change group name)

		Args:
			groupName (str): Group name to change
			groupId (int | str): Group ID to change name

		Returns:
			object: `Group` Group name change status
			None: If requet success/failed depending on the case
			dict: A dictionary containing error responses

		Raises:
			ZaloAPIException: If request failed
		"""
		params = {"zpw_ver": 645, "zpw_type": 30}

		payload = {"params": self._encode({"gname": groupName, "grid": str(groupId)})}

		response = self._post(
			"https://tt-group-wpa.chat.zalo.me/api/group/updateinfo",
			params=params,
			data=payload,
		)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return Group.fromDict(results, None)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def changeGroupSetting(self, groupId, defaultMode="default", **kwargs):
		"""Update group settings by ID.

		Client must be the Owner/Admin of the group.

		Warning:
			Other settings will default value if not set. See `defaultMode`

		Args:
			groupId (int | str): Group ID to update settings
			defaultMode (str): Default mode of settings

				default: Group default settings
				anti-raid: Group default settings for anti-raid

			**kwargs: Group settings kwargs, Value: (1 = True, 0 = False)

				blockName: Không cho phép user đổi tên & ảnh đại diện nhóm
				signAdminMsg: Đánh dấu tin nhắn từ chủ/phó nhóm
				addMemberOnly: Chỉ thêm members (Khi tắt link tham gia nhóm)
				setTopicOnly: Cho phép members ghim (tin nhắn, ghi chú, bình chọn)
				enableMsgHistory: Cho phép new members đọc tin nhắn gần nhất
				lockCreatePost: Không cho phép members tạo ghi chú, nhắc hẹn
				lockCreatePoll: Không cho phép members tạo bình chọn
				joinAppr: Chế độ phê duyệt thành viên
				bannFeature: Default (No description)
				dirtyMedia: Default (No description)
				banDuration: Default (No description)
				lockSendMsg: Không cho phép members gửi tin nhắn
				lockViewMember: Không cho phép members xem thành viên nhóm
				blocked_members: Danh sách members bị chặn

		Returns:
			object: `Group` Group settings change status
			None: If requet success/failed depending on the case
			dict: A dictionary containing error responses

		Raises:
			ZaloAPIException: If request failed
		"""
		if defaultMode == "anti-raid":
			defSetting = {
				"blockName": 1,
				"signAdminMsg": 1,
				"addMemberOnly": 0,
				"setTopicOnly": 1,
				"enableMsgHistory": 1,
				"lockCreatePost": 1,
				"lockCreatePoll": 1,
				"joinAppr": 1,
				"bannFeature": 0,
				"dirtyMedia": 0,
				"banDuration": 0,
				"lockSendMsg": 0,
				"lockViewMember": 0,
			}
		else:
			defSetting = self.fetchGroupInfo(groupId).gridInfoMap
			defSetting = defSetting[str(groupId)]["setting"]

		blockName = kwargs.get("blockName", defSetting.get("blockName", 1))
		signAdminMsg = kwargs.get("signAdminMsg", defSetting.get("signAdminMsg", 1))
		addMemberOnly = kwargs.get("addMemberOnly", defSetting.get("addMemberOnly", 0))
		setTopicOnly = kwargs.get("setTopicOnly", defSetting.get("setTopicOnly", 1))
		enableMsgHistory = kwargs.get(
			"enableMsgHistory", defSetting.get("enableMsgHistory", 1)
		)
		lockCreatePost = kwargs.get(
			"lockCreatePost", defSetting.get("lockCreatePost", 1)
		)
		lockCreatePoll = kwargs.get(
			"lockCreatePoll", defSetting.get("lockCreatePoll", 1)
		)
		joinAppr = kwargs.get("joinAppr", defSetting.get("joinAppr", 1))
		bannFeature = kwargs.get("bannFeature", defSetting.get("bannFeature", 0))
		dirtyMedia = kwargs.get("dirtyMedia", defSetting.get("dirtyMedia", 0))
		banDuration = kwargs.get("banDuration", defSetting.get("banDuration", 0))
		lockSendMsg = kwargs.get("lockSendMsg", defSetting.get("lockSendMsg", 0))
		lockViewMember = kwargs.get(
			"lockViewMember", defSetting.get("lockViewMember", 0)
		)
		blocked_members = kwargs.get("blocked_members", [])

		params = {
			"params": self._encode(
				{
					"blockName": blockName,
					"signAdminMsg": signAdminMsg,
					"addMemberOnly": addMemberOnly,
					"setTopicOnly": setTopicOnly,
					"enableMsgHistory": enableMsgHistory,
					"lockCreatePost": lockCreatePost,
					"lockCreatePoll": lockCreatePoll,
					"joinAppr": joinAppr,
					"bannFeature": bannFeature,
					"dirtyMedia": dirtyMedia,
					"banDuration": banDuration,
					"lockSendMsg": lockSendMsg,
					"lockViewMember": lockViewMember,
					"blocked_members": blocked_members,
					"grid": str(groupId),
					"imei": self._imei,
				}
			),
			"zpw_ver": 645,
			"zpw_type": 30,
		}

		response = self._get(
			"https://tt-group-wpa.chat.zalo.me/api/group/setting/update", params=params
		)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return Group.fromDict(results, None)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def changeGroupOwner(self, newAdminId, groupId):
		"""Change group owner (yellow key) by ID.

		Client must be the Owner of the group.

		Args:
			newAdminId (int | str): members ID to changer owner
			groupId (int | str): ID of the group to changer owner

		Returns:
			object: `Group` Group owner change status
			None: If requet success/failed depending on the case
			dict: A dictionary containing error responses

		Raises:
			ZaloAPIException: If request failed
		"""
		params = {
			"params": self._encode(
				{
					"grid": str(groupId),
					"newAdminId": str(newAdminId),
					"imei": self._imei,
					"language": "vi",
				}
			),
			"zpw_ver": 645,
			"zpw_type": 30,
		}

		response = self._get(
			"https://tt-group-wpa.chat.zalo.me/api/group/change-owner", params=params
		)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return Group.fromDict(results, None)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def addUsersToGroup(self, user_ids, groupId):
		"""Add friends/users to a group.

		Args:
			user_ids (str | list): One or more friend/user IDs to add
			groupId (int | str): Group ID to add friend/user to

		Returns:
			object: `Group` add friend/user data
			dict: A dictionary containing error_code, response if failed

		Raises:
			ZaloAPIException: If request failed
		"""
		memberTypes = []

		if user_ids and isinstance(user_ids, list):
			members = [str(user) for user in user_ids]
		else:
			members = [str(user_ids)]

		if members:
			for i in members:
				memberTypes.append(-1)

		params = {"zpw_ver": 645, "zpw_type": 30}

		payload = {
			"params": self._encode(
				{
					"grid": str(groupId),
					"members": members,
					"memberTypes": memberTypes,
					"imei": self._imei,
					"clientLang": "vi",
				}
			)
		}

		response = self._post(
			"https://tt-group-wpa.chat.zalo.me/api/group/invite/v2",
			params=params,
			data=payload,
		)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return Group.fromDict(results, None)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def kickUsersInGroup(self, members, groupId):
		"""Kickout members in group by ID.

		Client must be the Owner of the group.

		Args:
			members (str | list): One or More member IDs to kickout
			groupId (int | str): Group ID to kick member from

		Returns:
			object: `Group` kick data
			dict: A dictionary/object containing error responses

		Raises:
			ZaloAPIException: If request failed
		"""
		if isinstance(members, list):
			members = [str(member) for member in members]
		else:
			members = [str(members)]

		params = {"zpw_ver": 645, "zpw_type": 30}

		payload = {"params": self._encode({"grid": str(groupId), "members": members})}

		response = self._post(
			"https://tt-group-wpa.chat.zalo.me/api/group/kickout",
			params=params,
			data=payload,
		)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return Group.fromDict(results, None)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def blockUsersInGroup(self, members, groupId):
		"""Blocked members in group by ID.

		Client must be the Owner of the group.

		Args:
			members (str | list): One or More member IDs to block
			groupId (int | str): Group ID to block member from

		Returns:
			object: `Group` block members response
			dict: A dictionary/object containing error responses

		Raises:
			ZaloAPIException: If request failed
		"""
		if isinstance(members, list):
			members = [str(member) for member in members]
		else:
			members = [str(members)]

		params = {
			"zpw_ver": 645,
			"zpw_type": 30,
			"params": self._encode({"grid": str(groupId), "members": members}),
		}

		response = self._get(
			"https://tt-group-wpa.chat.zalo.me/api/group/blockedmems/add", params=params
		)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return Group.fromDict(results, None)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def unblockUsersInGroup(self, members, groupId):
		"""unblock members in group by ID.

		Client must be the Owner of the group.

		Args:
			members (str | list): One or More member IDs to unblock
			groupId (int | str): Group ID to unblock member from

		Returns:
			object: `Group` unblock members response
			dict: A dictionary/object containing error responses

		Raises:
			ZaloAPIException: If request failed
		"""
		if isinstance(members, list):
			members = [str(member) for member in members]
		else:
			members = [str(members)]

		params = {
			"zpw_ver": 645,
			"zpw_type": 30,
			"params": self._encode({"grid": str(groupId), "members": members}),
		}

		response = self._get(
			"https://tt-group-wpa.chat.zalo.me/api/group/blockedmems/remove",
			params=params,
		)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return Group.fromDict(results, None)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def addGroupAdmins(self, members, groupId):
		"""Add admins to the group (white key).

		Client must be the Owner of the group.

		Args:
			members (str | list): One or More member IDs to add
			groupId (int | str): Group ID to add admins

		Returns:
			object: `Group` Group admins add status
			None: If requet success/failed depending on the case
			dict: A dictionary containing error responses

		Raises:
			ZaloAPIException: If request failed
		"""
		if isinstance(members, list):
			members = [str(member) for member in members]
		else:
			members = [str(members)]

		params = {
			"params": self._encode(
				{"grid": str(groupId), "members": members, "imei": self._imei}
			),
			"zpw_ver": 645,
			"zpw_type": 30,
		}

		response = self._get(
			"https://tt-group-wpa.chat.zalo.me/api/group/admins/add", params=params
		)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return Group.fromDict(results, None)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def removeGroupAdmins(self, members, groupId):
		"""Remove admins in the group (white key) by ID.

		Client must be the Owner of the group.

		Args:
			members (str | list): One or More admin IDs to remove
			groupId (int | str): Group ID to remove admins

		Returns:
			object: `Group` Group admins remove status
			None: If requet success/failed depending on the case
			dict: A dictionary containing error responses

		Raises:
			ZaloAPIException: If request failed
		"""
		if isinstance(members, list):
			members = [str(member) for member in members]
		else:
			members = [str(members)]

		params = {
			"params": self._encode(
				{"grid": str(groupId), "members": members, "imei": self._imei}
			),
			"zpw_ver": 645,
			"zpw_type": 30,
		}

		response = self._get(
			"https://tt-group-wpa.chat.zalo.me/api/group/admins/remove", params=params
		)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return Group.fromDict(results, None)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def pinGroupMsg(self, pinMsg, groupId):
		"""Pin message in group by ID.

		Args:
			pinMsg (Message): Message Object to pin
			groupId (int | str): Group ID to pin message

		Returns:
			object: `Group` pin message status
			dict: A dictionary containing error_code & responses if failed

		Raises:
			ZaloAPIException: If request failed
		"""
		params = {"zpw_ver": 645, "zpw_type": 30}

		payload = {
			"params": {
				"grid": str(groupId),
				"type": 2,
				"color": -14540254,
				"emoji": "📌",
				"startTime": -1,
				"duration": -1,
				"repeat": 0,
				"src": -1,
				"imei": self._imei,
				"pinAct": 1,
			}
		}

		if pinMsg.msgType == "webchat":

			payload["params"]["params"] = json.dumps(
				{
					"client_msg_id": pinMsg.cliMsgId,
					"global_msg_id": pinMsg.msgId,
					"senderUid": str(int(pinMsg.uidFrom) or self.uid),
					"senderName": pinMsg.dName,
					"title": pinMsg.content,
					"msg_type": _util.getClientMessageType(pinMsg.msgType),
				}
			)

		elif pinMsg.msgType == "chat.voice":

			payload["params"]["params"] = json.dumps(
				{
					"client_msg_id": pinMsg.cliMsgId,
					"global_msg_id": pinMsg.msgId,
					"senderUid": str(int(pinMsg.uidFrom) or self.uid),
					"senderName": pinMsg.dName,
					"msg_type": _util.getClientMessageType(pinMsg.msgType),
				}
			)

		elif pinMsg.msgType in ["chat.photo", "chat.video.msg"]:

			payload["params"]["params"] = json.dumps(
				{
					"client_msg_id": pinMsg.cliMsgId,
					"global_msg_id": pinMsg.msgId,
					"senderUid": str(int(pinMsg.uidFrom) or self.uid),
					"senderName": pinMsg.dName,
					"thumb": pinMsg.content.thumb,
					"title": pinMsg.content.description,
					"msg_type": _util.getClientMessageType(pinMsg.msgType),
				}
			)

		elif pinMsg.msgType == "chat.sticker":

			payload["params"]["params"] = json.dumps(
				{
					"client_msg_id": pinMsg.cliMsgId,
					"global_msg_id": pinMsg.msgId,
					"senderUid": str(int(pinMsg.uidFrom) or self.uid),
					"senderName": pinMsg.dName,
					"extra": json.dumps(
						{
							"id": pinMsg.content.id,
							"catId": pinMsg.content.catId,
							"type": pinMsg.content.type,
						}
					),
					"msg_type": _util.getClientMessageType(pinMsg.msgType),
				}
			)

		elif pinMsg.msgType in ["chat.recommended", "chat.link"]:

			extra = json.loads(pinMsg.content.params)
			payload["params"]["params"] = json.dumps(
				{
					"client_msg_id": pinMsg.cliMsgId,
					"global_msg_id": pinMsg.msgId,
					"senderUid": str(int(pinMsg.uidFrom) or self.uid),
					"senderName": pinMsg.dName,
					"href": pinMsg.content.href,
					"thumb": pinMsg.content.thumb or "",
					"title": pinMsg.content.title,
					"linkCaption": "https://zalo.me/0816262451",
					"redirect_url": extra.get("redirect_url", ""),
					"streamUrl": extra.get("streamUrl", ""),
					"artist": extra.get("artist", ""),
					"stream_icon": extra.get("stream_icon", ""),
					"type": 2,
					"extra": json.dumps(
						{
							"action": pinMsg.content.action,
							"params": json.dumps(
								{
									"mediaTitle": extra.get("mediaTitle", ""),
									"artist": extra.get("artist", ""),
									"src": extra.get("src", ""),
									"stream_icon": extra.get("stream_icon", ""),
									"streamUrl": extra.get("streamUrl", ""),
									"type": 2,
								}
							),
						}
					),
					"msg_type": _util.getClientMessageType(pinMsg.msgType),
				}
			)

		elif pinMsg.msgType == "chat.location.new":

			payload["params"]["params"] = json.dumps(
				{
					"client_msg_id": pinMsg.cliMsgId,
					"global_msg_id": pinMsg.msgId,
					"senderUid": str(int(pinMsg.uidFrom) or self.uid),
					"senderName": pinMsg.dName,
					"msg_type": _util.getClientMessageType(pinMsg.msgType),
					"title": pinMsg.content.title or pinMsg.content.description,
				}
			)

		elif pinMsg.msgType == "share.file":

			extra = json.loads(pinMsg.content.params)
			payload["params"]["params"] = json.dumps(
				{
					"client_msg_id": pinMsg.cliMsgId,
					"global_msg_id": pinMsg.msgId,
					"senderUid": str(int(pinMsg.uidFrom) or self.uid),
					"senderName": pinMsg.dName,
					"title": pinMsg.content.title,
					"extra": json.dumps(
						{
							"fileSize": "7295",
							"checksum": extra.get("checksum", ""),
							"fileExt": extra.get("fileExt", ""),
							"tWidth": extra.get("tWidth", 0),
							"tHeight": extra.get("tHeight", 0),
							"duration": extra.get("duration", 0),
							"fType": extra.get("fType", 0),
							"fdata": extra.get("fdata", ""),
						}
					),
					"msg_type": _util.getClientMessageType(pinMsg.msgType),
				}
			)

		elif pinMsg.msgType == "chat.gif":

			payload["params"]["params"] = json.dumps(
				{
					"client_msg_id": pinMsg.cliMsgId,
					"global_msg_id": pinMsg.msgId,
					"senderUid": str(int(pinMsg.uidFrom) or self.uid),
					"senderName": pinMsg.dName,
					"thumb": pinMsg.content.thumb,
					"msg_type": _util.getClientMessageType(pinMsg.msgType),
				}
			)

		payload["params"] = self._encode(payload["params"])
		response = self._post(
			"https://groupboard-wpa.chat.zalo.me/api/board/topic/createv2",
			params=params,
			data=payload,
		)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return Group.fromDict(results, None)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def unpinGroupMsg(self, pinId, pinTime, groupId):
		"""Unpin message in group by ID.

		Args:
			pinId (int | str): Pin ID to unpin
			pinTime (int): Pin start time
			groupId (int | str): Group ID to unpin message

		Returns:
			object: `Group` unpin message status
			dict: A dictionary containing error_code & responses if failed

		Raises:
			ZaloAPIException: If request failed
		"""
		params = {
			"zpw_ver": 645,
			"zpw_type": 30,
			"params": self._encode(
				{
					"grid": str(groupId),
					"imei": self._imei,
					"topic": {"topicId": str(pinId), "topicType": 2},
					"boardVersion": int(pinTime),
				}
			),
		}

		response = self._get(
			"https://groupboard-wpa.chat.zalo.me/api/board/unpinv2", params=params
		)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return Group.fromDict(results, None)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def deleteGroupMsg(self, msgId, ownerId, clientMsgId, groupId):
		"""Delete message in group by ID.

		Args:
			groupId (int | str): Group ID to delete message
			msgId (int | str): Message ID to delete
			ownerId (int | str): Owner ID of the message to delete
			clientMsgId (int | str): Client message ID to delete message

		Returns:
			object: `Group` delete message status
			dict: A dictionary containing error_code & responses if failed

		Raises:
			ZaloAPIException: If request failed
		"""
		params = {"zpw_ver": 645, "zpw_type": 30}

		payload = {
			"params": self._encode(
				{
					"grid": str(groupId),
					"cliMsgId": _util.now(),
					"msgs": [
						{
							"cliMsgId": str(clientMsgId),
							"globalMsgId": str(msgId),
							"ownerId": str(ownerId),
							"destId": str(groupId),
						}
					],
					"onlyMe": 0,
				}
			)
		}

		response = self._post(
			"https://tt-group-wpa.chat.zalo.me/api/group/deletemsg",
			params=params,
			data=payload,
		)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return Group.fromDict(results, None)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def viewGroupPending(self, groupId):
		"""See list of people pending approval in group by ID.

		Args:
			groupId (int | str): Group ID to view pending members

		Returns:
			object: `Group` pending responses
			dict: A dictionary containing error_code & responses if failed

		Raises:
			ZaloAPIException: If request failed
		"""
		params = {
			"params": self._encode({"grid": str(groupId), "imei": self._imei}),
			"zpw_ver": 645,
			"zpw_type": 30,
		}

		response = self._get(
			"https://tt-group-wpa.chat.zalo.me/api/group/pending-mems/list",
			params=params,
		)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return Group.fromDict(results, None)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def handleGroupPending(self, members, groupId, isApprove=True):
		"""Approve/Deny pending users to the group from the group's approval.

		Client must be the Owner of the group.

		Args:
			members (str | list): One or More member IDs to handle
			groupId (int | str): ID of the group to handle pending members
			isApprove (bool): Approve/Reject pending members (True | False)

		Returns:
			object: `Group` handle pending responses
			dict: A dictionary/object containing error responses

		Raises:
			ZaloAPIException: If request failed
		"""
		if isinstance(members, list):
			members = [str(member) for member in members]
		else:
			members = [str(members)]

		params = {
			"params": self._encode(
				{
					"grid": str(groupId),
					"members": members,
					"isApprove": 1 if isApprove else 0,
				}
			),
			"zpw_ver": 645,
			"zpw_type": 30,
		}

		response = self._get(
			"https://tt-group-wpa.chat.zalo.me/api/group/pending-mems/review",
			params=params,
		)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return Group.fromDict(results, None)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def viewPollDetail(self, pollId):
		"""View poll data by ID.

		Args:
			pollId (int | str): Poll ID to view detail

		Returns:
			object: `Group` poll data
			dict: A dictionary containing error_code & response if failed

		Raises:
			ZaloAPIException: If request failed
		"""
		params = {
			"params": self._encode({"poll_id": int(pollId), "imei": self._imei}),
			"zpw_ver": 645,
			"zpw_type": 30,
		}

		response = self._get(
			"https://tt-group-wpa.chat.zalo.me/api/poll/detail", params=params
		)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return Group.fromDict(results, None)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def createPoll(
		self,
		question,
		options,
		groupId,
		expiredTime=0,
		pinAct=False,
		multiChoices=True,
		allowAddNewOption=True,
		hideVotePreview=False,
		isAnonymous=False,
	):
		"""Create poll in group by ID.

		Client must be the Owner of the group.

		Args:
			question (str): Question for poll
			options (str | list): List options for poll
			groupId (int | str): Group ID to create poll from
			expiredTime (int): Poll expiration time (0 = no expiration)
			pinAct (bool): Pin action (pin poll)
			multiChoices (bool): Allows multiple poll choices
			allowAddNewOption (bool): Allow members to add new options
			hideVotePreview (bool): Hide voting results when haven't voted
			isAnonymous (bool): Hide poll voters

		Returns:
			object: `Group` poll create data
			dict: A dictionary containing error responses

		Raises:
			ZaloAPIException: If request failed
		"""
		params = {"zpw_ver": 645, "zpw_type": 30}

		payload = {
			"params": {
				"group_id": str(groupId),
				"question": question,
				"options": [],
				"expired_time": expiredTime,
				"pinAct": pinAct,
				"allow_multi_choices": multiChoices,
				"allow_add_new_option": allowAddNewOption,
				"is_hide_vote_preview": hideVotePreview,
				"is_anonymous": isAnonymous,
				"poll_type": 0,
				"src": 1,
				"imei": self._imei,
			}
		}

		if isinstance(options, list):
			payload["params"]["options"] = options
		else:
			payload["params"]["options"].append(str(options))

		payload["params"] = self._encode(payload["params"])

		response = self._post(
			"https://tt-group-wpa.chat.zalo.me/api/poll/create",
			params=params,
			data=payload,
		)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return Group.fromDict(results, None)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def lockPoll(self, pollId):
		"""Lock/end poll in group by ID.

		Client must be the Owner of the group.

		Args:
			pollId (int | str): Poll ID to lock

		Returns:
			None: If requet success
			dict: A dictionary containing error responses

		Raises:
			ZaloAPIException: If request failed
		"""
		params = {"zpw_ver": 645, "zpw_type": 30}

		payload = {"params": self._encode({"poll_id": int(pollId), "imei": self._imei})}

		response = self._post(
			"https://tt-group-wpa.chat.zalo.me/api/poll/end",
			params=params,
			data=payload,
		)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return Group.fromDict(results, None)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def disperseGroup(self, groupId):
		"""Disperse group by ID.

		Client must be the Owner of the group.

		Args:
			groupId (int | str): Group ID to disperse

		Returns:
			None: If requet success
			dict: A dictionary containing error responses

		Raises:
			ZaloAPIException: If request failed
		"""
		params = {"zpw_ver": 645, "zpw_type": 30}

		payload = {"params": self._encode({"grid": str(groupId), "imei": self._imei})}

		response = self._post(
			"https://tt-group-wpa.chat.zalo.me/api/group/disperse",
			params=params,
			data=payload,
		)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("error_code") == 0 else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return Group.fromDict(results, None)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	"""
	END GROUP ACTION METHODS
	"""

	"""
	SEND METHODS
	"""

	def sendToDo(
		self,
		message_object,
		content,
		assignees,
		thread_id,
		thread_type,
		due_date=-1,
		description="PhuDev",
	):
		"""Send a todo to a user in group.

		Args:
			message_object (Message): The original message object
			content (str): The content of the todo
			assignees (list): List of recipient IDs
			thread_id (str): The ID of the thread
			thread_type (ThreadType): The type of thread (USER/GROUP)
			due_date (int): The due date (-1 if not specified)
			description (str): Description (can be empty)

		Returns:
			object: Result returned from the API

		Raises:
			ZaloAPIException: If the request fails
		"""
		if not content:
			raise ZaloAPIException("Missing todo content")
		if not assignees:
			raise ZaloAPIException("Missing assignees")

		params = {"zpw_ver": 641, "zpw_type": 30}

		is_group = thread_type == ThreadType.GROUP

		payload = {
			"params": {
				"assignees": json.dumps(assignees),
				"dueDate": due_date,
				"content": content,
				"description": description,
				"extra": json.dumps(
					{
						"msgId": message_object.msgId,
						"toUid": thread_id,
						"isGroup": is_group,
						"cliMsgId": message_object.cliMsgId,
						"msgType": 1,
						"mention": [],
						"ownerMsgUId": self.uid,
						"message": content,
					}
				),
				"dateDefaultType": 0,
				"status": -1,
				"watchers": "[]",
				"schedule": None,
				"src": 5,
				"imei": self._imei,
			}
		}

		payload["params"] = self._encode(payload["params"])

		response = self._post(
			"https://board-wpa.chat.zalo.me/api/board/personal/todo/create",
			params=params,
			data=payload,
		)

		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None

		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results

			if results is None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return results

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def callGroupRequest(self, groupId, userId, callId=None):
		params = {"zpw_ver": 667, "zpw_type": 24}
		if not callId:
			callId = int(time.time())
		
		payload = {
			"params": self._encode({
				"groupId": str(groupId),
				"callId": callId,
				"typeRequest": 1,
				"data": json.dumps({
					"extraData": "",
					"groupAvatar": "",
					"groupId": str(groupId),
					"groupName": "Xuan Bach Cte",
					"maxUsers": 8,
					"noiseId": userId if isinstance(userId, list) else [str(userId)]
				}),
				"partners": userId if isinstance(userId, list) else [str(userId)]
			})
		}

		response = self._post(
			"https://voicecall-wpa.chat.zalo.me/api/voicecall/group/requestcall",
			params=params, data=payload
		)

		try:
			data = response.json()
		except json.JSONDecodeError:
			raise ZaloAPIException("Invalid JSON response from server.")

		if data.get("error_code") != 0:
			raise ZaloAPIException(
				f"Error #{data.get('error_code')} when sending call request: {data.get('error_message', 'Unknown error')}"
			)

		results = data.get("data")
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					raise ZaloAPIException("Invalid results string.")
			return results

		raise ZaloAPIException(
			f"Error #{data.get('error_code')} when sending requests: {data.get('error_message')}"
		)

	def callGroup(self, groupId, userId, callId=None):
		if not callId:
			callId = int(time.time())

		params = {"zpw_ver": 667, "zpw_type": 24}
		request_data = self.callGroupRequest(groupId, userId, callId)

		try:
			params_data = json.loads(request_data.get("params", "{}"))
		except Exception:
			params_data = {}

		call_setting = params_data.get("callSetting", {})
		servers = call_setting.get("servers", [])
		session = call_setting.get("session", "")
		partner_ids = request_data.get("partnerIds", [])
		idcal = partner_ids[0] if isinstance(partner_ids, list) and partner_ids else None

		rtpaddr = rtcpaddr = rtpaddrIPv6 = rtcpaddrIPv6 = ""
		if servers:
			srv = servers[0]
			rtpaddr = srv.get("rtpaddr", "")
			rtcpaddr = srv.get("rtcpaddr", "")
			rtpaddrIPv6 = srv.get("rtpaddrIPv6", "")
			rtcpaddrIPv6 = srv.get("rtcpaddrIPv6", "")

		inner_data = (
			f'\n{{\n\t"groupAvatar" : "",\n\t"groupName" : "Xuan Bach Cte",'
			f'\n\t"hostCall" : {params_data.get("hostCall")},'
			f'\n\t"maxUsers" : {params_data.get("maxUsers",8)},'
			f'\n\t"noiseId" : ["{idcal}"]\n}}\n'
		)

		outer_data = (
			f'\n{{\n\t"codec" : "",\n\t"data" : "{inner_data.replace("\\", "\\\\").replace("\"", "\\\"")}",'
			f'\n\t"extendData" : "",\n\t"rtcpAddress" : "{rtcpaddr}",'
			f'\n\t"rtcpAddressIPv6" : "{rtcpaddrIPv6}",\n\t"rtpAddress" : "{rtpaddr}",'
			f'\n\t"rtpAddressIPv6" : "{rtpaddrIPv6}"\n}}\n'
		)

		payload = {
			"params": self._encode({
				"callId": params_data.get("callId", callId),
				"callType": 1,
				"data": outer_data,
				"session": session,
				"partners": f'[ "{idcal}" ]\n',
				"groupId": str(groupId)
			})
		}

		response = self._post(
			"https://voicecall-wpa.chat.zalo.me/api/voicecall/group/request",
			params=params, data=payload
		)

		try:
			data = response.json()
		except json.JSONDecodeError:
			raise ZaloAPIException("Invalid JSON response from server.")

		if data.get("error_code") != 0:
			raise ZaloAPIException(
				f"Error #{data.get('error_code')} when sending call: {data.get('error_message', 'Unknown error')}"
			)

		results = data.get("data")
		if results:
			return self._decode(results)

		raise ZaloAPIException("Empty response data in callGroup.")

	def callGroupAdd(self, userId, hostCall, groupId, callId=None):
		params = {"zpw_ver": 667, "zpw_type": 24}
		
		if not callId:
			callId = int(time.time())
		
		data_str = (
			'\n{\n'
			f'\t"codec" : "",\n'
			f'\t"data" : "\\n{{\\n\\t\\\"groupAvatar\\\" : \\\"\\\",\\n\\t\\\"groupId\\\" : {groupId},\\n\\t\\\"groupName\\\" : \\\"Xuan Bach Cte\\\",\\n\\t\\\"hostCall\\\" : {hostCall},\\n\\t\\\"maxUsers\\\" : 8\\n}}\\n",\n'
			f'\t"extendData" : "",\n'
			f'\t"rtcpAddress" : "",\n'
			f'\t"rtcpAddressIPv6" : "",\n'
			f'\t"rtpAddress" : "",\n'
			f'\t"rtpAddressIPv6" : ""\n'
			'}\n'
		)

		payload = {
			"params": self._encode({
				"callId": callId,
				"callType": 1,
				"hostCall": hostCall,
				"data": data_str,
				"session": "",
				"partners": f'[ "{userId}" ]\n',
				"groupId": str(groupId)
			})
		}

		response = self._post(
			"https://voicecall-wpa.chat.zalo.me/api/voicecall/group/adduser",
			params=params, data=payload
		)

		try:
			data = response.json()
		except json.JSONDecodeError:
			raise ZaloAPIException("Invalid JSON response from server.")

		if data.get("error_code") != 0:
			raise ZaloAPIException(
				f"Error #{data.get('error_code')} when sending call: {data.get('error_message', 'Unknown error')}"
			)

		results = data.get("data")
		if results:
			results = self._decode(results)
			print(results)
			return results

		raise ZaloAPIException("Empty response data in callGroupAdd.")

	def callGroupCancel(self, callId, hostCall, groupId):
		params = {"zpw_ver": 667, "zpw_type": 24}

		data_str = (
			'\n{\n'
			f'\t"callType" : 1,\n'
			f'\t"duration" : 0,\n'
			f'\t"extraData" : "",\n'
			f'\t"groupId" : {groupId}\n'
			'}\n'
		)

		payload = {
			"params": self._encode({
				"callId": callId,
				"hostCall": hostCall,
				"data": data_str
			})
		}

		response = self._post(
			"https://voicecall-wpa.chat.zalo.me/api/voicecall/group/cancel",
			params=params, data=payload
		)

		try:
			data = response.json()
		except json.JSONDecodeError:
			raise ZaloAPIException("Invalid JSON response from server.")

		if data.get("error_code") != 0:
			raise ZaloAPIException(
				f"Error #{data.get('error_code')} when sending call: {data.get('error_message', 'Unknown error')}"
			)

		results = data.get("data")
		if results:
			results = self._decode(results)
			print(results)
			return results

		raise ZaloAPIException("Empty response data in callGroupCancel.")
				
	def sendCall(self, userId, callId=None):
		"""Initiate a call to a specified user.

		Args:
			userId (int | str): ID of the user to call
			callId (int, optional): Unique call identifier. If not provided, generated from current timestamp

		Returns:
			dict: Call session information if successful
			dict: A dictionary containing error_code and error_message if failed

		Raises:
			ZaloAPIException: If the call request fails or server returns invalid response
		"""
		if not callId:
			callId = int(time.time())

		params = {"zpw_ver": 655, "zpw_type": 24}
		payload_request = {
			"params": self._encode(
				{
					"calleeId": str(userId),
					"callId": callId,
					"codec": "[]\n",
					"typeRequest": 1,
					"imei": self._imei,
				}
			)
		}

		response_request = self._post(
			"https://voicecall-wpa.chat.zalo.me/api/voicecall/requestcall",
			params=params,
			data=payload_request,
		)

		try:
			request_data = response_request.json()
		except json.JSONDecodeError:
			raise ZaloAPIException("Invalid JSON response from server.")

		if request_data.get("error_code") != 0:
			error_code = request_data.get("error_code")
			error_message = request_data.get("error_message", "Unknown error")
			raise ZaloAPIException(
				f"Error #{error_code} when sending call request: {error_message}"
			)

		results = request_data.get("data")
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results is None:
				results = {"error_code": 1337, "error_message": "Data is None"}
			if isinstance(results, str):
				try:
					results = json.loads(results)
				except json.JSONDecodeError:
					results = {"error_code": 1337, "error_message": results}
		else:
			error_code = request_data.get("error_code")
			error_message = request_data.get("error_message") or request_data.get(
				"data"
			)
			raise ZaloAPIException(
				f"Error #{error_code} when sending requests: {error_message}"
			)

		payload_call = {
			"params": self._encode(
				{
					"calleeId": str(userId),
					"rtcpAddress": results.get("rtcpIP", ""),
					"rtpAddress": results.get("rtcpIP", ""),
					"codec": results.get(
						"codec",
						'[{"dynamicFptime":0,"frmPtime":20,"name":"opus/16000/1","payload":112}]',
					),
					"session": results.get("sessId", ""),
					"callId": callId,
					"imei": self._imei,
					"extendData": {
						"callType": 0,
						"fecTP": 0,
						"gccAudio": 1,
						"gccEarlyCall": 0,
						"gccMode": 1,
						"gccSVLR": 1,
						"maxFT": 60,
						"newZrtc": 1,
						"numServers": 0,
						"p2p": [
							{"ip": "192.168.2.4", "port": 60258, "type": 0},
							{"ip": "117.5.147.202", "port": 20118, "type": 1},
						],
						"packetMode": 2,
						"platform": 2,
						"sP2P": 1,
						"serverAddr": [
							{
								"rtcp": "171.244.128.57:4200",
								"rtcpIPv6": "2401:5f80:3fff:7::19:4200",
								"rtp": "171.244.128.57:4200",
								"rtpIPv6": "2401:5f80:3fff:7::19:4200",
								"tpType": 0,
							}
						],
						"serverResult": [
							{
								"recv": 14,
								"rtcp": "171.244.128.57:4200",
								"rtcpIPv6": "2401:5f80:3fff:7::19:4200",
								"rtp": "171.244.128.57:4200",
								"rtpIPv6": "2401:5f80:3fff:7::19:4200",
								"rtt": 562,
								"spTcp": 1,
								"tpType": 0,
							}
						],
						"spTcp": 1,
						"srtcp": 0,
						"srtpMode": 1,
						"supportCallBusy": 1,
						"supportHevcDecode": 1,
						"tpType": 0,
						"video": {"codec": [{"name": "h264", "payload": 97}]},
					},
					"subCommand": 3,
				}
			)
		}

		response_call = self._post(
			"https://voicecall-wpa.chat.zalo.me/api/voicecall/request",
			params=params,
			data=payload_call,
		)

		try:
			data = response_call.json()
		except json.JSONDecodeError:
			raise ZaloAPIException("Invalid JSON response from server.")

		if data.get("error_code") != 0:
			error_code = data.get("error_code")
			error_message = data.get("error_message", "Unknown error")
			raise ZaloAPIException(
				f"Error #{error_code} when sending call request: {error_message}"
			)

		results = data.get("data")
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results is None:
				results = {"error_code": 1337, "error_message": "Data is None"}
			if isinstance(results, str):
				try:
					results = json.loads(results)
				except json.JSONDecodeError:
					results = {"error_code": 1337, "error_message": results}
			return results

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def createQuickMessage(
		self,
		item_id: int,
		keyword: str,
		title: str,
		params_text: str = "",
		media: dict | None = None,
		msg_type: int = 0,
	) -> dict:
		"""
		Create or update a quick message.

		Args:
			item_id (int): ID of the quick message (new or existing).
			keyword (str): Shortcut keyword.
			title (str): Message title or main content.
			params_text (str, optional): Extra params string (default: "").
			media (dict | None, optional): Media data if any (default: None).
			msg_type (int, optional): Message type (default: 0 = text).

		Returns:
			dict: Response data if successful.

		Raises:
			ZaloAPIException: If the request fails.
		"""
		if not (item_id and keyword and title):
			raise ZaloUserError("item_id, keyword and title must be provided")

		url = "https://quickmessage.chat.zalo.me/api/quickmessage/update"
		params = {"zpw_ver": 665, "zpw_type": 30}

		payload = {
			"itemId": int(item_id),
			"keyword": str(keyword),
			"message": {
				"title": str(title),
				"params": str(params_text),
			},
			"media": media,
			"type": msg_type,
		}

		payload["params"] = self._encode(payload)

		response = self._post(url, params=params, data=payload)

		try:
			data = response.json()
		except Exception:
			raise ZaloAPIException("Response is not valid JSON")

		if data.get("error_code") == 0:
			return self._decode(data.get("data")) or {"error_code": 0, "message": "Quick message updated"}
		else:
			raise ZaloAPIException(
				f"Error #{data.get('error_code')} when updating quick message: "
				f"{data.get('error_message') or data.get('data')}"
			)

	def send(
		self, message, thread_id, thread_type=ThreadType.USER, mark_message=None, ttl=0
	):
		"""Send message to a thread.

		Args:
			message (Message): Message to send
			thread_id (int | str): User/Group ID to send to
			thread_type (ThreadType): ThreadType.USER, ThreadType.GROUP

		Returns:
			object: `User/Group` (Returns msg ID just sent)
			dict: A dictionary containing error responses

		Raises:
			ZaloAPIException: If request failed
		"""
		thread_id = str(int(thread_id) or self.uid)
		if message.mention:
			return self.sendMentionMessage(message, thread_id, ttl)
		else:
			return self.sendMessage(message, thread_id, thread_type, mark_message, ttl)

	def sendMessage(self, message, thread_id, thread_type, mark_message=None, ttl=0):
		"""Send message to a thread (user/group).

		Args:
			message (Message): Message to send
			thread_id (int | str): User/Group ID to send to
			thread_type (ThreadType): ThreadType.USER, ThreadType.GROUP
			mark_message (str): Send messages as `Urgent` or `Important` mark

		Returns:
			object: `User/Group` (Returns msg ID just sent)
			dict: A dictionary containing error responses

		Raises:
			ZaloAPIException: If request failed
		"""
		params = {"zpw_ver": 645, "zpw_type": 30, "nretry": 0}

		payload = {
			"params": {
				"message": message.text,
				"clientId": _util.now(),
				"imei": self._imei,
				"ttl": ttl,
			}
		}

		if mark_message and mark_message.lower() in ["important", "urgent"]:
			markType = 1 if mark_message.lower() == "important" else 2
			payload["params"]["metaData"] = {"urgency": markType}

		if message.style:
			payload["params"]["textProperties"] = message.style

		if thread_type == ThreadType.USER:
			url = "https://tt-chat2-wpa.chat.zalo.me/api/message/sms"
			payload["params"]["toid"] = str(thread_id)
		elif thread_type == ThreadType.GROUP:
			url = "https://tt-group-wpa.chat.zalo.me/api/group/sendmsg"
			payload["params"]["visibility"] = 0
			payload["params"]["grid"] = str(thread_id)
		else:
			raise ZaloUserError("Thread type is invalid")

		payload["params"] = self._encode(payload["params"])

		response = self._post(url, params=params, data=payload)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return (
				Group.fromDict(results, None)
				if thread_type == ThreadType.GROUP
				else User.fromDict(results, None)
			)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def replyMessage(self, message, replyMsg, thread_id, thread_type, ttl=0):
		"""Reply message in group by ID.

		Args:
			message (Message): Message Object to send
			replyMsg (Message): Message Object to reply
			thread_id (int | str): User/Group ID to send to.
			thread_type (ThreadType): ThreadType.USER, ThreadType.GROUP

		Returns:
			object: `User/Group` (Returns msg ID just sent)
			dict: A dictionary containing error responses

		Raises:
			ZaloAPIException: If request failed
		"""
		params = {"zpw_ver": 645, "zpw_type": 30, "nretry": 1}

		payload = {
			"params": {
				"message": message.text,
				"clientId": _util.now(),
				"qmsgOwner": str(int(replyMsg.uidFrom) or self.uid),
				"qmsgId": replyMsg.msgId,
				"qmsgCliId": replyMsg.cliMsgId,
				"qmsgType": _util.getClientMessageType(replyMsg.msgType),
				"qmsg": replyMsg.content,
				"qmsgTs": replyMsg.ts,
				"qmsgAttach": json.dumps({}),
				"qmsgTTL": 0,
				"ttl": ttl,
			}
		}

		if not isinstance(replyMsg.content, str):
			payload["params"]["qmsg"] = ""
			payload["params"]["qmsgAttach"] = json.dumps(replyMsg.content.toDict())

		if message.style:
			payload["params"]["textProperties"] = message.style

		if message.mention:
			payload["params"]["mentionInfo"] = message.mention

		if thread_type == ThreadType.USER:
			url = "https://tt-chat2-wpa.chat.zalo.me/api/message/quote"
			payload["params"]["toid"] = str(thread_id)
		elif thread_type == ThreadType.GROUP:
			url = "https://tt-group-wpa.chat.zalo.me/api/group/quote"
			payload["params"]["visibility"] = 0
			payload["params"]["grid"] = str(thread_id)
		else:
			raise ZaloUserError("Thread type is invalid")

		payload["params"] = self._encode(payload["params"])

		response = self._post(url, params=params, data=payload)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return (
				Group.fromDict(results, None)
				if thread_type == ThreadType.GROUP
				else User.fromDict(results, None)
			)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def sendMentionMessage(self, message, groupId, ttl=0):
		"""Send message to a group with mention by ID.

		Args:
			mention (str): Mention format data to send
			message (Message): Message to send
			groupId: Group ID to send to.

		Returns:
			object: `User/Group` (Returns msg ID just sent)
			dict: A dictionary containing error responses

		Raises:
			ZaloAPIException: If request failed
		"""
		params = {"zpw_ver": 645, "zpw_type": 30, "nretry": 0}

		payload = {
			"params": {
				"grid": str(groupId),
				"message": message.text,
				"mentionInfo": message.mention,
				"clientId": _util.now(),
				"visibility": 0,
				"ttl": ttl,
			}
		}

		if message.style:
			payload["params"]["textProperties"] = message.style

		payload["params"] = self._encode(payload["params"])

		response = self._post(
			"https://tt-group-wpa.chat.zalo.me/api/group/mention",
			params=params,
			data=payload,
		)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return Group.fromDict(results, None)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def undoMessage(self, msgId, cliMsgId, thread_id, thread_type):
		"""Undo message from the client by ID.

		Args:
			msgId (int | str): Message ID to undo
			cliMsgId (int | str): Client Msg ID to undo
			thread_id (int | str): User/Group ID to undo message
			thread_type (ThreadType): ThreadType.USER, ThreadType.GROUP

		Returns:
			object: `User/Group` undo message status
			dict: A dictionary containing error responses

		Raises:
			ZaloAPIException: If request failed
		"""
		params = {"zpw_ver": 645, "zpw_type": 30, "nretry": 0}

		payload = {
			"params": {
				"msgId": str(msgId),
				"cliMsgIdUndo": str(cliMsgId),
				"clientId": _util.now(),
			}
		}

		if thread_type == ThreadType.USER:
			url = "https://tt-chat3-wpa.chat.zalo.me/api/message/undo"
			payload["params"]["toid"] = str(thread_id)
		elif thread_type == ThreadType.GROUP:
			url = "https://tt-group-wpa.chat.zalo.me/api/group/undomsg"
			payload["params"]["grid"] = str(thread_id)
			payload["params"]["visibility"] = 0
			payload["params"]["imei"] = self._imei
		else:
			raise ZaloUserError("Thread type is invalid")

		payload["params"] = self._encode(payload["params"])

		response = self._post(url, params=params, data=payload)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return (
				Group.fromDict(results, None)
				if thread_type == ThreadType.GROUP
				else User.fromDict(results, None)
			)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def sendReaction(
		self, messageObject, reactionIcon, thread_id, thread_type, reactionType=75
	):
		"""Reaction message by ID.

		Args:
			messageObject (Message): Message Object to reaction
			reactionIcon (str): Icon/Text to reaction
			thread_id (int | str): Group/User ID contain message to reaction
			thread_type (ThreadType): ThreadType.USER, ThreadType.GROUP

		Returns:
			object: `User/Group` message reaction data
			dict: A dictionary containing error responses

		Raises:
			ZaloAPIException: If request failed
		"""
		params = {"zpw_ver": 645, "zpw_type": 30}

		payload = {
			"params": {
				"react_list": [
					{
						"message": json.dumps(
							{
								"rMsg": [
									{
										"gMsgID": int(messageObject.msgId),
										"cMsgID": int(messageObject.cliMsgId),
										"msgType": _util.getClientMessageType(
											messageObject.msgType
										),
									}
								],
								"rIcon": reactionIcon,
								"rType": reactionType,
								"source": 6,
							}
						),
						"clientId": _util.now(),
					}
				],
				"imei": self._imei,
			}
		}

		if thread_type == ThreadType.USER:
			url = "https://reaction.chat.zalo.me/api/message/reaction"
			payload["params"]["toid"] = str(thread_id)
		elif thread_type == ThreadType.GROUP:
			url = "https://reaction.chat.zalo.me/api/group/reaction"
			payload["params"]["grid"] = str(thread_id)
		else:
			raise ZaloUserError("Thread type is invalid")

		payload["params"] = self._encode(payload["params"])

		response = self._post(url, params=params, data=payload)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return (
				Group.fromDict(results, None)
				if thread_type == ThreadType.GROUP
				else User.fromDict(results, None)
			)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def sendMultiReaction(
		self, reactionObj, reactionIcon, thread_id, thread_type, reactionType=75
	):
		"""Reaction message by ID.

		Args:
			reactionObj (MessageReaction): Message(s) data to reaction
			reactionIcon (str): Icon/Text to reaction
			thread_id (int | str): Group/User ID contain message to reaction
			thread_type (ThreadType): ThreadType.USER, ThreadType.GROUP

		Returns:
			object: `User/Group` message reaction data
			dict: A dictionary containing error responses

		Raises:
			ZaloAPIException: If request failed
		"""
		params = {"zpw_ver": 645, "zpw_type": 30}

		payload = {
			"params": {
				"react_list": [
					{
						"message": {
							"rMsg": [],
							"rIcon": reactionIcon,
							"rType": reactionType,
							"source": 6,
						},
						"clientId": _util.now(),
					}
				],
				"imei": self._imei,
			}
		}

		if isinstance(reactionObj, dict):
			payload["params"]["react_list"][0]["message"]["rMsg"].append(reactionObj)
		elif isinstance(reactionObj, list):
			payload["params"]["react_list"][0]["message"]["rMsg"] = reactionObj
		else:
			raise ZaloUserError("Reaction type is invalid")

		if thread_type == ThreadType.USER:
			url = "https://reaction.chat.zalo.me/api/message/reaction"
			payload["params"]["toid"] = str(thread_id)
		elif thread_type == ThreadType.GROUP:
			url = "https://reaction.chat.zalo.me/api/group/reaction"
			payload["params"]["grid"] = str(thread_id)
		else:
			raise ZaloUserError("Thread type is invalid")

		payload["params"]["react_list"][0]["message"] = json.dumps(
			payload["params"]["react_list"][0]["message"]
		)
		payload["params"] = self._encode(payload["params"])

		response = self._post(url, params=params, data=payload)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return (
				Group.fromDict(results, None)
				if thread_type == ThreadType.GROUP
				else User.fromDict(results, None)
			)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def sendRemoteFile(
		self,
		fileUrl,
		thread_id,
		thread_type,
		fileName="default",
		fileSize=None,
		extension="phudev",
		ttl=0,
	):
		"""Send File to a User/Group with url.

		Args:
			fileUrl (str): File url to send
			thread_id (int | str): User/Group ID to send to.
			thread_type (ThreadType): ThreadType.USER, ThreadType.GROUP
			fileName (str): File name to send
			fileSize (int): File size to send
			extension (str): type of file to send (py, txt, mp4, ...)

		Returns:
			object: `User/Group` (Returns msg ID just sent)
			dict: A dictionary containing error responses

		Raises:
			ZaloAPIException: If request failed
		"""
		if not fileSize:
			try:
				with self._state._session.get(fileUrl) as response:
					if response.status_code == 200:
						fileSize = int(
							response.headers.get(
								"Content-Length", len(response.content)
							)
						)
					else:
						fileSize = 0

					fileChecksum = hashlib.md5(response.content).hexdigest()

			except:
				raise ZaloAPIException("Unable to get url content")

		has_extension = fileName.rsplit(".")
		extension = has_extension[-1:][0] if len(has_extension) >= 2 else extension

		params = {"zpw_ver": 645, "zpw_type": 30, "nretry": 0}

		payload = {
			"params": {
				"fileId": str(int(_util.now() * 2)),
				"checksum": fileChecksum,
				"checksumSha": "",
				"extension": extension,
				"totalSize": fileSize,
				"fileName": fileName,
				"clientId": _util.now(),
				"fType": 1,
				"fileCount": 0,
				"fdata": "{}",
				"fileUrl": fileUrl,
				"zsource": 401,
				"ttl": ttl,
			}
		}

		if thread_type == ThreadType.USER:
			url = "https://tt-files-wpa.chat.zalo.me/api/message/asyncfile/msg"
			payload["params"]["toid"] = str(thread_id)
			payload["params"]["imei"] = self._imei
		elif thread_type == ThreadType.GROUP:
			url = "https://tt-files-wpa.chat.zalo.me/api/group/asyncfile/msg"
			payload["params"]["grid"] = str(thread_id)
		else:
			raise ZaloUserError("Thread type is invalid")

		payload["params"] = self._encode(payload["params"])
		response = self._post(url, params=params, data=payload)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return (
				Group.fromDict(results, None)
				if thread_type == ThreadType.GROUP
				else User.fromDict(results, None)
			)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def sendRemoteVideo(
		self,
		videoUrl,
		thumbnailUrl,
		duration,
		thread_id,
		thread_type,
		width=1280,
		height=720,
		message=None,
		ttl=0,
	):
		"""Send (Forward) video to a User/Group with url.

		Warning:
			This is a feature created through the forward function.
			Because Zalo Web does not allow viewing videos.

		Args:
			videoUrl (str): Video link to send
			thumbnailUrl (str): Thumbnail link for video
			duration (int | str): Time for video (ms)
			thread_id (int | str): User/Group ID to send to.
			thread_type (ThreadType): ThreadType.USER, ThreadType.GROUP
			width (int): Width of the video
			height (int): Height of the video
			message (Message): Message to send with video

		Returns:
			object: `User/Group` (Returns msg ID just sent)
			dict: A dictionary containing error responses

		Raises:
			ZaloAPIException: If request failed
		"""
		try:
			with self._state._session.head(videoUrl) as response:
				if response.status_code == 200:
					fileSize = int(
						response.headers.get("Content-Length", len(response.content))
					)
				else:
					fileSize = 0

		except Exception as e:
			raise ZaloAPIException(f"Unable to get url content: {e}")

		params = {"zpw_ver": 645, "zpw_type": 30, "nretry": 0}

		payload = {
			"params": {
				"clientId": str(_util.now()),
				"ttl": ttl,
				"zsource": 704,
				"msgType": 5,
				"msgInfo": json.dumps(
					{
						"videoUrl": str(videoUrl),
						"thumbUrl": str(thumbnailUrl),
						"duration": int(duration),
						"width": int(width),
						"height": int(height),
						"fileSize": fileSize,
						"properties": {
							"color": -1,
							"size": -1,
							"type": 1003,
							"subType": 0,
							"ext": {
								"sSrcType": -1,
								"sSrcStr": "",
								"msg_warning_type": 0,
							},
						},
						"title": message.text or "" if message else "",
					}
				),
			}
		}

		if message and message.mention:
			payload["params"]["mentionInfo"] = message.mention

		if thread_type == ThreadType.USER:
			url = "https://tt-files-wpa.chat.zalo.me/api/message/forward"
			payload["params"]["toId"] = str(thread_id)
			payload["params"]["imei"] = self._imei
		elif thread_type == ThreadType.GROUP:
			url = "https://tt-files-wpa.chat.zalo.me/api/group/forward"
			payload["params"]["visibility"] = 0
			payload["params"]["grid"] = str(thread_id)
		else:
			raise ZaloUserError("Thread type is invalid")

		payload["params"] = self._encode(payload["params"])

		response = self._post(url, params=params, data=payload)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return (
				Group.fromDict(results, None)
				if thread_type == ThreadType.GROUP
				else User.fromDict(results, None)
			)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def sendRemoteVoice(self, voiceUrl, thread_id, thread_type, fileSize=None, ttl=0):
		"""Send voice by url.

		Args:
			voiceUrl (str): Voice link to send
			thread_id (int | str): User/Group ID to change status in
			thread_type (ThreadType): ThreadType.USER, ThreadType.GROUP
			fileSize (int | str): Voice content length (size) to send

		Returns:
			object: `User/Group` response

		Raises:
			ZaloAPIException: If request failed
		"""
		with self._state._session.get(voiceUrl) as response:
			if response.status_code == 200:
				fileSize = (
					fileSize
					if fileSize
					else int(
						response.headers.get("Content-Length", len(response.content))
					)
				)
			else:
				fileSize = fileSize if fileSize else 0

		params = {"zpw_ver": 645, "zpw_type": 30, "nretry": 0}

		payload = {
			"params": {
				"ttl": ttl,
				"zsource": -1,
				"msgType": 3,
				"clientId": str(_util.now()),
				"msgInfo": json.dumps(
					{
						"voiceUrl": str(voiceUrl),
						"m4aUrl": str(voiceUrl),
						"fileSize": int(fileSize),
					}
				),
			}
		}

		if thread_type == ThreadType.USER:
			url = "https://tt-files-wpa.chat.zalo.me/api/message/forward"
			payload["params"]["toId"] = str(thread_id)
			payload["params"]["imei"] = self._imei
		else:
			url = "https://tt-files-wpa.chat.zalo.me/api/group/forward"
			payload["params"]["visibility"] = 0
			payload["params"]["grid"] = str(thread_id)

		payload["params"] = self._encode(payload["params"])

		response = self._post(url, params=params, data=payload)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return (
				Group.fromDict(results, None)
				if thread_type == ThreadType.GROUP
				else User.fromDict(results, None)
			)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def sendImageByUrl(
		self,
		image_url: str | list,
		thread_id,
		thread_type,
		width=2560,
		height=2560,
		message=None,
		ttl=0,
	):
		"""Send one or more images via direct URL to a User/Group.

		Args:
			image_url (str | list): A single URL or list of image URLs
			thread_id (int | str): User or Group ID
			thread_type (ThreadType): ThreadType.USER or ThreadType.GROUP
			width (int | list): Width(s)
			height (int | list): Height(s)
			message (Message | list | None): Message(s)
			ttl (int | list): TTL(s)

		Returns:
			list: List of User or Group objects
		"""
		if isinstance(image_url, str):
			image_url = [image_url]
		if not isinstance(width, list):
			width = [width] * len(image_url)
		if not isinstance(height, list):
			height = [height] * len(image_url)
		if not isinstance(ttl, list):
			ttl = [ttl] * len(image_url)
		if not isinstance(message, list):
			message = [message] * len(image_url)

		results = []

		for i, url_image in enumerate(image_url):
			desc = message[i].text if message[i] and hasattr(message[i], "text") else ""

			params = {"zpw_ver": 645, "zpw_type": 30, "nretry": 0}

			payload = {
				"params": {
					"photoId": int(_util.now() * 2),
					"clientId": int(_util.now() - 1000),
					"desc": desc,
					"width": width[i],
					"height": height[i],
					"rawUrl": url_image,
					"thumbUrl": url_image,
					"hdUrl": url_image,
					"thumbSize": "53932",
					"fileSize": "247671",
					"hdSize": "344622",
					"zsource": -1,
					"jcp": json.dumps({"sendSource": 1, "convertible": "jxl"}),
					"ttl": ttl[i],
					"imei": self._imei,
				}
			}

			if message[i] and getattr(message[i], "mention", None):
				payload["params"]["mentionInfo"] = message[i].mention

			if thread_type == ThreadType.USER:
				url = (
					"https://tt-files-wpa.chat.zalo.me/api/message/photo_original/send"
				)
				payload["params"]["toid"] = str(thread_id)
				payload["params"]["normalUrl"] = url_image
			elif thread_type == ThreadType.GROUP:
				url = "https://tt-files-wpa.chat.zalo.me/api/group/photo_original/send"
				payload["params"]["grid"] = str(thread_id)
				payload["params"]["oriUrl"] = url_image
			else:
				raise ZaloUserError("Thread type is invalid")

			payload["params"] = self._encode(payload["params"])

			response = self._post(url, params=params, data=payload)
			data = response.json()
			data_content = data.get("data") if data.get("error_code") == 0 else None

			if data_content:
				decoded = self._decode(data_content)
				decoded = decoded.get("data") if decoded.get("data") else decoded

				if decoded is None:
					decoded = {"error_code": 1337, "error_message": "Data is None"}

				if isinstance(decoded, str):
					try:
						decoded = json.loads(decoded)
					except:
						decoded = {"error_code": 1337, "error_message": decoded}

				obj = (
					Group.fromDict(decoded, None)
					if thread_type == ThreadType.GROUP
					else User.fromDict(decoded, None)
				)
				results.append(obj)
			else:
				error_code = data.get("error_code")
				error_message = data.get("error_message") or data.get("data")
				raise ZaloAPIException(
					f"Error #{error_code} when sending image {i + 1}: {error_message}"
				)

		return results

	def sendLocalImage(
		self,
		imagePath,
		thread_id,
		thread_type,
		width=2560,
		height=2560,
		message=None,
		custom_payload=None,
		ttl=0,
	):
		"""Send Image to a User/Group with local file.

		Args:
			imagePath (str): Image directory to send
			thread_id (int | str): User/Group ID to send to.
			thread_type (ThreadType): ThreadType.USER, ThreadType.GROUP
			width (int): Image width to send
			height (int): Image height to send
			message (Message): Message to send with image

		Returns:
			object: `User/Group` objects response
			dict: A dictionary containing error responses

		Raises:
			ZaloAPIException: If request failed
		"""
		params = {"zpw_ver": 645, "zpw_type": 30, "nretry": 0}

		if custom_payload:
			if thread_type == ThreadType.USER:
				url = (
					"https://tt-files-wpa.chat.zalo.me/api/message/photo_original/send"
				)
			elif thread_type == ThreadType.GROUP:
				url = "https://tt-files-wpa.chat.zalo.me/api/group/photo_original/send"
			else:
				raise ZaloUserError("Thread type is invalid")

			payload = custom_payload

		else:
			uploadImage = self._uploadImage(imagePath, thread_id, thread_type)

			payload = {
				"params": {
					"photoId": uploadImage.get("photoId", int(_util.now() * 2)),
					"clientId": uploadImage.get(
						"clientFileId", int(_util.now() - 1000)
					),
					"desc": message.text if message else "" or "",
					"width": width,
					"height": height,
					"rawUrl": uploadImage["normalUrl"],
					"thumbUrl": uploadImage["thumbUrl"],
					"hdUrl": uploadImage["hdUrl"],
					"thumbSize": "53932",
					"fileSize": "247671",
					"hdSize": "344622",
					"zsource": -1,
					"jcp": json.dumps({"sendSource": 1, "convertible": "jxl"}),
					"ttl": ttl,
					"imei": self._imei,
				}
			}

			if message and message.mention:
				payload["params"]["mentionInfo"] = message.mention

			if thread_type == ThreadType.USER:
				url = (
					"https://tt-files-wpa.chat.zalo.me/api/message/photo_original/send"
				)
				payload["params"]["toid"] = str(thread_id)
				payload["params"]["normalUrl"] = uploadImage["normalUrl"]
			elif thread_type == ThreadType.GROUP:
				url = "https://tt-files-wpa.chat.zalo.me/api/group/photo_original/send"
				payload["params"]["grid"] = str(thread_id)
				payload["params"]["oriUrl"] = uploadImage["normalUrl"]
			else:
				raise ZaloUserError("Thread type is invalid")

		payload["params"] = self._encode(payload["params"])

		response = self._post(url, params=params, data=payload)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return (
				Group.fromDict(results, None)
				if thread_type == ThreadType.GROUP
				else User.fromDict(results, None)
			)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def sendMultiLocalImage(
		self,
		imagePathList,
		thread_id,
		thread_type,
		width=2560,
		height=2560,
		message=None,
		ttl=0,
	):
		"""Send Multiple Image to a User/Group with local file.

		Args:
			imagePathList (list): List image directory to send
			width (int): Image width to send
			height (int): Image height to send
			message (Message): Message to send with image
			thread_id (int | str): User/Group ID to send to.
			thread_type (ThreadType): ThreadType.USER, ThreadType.GROUP

		Returns:
			object: `User/Group` objects
			dict: A dictionary containing error responses

		Raises:
			ZaloAPIException: If request failed
		"""
		uploadData = []

		if not isinstance(imagePathList, list) or len(imagePathList) < 1:
			raise ZaloUserError(
				"image path must be a list to be able to send multiple at once."
			)

		groupLayoutId = str(_util.now())

		for i, imagePath in enumerate(imagePathList):
			uploadImage = self._uploadImage(imagePath, thread_id, thread_type)

			payload = {
				"params": {
					"photoId": uploadImage.get("photoId", int(_util.now() * 2)),
					"clientId": uploadImage.get(
						"clientFileId", int(_util.now() - 1000)
					),
					"desc": message.text if message else "" or "",
					"width": width,
					"height": height,
					"groupLayoutId": groupLayoutId,
					"totalItemInGroup": len(imagePathList),
					"isGroupLayout": 1,
					"idInGroup": i,
					"rawUrl": uploadImage["normalUrl"],
					"thumbUrl": uploadImage["thumbUrl"],
					"hdUrl": uploadImage["hdUrl"],
					"thumbSize": "53932",
					"fileSize": "247671",
					"hdSize": "344622",
					"zsource": -1,
					"jcp": json.dumps({"sendSource": 1, "convertible": "jxl"}),
					"ttl": ttl,
					"imei": self._imei,
				}
			}

			if message and message.mention:
				payload["params"]["mentionInfo"] = message.mention

			if thread_type == ThreadType.USER:
				payload["params"]["toid"] = str(thread_id)
				payload["params"]["normalUrl"] = uploadImage["normalUrl"]
			elif thread_type == ThreadType.GROUP:
				payload["params"]["grid"] = str(thread_id)
				payload["params"]["oriUrl"] = uploadImage["normalUrl"]
			else:
				raise ZaloUserError("Thread type is invalid")

			data = self.sendLocalImage(
				imagePath,
				thread_id,
				thread_type,
				width,
				height,
				message,
				custom_payload=payload,
			)
			uploadData.append(data.toDict())

		return (
			Group.fromDict(uploadData, None)
			if thread_type == ThreadType.GROUP
			else User.fromDict(uploadData, None)
		)

	def sendQrCode(
		self,
		content: str,
		thread_id,
		thread_type,
		background: str = None,
		width=2560,
		height=2560,
		message=None,
		ttl=0,
	):
		"""
		Generate a QR code from text or a link and send it to a user or group.

		Args:
			content (str): Text or link to encode into the QR code.
			thread_id (int | str): User ID or Group ID.
			thread_type (ThreadType): ThreadType.USER or ThreadType.GROUP.
			background (str | None): Optional image URL for QR code background.
			width (int): Image width to send.
			height (int): Image height to send.
			message (Message | None): Optional accompanying message.
			ttl (int): Time-to-live for the image (in seconds).
		"""
		params = {"link": content}
		if background:
			params["background"] = background

		response = requests.get("https://phudev.42web.io/api/qrcode.php", params=params)
		data = response.json()

		if data.get("status") != "success":
			raise ZaloAPIException(f"QR code generation failed: {data}")

		qr_url = data["url"]

		return self.sendImageByUrl(
			image_url=qr_url,
			thread_id=thread_id,
			thread_type=thread_type,
			width=width,
			height=height,
			message=message,
			ttl=ttl,
		)

	def sendLocalGif(
		self,
		gifPath,
		thumbnailUrl,
		thread_id,
		thread_type,
		gifName="phudev.gif",
		width=500,
		height=500,
		ttl=0,
	):
		"""Send Gif to a User/Group with local file.

		Args:
			gifPath (str): Gif path to send
			thumbnailUrl (str): Thumbnail of gif to send
			gifName (str): Gif name to send
			width (int): Gif width to send
			height (int): Gif height to send
			thread_id (int | str): User/Group ID to send to.
			thread_type (ThreadType): ThreadType.USER, ThreadType.GROUP

		Returns:
			object: `User/Group` objects
			dict: A dictionary containing error responses

		Raises:
			ZaloAPIException: If request failed
		"""
		if not os.path.exists(gifPath):
			raise ZaloUserError(f"{gifPath} not found")

		files = [("chunkContent", open(gifPath, "rb"))]
		gifSize = len(open(gifPath, "rb").read())
		gifName = (
			gifName
			if gifName
			else gifPath if "/" not in gifPath else gifPath.rstrip("/")[1]
		)
		fileChecksum = hashlib.md5(open(gifPath, "rb").read()).hexdigest()

		params = {
			"zpw_ver": 645,
			"zpw_type": 30,
			"type": 1,
			"params": {
				"clientId": str(_util.now()),
				"fileName": gifName,
				"totalSize": gifSize,
				"width": width,
				"height": height,
				"msg": "",
				"type": 1,
				"ttl": ttl,
				"thumb": thumbnailUrl,
				"checksum": fileChecksum,
				"totalChunk": 1,
				"chunkId": 1,
			},
		}

		if thread_type == ThreadType.USER:
			url = "https://tt-files-wpa.chat.zalo.me/api/message/gif"
			params["params"]["toid"] = str(thread_id)
		elif thread_type == ThreadType.GROUP:
			url = "https://tt-files-wpa.chat.zalo.me/api/group/gif"
			params["params"]["visibility"] = 0
			params["params"]["grid"] = str(thread_id)
		else:
			raise ZaloUserError("Thread type is invalid")

		params["params"] = self._encode(params["params"])

		response = self._post(url, params=params, files=files)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return (
				Group.fromDict(results, None)
				if thread_type == ThreadType.GROUP
				else User.fromDict(results, None)
			)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def sendSticker(
		self, stickerType, stickerId, cateId, thread_id, thread_type, ttl=0
	):
		"""Send Sticker to a User/Group.

		Args:
			stickerType (int | str): Sticker type to send
			stickerId (int | str): Sticker id to send
			cateId (int | str): Sticker category id to send
			thread_id (int | str): User/Group ID to send to.
			thread_type (ThreadType): ThreadType.USER, ThreadType.GROUP

		Returns:
			object: `User/Group` objects
			dict: A dictionary containing error responses

		Raises:
			ZaloAPIException: If request failed
		"""
		params = {"zpw_ver": 645, "zpw_type": 30, "nretry": 0}

		payload = {
			"params": {
				"stickerId": int(stickerId),
				"cateId": int(cateId),
				"type": int(stickerType),
				"clientId": _util.now(),
				"imei": self._imei,
				"ttl": ttl,
			}
		}

		if thread_type == ThreadType.USER:
			url = "https://tt-chat2-wpa.chat.zalo.me/api/message/sticker"
			payload["params"]["zsource"] = 106
			payload["params"]["toid"] = str(thread_id)
		elif thread_type == ThreadType.GROUP:
			url = "https://tt-group-wpa.chat.zalo.me/api/group/sticker"
			payload["params"]["zsource"] = 103
			payload["params"]["grid"] = str(thread_id)
		else:
			raise ZaloUserError("Thread type is invalid")

		payload["params"] = self._encode(payload["params"])

		response = self._post(url, params=params, data=payload)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return (
				Group.fromDict(results, None)
				if thread_type == ThreadType.GROUP
				else User.fromDict(results, None)
			)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def sendCustomSticker(
		self,
		staticImgUrl,
		animationImgUrl,
		thread_id,
		thread_type,
		reply=None,
		width=None,
		height=None,
		ttl=0,
	):
		"""Send custom (static/animation) sticker to a User/Group with url.

		Args:
			staticImgUrl (str): Image url (png, jpg, jpeg) format to create sticker
			animationImgUrl (str): Static/Animation image url (webp) format to create sticker
			thread_id (int | str): User/Group ID to send sticker to.
			thread_type (ThreadType): ThreadType.USER, ThreadType.GROUP
			reply (int | str): Message ID to send stickers with quote
			width (int | str): Width of photo/sticker
			height (int | str): Height of photo/sticker

		Returns:
			object: `User/Group` sticker data
			dict: A dictionary containing error responses

		Raises:
			ZaloAPIException: If request failed
		"""
		width = int(width) if width else 0
		height = int(height) if height else 0
		params = {"zpw_ver": 645, "zpw_type": 30, "nretry": 0}

		payload = {
			"params": {
				"clientId": _util.now(),
				"title": "",
				"oriUrl": staticImgUrl,
				"thumbUrl": staticImgUrl,
				"hdUrl": staticImgUrl,
				"width": width,
				"height": height,
				"properties": json.dumps(
					{
						"subType": 0,
						"color": -1,
						"size": -1,
						"type": 3,
						"ext": json.dumps({"sSrcStr": "@STICKER", "sSrcType": 0}),
					}
				),
				"contentId": _util.now(),
				"thumb_height": width,
				"thumb_width": height,
				"webp": json.dumps(
					{"width": width, "height": height, "url": animationImgUrl}
				),
				"zsource": -1,
				"ttl": ttl,
			}
		}

		if reply:
			payload["params"]["refMessage"] = str(reply)

		if thread_type == ThreadType.USER:
			url = "https://tt-files-wpa.chat.zalo.me/api/message/photo_url"
			payload["params"]["toId"] = str(thread_id)
		elif thread_type == ThreadType.GROUP:
			url = "https://tt-files-wpa.chat.zalo.me/api/group/photo_url"
			payload["params"]["visibility"] = 0
			payload["params"]["grid"] = str(thread_id)
		else:
			raise ZaloUserError("Thread type is invalid")

		payload["params"] = self._encode(payload["params"])

		response = self._post(url, params=params, data=payload)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return (
				Group.fromDict(results, None)
				if thread_type == ThreadType.GROUP
				else User.fromDict(results, None)
			)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def sendLink(
		self,
		linkUrl,
		title,
		thread_id,
		thread_type,
		thumbnailUrl=None,
		domainUrl=None,
		description=None,
		message=None,
		ttl=0,
	):
		"""Send link to a User/Group with url.

		Args:
			linkUrl (str): Link url to send
			domainUrl (str): Main domain of Link to send (eg: github.com)
			thread_id (int | str): User/Group ID to send link to
			thread_type (ThreadType): ThreadType.USER, ThreadType.GROUP
			thumbnailUrl (str): Thumbnail link url for card to send
			title (str): Title for card to send
			description (str): Description for card to send
			message (Message): Message object to send with the link

		Returns:
			object: `User/Group` message id response
			dict: A dictionary containing error responses

		Raises:
			ZaloAPIException: If request failed
		"""
		params = {"zpw_ver": 645, "zpw_type": 30}

		payload = {
			"params": {
				"msg": message.text if message else "" or "",
				"href": linkUrl,
				"src": domainUrl or "",
				"title": str(title),
				"desc": description or "",
				"thumb": thumbnailUrl or "",
				"type": 0,
				"media": json.dumps(
					{
						"type": 0,
						"count": 0,
						"mediaTitle": "",
						"artist": "",
						"streamUrl": "",
						"stream_icon": "",
					}
				),
				"ttl": ttl,
				"clientId": _util.now(),
			}
		}

		if message and message.mention:
			payload["params"]["mentionInfo"] = message.mention

		if thread_type == ThreadType.USER:
			url = "https://tt-chat4-wpa.chat.zalo.me/api/message/link"
			payload["params"]["toid"] = str(thread_id)
		elif thread_type == ThreadType.GROUP:
			url = "https://tt-group-wpa.chat.zalo.me/api/group/sendlink"
			payload["params"]["imei"] = self._imei
			payload["params"]["grid"] = str(thread_id)
		else:
			raise ZaloUserError("Thread type is invalid")

		payload["params"] = self._encode(payload["params"])

		response = self._post(url, params=params, data=payload)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return (
				Group.fromDict(results, None)
				if thread_type == ThreadType.GROUP
				else User.fromDict(results, None)
			)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def parseLink(self, link: str) -> dict:
		"""
		Parse a product or webpage link.
		Args:
			link (str): The link to parse (e.g. Zalo catalog link).
		Returns:
			dict: Parsed metadata from the link.
		"""
		url = "https://tt-files-wpa.chat.zalo.me/api/message/parselink"
		params = {"zpw_ver": 665, "zpw_type": 30}
		payload = {
			"link": link,
			"version": 1,
			"imei": self._imei,
		}

		result = self._post(url, params, payload)
		if result.get("error_code") == 0:
			return result.get("data")
		raise Exception(
			f"Parse link failed: #{result.get('error_code')} - {result.get('error_message')}"
		)

	def sendReport(self, user_id, reason=0, content=None):
		"""Send report to Zalo.

		Args:
			reason (int): Reason for reporting
				1 = Nội dung nhạy cảm
				2 = Làm phiền
				3 = Lừa đảo
				0 = custom
			content (str): Report content (work if reason = custom)
			user_id (int | str): User ID to report

		Returns:
			object: `User` send report response

		Raises:
			ZaloAPIException: If request failed
		"""
		params = {"zpw_ver": 645, "zpw_type": 30}

		payload = {"params": {"idTo": str(user_id), "objId": "person.profile"}}

		content = (
			content
			if content and not reason
			else "" if not content and not reason else ""
		)
		if content:
			payload["params"]["content"] = content

		payload["params"]["reason"] = str(
			random.randint(1, 3) if not content else reason
		)
		payload["params"] = self._encode(payload["params"])

		response = self._post(
			"https://tt-profile-wpa.chat.zalo.me/api/report/abuse-v2",
			params=params,
			data=payload,
		)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return (
				Group.fromDict(results, None)
				if thread_type == ThreadType.GROUP
				else User.fromDict(results, None)
			)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def sendBusinessCard(
		self, userId, qrCodeUrl, thread_id, thread_type, phone=None, ttl=0
	):
		"""Send business card by user ID.

		Args:
			userId (int | str): Business card user ID
			qrCodeUrl (str): QR Code link with business card profile information
			phone (int | str): Send business card with phone number
			thread_id (int | str): User/Group ID to change status in
			thread_type (ThreadType): ThreadType.USER, ThreadType.GROUP

		Returns:
			object: `User/Group` send business card response

		Raises:
			ZaloAPIException: If request failed
		"""
		params = {"zpw_ver": 645, "zpw_type": 30, "nretry": 0}

		payload = {
			"params": {
				"ttl": ttl,
				"msgType": 6,
				"clientId": str(_util.now()),
				"msgInfo": {"contactUid": str(userId), "qrCodeUrl": str(qrCodeUrl)},
			}
		}

		if phone:
			payload["params"]["msgInfo"]["phone"] = str(phone)

		if thread_type == ThreadType.USER:
			url = "https://tt-files-wpa.chat.zalo.me/api/message/forward"
			payload["params"]["toId"] = str(thread_id)
			payload["params"]["imei"] = self._imei
		else:
			url = "https://tt-files-wpa.chat.zalo.me/api/group/forward"
			payload["params"]["visibility"] = 0
			payload["params"]["grid"] = str(thread_id)

		payload["params"]["msgInfo"] = json.dumps(payload["params"]["msgInfo"])
		payload["params"] = self._encode(payload["params"])

		response = self._post(url, params=params, data=payload)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			results = results.get("data") if results.get("data") else results
			if results == None:
				results = {"error_code": 1337, "error_message": "Data is None"}

			if isinstance(results, str):
				try:
					results = json.loads(results)
				except:
					results = {"error_code": 1337, "error_message": results}

			return (
				Group.fromDict(results, None)
				if thread_type == ThreadType.GROUP
				else User.fromDict(results, None)
			)

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	"""
	END SEND METHODS
	"""

	def setTyping(self, thread_id, thread_type):
		"""Set users typing status.

		Args:
			thread_id: User/Group ID to change status in.
			thread_type (ThreadType): ThreadType.USER, ThreadType.GROUP

		Raises:
			ZaloAPIException: If request failed
		"""
		params = {"zpw_ver": 645, "zpw_type": 30}

		payload = {"params": {"imei": self._imei}}

		if thread_type == ThreadType.USER:
			url = "https://tt-chat1-wpa.chat.zalo.me/api/message/typing"
			payload["params"]["toid"] = str(thread_id)
			payload["params"]["destType"] = 3
		elif thread_type == ThreadType.GROUP:
			url = "https://tt-group-wpa.chat.zalo.me/api/group/typing"
			payload["params"]["grid"] = str(thread_id)
		else:
			raise ZaloUserError("Thread type is invalid")

		payload["params"] = self._encode(payload["params"])

		response = self._post(url, params=params, data=payload)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			results = self._decode(results)
			return True

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def markAsDelivered(
		self,
		msgId,
		cliMsgId,
		senderId,
		thread_id,
		thread_type,
		seen=0,
		method="webchat",
	):
		"""Mark a message as delivered.

		Args:
			cliMsgId (int | str): Client message ID
			msgId (int | str): Message ID to set as delivered
			senderId (int | str): Message sender Id
			thread_id (int | str): User/Group ID to mark as delivered
			thread_type (ThreadType): ThreadType.USER, ThreadType.GROUP

		Returns:
			bool: True

		Raises:
			ZaloAPIException: If request failed
		"""
		destination_id = "0" if thread_type == ThreadType.USER else thread_id

		params = {"zpw_ver": 645, "zpw_type": 30}

		payload = {
			"params": {
				"msgInfos": {
					"seen": 0,
					"data": [
						{
							"cmi": str(cliMsgId),
							"gmi": str(msgId),
							"si": str(senderId),
							"di": str(destination_id),
							"mt": method,
							"st": 3,
							"at": 0,
							"ts": str(_util.now()),
						}
					],
				}
			}
		}

		if thread_type == ThreadType.USER:
			url = "https://tt-chat3-wpa.chat.zalo.me/api/message/deliveredv2"
			payload["params"]["msgInfos"]["data"][0]["cmd"] = 501
		else:
			url = "https://tt-group-wpa.chat.zalo.me/api/group/deliveredv2"
			payload["params"]["msgInfos"]["data"][0]["cmd"] = 521
			payload["params"]["msgInfos"]["grid"] = str(destination_id)
			payload["params"]["imei"] = self._imei

		payload["params"]["msgInfos"] = json.dumps(payload["params"]["msgInfos"])
		payload["params"] = self._encode(payload["params"])

		response = self._post(url, params=params, data=payload)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			self.onMessageDelivered(
				msg_ids=msgId,
				thread_id=thread_id,
				thread_type=thread_type,
				ts=_util.now(),
			)
			return True

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	def markAsRead(
		self, msgId, cliMsgId, senderId, thread_id, thread_type, method="webchat"
	):
		"""Mark a message as read.

		Args:
			cliMsgId (int | str): Client message ID
			msgId (int | str): Message ID to set as delivered
			senderId (int | str): Message sender Id
			thread_id (int | str): User/Group ID to mark as read
			thread_type (ThreadType): ThreadType.USER, ThreadType.GROUP

		Returns:
			bool: True

		Raises:
			ZaloAPIException: If request failed
		"""
		destination_id = "0" if thread_type == ThreadType.USER else thread_id

		params = {"zpw_ver": 645, "zpw_type": 30, "nretry": 0}

		payload = {
			"params": {
				"msgInfos": {
					"data": [
						{
							"cmi": str(cliMsgId),
							"gmi": str(msgId),
							"si": str(senderId),
							"di": str(destination_id),
							"mt": method,
							"st": 3,
							"ts": str(_util.now()),
						}
					]
				},
				"imei": self._imei,
			}
		}

		if thread_type == ThreadType.USER:
			url = "https://tt-chat1-wpa.chat.zalo.me/api/message/seenv2"
			payload["params"]["msgInfos"]["data"][0]["at"] = 7
			payload["params"]["msgInfos"]["data"][0]["cmd"] = 501
			payload["params"]["senderId"] = str(destination_id)
		elif thread_type == ThreadType.GROUP:
			url = "https://tt-group-wpa.chat.zalo.me/api/group/seenv2"
			payload["params"]["msgInfos"]["data"][0]["at"] = 0
			payload["params"]["msgInfos"]["data"][0]["cmd"] = 511
			payload["params"]["grid"] = str(destination_id)
		else:
			raise ZaloUserError("Thread type is invalid")

		payload["params"]["msgInfos"] = json.dumps(payload["params"]["msgInfos"])
		payload["params"] = self._encode(payload["params"])

		response = self._post(url, params=params, data=payload)
		data = response.json()
		results = data.get("data") if data.get("error_code") == 0 else None
		if results:
			self.onMarkedSeen(
				msg_ids=msgId,
				thread_id=thread_id,
				thread_type=thread_type,
				ts=_util.now(),
			)
			return True

		error_code = data.get("error_code")
		error_message = data.get("error_message") or data.get("data")
		raise ZaloAPIException(
			f"Error #{error_code} when sending requests: {error_message}"
		)

	"""
	LISTEN METHODS
	"""

	def _listen_req(self, delay=0, thread=False, reconnect=5):
		self._condition.clear()
		HasRead = set()

		try:
			self.onListening()
			self._listening = True

			while not self._condition.is_set():
				ListenTime = int((time.time() - 10) * 1000)

				if len(HasRead) > 10000000:
					HasRead.clear()

				messages = self.getLastMsgs()
				groupmsg = messages.groupMsgs
				messages = messages.msgs

				for message in messages + groupmsg:
					if (
						int(message["ts"]) >= ListenTime
						and message["msgId"] not in HasRead
					):
						HasRead.add(message["msgId"])
						msgObj = MessageObject.fromDict(message, None)
						if message in messages:

							[
								(
									pool.submit(
										self.onMessage,
										msgObj.msgId,
										str(int(msgObj.uidFrom) or self.uid),
										msgObj.content,
										msgObj,
										str(int(msgObj.uidFrom) or msgObj.idTo),
										ThreadType.USER,
									)
									if thread
									else self.onMessage(
										msgObj.msgId,
										str(int(msgObj.uidFrom) or self.uid),
										msgObj.content,
										msgObj,
										str(int(msgObj.uidFrom) or msgObj.idTo),
										ThreadType.USER,
									)
								)
							]

						else:

							[
								(
									pool.submit(
										self.onMessage,
										msgObj.msgId,
										str(int(msgObj.uidFrom) or self.uid),
										msgObj.content,
										msgObj,
										str(int(msgObj.idTo) or self.uid),
										ThreadType.GROUP,
									)
									if thread
									else self.onMessage(
										msgObj.msgId,
										str(int(msgObj.uidFrom) or self.uid),
										msgObj.content,
										msgObj,
										str(int(msgObj.idTo) or self.uid),
										ThreadType.GROUP,
									)
								)
							]

				time.sleep(delay)

		except KeyboardInterrupt:
			self._condition.set()
			print("\x1b[1K")
			logger.warning("Stop Listen Because KeyboardInterrupt Exception!")
			pid = os.getpid()
			os.kill(pid, signal.SIGTERM)

		except Exception as e:
			self._condition.set()
			self._listening = False
			self.onErrorCallBack(e)
			if self.run_forever:
				while not self._listening:
					try:
						logger.debug(
							"Run forever mode is enabled, trying to reconnect..."
						)
						self._listen_req(delay, thread, reconnect)
					except:
						pass

					time.sleep(reconnect)

		finally:
			self._listening = False

	def _fix_recv(self):
		old_timestamp = int(time.time())
		time.sleep(50 * 60)
		self._start_fix = True
		self._condition.set()

	def _listen_ws(self, thread=False, reconnect=5):
		self._condition.clear()
		params = {"zpw_ver": 645, "zpw_type": 30, "t": _util.now()}
		url = self._state._config["zpw_ws"][0] + "?" + urllib.parse.urlencode(params)

		user_agent = (
			self._state._headers.get("User-Agent") or _util.HEADERS["User-Agent"]
		)
		raw_cookies = _util.dict_to_raw_cookies(self._state.get_cookies())

		if not raw_cookies:
			raise ZaloUserError(
				"Unable to load cookies! Probably due to incorrect cookie format (cookies must be dict)"
			)

		headers = {
			"Accept-Encoding": "gzip, deflate, br, zstd",
			"Accept-Language": "en-US,en;q=0.9",
			"Cache-Control": "no-cache",
			"Connection": "Upgrade",
			"Host": urllib.parse.urlparse(url).netloc,
			"Origin": "https://chat.zalo.me",
			"Pargma": "no-cache",
			"Sec-Websocket-Extensions": "permessage-deflate; client_max_window_bits",
			"Sec-Websocket-Version": "13",
			"Upgrade": "websocket",
			"User-Agent": user_agent,
			"Cookie": raw_cookies,
		}

		with connect(url, additional_headers=headers) as ws:
			pool.submit(self._fix_recv)
			self.onListening()
			self._listening = True
			while not self._condition.is_set():
				try:
					data = ws.recv()
					if not isinstance(data, bytes):
						continue

					encodedHeader = data[:4]
					n, cmd, s = _util.getHeader(encodedHeader)

					dataToDecode = data[4:]
					decodedData = dataToDecode.decode("utf-8")
					if not decodedData:
						continue

					parsed = json.loads(decodedData)
					if n == 1 and cmd == 1 and s == 1 and "key" in parsed:
						self.ws_key = parsed["key"]
						continue

					if not hasattr(self, "ws_key"):
						logger.error("Unable to decrypt data because key not found")
						continue

					parsedData = _util.zws_decode(parsed, self.ws_key)
					if n == 1 and cmd == 3000 and s == 0:
						logger.warning("Another connection is opened, closing this one")
						ws.close()

					elif n == 1 and cmd == 501 and s == 0:
						parsedData = _util.zws_decode(parsed, self.ws_key)
						userMsgs = parsedData["data"]["msgs"]

						for message in userMsgs:
							msgObj = MessageObject.fromDict(message, None)
							[
								(
									pool.submit(
										self.onMessage,
										msgObj.msgId,
										str(int(msgObj.uidFrom) or self.uid),
										msgObj.content,
										msgObj,
										str(int(msgObj.uidFrom) or msgObj.idTo),
										ThreadType.USER,
									)
									if thread
									else self.onMessage(
										msgObj.msgId,
										str(int(msgObj.uidFrom) or self.uid),
										msgObj.content,
										msgObj,
										str(int(msgObj.uidFrom) or msgObj.idTo),
										ThreadType.USER,
									)
								)
							]

					elif n == 1 and cmd == 521 and s == 0:
						groupMsgs = parsedData["data"]["groupMsgs"]

						try:
							for message in groupMsgs:
								messages = self.getRecentGroup(message["idTo"])[
									"groupMsgs"
								]
								message = next(
									(
										msg
										for msg in messages
										if msg["msgId"] == message["msgId"]
									),
									message,
								)
						except:
							pass

						msgObj = MessageObject.fromDict(message, None)
						[
							(
								pool.submit(
									self.onMessage,
									msgObj.msgId,
									str(int(msgObj.uidFrom) or self.uid),
									msgObj.content,
									msgObj,
									str(int(msgObj.idTo) or self.uid),
									ThreadType.GROUP,
								)
								if thread
								else self.onMessage(
									msgObj.msgId,
									str(int(msgObj.uidFrom) or self.uid),
									msgObj.content,
									msgObj,
									str(int(msgObj.idTo) or self.uid),
									ThreadType.GROUP,
								)
							)
						]

					elif n == 1 and cmd in [502, 522, 504, 524] and s == 0:
						# Delivereds, Seen, Clear Unread, ...
						continue

					elif n == 1 and cmd == 602 and s == 0:
						# Typing Event
						continue

					elif n == 1 and cmd == 601 and s == 0:
						controls = parsedData["data"].get("controls", [])
						for control in controls:
							if control["content"]["act_type"] == "group":

								if control["content"]["act"] == "join_reject":
									continue

								groupEventData = (
									json.loads(control["content"]["data"])
									if isinstance(control["content"]["data"], str)
									else control["content"]["data"]
								)
								groupEventType = _util.getGroupEventType(
									control["content"]["act"]
								)
								event_data = EventObject.fromDict(groupEventData)
								event_type = groupEventType
								[
									(
										pool.submit(
											self.onEvent, event_data, event_type
										)
										if thread
										else self.onEvent(event_data, event_type)
									)
								]

						continue

					elif cmd == 612:
						reacts = parsedData["data"].get("reacts", [])
						reactGroups = parsedData["data"].get("reactGroups", [])

						for react in reacts:
							react["content"] = json.loads(react["content"])
							msgObj = MessageObject.fromDict(react, None)
							[
								(
									pool.submit(
										self.onMessage,
										msgObj.msgId,
										str(int(msgObj.uidFrom) or self.uid),
										msgObj.content,
										msgObj,
										str(int(msgObj.uidFrom) or msgObj.idTo),
										ThreadType.USER,
									)
									if thread
									else self.onMessage(
										msgObj.msgId,
										str(int(msgObj.uidFrom) or self.uid),
										msgObj.content,
										msgObj,
										str(int(msgObj.uidFrom) or msgObj.idTo),
										ThreadType.USER,
									)
								)
							]

						for reactGroup in reactGroups:
							reactGroup["content"] = json.loads(reactGroup["content"])
							msgObj = MessageObject.fromDict(reactGroup, None)
							[
								(
									pool.submit(
										self.onMessage,
										msgObj.msgId,
										str(int(msgObj.uidFrom) or self.uid),
										msgObj.content,
										msgObj,
										str(int(msgObj.idTo) or self.uid),
										ThreadType.GROUP,
									)
									if thread
									else self.onMessage(
										msgObj.msgId,
										str(int(msgObj.uidFrom) or self.uid),
										msgObj.content,
										msgObj,
										str(int(msgObj.idTo) or self.uid),
										ThreadType.GROUP,
									)
								)
							]

					else:
						continue

				except KeyboardInterrupt:
					self._condition.set()
					ws.close()
					print("\x1b[1K")
					logger.warning("Stop Listen Because KeyboardInterrupt Exception!")
					pid = os.getpid()
					os.kill(pid, signal.SIGTERM)

				except (
					websockets.ConnectionClosedOK,
					websockets.exceptions.ConnectionClosedOK,
				):
					self._condition.set()
					ws.close()
					break

				except (
					websockets.ConnectionClosedError,
					websockets.exceptions.ConnectionClosedError,
				):
					self._start_fix = True
					self._condition.set()
					ws.close()

				except Exception as e:
					if (
						str(e)
						== "sent 1000 (OK); then received 1000 (OK) NORMAL_CLOSURE"
					):
						pass

					else:
						self._listening = False
						self._start_fix = False
						self._condition.set()
						ws.close()
						self.onErrorCallBack(e)
						if self.run_forever:
							while not self._listening:
								try:
									logger.debug(
										"Run forever mode is enabled, trying to reconnect..."
									)
									self._listen_ws(thread, reconnect)
								except:
									pass

								time.sleep(reconnect)

				finally:
					self._listening = False

		if self._start_fix:
			logger.debug("Reconnecting websocket because of interruption...")
			self._start_fix = False
			self._listen_ws(thread, reconnect)

	def startListening(self, delay=0, thread=False, type="websocket", reconnect=5):
		"""Start listening from an external event loop.

		Args:
			delay (int): Delay time each time fetching a message
			thread (bool): Handle messages within the thread (Default: False)
			type (str): Type of listening (Default: websocket)
			reconnect (int): Delay interval when reconnecting

		Raises:
			ZaloAPIException: If request failed
		"""
		if str(type).lower() == "websocket":

			if self._state._config.get("zpw_ws"):
				self._listen_ws(thread, reconnect)

			else:
				logger.debug(
					"WebSocket url not found. Listen will switch to `requests` mode"
				)
				self._listen_req(delay, thread)

		elif str(type).lower() == "requests":
			self._listen_req(delay, thread)

		else:
			raise ZaloUserError("Invalid listen type, only `websocket` or `requests`")

	def stopListening(self):
		"""Stop the listening loop."""
		self.listening = False
		self._condition.set()

	def listen(
		self, delay=0, thread=False, type="websocket", run_forever=False, reconnect=5
	):
		"""Initialize and runs the listening loop continually.

		Args:
			delay (int): Delay time for each message fetch (Default: 1)
			thread (bool): Handle messages within the thread (Default: False)
			type (str): Type of listening (Default: websocket)
			reconnect (int): Delay interval when reconnecting
		"""
		self.run_forever = run_forever
		self.startListening(delay, thread, type, reconnect)

	"""
	END LISTEN METHODS
	"""

	"""
	EVENTS
	"""

	def onLoggingIn(self, phone=None):
		"""Called when the client is logging in.

		Args:
			phone: The phone number of the client
		"""
		logger.debug("Logging in {}...".format(phone))

	def onLoggedIn(self, phone=None):
		"""Called when the client is successfully logged in.

		Args:
			phone: The phone number of the client
		"""
		logger.login("Login of {} successful.".format(phone))

	def onListening(self):
		"""Called when the client is listening."""
		logger.debug("Listening...")

	def onMessage(
		self,
		mid=None,
		author_id=None,
		message=None,
		message_object=None,
		thread_id=None,
		thread_type=ThreadType.USER,
	):
		"""Called when the client is listening, and somebody sends a message.

		Args:
			mid: The message ID
			author_id: The ID of the author
			message: The message content of the author
			message_object: The message (As a `Message` object)
			thread_id: Thread ID that the message was sent to.
			thread_type (ThreadType): Type of thread that the message was sent to.
		"""
		logger.info("{} from {} in {}".format(message, thread_id, thread_type.name))

	def onEvent(self, event_data, event_type):
		"""Called when the client listening, and some events occurred.

		Args:
			event_data (EventObject): Event data (As a `EventObject` object)
			event_type (EventType/GroupEventType): Event Type
		"""

	def onMessageDelivered(
		self, msg_ids=None, thread_id=None, thread_type=ThreadType.USER, ts=None
	):
		"""Called when the client is listening, and the client has successfully marked messages as delivered.

		Args:
			msg_ids: The messages that are marked as delivered
			thread_id: Thread ID that the action was sent to
			thread_type (ThreadType): Type of thread that the action was sent to
			ts: A timestamp of the action
		"""
		logger.info(
			"Marked messages {} as delivered in [({}, {})] at {}.".format(
				msg_ids, thread_id, thread_type.name, int(ts / 1000)
			)
		)

	def onMarkedSeen(
		self, msg_ids=None, thread_id=None, thread_type=ThreadType.USER, ts=None
	):
		"""Called when the client is listening, and the client has successfully marked messages as read/seen.

		Args:
			msg_ids: The messages that are marked as read/seen
			thread_id: Thread ID that the action was sent to
			thread_type (ThreadType): Type of thread that the action was sent to
			ts: A timestamp of the action
		"""
		logger.info(
			"Marked messages {} as seen in [({}, {})] at {}.".format(
				msg_ids, thread_id, thread_type.name, int(ts / 1000)
			)
		)

	def onErrorCallBack(self, error, ts=int(time.time())):
		"""Called when the module has some error.

		Args:
			error: Description of the error
			ts: A timestamp of the error (Default: auto)
		"""
		logger.error(f"An error occurred at {ts}: {error}")
		print(traceback.format_exc())

	"""
	END EVENTS
	"""
