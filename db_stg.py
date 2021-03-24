import json
from os import stat_result
import sqlite3
from datetime import datetime
from time import strftime


class Stg(object):

	def __init__(self):
		super().__init__()
		self.conn = None

	def get_connection(self):
		if self.conn is None:
			self.conn = sqlite3.connect('yt_server.db')
			self.init_tables()
		return self.conn

	def init_tables(self):
		query = '''SELECT count(*) FROM sqlite_master WHERE type='table' AND name=:table_name;'''
		cur = self.get_connection().execute(query, {'table_name': 'downloads'})
		results = cur.fetchone()
		if results[0] == 0:
			cur.execute('''create table downloads(
				queued_time text, 
				run_time text, 
				done_time text,
				url text, 
				title text,
				ytld_opts_json text,
				filename text,
				filesize integer,
				log text)''')
		cur.close()

	def enqueue(self, url, ytdl_opts):
		conn = self.get_connection()
		ytdl_opts_json = json.dumps(ytdl_opts)
		sql = ''' insert into downloads(queued_time, url, ytld_opts_json) values(:qtime, :url, :ytdl_opts_json)'''
		cur = conn.execute(sql, {'qtime': self._now_str(), 'url': url, 'ytdl_opts_json': ytdl_opts_json})
		conn.commit()
		cur.close()
		return cur.lastrowid

	def get_start_info(self, stg_id):
		conn = self.get_connection()
		sql = ''' select url, ytld_opts_json from downloads where rowid = :stg_id ;'''
		cur = conn.execute(sql, {'stg_id': stg_id})
		info_rec = cur.fetchone()
		if info_rec is None:
			raise Exception("No row found for "+stg_id)
		conn.commit()
		cur.close()
		(url, opts_json) = info_rec
		opts = json.loads(opts_json)
		return (url, opts)

	def start_run(self, stg_id, dl_thrd):
		run_time = self._now_str()
		dl_thrd.run_time = run_time # Save for later (rendering)
		conn = self.get_connection()
		sql = ''' update downloads set run_time = :rtime, title = :title where rowid = :stg_id;'''
		cur = conn.execute(sql, {'rtime': run_time, 'stg_id': stg_id, 'title': dl_thrd.title})
		if cur.rowcount != 1:
			raise Exception("No row found for "+stg_id)
		conn.commit()
		cur.close()
	
	def done(self, stg_id, log, filename, filesize):
		conn = self.get_connection()
		sql = ''' update downloads set 
			done_time = :dtime,
			log = :log,
			filename = :filename,
			filesize = :filesize
			where rowid = :stg_id '''
		parms = {'dtime': self._now_str(), 'stg_id': stg_id, 'log': log, 'filename': filename, 'filesize': filesize}
		cur = conn.execute(sql, parms)
		if cur.rowcount != 1:
			raise Exception("No row found for "+stg_id)
		conn.commit()
		cur.close()

	def get_queued(self):
		conn = self.get_connection()
		sql = ''' select rowid from downloads where run_time is null and done_time is null
				order by rowid '''
		cur = conn.execute(sql)
		queued = cur.fetchall()
		cur.close()
		return [r[0] for r in queued]
	
	def get_queued_status(self):
		keys = ['rowid', 'queued_time', 'url']
		sql = 'select '+', '.join(keys)+' from downloads where queued_time is not null and run_time is null and done_time is null order by rowid'
		conn = self.get_connection()
		cur = conn.execute(sql)
		recs = cur.fetchall()
		cur.close()
		status = self._make_dict(keys, recs)
		return status

	def get_running(self):
		conn = self.get_connection()
		sql = ''' select rowid from downloads where run_time is not null and done_time is null
				order by rowid '''
		cur = conn.execute(sql)
		running = cur.fetchall()
		return [r[0] for r in running]

	def get_done(self):
		conn = self.get_connection()
		sql = ''' select rowid from downloads where done_time is not null
				order by rowid '''
		cur = conn.execute(sql)
		done = cur.fetchall()
		return [r[0] for r in done]

	def get_done_status(self, max_rows):
		keys = ['rowid', 'done_time', 'url', 'title', 'filename', 'filesize']
		sql = 'select '+', '.join(keys)+' from downloads where done_time is not null order by rowid desc'
		if max_rows >= 0:
			sql += ' limit '+str(max_rows)
		conn = self.get_connection()
		cur = conn.execute(sql)
		recs = cur.fetchall()
		cur.close()
		status = self._make_dict(keys, recs)
		return status

	def _make_dict(self, keys, recs):
		status = []
		for row in recs:
			row_dict = {}
			for i in range(len(keys)):
				row_dict[keys[i]] = row[i]
			status.append(row_dict)
		return status

	def get_log(self, rowid):
		conn = self.get_connection()
		sql = ''' select log from downloads where rowid == :rowid '''
		cur = conn.execute(sql, {'rowid': rowid})
		rec = cur.fetchone()
		return rec[0]

	def _now_str(self):
		now = datetime.now()
		return now.strftime("%m/%d/%y %H:%M:%S")

	def clean(self):
		'''
		  Clean up the database
		'''
		conn = self.get_connection()
		sql = ''' update downloads set run_time = null, log = null where run_time is not null and done_time is null ; '''
		cur = conn.execute(sql)
		conn.commit()
		cur.close()

	def clear_queued(self):
		conn = self.get_connection()
		sql = ''' delete from downloads where queued_time is not null and run_time is null ; '''
		cur = conn.execute(sql)
		conn.commit()
		cur.close()
		return cur.rowcount

	def clear_done(self):
		conn = self.get_connection()
		sql = ''' delete from downloads where done_time is not null ; '''
		cur = conn.execute(sql)
		conn.commit()
		cur.close()
		return cur.rowcount

	def delete_rec(self, id):
		conn = self.get_connection()
		sql = ''' delete from downloads where rowid = :rowid ; '''
		cur = conn.execute(sql, {'rowid': id})
		conn.commit()
		cur.close()
		return cur.rowcount

		
def _test():
	x = Stg()
	running = x.get_running()
	done = x.get_done()
	r1 = x.enqueue('my url1', {'opt1': 'xxx'})
	r2 = x.enqueue('my url2', {'opt1': 'xxx'})
	r3 = x.enqueue('my url3', {'opt1': 'xxx'})
	r4 = x.enqueue('my url4', {'opt1': 'xxx'})
	queued = x.get_queued_status();
	(url, opts) = x.get_start_info(r2)
	x.start_run(r3, 'title 1')
	queued2 = x.get_queued();
	z = x.clear_queued()
	print("Done")

if __name__ == "__main__":
	_test()
