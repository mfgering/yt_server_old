import os
import app
import datetime
import psutil
import sys
import jinja2.utils
import jinja2.filters
import youtube_dl
from wtforms import IntegerField, StringField, PasswordField, BooleanField, SubmitField
from flask import render_template, flash, redirect, request, session
import config, downloader
from app import app
from app.forms import LoginForm, DownloadForm, SettingsForm, MaintDownloadedForm
from subprocess import Popen, PIPE
from os import path
import db_stg

@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@app.route('/download', methods=['GET', 'POST'])
def download():
	if request.method == 'GET':
		form = DownloadForm(dl_dir=session.get('dl_dir', config.Config.instance().DEFAULT_DOWNLOAD_DIR),
							dl_patt=session.get('dl_patt', config.Config.instance().DEFAULT_DOWNLOAD_NAME_PATTERN),
							x_audio=session.get('x_audio', False),
							max_dl=session.get('max_dl', config.Config.instance().MAX_CONCURRENT_DL),
							use_proxy=session.get('use_proxy', True))
	else:
		form = DownloadForm(request.form)
	if form.validate_on_submit():
		session['dl_dir'] = form.dl_dir.data
		session['dl_patt'] = form.dl_patt.data
		session['x_audio'] = form.x_audio.data
		session['max_dl'] = form.max_dl.data
		session['use_proxy'] = form.use_proxy.data
		msg = downloader.Downloader.submit_download(form)
		if msg is not None:
			flash(msg)
		return redirect('/download')
	if len(form.errors) > 0:
		flash("Please fix the problems and try again.")
	return render_template('download.html', title='Download', form=form)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
	t = datetime.datetime.utcnow() - app.start_time
	hours, remainder = divmod(t.seconds, 3600)
	minutes, seconds = divmod(remainder, 60)
	uptime_str = '%s hours, %s minutes, %s seconds' % (hours, minutes, seconds)
	if request.method == 'GET':
		form = SettingsForm(dl_dir=session.get('dl_dir', config.Config.instance().DEFAULT_DOWNLOAD_DIR),
							dl_patt=session.get('dl_patt', config.Config.instance().DEFAULT_DOWNLOAD_NAME_PATTERN),
							x_audio=session.get('x_audio', False),
							max_dl=session.get('max_dl', config.Config.instance().MAX_CONCURRENT_DL),
							max_done=session.get('max_done', config.Config.instance().MAX_DONE),
							proxy_url=session.get('proxy_url', config.Config.instance().PROXY_URL)
							)
	else:
		form = SettingsForm(request.form)
	if form.validate_on_submit():
		cfg = config.Config.instance()
		cfg.DEFAULT_DOWNLOAD_DIR = session['dl_dir'] = form.dl_dir.data
		cfg.DEFAULT_DOWNLOAD_NAME_PATTERN = session['dl_patt'] = form.dl_patt.data
		cfg.MAX_CONCURRENT_DL = session['max_dl'] = form.max_dl.data
		cfg.MAX_DONE = session['max_done'] = form.max_done.data
		cfg.PROXY_URL = session['proxy_url'] = form.proxy_url.data
		msg = submit_settings(form)
		if msg is not None:
			flash(msg)
		return redirect('/settings')
	if len(form.errors) > 0:
		flash("Please fix the problems and try again.")
	
	return render_template('settings.html', title='Settings', form=form, uptime=uptime_str,
		yt_version=youtube_dl.youtube_dl.version.__version__)

def submit_settings(form):
	msg = None
	if form.update.data:
		update_server()
		if not form.restart.data:
			flash("**** You must restart the server to reload code updates.")
	if form.restart.data:
		restart_server()
	return msg

def update_server():
	flash("Updating the server")
	msg = None
	git_command = ['git', 'pull', '--recurse-submodules']
	do_proc(git_command)
	git_command = ['git', 'submodule', 'update', '--remote', '--recursive']
	do_proc(git_command)
	flash("Done updating the server")
	return msg

def do_proc(cmd):
	out_str = ''
	err_str = ''
	try:
		flash(" ".join(cmd))
		p = Popen(cmd, cwd=os.getcwd(), stdout=PIPE, stderr=PIPE)
		(out, err) = p.communicate()
		if p.poll() == 0:
			out_str = out.decode(sys.stdout.encoding)
			err_str = err.decode(sys.stdout.encoding)
		else:
			err_str = "Bad poll() result"
	except Exception as exc:
		err_str = "Exception: "+str(exc)
	if len(out_str) > 0:
		flash(f"Output: {out_str}")
	if len(err_str) > 0:
		flash(f"Error: {err_str}")
	return (out_str, err_str)

def restart_server():
	for proc in psutil.process_iter():
		try:
			print(" ".join(proc.cmdline()))
			for parm in proc.cmdline():
				if "gunicorn" in parm:
					proc.kill()
					break
		except Exception:
			pass

@app.route('/login', methods=['GET', 'POST'])
def login():
	form = LoginForm()
	if form.validate_on_submit():
		flash('Login requested for user {}, remember_me={}'.format(
			form.username.data, form.remember_me.data))
		return redirect('/index')
	return render_template('login.html', title='Sign In', form=form)

@app.route('/status', methods=['GET'])
def status():
	context = {}
	context["queued"] = _get_queued_context()
	context["running"] = _get_running_context()
	context['done'] = _get_done_context()
	context['config'] = config.Config.instance()
	return render_template("status.html", title="Status", context=context)

