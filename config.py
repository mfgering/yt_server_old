import os
import local_settings

class Config(object):
	_instance = None

	SECRET_KEY = os.environ.get("SECRET_KEY") or "sske89822Jl..234BBB--=SSS298234"
	MAX_CONCURRENT_DL = 5
	TEMPLATES_AUTO_RELOAD = False
	DEFAULT_DOWNLOAD_DIR = None
	DEFAULT_DOWNLOAD_NAME_PATTERN = '%(title)s.%(ext)s'
	FFMPEG_LOCATION = None
	RESTRICT_FILENAMES = False
	MAX_DONE = 50
	PROXY_URL = "socks5://192.168.1.13:1080"

	def __init__(self):
		raise RuntimeError('Call instance() instead')

	@classmethod
	def instance(cls):
		if cls._instance is None:
			cls._instance = cls.__new__(cls)
			# Put any additional initialization here
			#TODO: How to init instance vars for all the above class 
			members = [attr for attr in dir(cls) if not callable(getattr(cls, attr)) and not attr.startswith("__")]
			for member in members:
				setattr(cls._instance, member, getattr(cls, member))
		return cls._instance

_local_members = [attr for attr in dir(local_settings) if not callable(getattr(local_settings, attr)) and not attr.startswith("__")]
for local_member in _local_members:
	setattr(Config, local_member, getattr(local_settings, local_member))
