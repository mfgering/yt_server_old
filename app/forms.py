from pathlib import Path
from flask_wtf import FlaskForm
from wtforms import FormField, FieldList, IntegerField, StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, NumberRange, URL, ValidationError

class LoginForm(FlaskForm):
	username = StringField('Username', validators=[DataRequired()])
	password = PasswordField('Password', validators=[DataRequired()])
	remember_me = BooleanField('Remember Me')
	submit = SubmitField('Sign In')

class DownloadForm(FlaskForm):
	url = StringField('URL', validators=[DataRequired(message='URL is needed'), URL(message="Invalid URL")])
	dl_dir = StringField('Download directory', validators=[DataRequired(message='A directory name is needed')])
	dl_patt = StringField('Download pattern', validators=[DataRequired(message='A pattern is needed')])
	x_audio = BooleanField("Audio only")
	use_proxy = BooleanField("Use proxy")
	max_dl = IntegerField("Max concurrent downloads", validators=[NumberRange(min=1, message="Must be at least 1")])
	submit = SubmitField('Submit')

	@staticmethod
	def validate_dl_dir(form, field):
		path1 = Path(field.data)
		if path1.is_file():
			raise ValidationError("Should be a directory, not a file.")
		if path1.is_dir():
			#TODO: Can write file in the directory?
			return
		try:
			path1.mkdir(parents=True, exist_ok=False)
		except Exception as exc:
			raise ValidationError("Could not create the directory: "+str(exc))

class SettingsForm(FlaskForm):
	dl_dir = StringField('Download directory', validators=[DataRequired(message='A directory name is needed')])
	dl_patt = StringField('Download pattern', validators=[DataRequired(message='A pattern is needed')])
	proxy_url = StringField('Proxy URL')
	max_dl = IntegerField("Max concurrent downloads", validators=[NumberRange(min=1, message="Must be at least 1")])
	restart = BooleanField("Restart server")
	update = BooleanField("Update server")
	max_done = IntegerField("Max number of 'done' records for status")
	submit = SubmitField('Submit')

	@staticmethod
	def validate_dl_dir(form, field):
		path1 = Path(field.data)
		if path1.is_file():
			raise ValidationError("Should be a directory, not a file.")
		if path1.is_dir():
			#TODO: Can write file in the directory?
			return
		try:
			path1.mkdir(parents=True, exist_ok=False)
		except Exception as exc:
			raise ValidationError("Could not create the directory: "+str(exc))

class MaintDownloadedRowForm(FlaskForm):
#['Id', 'Done', 'URL', 'Title', 'Filename', 'Total Bytes', 'Log'],
#        ['rowid', 'done_time', 'url', 'title', 'filename', 'filesize', 'log']
	selected = BooleanField("Selected")
	rowid = IntegerField("ID")
	done_time = StringField("Done")
	url = StringField("URL")
	title = StringField("Title")
	filename = StringField("Filename")
	filesize = StringField("Total Bytes")

class MaintDownloadedForm(FlaskForm):

	max_maint_done = IntegerField("Number of rows")
	recs = FieldList(FormField(MaintDownloadedRowForm))
	submit = SubmitField('Delete')