@app.route('/clear/<arr_name>', methods=['GET'])
def clear_array(arr_name):
	if arr_name == "queued":
		deleted = db_stg.Stg().clear_queued()
		flash(f"Deleted {deleted} queued entries")
	if arr_name == "done":
		deleted = db_stg.Stg().clear_done()
		flash(f"Deleted {deleted} done entries")
	return redirect('/status')

@app.route('/log/thread/<thread_id>', methods=['GET'])
def get_log(thread_id):
	context = {'thread_id': thread_id, 'log': 'Nothing logged'}
	for thrd in downloader.Downloader.Running:
		if str(thrd.ident) == thread_id:
			context['log'] = thrd.get_log()
			break
	return render_template("log.html", title="Log", context=context)

@app.route('/log/stg/<rowid>', methods=['GET'])
def get_log_stg(rowid):
	log_str = db_stg.Stg().get_log(rowid)
	if log_str == None:
		log_str = 'Nothing logged'
	context = {'rowid': rowid, 'log': log_str}
	return render_template("log.html", title="Log", context=context)

@app.route('/maint/downloaded', methods=['GET', 'POST'])
def maint_downloaded():
	done_recs = db_stg.Stg().get_done_status(session.get('max_maint_done', 100))
	if request.method == 'GET':
		form = MaintDownloadedForm(max_maint_done=session.get('max_maint_done', 100), recs=done_recs)
	else:
		form = MaintDownloadedForm(request.form, recs=done_recs)
	if form.validate_on_submit():
		session['max_maint_done'] = form.max_maint_done.data
		msg = submit_maint_downloads(form)
		if msg is not None:
			flash(msg)
		return redirect('/maint/downloaded')
	if len(form.errors) > 0:
		flash("Please fix the problems and try again.")
	return render_template('maint-downloaded.html', title='Maintain Downloaded Records', form=form, done_recs=done_recs)

def submit_maint_downloads(form):
	msg = None
	cnt = 0
	stg = db_stg.Stg()
	for rec in form.recs.entries:
		if rec.selected.data:
			cnt += 1
			rowid = rec.rowid.data
			deleted = stg.delete_rec(rowid)
			if deleted != 1:
				msg = 'Could not delete '+str(rowid)
				return msg
	msg = 'Deleted '+str(cnt)
	return msg

def _get_queued_context():
	stg = db_stg.Stg()
	ctx = stg.get_queued_status()
	for row in ctx:
		if 'url' in ctx:
			row['url'] = '<a href="'+row['url']+'" target="_blank">'+row['url']+'</a>'
	return ctx

def _get_done_context():
	stg = db_stg.Stg()
	ctx = stg.get_done_status(config.Config.instance().MAX_DONE)
	for row in ctx:
		if 'url' in row:
			url = row['url']
			row['url'] = '<a href="'+url+'" target="_blank">'+url+"</a>"
		log_str = '<a href="/log/stg/'+str(row['rowid'])+'" target="_blank">Log</a>'
		if 'filesize' in row:
			if row['filesize'] is None:
				row['filesize'] = ''
		row['log'] = log_str
	return ctx

def _get_running_context():
	ctx = []
	for thrd in downloader.Downloader.Running:
		j_data = {"url": jinja2.utils.urlize(thrd.url, target="_blank")}
		j_data['thread_id'] = thrd.ident
		j_data['rowid'] = thrd.stg_id
		j_data['run_time'] = thrd.run_time
		j_data['log'] = '<a href="/log/thread/{}" target="_blank">Log</a>'.format(thrd.ident)
		if thrd.progress is not None:
			j_data['ETA'] = thrd.progress.get('_eta_str', '')
			j_data['Percent'] = thrd.progress.get('_percent_str', '')
			j_data['Status'] = thrd.progress.get('status', '')
			j_data['Filename'] = thrd.progress.get('filename', '')
			j_data['Total Bytes'] = jinja2.filters.do_filesizeformat(thrd.progress.get('total_bytes', '0'))
			j_data['Speed'] = thrd.progress.get('_speed_str', '')
			j_data['title'] = thrd.title
		ctx.append(j_data)
	return ctx

def _get_thread_status(items):
	"""
	{'_eta_str': '02:47:10', '_percent_str': '  0.0%', '_speed_str': '155.37KiB/s', 
	'_total_bytes_estimate_str': '34.80MiB', 'downloaded_bytes': 1024, 
	'elapsed': 0.2814369201660156, 'eta': 10030, 'filename': '//alpha.dawson/test...ation.mp4', 
	'fragment_count': 101, 'fragment_index': 0, 'speed': 159096.43265668987, 'status': 
	'downloading', 'tmpfilename': '//alpha.dawson/test....mp4.part', 
	'total_bytes_estimate': 36494936.0}
	"""
	result_data = []
	for thrd in items:
		j_data = {"URL": jinja2.utils.urlize(thrd.url, target="_blank")}
		j_data['thread_id'] = thrd.ident
		j_data['Log'] = '<a href="/log/{}" target="_blank">Log</a>'.format(thrd.ident)
		if thrd.progress is not None:
			j_data['ETA'] = thrd.progress.get('_eta_str', '')
			j_data['Percent'] = thrd.progress.get('_percent_str', '')
			j_data['Status'] = thrd.progress.get('status', '')
			j_data['Filename'] = thrd.progress.get('filename', '')
			j_data['Total Bytes'] = jinja2.filters.do_filesizeformat(thrd.progress.get('total_bytes', '0'))
			j_data['Speed'] = thrd.progress.get('_speed_str', '')
		result_data.append(j_data)
	return result_data
