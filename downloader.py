import os, sys
from config import Config
from io import StringIO
import logging
from threading import Thread
import youtube_dl.youtube_dl.YoutubeDL
import db_stg

class Downloader(object):
	Running = []

	@classmethod
	def submit_download(cls, form):
		ytdl_opts = {}
		dl_dir = os.path.normpath(form.dl_dir.data)
		dl_patt = form.dl_patt.data
		ytdl_opts['outtmpl'] = os.path.join(dl_dir, dl_patt)
		ytdl_opts['ffmpeg_location'] = Config.instance().FFMPEG_LOCATION
		ytdl_opts['restrictfilenames'] = Config.instance().RESTRICT_FILENAMES
		ytdl_opts['no-cache-dir'] = True
		ytdl_opts['no-playlist'] = True
		#ytdl_opts['verbose'] = True
		if form.x_audio.data:
			ytdl_opts['postprocessors'] = [{
				'key': 'FFmpegExtractAudio',
				'preferredcodec': 'mp3',
				'preferredquality': '192',
			}]
			#ytdl_opts["extractaudio"] = True
			#ytdl_opts["audioformat"] = "best"
		if form.use_proxy.data:
			proxy_url = Config.instance().PROXY_URL.strip()
			if proxy_url is not None and len(proxy_url) > 0:
				ytdl_opts['proxy'] = Config.instance().PROXY_URL
			else:
				msg = "No proxy URL is configured"
				return msg
		url = form.url.data
		Config.instance().MAX_CONCURRENT_DL = form.max_dl.data
		stg = db_stg.Stg()
		stg.enqueue(url, ytdl_opts)
		Downloader.run_next_queued()
		msg = "Download submitted"
		return msg
	
	@classmethod
	def thread_callback(cls, thread, data=None):
		filename = None
		filesize = None
		if thread.progress is not None:
			filename = thread.progress.get('filename', None)
			try:
				filesize = os.stat(filename).st_size
			except:
				filesize = -1
				pass
		db_stg.Stg().done(thread.stg_id, thread.get_log(), filename, filesize)
		Downloader.Running.remove(thread)
		Downloader.run_next_queued()

	@classmethod
	def run_next_queued(cls):
		stg = db_stg.Stg()
		queued = stg.get_queued()
		running = stg.get_running()
		to_run = len(queued)
		if Config.instance().MAX_CONCURRENT_DL >= 0:
			to_run = min(len(queued), Config.instance().MAX_CONCURRENT_DL - len(running))
		for x in range(to_run):
			id = queued[x]
			(url, opts) = stg.get_start_info(id)
			dl_thread = DownloadThread(opts, url, Downloader.thread_callback, id)
			stg.start_run(id, dl_thread)
			Downloader.Running.append(dl_thread)
			dl_thread.start()		

class DownloadThread(Thread):
	def __init__(self, ytdl_opts, url, callback, stg_id):
		super().__init__()
		self.stg_id = stg_id
		self.callback = callback
		self.url = url
		self.log = ""
		self.ytdl = None
		self.title = None
		self.exception = None
		self.progress = None
		self.logger = logging.getLogger(self.getName())
		self.log_stream = StringIO()
		handler = logging.StreamHandler(stream=self.log_stream)
		self.logger.addHandler(handler)
		self.logger.setLevel(logging.DEBUG)
		opts = ytdl_opts.copy()
		opts['logger'] = self.logger
		self.dump_dl_opts(opts)
		ytdl = youtube_dl.youtube_dl.YoutubeDL(opts)
		try:
			info = ytdl.extract_info(url, download=False)
			if 'title' in info:
				self.title = info['title']
			ytdl.add_progress_hook(self.progress_callback)
			self.ytdl = ytdl
		except Exception as exc:
			self.exception = exc
			print(str(exc))

	def get_logger(self):
		return self.logger

	def run(self):
		if self.ytdl is not None:
			try:
				self.ytdl.download([self.url])
			except Exception as exc:
				print(str(exc))
		self.log = self.log_stream.getvalue()
		self.log_stream.close()
		self.callback(thread=self, data={})

	def progress_callback(self, data):
		assert(data is not None)
		self.progress = data

	def get_log(self):
		if len(self.log) == 0:
			self.log = self.log_stream.getvalue()
		return self.log

	def dump_dl_opts(self, opts):
		opt_str = StringIO()
		opt_str.write("Options:\n")
		for k in sorted(opts.keys()):
			opt_str.write(f"    {k}: {str(opts[k])}\n")
		self.logger.info(str(opt_str.getvalue()))
		opt_str.close()
